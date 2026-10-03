#!/usr/bin/env python3
"""
End-to-end smoke test for machine-command-service.

Verifies:
1. A uretos.machine.command.register command for an existing connector box's
   hardware_id results in a uretos.machine.event.registered response.
2. The response envelope's tenantid is the box's ACTUAL tenant (resolved via
   system-postgres) - regression test for the bug where the outgoing event
   used to echo the incoming (always "system") tenantid instead.
3. The registered machines list matches what was sent.

Picks an existing connector box via gateway-api (GET /v1/connector-boxes) so
the test doesn't need a hardcoded hardware_id - create at least one box via
the admin panel first.

Usage:
    python scripts/test_machine_registration_e2e.py
"""
from __future__ import annotations

import json
import sys
import time
import uuid
from datetime import datetime, timezone

import pika
import requests

RABBITMQ_URL = "amqp://uretos:uretos_dev_pass@localhost:5672/"
EXCHANGE = "uretos.events"
GATEWAY_URL = "http://localhost:8080"
TIMEOUT_SECONDS = 20


def build_command_envelope(hardware_id: str, machines: list[dict], correlation_id: str) -> dict:
    return {
        "specversion": "1.0",
        "id": str(uuid.uuid4()),
        "source": "test-script/machine-registration-e2e",
        "type": "uretos.machine.command.register",
        "datacontenttype": "application/json",
        "time": datetime.now(timezone.utc).isoformat(),
        "correlationid": correlation_id,
        "messagetype": "command",
        "tenantid": "system",
        "data": {"hardware_id": hardware_id, "machines": machines},
    }


def pick_connector_box() -> dict:
    response = requests.get(f"{GATEWAY_URL}/v1/connector-boxes", timeout=10)
    response.raise_for_status()
    boxes = response.json()
    if not boxes:
        print("[test] FAIL - no connector boxes exist yet. Create one via the admin panel first.")
        sys.exit(1)
    return boxes[0]


def main() -> int:
    box = pick_connector_box()
    hardware_id = box["hardware_id"]
    expected_tenant_id = box["tenant_id"]
    print(f"[test] Using connector box hardware_id={hardware_id} (expected tenant_id={expected_tenant_id})")

    machine_id = f"test-machine-{uuid.uuid4().hex[:8]}"
    machines = [
        {
            "machine_id": machine_id,
            "name": "E2E Test CNC",
            "endpoint_url": "opc.tcp://192.168.1.50:4840",
        }
    ]
    correlation_id = str(uuid.uuid4())

    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()
    channel.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)

    result = channel.queue_declare(queue="", exclusive=True)
    listen_queue = result.method.queue
    for routing_key in (
        "uretos.machine.event.registered",
        "uretos.machine.event.registration_failed",
    ):
        channel.queue_bind(queue=listen_queue, exchange=EXCHANGE, routing_key=routing_key)

    print(f"[test] Publishing registration command for machine_id={machine_id}")
    channel.basic_publish(
        exchange=EXCHANGE,
        routing_key="uretos.machine.command.register",
        body=json.dumps(build_command_envelope(hardware_id, machines, correlation_id)).encode("utf-8"),
        properties=pika.BasicProperties(content_type="application/json"),
    )

    deadline = time.monotonic() + TIMEOUT_SECONDS
    envelope = None
    while time.monotonic() < deadline:
        method, properties, body = channel.basic_get(queue=listen_queue, auto_ack=True)
        if body is None:
            time.sleep(0.3)
            continue
        candidate = json.loads(body)
        if candidate.get("correlationid") == correlation_id:
            envelope = candidate
            break

    connection.close()

    if envelope is None:
        print(f"[test] FAIL - no response within {TIMEOUT_SECONDS}s")
        return 1

    if envelope["type"] != "uretos.machine.event.registered":
        print("[test] FAIL - registration failed:")
        print(json.dumps(envelope["data"], indent=2))
        return 1

    checks_passed = True

    actual_tenant_id = envelope.get("tenantid")
    if actual_tenant_id == expected_tenant_id:
        print(f"[test] PASS - event tenantid correctly resolved to '{actual_tenant_id}'")
    else:
        print(f"[test] FAIL - event tenantid is '{actual_tenant_id}', expected '{expected_tenant_id}'")
        checks_passed = False

    registered_ids = [m["machine_id"] for m in envelope["data"].get("machines", [])]
    if machine_id in registered_ids:
        print(f"[test] PASS - machine_id '{machine_id}' present in response")
    else:
        print(f"[test] FAIL - machine_id '{machine_id}' missing from response: {registered_ids}")
        checks_passed = False

    if envelope["data"].get("registered_count") == len(machines):
        print("[test] PASS - registered_count matches")
    else:
        print(f"[test] FAIL - registered_count mismatch: {envelope['data'].get('registered_count')}")
        checks_passed = False

    print(json.dumps(envelope, indent=2))
    return 0 if checks_passed else 1


if __name__ == "__main__":
    sys.exit(main())