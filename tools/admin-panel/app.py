"""
uretOS super_admin panel - throwaway internal tool.

Deliberately NOT following uretOS's normal architecture rules: talks to
RabbitMQ directly via pika instead of going through a Gateway REST API,
since this tool is only ever used locally by the super_admin. A real
customer-facing client MUST go through a Gateway service instead - see
project notes.

Run with:
    streamlit run app.py
"""
import json
import os
import time
import uuid
from datetime import datetime, timezone

import pika
import streamlit as st

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://uretos:uretos_dev_pass@localhost:5672/")
EXCHANGE = "uretos.events"
SUPER_ADMIN_USER = os.environ.get("SUPER_ADMIN_USER", "admin")
SUPER_ADMIN_PASSWORD = os.environ.get("SUPER_ADMIN_PASSWORD", "changeme")
TIMEOUT_SECONDS = 45


def build_command_envelope(tenant_id: str, correlation_id: str) -> dict:
    return {
        "specversion": "1.0",
        "id": str(uuid.uuid4()),
        "source": "tools/admin-panel",
        "type": "uretos.tenant.command.create",
        "datacontenttype": "application/json",
        "time": datetime.now(timezone.utc).isoformat(),
        "correlationid": correlation_id,
        "messagetype": "command",
        "tenantid": "system",
        "data": {"tenant_id": tenant_id},
    }


def create_tenant(tenant_id: str) -> dict:
    correlation_id = str(uuid.uuid4())
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()
    channel.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)

    result = channel.queue_declare(queue="", exclusive=True)
    listen_queue = result.method.queue
    for routing_key in (
        "uretos.tenant.event.provisioned",
        "uretos.tenant.event.provisioning_failed",
    ):
        channel.queue_bind(queue=listen_queue, exchange=EXCHANGE, routing_key=routing_key)

    channel.basic_publish(
        exchange=EXCHANGE,
        routing_key="uretos.tenant.command.create",
        body=json.dumps(build_command_envelope(tenant_id, correlation_id)).encode("utf-8"),
        properties=pika.BasicProperties(content_type="application/json"),
    )

    deadline = time.monotonic() + TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        method, properties, body = channel.basic_get(queue=listen_queue, auto_ack=True)
        if body is None:
            time.sleep(0.5)
            continue
        envelope = json.loads(body)
        if envelope.get("correlationid") != correlation_id:
            continue
        connection.close()
        return envelope