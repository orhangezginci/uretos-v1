"""
connector-box-query-service

Consumes: 
  - uretos.connectorbox.query.list
  - uretos.connectorbox.query.by_hardware_id
Replies directly via RabbitMQ's Direct-Reply-To mechanism.

Read-only - never writes to system-postgres.
"""
from __future__ import annotations

import json
import logging
import os

import pika

from cloudevents import build_envelope, loads
from db import get_connector_box_by_hardware_id, list_connector_boxes

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("connector-box-query-service")

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://uretos:uretos_dev_pass@rabbitmq:5672/")
EXCHANGE = "uretos.events"
SOURCE = "uretos/services/connector-box-query-service"


def handle_list_query(channel: pika.channel.Channel, method, properties, body: bytes) -> None:
    try:
        envelope = loads(body)
    except Exception:
        log.exception("Rejecting malformed message - not valid CloudEvent envelope")
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return

    if not properties.reply_to:
        log.error("Query received without AMQP reply_to - cannot answer, dropping")
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return

    correlation_id = envelope["correlationid"]
    boxes = list_connector_boxes()
    log.info("Answering connector-box list query with %d box(es)", len(boxes))

    response = build_envelope(
        event_type="uretos.connectorbox.query.list.result",
        source=SOURCE,
        data={"connector_boxes": boxes},
        tenant_id="system",
        messagetype="event",
        correlation_id=correlation_id,
    )
    channel.basic_publish(
        exchange="",
        routing_key=properties.reply_to,
        properties=pika.BasicProperties(
            correlation_id=properties.correlation_id,
            content_type="application/json",
        ),
        body=json.dumps(response).encode("utf-8"),
    )
    channel.basic_ack(delivery_tag=method.delivery_tag)


def handle_hardware_id_query(channel: pika.channel.Channel, method, properties, body: bytes) -> None:
    try:
        envelope = loads(body)
    except Exception:
        log.exception("Rejecting malformed message - not valid CloudEvent envelope")
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return

    if not properties.reply_to:
        log.error("Query received without AMQP reply_to - cannot answer, dropping")
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return

    correlation_id = envelope["correlationid"]
    data = envelope.get("data", {})
    hardware_id = data.get("hardware_id")

    box = get_connector_box_by_hardware_id(hardware_id) if hardware_id else None
    log.info("Answering hardware_id query for '%s': found=%s", hardware_id, box is not None)

    response = build_envelope(
        event_type="uretos.connectorbox.query.by_hardware_id.result",
        source=SOURCE,
        data={"connector_box": box},
        tenant_id="system",
        messagetype="event",
        correlation_id=correlation_id,
    )
    channel.basic_publish(
        exchange="",
        routing_key=properties.reply_to,
        properties=pika.BasicProperties(
            correlation_id=properties.correlation_id,
            content_type="application/json",
        ),
        body=json.dumps(response).encode("utf-8"),
    )
    channel.basic_ack(delivery_tag=method.delivery_tag)


def main() -> None:
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()

    channel.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)

    # Queue für den List-Query
    queue_list = "connector-box-query-service.connectorbox.query.list"
    channel.queue_declare(queue=queue_list, durable=True)
    channel.queue_bind(queue=queue_list, exchange=EXCHANGE, routing_key="uretos.connectorbox.query.list")
    channel.basic_consume(queue=queue_list, on_message_callback=handle_list_query, auto_ack=False)

    # Queue für den Hardware-ID-Query
    queue_hw = "connector-box-query-service.connectorbox.query.hardware_id"
    channel.queue_declare(queue=queue_hw, durable=True)
    channel.queue_bind(queue=queue_hw, exchange=EXCHANGE, routing_key="uretos.connectorbox.query.by_hardware_id")
    channel.basic_consume(queue=queue_hw, on_message_callback=handle_hardware_id_query, auto_ack=False)

    channel.basic_qos(prefetch_count=1)
    log.info("connector-box-query-service listening for queries...")
    
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        channel.stop_consuming()

    connection.close()


if __name__ == "__main__":
    main()