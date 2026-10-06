"""
shopfloor-stream-service

Bridges RabbitMQ machine events to SSE streams for uretOS modules (Cockpit
and others) that need live shopfloor state - without those modules ever
touching RabbitMQ or machine-command-service/machine-query-service directly.

Two RabbitMQ touchpoints:
  1. A background thread subscribes to uretos.machine.event.* and fans out
     each event to all SSE clients currently connected for that tenant.
  2. On a new SSE connection, a one-off RPC call to machine-query-service
     (uretos.machine.query.list) fetches the current machine snapshot, sent
     as the first SSE message before live events follow.

In-memory only, single-instance pub/sub (dict tenant_id -> set of queues).
No Redis, no persistence - acceptable at the current scale; revisit if this
service ever needs to run as more than one replica.

Endpoint:
  GET /v1/shopfloor/stream?tenant_id=<id>   (SSE)
  GET /healthz
"""
from __future__ import annotations

import json
import logging
import os
import queue
import threading
import time
import uuid

import pika
from flask import Flask, Response, jsonify, request

from cloudevents import build_envelope, loads

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("shopfloor-stream-service")

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://uretos_system:uretos_system_dev_pass@rabbitmq:5672/")
EXCHANGE = "uretos.events"
QUEUE_NAME = "shopfloor-stream-service.machine.events"
SOURCE = "uretos/services/shopfloor-stream-service"
SNAPSHOT_TIMEOUT_SECONDS = 15
KEEPALIVE_SECONDS = 20

# Future telemetry events get added to this tuple once that stage starts.
MACHINE_EVENT_ROUTING_KEYS = (
    "uretos.machine.event.registered",
)

app = Flask(__name__)

_subscribers: dict[str, set] = {}
_subscribers_lock = threading.Lock()


def _subscribe(tenant_id: str) -> "queue.Queue":
    q: "queue.Queue" = queue.Queue()
    with _subscribers_lock:
        _subscribers.setdefault(tenant_id, set()).add(q)
    return q


def _unsubscribe(tenant_id: str, q: "queue.Queue") -> None:
    with _subscribers_lock:
        subs = _subscribers.get(tenant_id)
        if subs is not None:
            subs.discard(q)
            if not subs:
                _subscribers.pop(tenant_id, None)


def _publish_to_subscribers(tenant_id: str, payload: dict) -> None:
    with _subscribers_lock:
        subs = list(_subscribers.get(tenant_id, ()))
    for q in subs:
        q.put(payload)


def _consume_machine_events() -> None:
    """Runs in a background thread for the lifetime of the process.
    Reconnects on any failure instead of letting the whole service die."""
    while True:
        try:
            connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
            channel = connection.channel()
            channel.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)
            channel.queue_declare(queue=QUEUE_NAME, durable=True)
            for routing_key in MACHINE_EVENT_ROUTING_KEYS:
                channel.queue_bind(queue=QUEUE_NAME, exchange=EXCHANGE, routing_key=routing_key)

            def on_message(ch, method, properties, body):
                try:
                    envelope = loads(body)
                except Exception:
                    log.exception("Dropping malformed machine event")
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                    return

                tenant_id = envelope.get("tenantid")
                if tenant_id and tenant_id != "system":
                    _publish_to_subscribers(tenant_id, envelope)
                ch.basic_ack(delivery_tag=method.delivery_tag)

            channel.basic_qos(prefetch_count=10)
            channel.basic_consume(queue=QUEUE_NAME, on_message_callback=on_message)
            log.info("shopfloor-stream-service consuming machine events...")
            channel.start_consuming()

        except Exception:
            log.exception("RabbitMQ consumer crashed - reconnecting in 5s")
            time.sleep(5)


def _fetch_snapshot(tenant_id: str) -> list[dict]:
    """One-off RPC call to machine-query-service for the current machine list."""
    correlation_id = str(uuid.uuid4())
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()
    channel.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)

    envelope_out = build_envelope(
        event_type="uretos.machine.query.list",
        source=SOURCE,
        data={"tenant_id": tenant_id},
        tenant_id=tenant_id,
        messagetype="query",
        correlation_id=correlation_id,
    )

    result_holder: dict = {}

    def on_response(ch, method, properties, body):
        if properties.correlation_id == correlation_id:
            result_holder["envelope"] = json.loads(body)
            ch.stop_consuming()

    channel.basic_consume(queue="amq.rabbitmq.reply-to", on_message_callback=on_response, auto_ack=True)
    channel.basic_publish(
        exchange=EXCHANGE,
        routing_key="uretos.machine.query.list",
        properties=pika.BasicProperties(
            reply_to="amq.rabbitmq.reply-to",
            correlation_id=correlation_id,
            content_type="application/json",
        ),
        body=json.dumps(envelope_out).encode("utf-8"),
    )

    connection.process_data_events(time_limit=SNAPSHOT_TIMEOUT_SECONDS)
    connection.close()

    envelope_in = result_holder.get("envelope")
    if envelope_in is None:
        log.warning("Snapshot query timed out for tenant_id=%s", tenant_id)
        return []
    return envelope_in.get("data", {}).get("machines", [])


@app.route("/v1/shopfloor/stream", methods=["GET"])
def stream():
    tenant_id = request.args.get("tenant_id")
    if not tenant_id:
        return jsonify({"error": "tenant_id query parameter is required"}), 400

    def event_stream():
        snapshot = _fetch_snapshot(tenant_id)
        snapshot_envelope = build_envelope(
            event_type="uretos.shopfloor.snapshot",
            source=SOURCE,
            data={"machines": snapshot},
            tenant_id=tenant_id,
            messagetype="event",
        )
        yield f"data: {json.dumps(snapshot_envelope)}\n\n"

        q = _subscribe(tenant_id)
        log.info("SSE client connected for tenant_id=%s", tenant_id)
        try:
            while True:
                try:
                    payload = q.get(timeout=KEEPALIVE_SECONDS)
                    yield f"data: {json.dumps(payload)}\n\n"
                except queue.Empty:
                    yield ": keep-alive\n\n"
        finally:
            _unsubscribe(tenant_id, q)
            log.info("SSE client disconnected for tenant_id=%s", tenant_id)

    return Response(
        event_stream(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/healthz", methods=["GET"])
def healthz():
    return jsonify({"status": "ok"}), 200


def main() -> None:
    consumer_thread = threading.Thread(target=_consume_machine_events, daemon=True)
    consumer_thread.start()
    app.run(host="0.0.0.0", port=8081, threaded=True)


if __name__ == "__main__":
    main()