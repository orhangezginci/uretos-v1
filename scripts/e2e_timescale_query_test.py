"""
End-to-End Test for the timescale-query-service via RabbitMQ RPC.
"""
from __future__ import annotations

import json
import os
import uuid
import pika

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://uretos_system:uretos_system_dev_pass@rabbitmq:5672/")
EXCHANGE = "uretos.events"
QUERY_ROUTING_KEY = "uretos.timescale.query.history"
SOURCE = "uretos/scripts/e2e-query-test"

TEST_TENANT = "test-tenant-e2e"
TEST_MACHINE = "FullMachineTool"


class TimescaleQueryTestClient:
    def __init__(self):
        self.connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
        self.channel = self.connection.channel()
        
        result_queue = self.channel.queue_declare(queue="", exclusive=True)
        self.callback_queue = result_queue.method.queue

        self.response = None
        self.correlation_id = None

        self.channel.basic_consume(
            queue=self.callback_queue,
            on_message_callback=self.on_response,
            auto_ack=True,
        )

    def on_response(self, ch, method, properties, body):
        if self.correlation_id == properties.correlation_id:
            self.response = json.loads(body)

    def call(self, tenant_id: str, machine_id: str, limit: int = 10):
        self.correlation_id = str(uuid.uuid4())
        
        payload = {
            "tenant_id": tenant_id,
            "machine_id": machine_id,
            "limit": limit
        }

        envelope = {
            "specversion": "1.0",
            "id": str(uuid.uuid4()),
            "source": SOURCE,
            "type": QUERY_ROUTING_KEY,
            "datacontenttype": "application/json",
            "time": "2026-10-12T00:00:00Z",
            "correlationid": self.correlation_id,
            "messagetype": "query",
            "tenantid": tenant_id,
            "data": payload,
        }

        self.channel.basic_publish(
            exchange=EXCHANGE,
            routing_key=QUERY_ROUTING_KEY,
            body=json.dumps(envelope).encode("utf-8"),
            properties=pika.BasicProperties(
                reply_to=self.callback_queue,
                correlation_id=self.correlation_id,
                content_type="application/json",
            ),
        )

        while self.response is None:
            self.connection.process_data_events(time_limit=1.0)

        return self.response


if __name__ == "__main__":
    print("--- Starte E2E-Test für timescale-query-service ---")
    client = TimescaleQueryTestClient()
    
    print(f" [x] Sende Query-Request für Tenant '{TEST_TENANT}' / Maschine '{TEST_MACHINE}'...")
    response_envelope = client.call(TEST_TENANT, TEST_MACHINE, limit=5)
    
    print(f"📦 Empfangene Antwort:\n{json.dumps(response_envelope, indent=2)}")
    
    data = response_envelope.get("data", {})
    history = data.get("history", [])
    
    if data.get("error_code"):
        raise AssertionError(f"Query fehlgeschlagen mit Fehler: {data.get('error_code')} - {data.get('error')}")

    if not history:
        raise AssertionError("FAILURE: Keine Historie-Einträge vom timescale-query-service zurückgegeben!")

    print(f"✔ SUCCESS: {len(history)} Historie-Einträge erfolgreich via RabbitMQ RPC abgerufen!")
    for item in history:
        print(f"     Zeit: {item['time']} | Status: {item['status']} | Error: {item['error_code']}")

    print("--- Query-E2E-Test erfolgreich abgeschlossen! ---")