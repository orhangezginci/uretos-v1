"""
connector-box-command-service

Consumes: uretos.connectorbox.command.create (messagetype=command, tenantid="system")
Publishes: uretos.connectorbox.event.created (messagetype=event, tenantid=<tenant>)
       or: uretos.connectorbox.event.creation_failed (messagetype=event, tenantid="system")

Required data fields on the command: tenant_id, hardware_id, mac_address.
Only the super_admin level is expected to send this command.
"""
from __future__ import annotations

import json
import logging
import os

import pika

from cloudevents import build_envelope, loads
from db import ConnectorBoxError, ensure_schema, insert_connector_box

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("connector-box-command-service")

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://uretos:uretos_dev_pass@rabbitmq:5672/")
EXCHANGE = "uretos.events"
COMMAND_QUEUE = "connector-box-command-service.connectorbox.command.create"
ROUTING_KEY_IN = "uretos.connectorbox.command.create"
SOURCE = "uretos/services/connector-box-command-service"

REQUIRED_FIELDS = ("tenant_id", "hardware_id", "mac_address")


def handle_command(channel: pika.channel.Channel, method, properties, body: bytes) -> None:
    try:
        envelope = loads(body)
    except Exception:
        log.exception("Rejecting malformed message - not valid CloudEvent envelope")
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return

    correlation_id = envelope["correlationid"]
    data = envelope["data"]
    missing = [f for f in REQUIRED_FIELDS if not data.get(f)]

    if missing:
        log.error("Rejecting command - missing required fields: %s", missing)
        response = build_envelope(
            event_type="uretos.connectorbox.event.creation_failed",
            source=SOURCE,
            data={"reason": f"Missing required fields: {missing}"},
            tenant_id="system",
            messagetype="event",
            correlation_id=correlation_id,
        )
    else:
        try:
            box_info = insert_connector_box(
                tenant_id=data["tenant_id"],
                hardware_id=data["hardware_id"],
                mac_address=data["mac_address"],
            )
            log.info("Connector box '%s' created for tenant '%s'", box_info["box_id"], data["tenant_id"])
            response = build_envelope(
                event_type="uretos.connectorbox.event.created",
                source=SOURCE,
                data=box_info,
                tenant_id=data["tenant_id"],
                messagetype="event",
                correlation_id=correlation_id,
            )
        except ConnectorBoxError as exc:
            log.error("Connector box creation failed: %s", exc)
            response = build_envelope(
                event_type="uretos.connectorbox.event.creation_failed",
                source=SOURCE,
                data={"reason": str(exc)},
                tenant_id="system",
                messagetype="event",
                correlation_id=correlation_id,
            )

    channel.basic_publish(
        exchange=EXCHANGE,
        routing_key=response["type"],
        body=json.dumps(response).encode("utf-8"),
        properties=pika.BasicProperties(content_type="application/json"),
    )
    channel.basic_ack(delivery_tag=method.delivery_tag)


def main() -> None:
    ensure_schema()

    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()

    channel.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)
    channel.queue_declare(queue=COMMAND_QUEUE, durable=True)
    channel.queue_bind(queue=COMMAND_QUEUE, exchange=EXCHANGE, routing_key=ROUTING_KEY_IN)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=COMMAND_QUEUE, on_message_callback=handle_command)

    log.info("connector-box-command-service listening on '%s'", ROUTING_KEY_IN)
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        channel.stop_consuming()

    connection.close()


if __name__ == "__main__":
    main()