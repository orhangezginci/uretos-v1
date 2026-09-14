"""
gateway-api

First REST-facing entry point into uretOS. External clients (physical
connector boxes, later possibly other clients) call this HTTP API instead
of ever touching RabbitMQ directly - this service is the only thing that
translates REST calls into internal CloudEvent commands.

Endpoint:
  POST /v1/connector-boxes/pair
    body: {"hardware_id": "..."}
    -> publishes uretos.connectorbox.command.pair, waits for the
       resulting event, returns it as an HTTP response.
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
    Same fire-a-command / listen-on-a-temp-queue pattern used by the
    admin panel - not true RabbitMQ RPC (no reply-to), just a temporary
    exclusive queue bound to the two possible outcome routing keys.
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


@app.route("/healthz", methods=["GET"])
def healthz():
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)