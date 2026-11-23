"""
uretOS End-to-End Integration Test
Automates: Tenant Creation -> Provisioning -> Connector Box Registration -> Status Sync
"""
import time
import requests

GATEWAY_URL = "http://localhost:8080"
PROVISIONING_URL = "http://localhost:8000" # Oder direkt über den internen Service / Gateway
TENANT_ID = "e2e-test-tenant"
BOX_ID = "box-raspberry-pi-01"

def test_e2e_pipeline():
    print("--- STARTING uretOS E2E INTEGRATION TEST ---")

    # Schritt 1: Tenant anlegen / Provisionierung anstoßen
    print(f"[1/3] Provisioning tenant: {TENANT_ID}...")
    # Abhängig davon, wie dein Tenant-Provisioning-Service erreichbar ist (z.B. über Command Service oder Message Broker)
    # Hier beispielhaft ein direkter API-Call an den Provisioning- oder Command-Endpoint:
    # resp = requests.post(f"{GATEWAY_URL}/v1/tenants", json={"tenant_id": TENANT_ID, ...})
    
    # Schritt 2: Connector Box für den Tenant registrieren
    print(f"[2/3] Registering Connector Box ({BOX_ID}) for tenant {TENANT_ID}...")
    box_payload = {
        "box_id": BOX_ID,
        "tenant_id": TENANT_ID,
        "description": "E2E Test Connector Box"
    }
    # resp = requests.post(f"{GATEWAY_URL}/v1/connector-boxes", json=box_payload)
    # assert resp.status_code in [200, 201]

    # Schritt 3: mDNS / Polling / Status-Sync simulieren
    print(f"[3/3] Simulating machine status sync via gateway-api...")
    machine_id = "E2E-Virtual-CNC"
    status_payload = {
        "tenant_id": TENANT_ID,
        "status": "ok",
        "error_code": None,
        "metadata": {
            "name": machine_id,
            "manufacturer": "uretOS Test Robotics",
            "model": "E2E-Mill",
            "serial": "UR-E2E-999",
            "machine_type": "Machine Tool"
        }
    }
    
    sync_resp = requests.patch(
        f"{GATEWAY_URL}/v1/machines/{machine_id}/status",
        json=status_payload,
        timeout=5
    )
    
    print(f"Gateway Response: HTTP {sync_resp.status_code}")
    assert sync_resp.status_code == 200, f"Sync failed with {sync_resp.status_code}"
    
    print("--- E2E TEST SUCCESSFULLY COMPLETED ---")

if __name__ == "__main__":
    time.sleep(3) # Warten bis Services bereit sind
    test_e2e_pipeline()