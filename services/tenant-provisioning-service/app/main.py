"""
tenant-provisioning-service

Consumes:  uretos.tenant.command.create   (messagetype=command, tenantid="system")
Publishes: uretos.tenant.event.provisioned (messagetype=event,  tenantid=<new tenant>)
       or: uretos.tenant.event.provisioning_failed (messagetype=event, tenantid="system")

Only the super_admin level is expected to ever send the create-command, which
is why it travels under tenantid="system" - it is not itself tenant data.
"""
from __future__ import annotations

import json
import logging
import os

import pika

from cloudevents import build_envelope, loads
from provisioning import ProvisioningError, provision_tenant_infrastructure

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("tenant-provisioning-service")

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://uretos:uretos_dev_pass@rabbitmq:5672/")
EXCHANGE = "uretos.events"
COMMAND_QUEUE = "tenant-provisioning-service.tenant.command.create"
ROUTING_KEY_IN = "uretos.tenant.command.create"
SOURCE = "uretos/services/tenant-provisioning-service"


def handle_command(channel: pika.channel.Channel, method, properties, body: bytes) -> None:
    try:
        envelope = loads(body)
    except Exception:
        log.exception("Rejecting malformed message - not valid CloudEvent envelope")
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return

    correlation_id = envelope["correlationid"]
    tenant_id = envelope["data"].get("tenant_id")
    log.info("Received tenant creation command for tenant_id=%s", tenant_id)

    try:
        infra_info = provision_tenant_infrastructure(tenant_id)
        out_type = "uretos.tenant.event.provisioned"
        out_tenant = tenant_id
        out_data = infra_info
        log.info("Tenant '%s' provisioned successfully", tenant_id)
    except ProvisioningError as exc:
        log.error("Provisioning failed for tenant_id=%s: %s", tenant_id, exc)
        out_type = "uretos.tenant.event.provisioning_failed"
        out_tenant = "system"
        out_data = {"tenant_id": tenant_id, "reason": str(exc)}

    response = build_envelope(
        event_type=out_type,
        source=SOURCE,
        data=out_data,
        tenant_id=out_tenant,
        messagetype="event",
        correlation_id=correlation_id,
    )
    channel.basic_publish(
        exchange=EXCHANGE,
        routing_key=out_type,
        body=json.dumps(response).encode("utf-8"),
        properties=pika.BasicProperties(content_type="application/json"),
    )
    channel.basic_ack(delivery_tag=method.delivery_tag)


def main() -> None:
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()

    channel.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)
    channel.queue_declare(queue=COMMAND_QUEUE, durable=True)
    channel.queue_bind(queue=COMMAND_QUEUE, exchange=EXCHANGE, routing_key=ROUTING_KEY_IN)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=COMMAND_QUEUE, on_message_callback=handle_command)

    log.info("tenant-provisioning-service listening on '%s'", ROUTING_KEY_IN)
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        channel.stop_consuming()
    connection.close()


if __name__ == "__main__":
    main()