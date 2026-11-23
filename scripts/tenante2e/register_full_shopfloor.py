import json
import requests

GATEWAY_URL = "http://localhost:8080"

def register_full_shopfloor():
    hardware_id = "sim-box-01"
    tenant_id = "schwarzwald-metallwaren"
    
    print(f"1. Registriere/Prüfe Connector Box: {hardware_id} (Tenant: {tenant_id}) am Gateway...")
    box_payload = {
        "hardware_id": hardware_id,
        "tenant_id": tenant_id
    }
    
    try:
        # Registriert die Box direkt über den Gateway-Endpunkt
        reg_resp = requests.post(f"{GATEWAY_URL}/v1/connector-boxes/register", json=box_payload, timeout=10)
        reg_resp.raise_for_status()
        print("Connector Box erfolgreich am Gateway registriert.")
    except Exception as exc:
        print(f"Fehler beim Registrieren der Box am Gateway: {exc}")
        return

    # Die 8 Maschinen aus deiner shopfloor.yaml
    machines = [
        {
            "hardware_id": hardware_id,
            "machines": [
                {
                    "machine_id": "urn:uretos:machine:CNC-LATHE-01",
                    "name": "CNC Lathe 01",
                    "manufacturer": "DMG Mori",
                    "model": "NLX 2500",
                    "machine_type": "Machine Tool",
                    "status": "ok"
                }
            ]
        },
        {
            "hardware_id": hardware_id,
            "machines": [
                {
                    "machine_id": "urn:uretos:machine:CNC-LATHE-02",
                    "name": "CNC Lathe 02",
                    "manufacturer": "DMG Mori",
                    "model": "NLX 2500",
                    "machine_type": "Machine Tool",
                    "status": "ok"
                }
            ]
        },
        {
            "hardware_id": hardware_id,
            "machines": [
                {
                    "machine_id": "urn:uretos:machine:CNC-LATHE-03",
                    "name": "CNC Lathe 03",
                    "manufacturer": "DMG Mori",
                    "model": "NLX 2500",
                    "machine_type": "Machine Tool",
                    "status": "ok"
                }
            ]
        },
        {
            "hardware_id": hardware_id,
            "machines": [
                {
                    "machine_id": "urn:uretos:machine:CNC-LATHE-04",
                    "name": "CNC Lathe 04",
                    "manufacturer": "DMG Mori",
                    "model": "NLX 2500",
                    "machine_type": "Machine Tool",
                    "status": "ok"
                }
            ]
        },
        {
            "hardware_id": hardware_id,
            "machines": [
                {
                    "machine_id": "urn:uretos:machine:CNC-LATHE-05",
                    "name": "CNC Lathe 05",
                    "manufacturer": "DMG Mori",
                    "model": "NLX 2500",
                    "machine_type": "Machine Tool",
                    "status": "ok"
                }
            ]
        },
        {
            "hardware_id": hardware_id,
            "machines": [
                {
                    "machine_id": "urn:uretos:machine:CNC-MILL-06",
                    "name": "CNC Mill 06",
                    "manufacturer": "Hermle",
                    "model": "C 42U",
                    "machine_type": "Machine Tool",
                    "status": "ok"
                }
            ]
        },
        {
            "hardware_id": hardware_id,
            "machines": [
                {
                    "machine_id": "urn:uretos:machine:CNC-MILL-07",
                    "name": "CNC Mill 07",
                    "manufacturer": "Hermle",
                    "model": "C 42U",
                    "machine_type": "Machine Tool",
                    "status": "ok"
                }
            ]
        },
        {
            "hardware_id": hardware_id,
            "machines": [
                {
                    "machine_id": "urn:uretos:machine:CNC-MILL-08",
                    "name": "CNC Mill 08",
                    "manufacturer": "Hermle",
                    "model": "C 42U",
                    "machine_type": "Machine Tool",
                    "status": "ok"
                }
            ]
        }
    ]

    print("2. Registriere Maschinen über den Gateway Autoscan-Endpunkt...")
    for payload in machines:
        m_name = payload["machines"][0]["name"]
        try:
            # Nutzt den bereits im Poller erprobten Autoscan-Endpunkt der Gateway-API
            resp = requests.post(f"{GATEWAY_URL}/v1/connector-boxes/autoscan", json=payload, timeout=10)
            if resp.status_code == 200:
                print(f"  -> Maschine '{m_name}' erfolgreich registriert.")
            else:
                print(f"  -> Warnung bei '{m_name}': Status {resp.status_code} - {resp.text}")
        except Exception as exc:
            print(f"  -> Netzwerkfehler bei '{m_name}': {exc}")

    print("Virtueller Shopfloor erfolgreich über die Gateway-API eingerichtet!")

if __name__ == "__main__":
    register_full_shopfloor()