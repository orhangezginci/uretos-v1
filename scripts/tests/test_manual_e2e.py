"""
Extended Manual E2E Test Script for uretOS Pipeline (mit korrigierten Payloads)
"""
import requests

GATEWAY_URL = "http://localhost:8080"
TENANT_ID = "test-tenant-e2e"
BOX_ID = "box-raspberry-pi-01"
MACHINE_ID = "Manual-E2E-CNC-01"

def run_extended_e2e_test():
    print("--- STARTE ERWEITERTEN E2E-TEST ---")

    # Schritt 1: Tenant anlegen (Erwartet nur tenant_id)
    print(f"[1/3] Erstelle Tenant / triggere Provisioning für: {TENANT_ID}")
    tenant_payload = {
        "tenant_id": TENANT_ID
    }
    try:
        resp = requests.post(f"{GATEWAY_URL}/v1/tenants", json=tenant_payload, timeout=30)
        print(f"Tenant-Provisioning Antwort: HTTP {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"Fehler bei Schritt 1: {e}")

    # Schritt 2: Connector Box registrieren (Erwartet tenant_id, hardware_id UND mac_address)
    print(f"[2/3] Registriere Connector Box ({BOX_ID}) für Tenant {TENANT_ID}")
    box_payload = {
        "tenant_id": TENANT_ID,
        "hardware_id": BOX_ID,
        "mac_address": "00:11:22:33:44:55"
    }
    try:
        resp = requests.post(f"{GATEWAY_URL}/v1/connector-boxes", json=box_payload, timeout=30)
        print(f"Connector-Box-Registrierung Antwort: HTTP {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"Fehler bei Schritt 2: {e}")

    # Schritt 3: Maschinen-Status-Update via PATCH
    print(f"[3/3] Sende Maschinen-Status-Update für {MACHINE_ID}")
    status_payload = {
        "tenant_id": TENANT_ID,
        "status": "ok",
        "error_code": None,
        "metadata": {
            "name": MACHINE_ID,
            "manufacturer": "Manual Test Machine Corp",
            "model": "Model-X1",
            "serial": "SN-MANUAL-001",
            "machine_type": "Machine Tool"
        }
    }

    try:
        resp = requests.patch(
            f"{GATEWAY_URL}/v1/machines/{MACHINE_ID}/status",
            json=status_payload,
            timeout=5
        )
        print(f"Status-Update Antwort: HTTP {resp.status_code} - {resp.text}")
        if resp.status_code == 200:
            print("Erfolgreich! Die gesamte Kette wurde durchlaufen.")
        else:
            print(f"Fehlerhafte Antwort: {resp.text}")
    except Exception as e:
        print(f"Verbindungsfehler bei Status-Update: {e}")

    print("--- E2E-TEST BEENDET ---")

if __name__ == "__main__":
    run_extended_e2e_test()