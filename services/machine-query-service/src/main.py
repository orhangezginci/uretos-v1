"""
machine-query-service

Answers machine queries via Direct-Reply-To. Machines live in the per-tenant
database, so every query must carry the tenant_id in its data:

  uretos.machine.query.list     data: {"tenant_id": ...}
  uretos.machine.query.by_box   data: {"tenant_id": ..., "box_id": ...}

Reads only ever produce a single '<query_type>.result' event. Errors are
reported inside that event ("error_code" + "error") so that the gateway gets
a clear answer instead of running into its RPC timeout.
"""
from __future__ import annotations

import json
import logging
import os

import pika

from cloudevents import build_envelope
from db import TenantNotFound, get_all_machines, get_machines_by_box

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("machine-query-service")

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://uretos_system:uretos_system_dev_pass@rabbitmq:5672/")
EXCHANGE = "uretos.events"
QUEUE_NAME = "machine_query_queue"
SOURCE = "uretos/services/machine-query-service"

QUERY_LIST = "uretos.machine.query.list"
QUERY_BY_BOX = "uretos.machine.query.by_box"


def run_query(event_type: str, data: dict) -> dict:
    """Returns the response data: {"machines": [...]} or {"machines": [], "error_code", "error"}."""
    tenant_id = data.get("tenant_id")
    if not tenant_id:
        return {"machines": [], "error_code": "tenant_required", "error": "tenant_id is required"}

    try:
        if event_type == QUERY_LIST:
            return {"machines": get_all_machines(tenant_id)}

        if event_type == QUERY_BY_BOX:
            box_id = data.get("box_id")
            if not box_id:
                return {"machines": [], "error_code": "box_id_required", "error": "box_id is required"}
            return {"machines": get_machines_by_box(tenant_id, box_id)}

        return {"machines": [], "error_code": "unsupported_query", "error": f"Unsupported query '{event_type}'"}

    except TenantNotFound as exc:
        return {"machines": [], "error_code": "tenant_not_found", "error": str(exc)}
    except Exception as exc:
        log.exception("Machine query failed for tenant_id=%s", tenant_id)
        return {"machines": [], "error_code": "query_failed", "error": f"Query failed: {exc}"}


def callback(ch, method, properties, body):
    try:
        envelope = json.loads(body)
        event_type = envelope.get("type")
        correlation_id = envelope.get("correlationid")
        reply_to = properties.reply_to
        data = envelope.get("data", {})

        if not reply_to:
            log.error("Query received without AMQP reply_to - cannot answer, dropping")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            return

        log.info("Received query type=%s tenant_id=%s", event_type, data.get("tenant_id"))

        response_data = run_query(event_type, data)

        envelope_out = build_envelope(
            event_type=f"{event_type}.result",
            source=SOURCE,
            data=response_data,
            tenant_id=envelope.get("tenantid", "system"),
            messagetype="query",
            correlation_id=correlation_id,
        )

        ch.basic_publish(
            exchange="",
            routing_key=reply_to,
            body=json.dumps(envelope_out).encode("utf-8"),
            properties=pika.BasicProperties(
                content_type="application/json",
                correlation_id=correlation_id,
            ),
        )

        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception:
        log.exception("Error processing machine query")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        
def main():
    log.info("Starting machine-query-service consumer...")
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()

    channel.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)
    channel.queue_declare(queue=QUEUE_NAME, durable=True)

    channel.queue_bind(queue=QUEUE_NAME, exchange=EXCHANGE, routing_key=QUERY_LIST)
    channel.queue_bind(queue=QUEUE_NAME, exchange=EXCHANGE, routing_key=QUERY_BY_BOX)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)

    log.info("Waiting for machine queries...")
    channel.start_consuming()


if __name__ == "__main__":
    main()
