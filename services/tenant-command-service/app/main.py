"""
tenant-command-service

Consumes: uretos.tenant.event.provisioned (messagetype=event, tenantid=<tenant>)
Writes the tenant's registry entry into system-postgres. This is the single
writer for the `tenants` table - no other service is allowed to write to it.

Does NOT consume uretos.tenant.event.provisioning_failed - a failed
provisioning attempt never becomes a tenant record.

Error handling: a message is only requeued when a retry can help (system-postgres
temporarily unreachable). Everything else is permanent and would otherwise be
redelivered forever, blocking the queue (prefetch_count=1). Log messages never
include the exception text of database errors: SQLAlchemy puts the statement
parameters into it, and here those are the tenant's passwords.
"""
from __future__ import annotations

import logging
import os
import time

import pika
from sqlalchemy.exc import IntegrityError, OperationalError

from cloudevents import loads
from db import ensure_schema, insert_tenant

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("tenant-command-service")

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://uretos:uretos_dev_pass@rabbitmq:5672/")
EXCHANGE = "uretos.events"
QUEUE = "tenant-command-service.tenant.event.provisioned"
ROUTING_KEY_IN = "uretos.tenant.event.provisioned"

# Pause before a requeue, so an unreachable database does not cause a hot loop
RETRY_DELAY_SECONDS = 5


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

    except IntegrityError:
        # Permanent: the tenant is already in the registry. Redelivery can never succeed.
        log.error(
            "Tenant '%s' is already in the registry - the credentials of this provisioning "
            "were NOT stored, the existing entry may be stale. Dropping message.",
            tenant_id,
        )
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    except (KeyError, TypeError) as exc:
        # Permanent: the event payload is incomplete or has the wrong shape.
        log.error("Malformed provisioned event for tenant '%s' (%s: %s). Dropping message.",
                  tenant_id, type(exc).__name__, exc)
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    except OperationalError:
        # Transient: system-postgres not reachable. Retry, but with a pause.
        log.warning("system-postgres not reachable while writing tenant '%s' - retrying in %ds",
                    tenant_id, RETRY_DELAY_SECONDS)
        time.sleep(RETRY_DELAY_SECONDS)
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    except Exception as exc:
        # Unknown: do not loop forever. Only the exception class is logged (no parameters).
        log.error("Unexpected %s while writing tenant '%s' to registry. Dropping message.",
                  type(exc).__name__, tenant_id)
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


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
        channel.stop_consuming()

    connection.close()


if __name__ == "__main__":
    main()