from __future__ import annotations

import json
import logging
import os

import pika

from cloudevents import build_envelope
from db import TenantNotFound, get_machine_history

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("timescale-query-service")

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://uretos_system:uretos_system_dev_pass@rabbitmq:5672/")
EXCHANGE = "uretos.events"
QUEUE_NAME = "timescale_query_queue"
SOURCE = "uretos/services/timescale-query-service"

QUERY_HISTORY = "uretos.timescale.query.history"


def run_query(event_type: str, data: dict) -> dict:
    tenant_id = data.get("tenant_id")
    if not tenant_id:
        return {"history": [], "error_code": "tenant_required", "error": "tenant_id is required"}

    machine_id = data.get("machine_id")
    if not machine_id:
        return {"history": [], "error_code": "machine_id_required", "error": "machine_id is required"}

    limit = data.get("limit", 50)

    try:
        if event_type == QUERY_HISTORY:
            history = get_machine_history(tenant_id, machine_id, limit=limit)
            return {"history": history}

        return {"history": [], "error_code": "unsupported_query", "error": f"Unsupported query '{event_type}'"}

    except TenantNotFound as exc:
        return {"history": [], "error_code": "tenant_not_found", "error": str(exc)}
    except Exception as exc:
        log.exception("Timescale query failed for tenant_id=%s, machine_id=%s", tenant_id, machine_id)
        return {"history": [], "error_code": "query_failed", "error": f"Query failed: {exc}"}


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

        log.info("Received query type=%s tenant_id=%s machine_id=%s", event_type, data.get("tenant_id"), data.get("machine_id"))

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
        log.exception("Error processing timescale query")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def main():
    log.info("Starting timescale-query-service consumer...")
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()

    channel.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)
    channel.queue_declare(queue=QUEUE_NAME, durable=True)

    channel.queue_bind(queue=QUEUE_NAME, exchange=EXCHANGE, routing_key=QUERY_HISTORY)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)

    log.info("Waiting for timescale queries...")
    channel.start_consuming()


if __name__ == "__main__":
    main()