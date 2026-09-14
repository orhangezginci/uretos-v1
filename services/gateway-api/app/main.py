"""
gateway-api

First REST-facing entry point into uretOS. External clients (physical
connector boxes, the admin panel, later possibly other clients) call this
HTTP API instead of ever touching RabbitMQ directly - this service is the
only thing that translates REST calls into internal CloudEvent commands
and queries.

Endpoints:
  POST /v1/connector-boxes/pair
  POST /v1/connector-boxes
  GET  /v1/connector-boxes
  POST /v1/tenants
  GET  /v1/tenants
  GET  /healthz
"""
from __future__ import annotations

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone

import pika
from flask import Flask, jsonify, request

from cloudevents import build_envelope

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("gateway-api")

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://uretos:uretos_dev_pass@rabbitmq:5672/")
EXCHANGE = "uretos.events"
SOURCE = "uretos/services/gateway-api"
TIMEOUT_SECONDS = int(os.environ.get("GATEWAY_RPC_TIMEOUT_SECONDS", "20"))

app = Flask(__name__)


def publish_command_and_wait(command_type: str, data: dict, success_type: str, failure_type: str):
    """
    Fire a command, listen on a temporary exclusive queue bound to the two
    possible outcome routing keys. Not true RabbitMQ RPC (no reply-to) -
    used for commands, which have distinct success/failure event types.
    """
    correlation_id = str(uuid.uuid4())
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()
    channel.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)

    result = channel.queue_declare(queue="", exclusive=True)
    listen_queue = result.method.queue
    for routing_key in (success_type, failure_type):
        channel.queue_bind(queue=listen_queue, exchange=EXCHANGE, routing_key=routing_key)

    envelope_out = build_envelope(
        event_type=command_type,
        source=SOURCE,
        data=data,
        tenant_id="system",
        messagetype="command",
        correlation_id=correlation_id,
    )
    channel.basic_publish(
        exchange=EXCHANGE,
        routing_key=command_type,
        body=json.dumps(envelope_out).encode("utf-8"),
        properties=pika.BasicProperties(content_type="application/json"),
    )

    deadline = time.monotonic() + TIMEOUT_SECONDS
    envelope_in = None
    while time.monotonic() < deadline:
        method, properties, body = channel.basic_get(queue=listen_queue, auto_ack=True)
        if body is None:
            time.sleep(0.2)
            continue
        candidate = json.loads(body)
        if candidate.get("correlationid") == correlation_id:
            envelope_in = candidate
            break

    connection.close()
    return envelope_in


def query_rpc(query_type: str, data: dict):
    """
    True RabbitMQ RPC via Direct-Reply-To, for query-services that only
    ever answer with a single '<query_type>.result' event type - no
    separate failure routing key exists for reads.
    """
    correlation_id = str(uuid.uuid4())
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()
    channel.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)

    envelope_out = build_envelope(
        event_type=query_type,
        source=SOURCE,
        data=data,
        tenant_id="system",
        messagetype="query",
        correlation_id=correlation_id,
    )

    result_holder = {}

    def on_response(ch, method, properties, body):
        if properties.correlation_id == correlation_id:
            result_holder["envelope"] = json.loads(body)
            ch.stop_consuming()

    channel.basic_consume(queue="amq.rabbitmq.reply-to", on_message_callback=on_response, auto_ack=True)
    channel.basic_publish(
        exchange=EXCHANGE,
        routing_key=query_type,
        properties=pika.BasicProperties(
            reply_to="amq.rabbitmq.reply-to",
            correlation_id=correlation_id,
            content_type="application/json",
        ),
        body=json.dumps(envelope_out).encode("utf-8"),
    )

    connection.process_data_events(time_limit=TIMEOUT_SECONDS)
    connection.close()

    return result_holder.get("envelope")


@app.route("/v1/connector-boxes/pair", methods=["POST"])
def pair_connector_box():
    payload = request.get_json(silent=True) or {}
    hardware_id = payload.get("hardware_id")

    if not hardware_id:
        return jsonify({"error": "hardware_id is required"}), 400

    log.info("Pairing request for hardware_id=%s", hardware_id)
    envelope = publish_command_and_wait(
        "uretos.connectorbox.command.pair",
        {"hardware_id": hardware_id},
        "uretos.connectorbox.event.paired",
        "uretos.connectorbox.event.pairing_failed",
    )

    if envelope is None:
        return jsonify({"error": "Timed out waiting for pairing result"}), 504

    if envelope["type"] == "uretos.connectorbox.event.paired":
        return jsonify(envelope["data"]), 200

    # NOTE: kept simple for now - all failure reasons map to 400.
    # Distinguishing "unknown hardware_id" (404) from "already paired" (409)
    # by parsing the reason string would be more correct but more brittle;
    # revisit once the gateway has more than one consumer of this response.
    return jsonify({"error": envelope["data"].get("reason", "Pairing failed")}), 400


@app.route("/v1/connector-boxes", methods=["POST"])
def create_connector_box():
    payload = request.get_json(silent=True) or {}
    tenant_id = payload.get("tenant_id")
    hardware_id = payload.get("hardware_id")
    mac_address = payload.get("mac_address")

    if not tenant_id or not hardware_id or not mac_address:
        return jsonify({"error": "tenant_id, hardware_id, and mac_address are required"}), 400

    log.info("Connector box creation request for tenant_id=%s, hardware_id=%s", tenant_id, hardware_id)
    envelope = publish_command_and_wait(
        "uretos.connectorbox.command.create",
        {"tenant_id": tenant_id, "hardware_id": hardware_id, "mac_address": mac_address},
        "uretos.connectorbox.event.created",
        "uretos.connectorbox.event.creation_failed",
    )

    if envelope is None:
        return jsonify({"error": "Timed out waiting for creation result"}), 504

    if envelope["type"] == "uretos.connectorbox.event.created":
        return jsonify(envelope["data"]), 201

    return jsonify({"error": envelope["data"].get("reason", "Creation failed")}), 400


@app.route("/v1/connector-boxes", methods=["GET"])
def list_connector_boxes():
    envelope = query_rpc("uretos.connectorbox.query.list", {})
    if envelope is None:
        return jsonify({"error": "Timed out waiting for query result"}), 504
    return jsonify(envelope["data"]["connector_boxes"]), 200


@app.route("/v1/tenants", methods=["POST"])
def create_tenant():
    payload = request.get_json(silent=True) or {}
    tenant_id = payload.get("tenant_id")

    if not tenant_id:
        return jsonify({"error": "tenant_id is required"}), 400

    log.info("Tenant creation request for tenant_id=%s", tenant_id)
    envelope = publish_command_and_wait(
        "uretos.tenant.command.create",
        {"tenant_id": tenant_id},
        "uretos.tenant.event.provisioned",
        "uretos.tenant.event.provisioning_failed",
    )

    if envelope is None:
        return jsonify({"error": "Timed out waiting for provisioning result"}), 504

    if envelope["type"] == "uretos.tenant.event.provisioned":
        return jsonify(envelope["data"]), 201

    return jsonify({"error": envelope["data"].get("reason", "Provisioning failed")}), 400


@app.route("/v1/tenants", methods=["GET"])
def list_tenants():
    envelope = query_rpc("uretos.tenant.query.list", {})
    if envelope is None:
        return jsonify({"error": "Timed out waiting for query result"}), 504
    return jsonify(envelope["data"]["tenants"]), 200


@app.route("/healthz", methods=["GET"])
def healthz():
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)