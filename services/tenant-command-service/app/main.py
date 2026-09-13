"""
tenant-command-service

Consumes: uretos.tenant.event.provisioned (messagetype=event, tenantid=<tenant>)
Writes the tenant's registry entry into system-postgres. This is the single
writer for the `tenants` table - no other service is allowed to write to it.

Does NOT consume uretos.tenant.event.provisioning_failed - a failed
provisioning attempt never becomes a tenant record.
"""
from __future__ import annotations

import logging
import os

import pika

from cloudevents import loads
from db import ensure_schema, insert_tenant

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("tenant-command-service")

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://uretos:uretos_dev_pass@rabbitmq:5672/")
EXCHANGE = "uretos.events"
QUEUE = "tenant-command-service.tenant.event.provisioned"
ROUTING_KEY_IN = "uretos.tenant.event.provisioned"


def handle_provisioned(channel: pika.channel.Channel, method, properties, body: bytes) -> None:
    try:
        envelope = loads(body)
    except Exception:
        log.exception("Rejecting malformed message - not valid CloudEvent envelope")
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return

    tenant_id = envelope["data"].get("tenant_id")
    try:
        insert_tenant(envelope["data"])
        log.info("Tenant '%s' written to registry", tenant_id)
        channel.basic_ack(delivery_tag=method.delivery_tag)
    except Exception:
        log.exception("Failed to write tenant '%s' to registry - requeueing", tenant_id)
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


def main() -> None:
    ensure_schema()

    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()

    channel.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)
    channel.queue_declare(queue=QUEUE, durable=True)
    channel.queue_bind(queue=QUEUE, exchange=EXCHANGE, routing_key=ROUTING_KEY_IN)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=QUEUE, on_message_callback=handle_provisioned)

    log.info("tenant-command-service listening on '%s'", ROUTING_KEY_IN)
    try:
        channel.start_consuming()
    except KeyboardInterrupt: