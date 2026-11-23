"""
gateway-api

First REST-facing entry point into uretOS. External clients (physical
connector boxes, the admin panel, later possibly other clients) call this
HTTP API instead of ever touching RabbitMQ directly - this service is the
only thing that translates REST calls into internal CloudEvent commands
and queries.

Endpoints:
  POST /v1/tenants
  GET  /v1/tenants
  POST /v1/connector-boxes
  GET  /v1/connector-boxes
  POST /v1/connector-boxes/pair
  POST /v1/connector-boxes/handshake
  POST /v1/connector-boxes/autoscan
  POST /v1/connector-boxes/discovered
  GET  /v1/connector-boxes/<hardware_id>/machines
  GET  /v1/machines?tenant_id=<tenant_id>
  GET  /healthz

Machines live in the per-tenant database, so machine queries always carry a
tenant_id: for a box it is resolved from the box itself, for the tenant-wide
list it is a required query parameter (until authentication provides it).
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
TIMEOUT_SECONDS = int(os.environ.get("GATEWAY_RPC_TIMEOUT_SECONDS", "60"))

# In-Memory-State für aktive Box-Status (kann für Multi-Worker ggf. in Redis/DB gespiegelt werden, reicht für Single-Instance/Edge aber aus)
BOX_STATUS_STORE = {}

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


def machine_query_error_response(data: dict):
    """Maps the error_code of a machine query result to an HTTP response."""
    status = {
        "tenant_required": 400,
        "box_id_required": 400,
        "tenant_not_found": 404,
    }.get(data.get("error_code"), 500)
    return jsonify({"error": data.get("error", "Machine query failed")}), status


def public_tenant_view(provisioned_data: dict) -> dict:
    """
    What an external client may learn about a freshly provisioned tenant.

    The provisioned event also carries infrastructure credentials (Postgres and
    RabbitMQ passwords). Those are meant for tenant-command-service only (tenant
    registry in system-postgres) and must never leave the platform. Whitelist
    instead of blacklist: new fields in the event stay private by default.
    """
    return {"tenant_id": provisioned_data.get("tenant_id"), "status": "provisioned"}


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


@app.route("/v1/machines", methods=["GET"])
def list_all_machines():
    # Machines live in the per-tenant database -> a tenant is always required.
    # Until authentication provides it, it is passed as a query parameter.
    tenant_id = request.args.get("tenant_id")
    if not tenant_id:
        return jsonify({"error": "tenant_id query parameter is required"}), 400

    envelope = query_rpc("uretos.machine.query.list", {"tenant_id": tenant_id})
    if envelope is None:
        return jsonify({"error": "Timed out waiting for query result"}), 504

    data = envelope.get("data", {})
    if data.get("error_code"):
        return machine_query_error_response(data)
    return jsonify(data.get("machines", [])), 200


@app.route("/v1/connector-boxes/<hardware_id>/machines", methods=["GET"])
def list_machines_by_hardware_id(hardware_id: str):
    # The box (system-postgres) is the authoritative source for box_id AND tenant_id.
    box_env = query_rpc("uretos.connectorbox.query.by_hardware_id", {"hardware_id": hardware_id})
    if box_env is None:
        return jsonify({"error": "Timed out waiting for query result"}), 504

    box = box_env.get("data", {}).get("connector_box")
    if not box:
        return jsonify({"error": "Connector box not found"}), 404

    envelope = query_rpc(
        "uretos.machine.query.by_box",
        {"box_id": box["box_id"], "tenant_id": box["tenant_id"]},
    )
    if envelope is None:
        return jsonify({"error": "Timed out waiting for query result"}), 504

    data = envelope.get("data", {})
    if data.get("error_code"):
        return machine_query_error_response(data)
    return jsonify(data.get("machines", [])), 200


@app.route("/v1/connector-boxes/autoscan", methods=["POST"])
def register_autoscan_machines():
    payload = request.get_json(silent=True) or {}
    hardware_id = payload.get("hardware_id")
    machines = payload.get("machines", [])

    if not hardware_id:
        return jsonify({"error": "hardware_id is required"}), 400

    # Pairing-Status selbst prüfen statt sich auf Handshake-vor-Autoscan beim Aufrufer zu verlassen
    box_env = query_rpc("uretos.connectorbox.query.by_hardware_id", {"hardware_id": hardware_id})
    if box_env is None:
        return jsonify({"error": "Timed out waiting for query result"}), 504

    box = box_env.get("data", {}).get("connector_box")
    if not box:
        return jsonify({"error": "Connector box not found"}), 404

    if box.get("status") != "paired":
        return jsonify({"error": "Box is not paired yet", "status": box.get("status")}), 403

    log.info("Autoscan registration request for hardware_id=%s, machines_count=%d", hardware_id, len(machines))

    envelope = publish_command_and_wait(
        "uretos.machine.command.register",
        {"hardware_id": hardware_id, "machines": machines},
        "uretos.machine.event.registered",
        "uretos.machine.event.registration_failed",
    )

    if envelope is None:
        return jsonify({"error": "Timed out waiting for machine registration result"}), 504

    if envelope["type"] == "uretos.machine.event.registered":
        return jsonify(envelope["data"]), 200

    reason = envelope["data"].get("reason", "Machine registration failed")
    error_code = envelope["data"].get("error_code")
    # Rule violations are conflicts (409) with a machine readable code; everything else stays 400.
    status = 409 if error_code in ("machine_taken", "box_limit_reached") else 400
    return jsonify({"error": reason, "error_code": error_code}), status

@app.route("/v1/connector-boxes/handshake", methods=["POST"])
def connector_box_handshake():
    data = request.get_json(silent=True) or {}
    hardware_id = data.get("hardware_id")

    if not hardware_id:
        return jsonify({"error": "hardware_id is required"}), 400

    # Gezielter RPC-Query an den Query-Service
    envelope = query_rpc("uretos.connectorbox.query.by_hardware_id", {"hardware_id": hardware_id})
    if envelope is None:
        return jsonify({"error": "Timed out waiting for query result"}), 504

    box = envelope.get("data", {}).get("connector_box")

    if not box:
        return jsonify({"error": "Box not found, initial pairing required", "status": "pending_pairing"}), 404

    if box.get("status") != "paired":
        return jsonify({"error": "Box is not paired yet", "status": box.get("status")}), 403

    # Lizenzkontingent und Status auslesen (Hardware-Hrtlimit max. 5, bei Zahlungsverzug/Sperre 0)
    raw_max_machines = box.get("max_machines", 5)
    license_status = box.get("license_status", "active")

    if license_status in ("suspended", "overdue", "revoked"):
        max_machines = 0
    else:
        max_machines = min(int(raw_max_machines), 5)

    log.info("Handshake successful for box: %s (max_machines=%d, status=%s)", hardware_id, max_machines, license_status)
    return jsonify({
        "status": "ok",
        "box_id": box.get("box_id"),
        "tenant_id": box.get("tenant_id"),
        "licensing": {
            "max_machines": max_machines,
            "status": license_status
        },
        "message": "Handshake accepted. Proceed with autoscan."
    }), 200
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
        return jsonify(public_tenant_view(envelope["data"])), 201

    return jsonify({"error": envelope["data"].get("reason", "Provisioning failed")}), 400


@app.route("/v1/tenants", methods=["GET"])
def list_tenants():
    envelope = query_rpc("uretos.tenant.query.list", {})
    if envelope is None:
        return jsonify({"error": "Timed out waiting for query result"}), 504
    return jsonify(envelope["data"]["tenants"]), 200

@app.route("/v1/machines/<machine_id>/status", methods=["PATCH"])
def update_machine_status(machine_id: str):
    payload = request.get_json(silent=True) or {}
    status = payload.get("status")  # "ok", "warning", "error"
    error_code = payload.get("error_code")
    tenant_id = payload.get("tenant_id")

    if not status or not tenant_id:
        return jsonify({"error": "status and tenant_id are required"}), 400

    if status not in ("ok", "warning", "error"):
        return jsonify({"error": "Invalid status value. Must be 'ok', 'warning', or 'error'"}), 400

    log.info("Status update request for machine_id=%s, status=%s", machine_id, status)

    # CloudEvent für den Statuswechsel erzeugen und über RabbitMQ publizieren
    envelope_out = build_envelope(
        event_type="uretos.machine.event.status_changed",
        source=SOURCE,
        data={
            "machine_id": machine_id,
            "tenant_id": tenant_id,
            "status": status,
            "error_code": error_code,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        tenant_id=tenant_id,
        messagetype="event",
    )

    try:
        connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
        channel = connection.channel()
        channel.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)
        channel.basic_publish(
            exchange=EXCHANGE,
            routing_key="uretos.machine.event.status_changed",
            body=json.dumps(envelope_out).encode("utf-8"),
            properties=pika.BasicProperties(content_type="application/json"),
        )
        connection.close()
    except Exception as exc:
        log.error("Failed to publish machine status event: %s", exc)
        return jsonify({"error": "Internal broker error"}), 500

    return jsonify({"success": True, "machine_id": machine_id, "status": status}), 200
    
DISCOVERED_STATES = ("assigned", "limit", "rejected")
DISCOVERED_MAX_MACHINES = 500
DISCOVERED_FIELDS = ("uid", "name", "manufacturer", "model", "serial_number", "endpoint_url", "product_instance_uri")


def publish_event(event_type: str, data: dict, tenant_id: str) -> None:
    """Fire-and-forget: publishes a CloudEvent, no reply expected."""
    envelope_out = build_envelope(
        event_type=event_type, source=SOURCE, data=data, tenant_id=tenant_id, messagetype="event",
    )
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    try:
        channel = connection.channel()
        channel.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)
        channel.basic_publish(
            exchange=EXCHANGE,
            routing_key=event_type,
            body=json.dumps(envelope_out).encode("utf-8"),
            properties=pika.BasicProperties(content_type="application/json"),
        )
    finally:
        connection.close()


@app.route("/v1/connector-boxes/discovered", methods=["POST"])
def report_discovered_machines():
    """
    A box reports EVERYTHING it currently sees on its network - including machines
    it could not take over (box limit reached, claimed by another box). This is a
    snapshot (observation), not a registration: it never changes assignments.

    Published as event `uretos.connectorbox.event.machines_discovered`; consumers
    upsert by (tenant_id, uid) and may treat machines missing from a later snapshot
    of the same box as "not seen anymore". Fire-and-forget on purpose: while no
    consumer exists the event is simply dropped by the topic exchange, the box
    never waits for it.
    """
    payload = request.get_json(silent=True) or {}
    hardware_id = payload.get("hardware_id")
    machines = payload.get("machines")

    if not hardware_id:
        return jsonify({"error": "hardware_id is required"}), 400
    if not isinstance(machines, list) or len(machines) > DISCOVERED_MAX_MACHINES:
        return jsonify({"error": f"machines must be a list with at most {DISCOVERED_MAX_MACHINES} entries"}), 400

    # Whitelist fields: whatever else a client sends never reaches the event bus.
    clean = []
    for i, m in enumerate(machines):
        if not isinstance(m, dict) or not m.get("uid"):
            return jsonify({"error": f"machines[{i}].uid is required"}), 400
        if m.get("state") not in DISCOVERED_STATES:
            return jsonify({"error": f"machines[{i}].state must be one of {list(DISCOVERED_STATES)}"}), 400
        entry = {k: m.get(k) for k in DISCOVERED_FIELDS}
        entry["state"] = m["state"]
        entry["reason"] = str(m.get("reason") or "")[:300]
        clean.append(entry)

    box_env = query_rpc("uretos.connectorbox.query.by_hardware_id", {"hardware_id": hardware_id})
    if box_env is None:
        return jsonify({"error": "Timed out waiting for query result"}), 504
    box = box_env.get("data", {}).get("connector_box")
    if not box:
        return jsonify({"error": "Connector box not found"}), 404
    if box.get("status") != "paired":
        return jsonify({"error": "Box is not paired yet", "status": box.get("status")}), 403

    try:
        publish_event(
            "uretos.connectorbox.event.machines_discovered",
            {
                "hardware_id": hardware_id,
                "box_id": box.get("box_id"),
                "tenant_id": box.get("tenant_id"),
                "machines": clean,
                "reported_at": datetime.now(timezone.utc).isoformat(),
            },
            tenant_id=box.get("tenant_id"),
        )
    except Exception as exc:
        log.error("Failed to publish machines_discovered event: %s", exc)
        return jsonify({"error": "Internal broker error"}), 500

    log.info("Discovered report: hardware_id=%s, machines=%d", hardware_id, len(clean))
    return jsonify({"success": True, "count": len(clean)}), 202


@app.route("/healthz", methods=["GET"])
def healthz():
    return jsonify({"status": "ok"}), 200
# In-Memory-State für aktive Box-Status (kann für Multi-Worker ggf. in Redis/DB gespiegelt werden, reicht für Single-Instance/Edge aber aus)
BOX_STATUS_STORE = {}

@app.route("/v1/connector-boxes/status", methods=["POST"])
def update_connector_box_status():
    payload = request.get_json(silent=True) or {}
    hardware_id = payload.get("hardware_id")
    status = payload.get("status")

    if not hardware_id or not status:
        return jsonify({"error": "hardware_id and status are required"}), 400

    BOX_STATUS_STORE[hardware_id] = {
        "status": status,
        "updated_at": time.time()
    }
    log.info("Box status updated: hardware_id=%s, status=%s", hardware_id, status)
    return jsonify({"success": True, "hardware_id": hardware_id, "status": status}), 200


@app.route("/v1/connector-boxes/status", methods=["GET"])
def list_connector_box_status():
    """Letzter gemeldeter Status je Box (nur im Speicher dieser Gateway-Instanz). age_seconds wird hier berechnet,
    damit Clients keine Uhren vergleichen müssen."""
    now = time.time()
    return jsonify({
        hw_id: {"status": info.get("status"), "updated_at": info.get("updated_at"),
                "age_seconds": round(now - info.get("updated_at", 0), 1)}
        for hw_id, info in BOX_STATUS_STORE.items()
    }), 200


@app.route("/v1/connector-boxes/active-scan", methods=["GET"])
def get_active_scan_box():
    """Prüft, welche Box sich aktuell im Modus 'scanning' befindet."""
    active_scanner = None
    current_time = time.time()

    for hw_id, info in BOX_STATUS_STORE.items():
        # Falls ein Status älter als 60 Sekunden ist, betrachten wir ihn als veraltet/abgestürzt
        if info.get("status") == "scanning":
            if current_time - info.get("updated_at", 0) < 60:
                active_scanner = hw_id
                break
            else:
                # Timeout abgelaufen, Status bereinigen
                info["status"] = "connected"

    return jsonify({"active_scanner": active_scanner}), 200

@app.route("/v1/telemetry", methods=["POST"])
def receive_generic_telemetry():
    payload = request.get_json(silent=True) or {}
    hardware_id = payload.get("box_id") or payload.get("hardware_id")
    machine_id = payload.get("machine_id")
    telemetry_data = payload.get("telemetry", {})

    if not machine_id:
        return jsonify({"error": "machine_id is required"}), 400

    if not isinstance(telemetry_data, dict):
        return jsonify({"error": "telemetry must be a dictionary"}), 400

    # Tenant-ID robust auflösen: Entweder direkt im Payload oder dynamisch über die Hardware-ID der Box
    tenant_id = payload.get("tenant_id")
    if not tenant_id and hardware_id:
        box_env = query_rpc("uretos.connectorbox.query.by_hardware_id", {"hardware_id": hardware_id})
        if box_env and box_env.get("data", {}).get("connector_box"):
            tenant_id = box_env["data"]["connector_box"].get("tenant_id")

    if not tenant_id:
        return jsonify({"error": "Could not resolve tenant_id for telemetry payload"}), 400

    try:
        publish_event(
            "uretos.machine.event.telemetry_updated",
            {
                "machine_id": machine_id,
                "hardware_id": hardware_id,
                "telemetry": telemetry_data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            tenant_id=tenant_id,
        )
    except Exception as exc:
        log.error("Failed to publish telemetry event: %s", exc)
        return jsonify({"error": "Internal broker error"}), 500

    log.debug("Published telemetry for machine_id=%s under tenant_id=%s", machine_id, tenant_id)
    return jsonify({"status": "published", "tenant_id": tenant_id}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
