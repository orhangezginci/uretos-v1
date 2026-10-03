"""
machine-command-service
"""
from __future__ import annotations

import json
import logging
import os

import pika

from cloudevents import build_envelope
from db import init_db, register_machines_for_box

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("machine-command-service")

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://uretos:uretos_dev_pass@rabbitmq:5672/")
EXCHANGE = "uretos.events"
QUEUE_NAME = "machine_command_queue"
SOURCE = "uretos/services/machine-command-service"

REGISTER_COMMAND = "uretos.machine.command.register"
REGISTERED_EVENT = "uretos.machine.event.registered"
REGISTRATION_FAILED_EVENT = "uretos.machine.event.registration_failed"


def publish_event(ch, response_type: str, response_data: dict, tenant_id: str, correlation_id):
    envelope_out = build_envelope(
        event_type=response_type,
        source=SOURCE,
        data=response_data,
        tenant_id=tenant_id,
        messagetype="event",
        correlation_id=correlation_id,
    )
    ch.basic_publish(
        exchange=EXCHANGE,
        routing_key=response_type,
        body=json.dumps(envelope_out).encode("utf-8"),
        properties=pika.BasicProperties(
            content_type="application/json",
            correlation_id=correlation_id,
        ),
    )


def callback(ch, method, properties, body):
    try:
        envelope = json.loads(body)
        event_type = envelope.get("type")
        correlation_id = envelope.get("correlationid")
        tenant_id = envelope.get("tenantid", "system")
        data = envelope.get("data", {})

        if event_type != REGISTER_COMMAND:
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        hardware_id = data.get("hardware_id")
        machines = data.get("machines", [])

        log.info("Processing machine registration for hardware_id=%s (Count: %d)", hardware_id, len(machines))

        result, error_reason, resolved_tenant_id = register_machines_for_box(hardware_id, machines)

        if error_reason:
            response_type = REGISTRATION_FAILED_EVENT
            response_data = {"reason": error_reason, "hardware_id": hardware_id}
            response_tenant_id = tenant_id  # "system" - Fehlerfall betrifft keinen konkreten Tenant-Stream
        else:
            response_type = REGISTERED_EVENT
            response_data = {"status": "success", "registered_count": len(machines), "machines": result}
            response_tenant_id = resolved_tenant_id  # echter Tenant, aufgelöst über hardware_id

        publish_event(ch, response_type, response_data, response_tenant_id, correlation_id)
        ch.basic_ack(delivery_tag=method.delivery_tag)
        log.info("Successfully finished machine registration for hardware_id=%s", hardware_id)

    except Exception as exc:
        log.exception("Error processing machine command message")

        try:
            envelope_in = json.loads(body)
            publish_event(
                ch,
                REGISTRATION_FAILED_EVENT,
                {"reason": f"Internal error: {exc}"},
                envelope_in.get("tenantid", "system"),
                envelope_in.get("correlationid"),
            )
        except Exception:
            log.exception("Could not publish failure event")

        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def main():
    log.info("Initializing database tables...")
    init_db()

    log.info("Starting machine-command-service consumer...")
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()

    channel.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    channel.queue_bind(queue=QUEUE_NAME, exchange=EXCHANGE, routing_key=REGISTER_COMMAND)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)

    log.info("Waiting for machine commands...")
    channel.start_consuming()


if __name__ == "__main__":
    main()