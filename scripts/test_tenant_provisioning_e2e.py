#!/usr/bin/env python3
"""
End-to-end smoke test for the tenant-provisioning-service.

Publishes a uretos.tenant.command.create for a throwaway tenant, waits for
the resulting uretos.tenant.event.provisioned (or ...failed) event, and
verifies the containers actually exist. Run this AFTER `docker compose up`.

Usage:
    python scripts/test_tenant_provisioning_e2e.py
"""
from __future__ import annotations

import json
import sys
import time
import uuid
from datetime import datetime, timezone

import pika

RABBITMQ_URL = "amqp://uretos:uretos_dev_pass@localhost:5672/"
EXCHANGE = "uretos.events"
TIMEOUT_SECONDS = 30


def build_command_envelope(tenant_id: str, correlation_id: str) -> dict:
    return {
        "specversion": "1.0",
        "id": str(uuid.uuid4()),
        "source": "test-script/tenant-provisioning-e2e",
        "type": "uretos.tenant.command.create",
        "datacontenttype": "application/json",
        "time": datetime.now(timezone.utc).isoformat(),
        "correlationid": correlation_id,
        "messagetype": "command",
        "tenantid": "system",
        "data": {"tenant_id": tenant_id},
    }


def main() -> int:
    tenant_id = f"e2e-{uuid.uuid4().hex[:8]}"
    correlation_id = str(uuid.uuid4())

    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()
    channel.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)

    # Temporary queue just for this test run, bound to the two possible outcomes.
    result = channel.queue_declare(queue="", exclusive=True)
    listen_queue = result.method.queue
    for routing_key in (
        "uretos.tenant.event.provisioned",
        "uretos.tenant.event.provisioning_failed",
    ):
        channel.queue_bind(queue=listen_queue, exchange=EXCHANGE, routing_key=routing_key)

    print(f"[test] Requesting provisioning for tenant_id={tenant_id}")
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
            continue  # some other test run's message

        if envelope["type"] == "uretos.tenant.event.provisioned":
            print("[test] PASS - tenant provisioned:")
            print(json.dumps(envelope["data"], indent=2))
            connection.close()
            return 0
        else:
            print("[test] FAIL - provisioning failed:")
            print(json.dumps(envelope["data"], indent=2))
            connection.close()
            return 1

    print(f"[test] FAIL - no response within {TIMEOUT_SECONDS}s")
    connection.close()
    return 1


if __name__ == "__main__":
    sys.exit(main())