"""
End-to-End Test (Dockerized) starting from the Gateway-API endpoint 
down to TimescaleDB persistence.
"""
from __future__ import annotations

import os
import time
import requests
from sqlalchemy import create_engine, text

# Im Docker-Netzwerk sprechen wir den Gateway und die System-DB direkt über ihre Service-Namen an
GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://gateway-api:8080")
SYSTEM_DB_URL = os.environ.get(
    "SYSTEM_DB_URL",
    "postgresql+psycopg://uretos_system:uretos_system_dev_pass@system-postgres:5432/uretos_system",
)

TEST_TENANT = "test-tenant-e2e"
TEST_MACHINE = "FullMachineTool"


def get_tenant_db_url(tenant_id: str) -> str:
    engine = create_engine(SYSTEM_DB_URL)
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT postgres_host, postgres_port, postgres_user, "
                "postgres_password, postgres_db FROM tenants WHERE tenant_id = :t"
            ),
            {"t": tenant_id},
        ).fetchone()
    if not row:
        raise RuntimeError(f"Tenant '{tenant_id}' not found in system registry. Did you provision it?")
    
    # Innerhalb des Docker-Netzwerks nutzen wir direkt den Container-Hostnamen aus der Registry
    host = row.postgres_host
    port = row.postgres_port

    return f"postgresql+psycopg://{row.postgres_user}:{row.postgres_password}@{host}:{port}/{row.postgres_db}"


def send_status_via_gateway():
    url = f"{GATEWAY_URL}/v1/machines/{TEST_MACHINE}/status"
    
    payload = {
        "tenant_id": TEST_TENANT,
        "status": "error",
        "error_code": "E-404-CNC"
    }

    print(f" [x] Sende PATCH-Request an Gateway für Tenant '{TEST_TENANT}' / Maschine '{TEST_MACHINE}': {url}")
    response = requests.patch(url, json=payload, timeout=5)
    
    if response.status_code not in (200, 201, 202):
        raise RuntimeError(f"Gateway hat den Request abgelehnt: {response.status_code} - {response.text}")
    
    print(" [x] Gateway hat das Status-Event erfolgreich entgegengenommen und weitergeleitet.")


def verify_database():
    print(" [x] Warte 2 Sekunden auf asynchrone Verarbeitung (RabbitMQ -> Writer -> TimescaleDB)...")
    time.sleep(2)

    db_url = get_tenant_db_url(TEST_TENANT)
    engine = create_engine(db_url)

    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT machine_id, status, error_code FROM machine_states WHERE machine_id = :m ORDER BY time DESC LIMIT 1"),
            {"m": TEST_MACHINE}
        ).fetchone()

        if result:
            print("✔ SUCCESS: Persistierter Status in der Tenant-TimescaleDB gefunden!")
            print(f"     Machine ID: {result.machine_id}")
            print(f"     Status:     {result.status}")
            print(f"     Error Code: {result.error_code}")
            assert result.status == "error"
            assert result.error_code == "E-404-CNC"
        else:
            raise AssertionError("FAILURE: Kein Eintrag in der Tenant-DB gefunden!")


if __name__ == "__main__":
    print("--- Starte E2E-Test (Dockerized) ---")
    send_status_via_gateway()
    verify_database()
    print("--- E2E-Test erfolgreich abgeschlossen! ---")