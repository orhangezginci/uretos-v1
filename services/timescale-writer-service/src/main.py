"""
timescale-writer-service

Consumes machine status and telemetry events from RabbitMQ and writes them
into the respective per-tenant TimescaleDB hypertable.
"""
from __future__ import annotations

import logging
import os

import pika

from cloudevents import loads
from db import TenantNotFound, insert_machine_state

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("timescale-writer-service")

RABBITMQ_URL = os.environ.get(
    "RABBITMQ_URL", "amqp://uretos_system:uretos_system_dev_pass@rabbitmq:5672/"
)
EXCHANGE = "uretos.events"
QUEUE_NAME = "timescale_writer_queue"
ROUTING_KEY = "uretos.machine.event.status_changed"


def callback(ch, method, properties, body):
    try:
        envelope = loads(body)
        data = envelope.get("data", {})
        tenant_id = envelope.get("tenantid") or data.get("tenant_id")
        machine_id = data.get("machine_id") or envelope.get("subject")
        status = data.get("status")
        error_code = data.get("error_code")

        if not tenant_id or not machine_id or not status:
            log.error("Invalid event payload - missing tenant_id, machine_id or status. Dropping.")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            return

        log.info("Received status event for machine_id=%s tenant_id=%s status=%s", machine_id, tenant_id, status)

        insert_machine_state(tenant_id, machine_id, status, error_code)
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except TenantNotFound as exc:
        log.error("Tenant not found: %s. Dropping event.", exc)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    except Exception:
        log.exception("Error processing machine status event")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def main():
    log.info("Starting timescale-writer-service consumer...")
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()

    channel.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    channel.queue_bind(queue=QUEUE_NAME, exchange=EXCHANGE, routing_key=ROUTING_KEY)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)

    log.info("Waiting for machine events on '%s'...", ROUTING_KEY)
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        channel.stop_consuming()
    connection.close()


if __name__ == "__main__":
    main()