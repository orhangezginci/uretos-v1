"""
uretOS Shopfloor Report Generator
Fragt die aktuellen Zustände über die Gateway-API ab und 
erstellt einen strukturierten Bericht über Box- und Maschinenzuweisungen.
"""
from __future__ import annotations

import requests

GATEWAY_URL = "http://localhost:8080"
TENANT_ID = "schwarzwald-metallwaren"

def print_shopfloor_report():
    print(f"\n" + "="*60)
    print(f"  uretOS SHOPFLOOR REPORT - Tenant: {TENANT_ID}")
    print("="*60)

    # 1. Alle Connector-Boxen abrufen
    try:
        resp = requests.get(f"{GATEWAY_URL}/v1/connector-boxes")
        if resp.status_code != 200:
            print(f"[ERROR] Konnte Connector-Boxen nicht abrufen: HTTP {resp.status_code}")
            return
        
        boxes = resp.get("connector_boxes", []) if isinstance(resp.json(), dict) else resp.json()
    except Exception as exc:
        print(f"[ERROR] Verbindungsfehler zum Gateway: {exc}")
        return

    tenant_boxes = [b for b in boxes if b.get("tenant_id") == TENANT_ID]

    if not tenant_boxes:
        print(f"\n[Info] Keine Connector-Boxen für Tenant '{TENANT_ID}' gefunden.")
        return

    total_machines_count = 0

    for box in tenant_boxes:
        hardware_id = box.get("hardware_id")
        box_id = box.get("box_id")
        status = box.get("status")

        print(f"\n📦 Connector Box: {hardware_id} (ID: {box_id})")
        print(f"   Status: {status.upper()}")

        # 2. Maschinen für diese Box über den Gateway-Endpunkt abrufen
        machines_resp = requests.get(f"{GATEWAY_URL}/v1/connector-boxes/{hardware_id}/machines")
        if machines_resp.status_code == 200:
            machines = machines_resp.json()
            total_machines_count += len(machines)
            
            print(f"   Zugeordnete Maschinen ({len(machines)} / Max. 5 Lizenz-Limit):")
            if not machines:
                print("     (Bisher keine Maschinen entdeckt/zugewiesen)")
            for m in machines:
                print(f"     ├── Machine-ID : {m.get('machine_id')}")
                print(f"     │   Name       : {m.get('name')}")
                print(f"     │   Status     : {m.get('metadata', {}).get('status', 'unknown')}")
        else:
            print(f"   [Warning] Konnte Maschinen für Box nicht laden: HTTP {machines_resp.status_code}")

    print("\n" + "-"*60)
    print(f"  ZUSAMMENFASSUNG:")
    print(f"  - Aktive Boxen     : {len(tenant_boxes)}")
    print(f"  - Total Maschinen  : {total_machines_count}")
    print(f"  - Lizenz-Status    : {'LIMIT EINGEHALTEN (<= 5 pro Box)' if all(len(requests.get(f'{GATEWAY_URL}/v1/connector-boxes/{b.get("hardware_id")}/machines').json()) <= 5 for b in tenant_boxes) else 'WARNUNG: LIMIT ÜBERSCHREITEN!'}")
    print("="*60 + "\n")

if __name__ == "__main__":
    print_shopfloor_report()