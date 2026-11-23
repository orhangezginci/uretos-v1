This file is a merged representation of the entire codebase, combined into a single document by Repomix.
The content has been processed where security check has been disabled.

# File Summary

## Purpose
This file contains a packed representation of the entire repository's contents.
It is designed to be easily consumable by AI systems for analysis, code review,
or other automated processes.

## File Format
The content is organized as follows:
1. This summary section
2. Repository information
3. Directory structure
4. Repository files (if enabled)
5. Multiple file entries, each consisting of:
  a. A header with the file path (## File: path/to/file)
  b. The full contents of the file in a code block

## Usage Guidelines
- This file should be treated as read-only. Any changes should be made to the
  original repository files, not this packed version.
- When processing this file, use the file path to distinguish
  between different files in the repository.
- Be aware that this file may contain sensitive information. Handle it with
  the same level of security as you would the original repository.

## Notes
- Some files may have been excluded based on .gitignore rules and Repomix's configuration
- Binary files are not included in this packed representation. Please refer to the Repository Structure section for a complete list of file paths, including binary files
- Files matching patterns in .gitignore are excluded
- Files matching default ignore patterns are excluded
- Security check has been disabled - content may contain sensitive information
- Files are sorted by Git change count (files with more changes are at the bottom)

# Directory Structure
```
contracts/
  .gitkeep
  cloudevent-v1.0.json
infra/
  rabbitmq/
    definitions.json
    rabbitmq.conf
  .gitkeep
scripts/
  tests/
    e2e_integration_test.py
    generate_shopfloor_report.py
    test_hierarchical_shopfloor.py
    test_manual_e2e.py
  .gitkeep
  e2e_gateway_timescale_test.py
  e2e_timescale_query_test.py
  reset-dev.sh
  test_machine_registration_e2e.py
  test_tenant_provisioning_e2e.py
services/
  connector-box-command-service/
    app/
      cloudevents.py
      db.py
      main.py
    contracts/
      cloudevent-v1.0.json
    Dockerfile
    requirements.txt
  connector-box-poller/
    src/
      discovery.py
      main.py
    Dockerfile
    requirements.txt
  connector-box-query-service/
    app/
      cloudevents.py
      db.py
      main.py
    contracts/
      cloudevent-v1.0.json
    Dockerfile
    requirements.txt
  gateway-api/
    app/
      cloudevents.py
      main.py
    contracts/
      cloudevent-v1.0.json
    tests/
      e2e_test_machines.py
    Dockerfile
    requirements.txt
  machine-command-service/
    contracts/
      cloudevent-v1.0.json
    src/
      cloudevents.py
      db.py
      main.py
      models.py
    Dockerfile
    requirements.txt
  machine-query-service/
    contracts/
      cloudevent-v1.0.json
    src/
      cloudevents.py
      db.py
      main.py
      models.py
    Dockerfile
    requirements.txt
  shopfloor-bff-api/
    src/
      cloudevents.py
      main.py
    Dockerfile
    requirements.txt
  shopfloor-stream-service/
    contracts/
      cloudevent-v1.0.json
    src/
      cloudevents.py
      main.py
    Dockerfile
    requirements.txt
  tenant-command-service/
    app/
      cloudevents.py
      db.py
      main.py
      models.py
    contracts/
      cloudevent-v1.0.json
    Dockerfile
    requirements.txt
  tenant-provisioning-service/
    app/
      cloudevents.py
      init-extension.sql
      main.py
      provisioning.py
    contracts/
      cloudevent-v1.0.json
    Dockerfile
    requirements.txt
  tenant-query-service/
    app/
      cloudevents.py
      db.py
      main.py
      models.py
    contracts/
      cloudevent-v1.0.json
    Dockerfile
    requirements.txt
  timescale-query-service/
    src/
      cloudevents.py
      db.py
      main.py
      models.py
    Dockerfile
    requirements.txt
  timescale-writer-service/
    contracts/
      cloudevent-v1.0.json
    src/
      contracts/
        cloudevent-v1.0.json
      cloudevents.py
      db.py
      main.py
      models.py
    Dockerfile
    requirements.txt
  .gitkeep
tools/
  admin-panel/
    app.py
    requirements.txt
  connector-box-simulator/
    app.py
    discovery.py
    requirements.txt
  opc-machine-sim/
    src/
      main.py
    Dockerfile
    requirements.txt
  shopfloor-stream-poc/
    index.html
  app.py
.gitignore
docker-compose.yml
README.md
repomix.config.json
shopfloor.yaml
```

# Files

## File: contracts/.gitkeep
```

```

## File: infra/.gitkeep
```

```

## File: scripts/tests/e2e_integration_test.py
```python
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
```

## File: scripts/tests/generate_shopfloor_report.py
```python
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
```

## File: scripts/tests/test_hierarchical_shopfloor.py
```python
"""
Vollautomatisches E2E-Shopfloor-Testskript für 'Schwarzwald-Metallwaren':
Setzt die Umgebung bei jedem Start komplett auf 0 zurück (Clean Reset via Docker),
provisioniert den Tenant, paired die Boxen und verifiziert das 5er-Lizenzlimit.
"""
from __future__ import annotations

import subprocess
import time
import requests

GATEWAY_URL = "http://localhost:8080"
TENANT_ID = "schwarzwald-metallwaren"

def reset_and_start_docker():
    print("--- [0/4] Setze Umgebung komplett auf 0 zurück (Clean Reset) ---")
    try:
        print("Fahre alte Container herunter und lösche Volumes...")
        subprocess.run(["docker", "compose", "down", "-v", "--remove-orphans"], check=True, stdout=subprocess.DEVNULL)
        
        # Kurz warten, damit Docker die Container-Namen im Daemon garantiert freigibt
        time.sleep(3)
        
        print("Starte Docker-Stack frisch...")
        subprocess.run(["docker", "compose", "up", "-d"], check=True, stdout=subprocess.DEVNULL)
        
        print("Warte 15 Sekunden, bis RabbitMQ, PostgreSQL und Services voll da sind...")
        time.sleep(15)
        print("  -> Umgebung ist bereit und sauber aufgesetzt!\n")
    except Exception as exc:
        print(f"[ERROR] Konnte Docker-Umgebung nicht starten: {exc}")
        exit(1)

def print_shopfloor_report():
    print(f"\n" + "="*60)
    print(f"  uretOS SHOPFLOOR REPORT - Tenant: {TENANT_ID}")
    print("="*60)

    try:
        resp = requests.get(f"{GATEWAY_URL}/v1/connector-boxes")
        if resp.status_code != 200:
            print(f"[ERROR] Konnte Connector-Boxen nicht abrufen: HTTP {resp.status_code}")
            return
        
        boxes = resp.json()
        tenant_boxes = [b for b in boxes if b.get("tenant_id") == TENANT_ID]
    except Exception as exc:
        print(f"[ERROR] Verbindungsfehler zum Gateway: {exc}")
        return

    if not tenant_boxes:
        print(f"\n[Info] Keine Connector-Boxen für Tenant '{TENANT_ID}' gefunden.")
        return

    total_machines_count = 0
    box_stats = []

    for box in tenant_boxes:
        hardware_id = box.get("hardware_id")
        box_id = box.get("box_id")
        status = box.get("status")

        print(f"\n📦 Connector Box: {hardware_id} (ID: {box_id})")
        print(f"   Status: {status.upper()}")

        machines_resp = requests.get(f"{GATEWAY_URL}/v1/connector-boxes/{hardware_id}/machines")
        if machines_resp.status_code == 200:
            machines = machines_resp.json()
            total_machines_count += len(machines)
            box_stats.append((hardware_id, len(machines)))
            
            print(f"   Zugeordnete Maschinen ({len(machines)} / Max. 5 Lizenz-Limit):")
            if not machines:
                print("     (Bisher keine Maschinen entdeckt)")
            for m in machines:
                print(f"     ├── Machine-ID : {m.get('machine_id')}")
                print(f"     │   Name       : {m.get('name')}")
        else:
            print(f"   [Warning] Konnte Maschinen für Box nicht laden: HTTP {machines_resp.status_code}")

    print("\n" + "-"*60)
    print(f"  ZUSAMMENFASSUNG:")
    print(f"  - Aktive Boxen     : {len(tenant_boxes)}")
    print(f"  - Total Maschinen  : {total_machines_count}")
    limit_ok = all(count <= 5 for _, count in box_stats)
    print(f"  - Lizenz-Status    : {'LIMIT EINGEHALTEN (<= 5 pro Box)' if limit_ok else 'WARNUNG: LIZENZLIMIT ÜBERSCHRITTEN!'}")
    print("="*60 + "\n")

def run_hierarchical_test():
    # 0. Umgebung plattmachen und frisch hochfahren
    reset_and_start_docker()

    print("--- Starte realistisches Shopfloor-E2E-Setup ---")

    # 1. Tenant anlegen
    print(f"\n[1/3] Provisioniere Tenant: {TENANT_ID}")
    resp = requests.post(f"{GATEWAY_URL}/v1/tenants", json={"tenant_id": TENANT_ID})
    print(f"Tenant-Status: HTTP {resp.status_code} - {resp.text}")

    # 2. Connector Boxen registrieren und pairen
    boxes = [
        {"hardware_id": "box-sw-01", "mac_address": "AA:BB:CC:DD:EE:01"},
        {"hardware_id": "box-sw-02", "mac_address": "AA:BB:CC:DD:EE:02"}
    ]

    for box in boxes:
        print(f"\n[2/3] Registriere & Paiere Box: {box['hardware_id']}")
        requests.post(f"{GATEWAY_URL}/v1/connector-boxes", json={**box, "tenant_id": TENANT_ID})
        resp_pair = requests.post(f"{GATEWAY_URL}/v1/connector-boxes/pair", json={"hardware_id": box["hardware_id"]})
        print(f"  -> Pairing-Status: HTTP {resp_pair.status_code} - {resp_pair.text}")

    print("\n[3/3] Setup aktiv. Warte auf mDNS-Discovery und Sync (ca. 8 Sekunden)...")
    time.sleep(8)

    # Report generieren
    print_shopfloor_report()

if __name__ == "__main__":
    run_hierarchical_test()
```

## File: scripts/tests/test_manual_e2e.py
```python
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
```

## File: scripts/.gitkeep
```

```

## File: services/tenant-provisioning-service/app/cloudevents.py
```python
"""
Minimal CloudEvent v1.0 (uretOS dialect) envelope helper.

This module is intentionally duplicated per-service rather than shared as a
library, per uretOS's hyper-decoupled architecture principle. Any service
needing this logic should copy this file, not import it from elsewhere.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import jsonschema

_SCHEMA_PATH = Path(__file__).parent.parent / "contracts" / "cloudevent-v1.0.json"
_SCHEMA = json.loads(_SCHEMA_PATH.read_text())


def build_envelope(
    *,
    event_type: str,
    source: str,
    data: dict[str, Any],
    tenant_id: str,
    messagetype: str = "event",
    correlation_id: Optional[str] = None,
    subject: Optional[str] = None,
) -> dict[str, Any]:
    """Build a CloudEvent envelope dict ready to be published to RabbitMQ."""
    envelope = {
        "specversion": "1.0",
        "id": str(uuid.uuid4()),
        "source": source,
        "type": event_type,
        "datacontenttype": "application/json",
        "time": datetime.now(timezone.utc).isoformat(),
        "correlationid": correlation_id or str(uuid.uuid4()),
        "messagetype": messagetype,
        "tenantid": tenant_id,
        "data": data,
    }
    if subject:
        envelope["subject"] = subject
    validate_envelope(envelope)
    return envelope


def validate_envelope(envelope: dict[str, Any]) -> None:
    """Raises jsonschema.ValidationError if the envelope is malformed."""
    jsonschema.validate(instance=envelope, schema=_SCHEMA)


def loads(raw_body: bytes) -> dict[str, Any]:
    """Parse and validate a raw RabbitMQ message body into an envelope."""
    envelope = json.loads(raw_body)
    validate_envelope(envelope)
    return envelope
```

## File: services/tenant-provisioning-service/contracts/cloudevent-v1.0.json
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "uretOS CloudEvent v1.0 Specification",
  "description": "Standardized CloudEvent envelope for all asynchronous message exchanges across uretOS services. This file is a documentation/validation copy local to this service - it is intentionally NOT imported from a shared package (hyper-decoupled principle).",
  "type": "object",
  "required": [
    "specversion",
    "id",
    "source",
    "type",
    "datacontenttype",
    "time",
    "correlationid",
    "messagetype",
    "tenantid",
    "data"
  ],
  "properties": {
    "specversion": { "type": "string", "const": "1.0" },
    "id": { "type": "string", "format": "uuid" },
    "source": { "type": "string", "format": "uri-reference" },
    "type": { "type": "string" },
    "datacontenttype": { "type": "string", "const": "application/json" },
    "time": { "type": "string", "format": "date-time" },
    "correlationid": { "type": "string", "format": "uuid" },
    "messagetype": { "type": "string", "enum": ["event", "command", "query"] },
    "tenantid": {
      "type": "string",
      "minLength": 1,
      "description": "Identifies which tenant this message belongs to. Reserved value 'system' is used for super_admin-level operations such as tenant provisioning itself."
    },
    "subject": { "type": "string" },
    "data": { "type": "object" }
  }
}
```

## File: services/tenant-provisioning-service/Dockerfile
```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY contracts/ ./contracts/
COPY app/ ./app/

WORKDIR /app/app
CMD ["python", "main.py"]
```

## File: services/.gitkeep
```

```

## File: tools/opc-machine-sim/src/main.py
```python
"""
Standard-Compliant Single-Machine OPC-UA Server Simulator for uretOS Virtual Shopfloor.
Located in tools/ as a companion utility for trial periods and testing.
"""
from __future__ import annotations

import logging
import os
import socket
import time
from opcua import Server, ua
from zeroconf import ServiceInfo, Zeroconf

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("opc-machine-sim")

MACHINE_NAME = os.environ.get("MACHINE_NAME", "VirtualCNC-01")
MANUFACTURER = os.environ.get("MANUFACTURER", "uretOS Robotics")
MODEL = os.environ.get("MODEL", "V-Mill 500")
SERIAL = os.environ.get("SERIAL", "UR-2026-001")
PORT = int(os.environ.get("PORT", "4840"))


def main() -> None:
    server = Server()
    server.set_endpoint(f"opc.tcp://0.0.0.0:{PORT}")

    # Namespaces registrieren (Standard DI & Machinery URIs für native Erkennung durch discovery.py)
    uri_di = "http://opcfoundation.org/UA/DI/"
    uri_machinery = "http://opcfoundation.org/UA/Machinery/"
    
    idx_di = server.register_namespace(uri_di)
    idx_mach = server.register_namespace(uri_machinery)
    idx_custom = server.register_namespace("http://uretos.io/opcua/machine")

    objects = server.get_objects_node()

    # OPC DI / Machinery Struktur: DeviceSet -> Maschinen-Instanz -> Identification
    deviceset = objects.add_object(idx_di, "DeviceSet")
    machine_node = deviceset.add_object(idx_custom, MACHINE_NAME)

    ident_node = machine_node.add_object(idx_di, "Identification")
    ident_node.add_variable(idx_di, "Manufacturer", MANUFACTURER)
    ident_node.add_variable(idx_di, "Model", MODEL)
    ident_node.add_variable(idx_di, "SerialNumber", SERIAL)
    ident_node.add_variable(idx_di, "ProductInstanceUri", f"urn:uretos:machine:{MACHINE_NAME}")

    # Status-Variable für den Poller
    status_var = machine_node.add_variable(idx_custom, "Status", "ok")
    status_var.set_writable()

    server.start()
    log.info("Standard-compliant OPC-UA Server for '%s' running on port %d", MACHINE_NAME, PORT)

    # mDNS Zeroconf Registrierung für Zero-Configuration Discovery im LAN
    zeroconf = None
    info = None
    try:
        service_type = "_opcua-tcp._tcp.local."
        service_name = f"{MACHINE_NAME}._opcua-tcp._tcp.local."
        
        # Lokale IP-Adresse ermitteln
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("10.255.255.255", 1))
            local_ip = s.getsockname()[0]
        except Exception:
            local_ip = "127.0.0.1"
        finally:
            s.close()

        zc_ip_bytes = socket.inet_aton(local_ip)
        
        info = ServiceInfo(
            service_type,
            service_name,
            addresses=[zc_ip_bytes],
            port=PORT,
            properties={"manufacturer": MANUFACTURER, "model": MODEL, "serial": SERIAL},
            server=f"{MACHINE_NAME.lower().replace(' ', '-')}.local.",
        )
        
        zeroconf = Zeroconf()
        zeroconf.register_service(info)
        log.info("mDNS service registered: %s at %s:%d", service_name, local_ip, PORT)
    except Exception as exc:
        log.warning("Could not register mDNS service: %s", exc)

    try:
        while True:
            time.sleep(1)
    finally:
        if zeroconf and info:
            zeroconf.unregister_service(info)
            zeroconf.close()
        server.stop()
        log.info("OPC-UA server stopped.")


if __name__ == "__main__":
    main()
```

## File: tools/opc-machine-sim/Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

ENV PYTHONPATH=/app/src

EXPOSE 4840

CMD ["python", "src/main.py"]
```

## File: tools/opc-machine-sim/requirements.txt
```
opcua>=0.98.13
zeroconf>=0.39.0
```

## File: README.md
```markdown
# uretOS

> uretOS is the operating system for modern manufacturing — connecting
> machines, processes and production data into one open, event-driven
> platform.

**Plan. Produce. Monitor. Optimize.**

uretOS is a Manufacturing Operating System, not a classical ERP: an open,
modular runtime for production. It connects machines, production processes,
and shopfloor data through event-driven communication and real-time
monitoring — with AI-assisted analysis and optimization planned for later
stages, from the shopfloor to the cloud.

## Architecture principles

- **Hyper-decoupled**: no shared runtime libraries between services.
  Duplication is preferred over coupling.
- **Message/event-driven**: all inter-service communication goes through
  RabbitMQ. No direct service-to-service calls.
- **CQRS per domain**: each domain with DB access gets a separate
  command-service (writes) and a generic, GraphQL-fed read-service (reads).
  Responses run over RPC.
- **Multi-tenant SaaS**: two user levels — `super_admin` (provisions tenants
  and connector boxes) and per-tenant users (`admin`, `operator`, ...).
  Each tenant gets its own isolated database containers.

## Status

Early rebuild (`v1`) of the project — the previous `uretos` repository is
kept as a proof-of-concept / reference, not as a base to build on.
```

## File: repomix.config.json
```json
{
  "$schema": "https://repomix.com/schemas/latest/schema.json",
  "input": {
    "maxFileSize": 52428800
  },
  "output": {
    "filePath": "repomix-output.json",
    "style": "json",
    "filePathStyle": "target-relative",
    "parsableStyle": false,
    "fileSummary": true,
    "directoryStructure": true,
    "files": true,
    "removeComments": false,
    "removeEmptyLines": false,
    "compress": false,
    "topFilesLength": 5,
    "showLineNumbers": false,
    "truncateBase64": false,
    "copyToClipboard": false,
    "includeFullDirectoryStructure": false,
    "tokenCountTree": false,
    "git": {
      "sortByChanges": true,
      "sortByChangesMaxCommits": 100,
      "includeDiffs": false,
      "includeLogs": false,
      "includeLogsCount": 50
    }
  },
  "include": [],
  "ignore": {
    "useGitignore": true,
    "useDotIgnore": true,
    "useDefaultPatterns": true,
    "customPatterns": []
  },
  "security": {
    "enableSecurityCheck": false
  },
  "tokenCount": {
    "encoding": "o200k_base"
  }
}
```

## File: shopfloor.yaml
```yaml
version: '3.8'

services:
  machine-lathe-01:
    build: ./tools/opc-machine-sim
    container_name: opc-machine-lathe-01
    environment:
      - MACHINE_NAME=CNC-LATHE-01
      - MANUFACTURER=DMG Mori
      - MODEL=NLX 2500
      - SERIAL=SN-DMG-01
      - PORT=4840
    ports:
      - "4840:4840"
    networks:
      - default
    restart: unless-stopped

  machine-lathe-02:
    build: ./tools/opc-machine-sim
    container_name: opc-machine-lathe-02
    environment:
      - MACHINE_NAME=CNC-LATHE-02
      - MANUFACTURER=DMG Mori
      - MODEL=NLX 2500
      - SERIAL=SN-DMG-02
      - PORT=4841
    ports:
      - "4841:4841"
    networks:
      - default
    restart: unless-stopped

  machine-lathe-03:
    build: ./tools/opc-machine-sim
    container_name: opc-machine-lathe-03
    environment:
      - MACHINE_NAME=CNC-LATHE-03
      - MANUFACTURER=DMG Mori
      - MODEL=NLX 2500
      - SERIAL=SN-DMG-03
      - PORT=4842
    ports:
      - "4842:4842"
    networks:
      - default
    restart: unless-stopped

  machine-lathe-04:
    build: ./tools/opc-machine-sim
    container_name: opc-machine-lathe-04
    environment:
      - MACHINE_NAME=CNC-LATHE-04
      - MANUFACTURER=DMG Mori
      - MODEL=NLX 2500
      - SERIAL=SN-DMG-04
      - PORT=4843
    ports:
      - "4843:4843"
    networks:
      - default
    restart: unless-stopped

  machine-lathe-05:
    build: ./tools/opc-machine-sim
    container_name: opc-machine-lathe-05
    environment:
      - MACHINE_NAME=CNC-LATHE-05
      - MANUFACTURER=DMG Mori
      - MODEL=NLX 2500
      - SERIAL=SN-DMG-05
      - PORT=4844
    ports:
      - "4844:4844"
    networks:
      - default
    restart: unless-stopped

  machine-mill-06:
    build: ./tools/opc-machine-sim
    container_name: opc-machine-mill-06
    environment:
      - MACHINE_NAME=CNC-MILL-06
      - MANUFACTURER=Hermle
      - MODEL=C 42U
      - SERIAL=SN-HER-06
      - PORT=4845
    ports:
      - "4845:4845"
    networks:
      - default
    restart: unless-stopped

  machine-mill-07:
    build: ./tools/opc-machine-sim
    container_name: opc-machine-mill-07
    environment:
      - MACHINE_NAME=CNC-MILL-07
      - MANUFACTURER=Hermle
      - MODEL=C 42U
      - SERIAL=SN-HER-07
      - PORT=4846
    ports:
      - "4846:4846"
    networks:
      - default
    restart: unless-stopped

  machine-mill-08:
    build: ./tools/opc-machine-sim
    container_name: opc-machine-mill-08
    environment:
      - MACHINE_NAME=CNC-MILL-08
      - MANUFACTURER=Hermle
      - MODEL=C 42U
      - SERIAL=SN-HER-08
      - PORT=4847
    ports:
      - "4847:4847"
    networks:
      - default
    restart: unless-stopped
```

## File: contracts/cloudevent-v1.0.json
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "uretOS CloudEvent v1.0 Specification",
  "description": "Standardized CloudEvent envelope for all asynchronous message exchanges across uretOS services. This is documentation/reference only - services copy this file locally rather than importing it as a shared package (hyper-decoupled principle).",
  "type": "object",
  "required": [
    "specversion",
    "id",
    "source",
    "type",
    "datacontenttype",
    "time",
    "correlationid",
    "messagetype",
    "tenantid",
    "data"
  ],
  "properties": {
    "specversion": {
      "type": "string",
      "const": "1.0",
      "description": "CloudEvents specification version."
    },
    "id": {
      "type": "string",
      "format": "uuid",
      "description": "Unique identifier for the specific event instance."
    },
    "source": {
      "type": "string",
      "format": "uri-reference",
      "description": "Identifies the context or service in which an event happened (e.g., 'uretos/services/machine-command-service')."
    },
    "type": {
      "type": "string",
      "description": "Describes the type of event related to the originating occurrence (e.g., 'uretos.machine.command.create')."
    },
    "datacontenttype": {
      "type": "string",
      "const": "application/json",
      "description": "Content type of data value."
    },
    "time": {
      "type": "string",
      "format": "date-time",
      "description": "Timestamp when the occurrence happened (ISO 8601 / RFC 3339)."
    },
    "correlationid": {
      "type": "string",
      "format": "uuid",
      "description": "Mandatory tracing ID passed across execution flows to correlate events, commands, and queries."
    },
    "messagetype": {
      "type": "string",
      "enum": ["event", "command", "query"],
      "description": "Explicit message categorization for strict workflow handling."
    },
    "tenantid": {
      "type": "string",
      "minLength": 1,
      "description": "Identifies which tenant this message belongs to. Reserved value 'system' is used for super_admin-level operations such as tenant provisioning itself."
    },
    "subject": {
      "type": "string",
      "description": "Optional subject of the event in the context of the event producer (e.g., entity ID)."
    },
    "data": {
      "type": "object",
      "description": "Domain payload associated with the message."
    }
  }
}
```

## File: infra/rabbitmq/definitions.json
```json
{
  "rabbit_version": "3.13.0",
  "vhosts": [
    { "name": "/" }
  ],
  "users": [
    {
      "name": "uretos",
      "password": "uretos_dev_pass",
      "tags": ["administrator"]
    },
    {
      "name": "uretos_system",
      "password": "uretos_system_dev_pass",
      "tags": []
    }
  ],
  "permissions": [
    {
      "user": "uretos",
      "vhost": "/",
      "configure": ".*",
      "write": ".*",
      "read": ".*"
    },
    {
      "user": "uretos_system",
      "vhost": "/",
      "configure": ".*",
      "write": ".*",
      "read": ".*"
    }
  ],
  "exchanges": [
    {
      "name": "uretos.events",
      "vhost": "/",
      "type": "topic",
      "durable": true,
      "auto_delete": false,
      "internal": false,
      "arguments": {}
    }
  ],
  "queues": [],
  "bindings": []
}
```

## File: infra/rabbitmq/rabbitmq.conf
```ini
management.load_definitions = /etc/rabbitmq/definitions.json
```

## File: scripts/e2e_gateway_timescale_test.py
```python
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
```

## File: scripts/e2e_timescale_query_test.py
```python
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
```

## File: scripts/test_machine_registration_e2e.py
```python
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
```

## File: scripts/test_tenant_provisioning_e2e.py
```python
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
```

## File: services/connector-box-command-service/app/cloudevents.py
```python
"""
Minimal CloudEvent v1.0 (uretOS dialect) envelope helper.

This module is intentionally duplicated per-service rather than shared as a
library, per uretOS's hyper-decoupled architecture principle. Any service
needing this logic should copy this file, not import it from elsewhere.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import jsonschema

_SCHEMA_PATH = Path(__file__).parent.parent / "contracts" / "cloudevent-v1.0.json"
_SCHEMA = json.loads(_SCHEMA_PATH.read_text())


def build_envelope(
    *,
    event_type: str,
    source: str,
    data: dict[str, Any],
    tenant_id: str,
    messagetype: str = "event",
    correlation_id: Optional[str] = None,
    subject: Optional[str] = None,
) -> dict[str, Any]:
    """Build a CloudEvent envelope dict ready to be published to RabbitMQ."""
    envelope = {
        "specversion": "1.0",
        "id": str(uuid.uuid4()),
        "source": source,
        "type": event_type,
        "datacontenttype": "application/json",
        "time": datetime.now(timezone.utc).isoformat(),
        "correlationid": correlation_id or str(uuid.uuid4()),
        "messagetype": messagetype,
        "tenantid": tenant_id,
        "data": data,
    }
    if subject:
        envelope["subject"] = subject
    validate_envelope(envelope)
    return envelope


def validate_envelope(envelope: dict[str, Any]) -> None:
    """Raises jsonschema.ValidationError if the envelope is malformed."""
    jsonschema.validate(instance=envelope, schema=_SCHEMA)


def loads(raw_body: bytes) -> dict[str, Any]:
    """Parse and validate a raw RabbitMQ message body into an envelope."""
    envelope = json.loads(raw_body)
    validate_envelope(envelope)
    return envelope
```

## File: services/connector-box-command-service/contracts/cloudevent-v1.0.json
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "uretOS CloudEvent v1.0 Specification",
  "description": "Standardized CloudEvent envelope for all asynchronous message exchanges across uretOS services. This file is a documentation/validation copy local to this service - it is intentionally NOT imported from a shared package (hyper-decoupled principle).",
  "type": "object",
  "required": [
    "specversion",
    "id",
    "source",
    "type",
    "datacontenttype",
    "time",
    "correlationid",
    "messagetype",
    "tenantid",
    "data"
  ],
  "properties": {
    "specversion": { "type": "string", "const": "1.0" },
    "id": { "type": "string", "format": "uuid" },
    "source": { "type": "string", "format": "uri-reference" },
    "type": { "type": "string" },
    "datacontenttype": { "type": "string", "const": "application/json" },
    "time": { "type": "string", "format": "date-time" },
    "correlationid": { "type": "string", "format": "uuid" },
    "messagetype": { "type": "string", "enum": ["event", "command", "query"] },
    "tenantid": {
      "type": "string",
      "minLength": 1,
      "description": "Identifies which tenant this message belongs to. Reserved value 'system' is used for super_admin-level operations such as tenant provisioning itself."
    },
    "subject": { "type": "string" },
    "data": { "type": "object" }
  }
}
```

## File: services/connector-box-command-service/Dockerfile
```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY contracts/ ./contracts/
COPY app/ ./app/

WORKDIR /app/app
CMD ["python", "main.py"]
```

## File: services/connector-box-command-service/requirements.txt
```
pika==1.3.2
jsonschema==4.23.0
psycopg[binary]==3.2.3
pyjwt==2.9.0
```

## File: services/connector-box-poller/src/discovery.py
```python
"""
discovery.py - Multi-machine OPC UA identity discovery for the uretOS Connector Box.

Goal: find name, manufacturer, model, serial number and machine type for up to 
N licensed machines (supporting umati multi-machine instances as well as 1:1 production servers).

  Stage 1  Official standards   BuildInfo, OPC 40001 Machinery (Machines/Identification),
                                OPC 10000-100 DI (DeviceSet), Companion-Spec namespaces -> type
  Stage 2  Vendor patterns      data-driven profiles (Siemens, Index, Fanuc, ...) - see VENDOR_PROFILES
  Stage 3  Generic tree scan    bounded BFS, scores properties/objects by name
"""
from __future__ import annotations

import logging
import re
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

from opcua import Client, ua

log = logging.getLogger("uretos.discovery")

# --------------------------------------------------------------------------- #
# Configuration / knowledge tables
# --------------------------------------------------------------------------- #

MACHINERY_URI = "http://opcfoundation.org/UA/Machinery/"
DI_URI = "http://opcfoundation.org/UA/DI/"

SPEC_TYPES = {
    "/UA/MachineTool/": "Machine Tool",
    "/UA/Robotics/": "Robot",
    "/UA/PackML/": "Packaging Machine",
    "/UA/PlasticsRubber/": "Plastics/Rubber Machine",
    "/UA/Woodworking/": "Woodworking Machine",
    "/UA/Weihenstephan/": "Food & Beverage Machine",
    "/UA/AdditiveManufacturing/": "Additive Manufacturing",
    "/UA/GMS/": "Coordinate Measuring Machine",
}

ALIASES = {
    # ---------- manufacturer ----------
    "manufacturer": "manufacturer",
    "manufacturername": "manufacturer",
    "vendorname": "manufacturer",
    "hersteller": "manufacturer",
    "herstellername": "manufacturer",
    "companyname": "manufacturer",
    "oem": "manufacturer",
    "supplier": "manufacturer",
    "vendor": "manufacturer",

    # ---------- model ----------
    "model": "model",
    "modelname": "model",
    "productname": "model",
    "typedesignation": "model",
    "typename": "model",
    "maschinentyp": "model",
    "produktname": "model",

    # ---------- serial ----------
    "serialnumber": "serial",
    "serialno": "serial",
    "seriennummer": "serial",
    "serial": "serial",
    "sernr": "serial",
    "sn": "serial",
    "serialnr": "serial",

    # ---------- name ----------
    "machinename": "name",
    "devicename": "name",
    "componentname": "name",
    "assetname": "name",
    "equipmentname": "name",
    "unitname": "name",
    "displayname": "name",
    "label": "name",
    "name": "name",

    # ---------- machine type ----------
    "deviceclass": "machine_type",
    "machinetype": "machine_type",
    "machinecategory": "machine_type",
    "equipmentclass": "machine_type",
    "maschinenklasse": "machine_type",
    "category": "machine_type",
    "class": "machine_type",

    # ---------- software ----------
    "softwarerevision": "software_version",
    "softwareversion": "software_version",
    "firmwareversion": "software_version",
    "revision": "software_version",
    "swversion": "software_version",
}

VENDOR_PROFILES = [
    dict(
        vendor="Siemens",
        signals=r"siemens|simatic|sinumerik|sinamics",
        anchors=r"^(PLC|SIMATIC|S7|Sinumerik|SINUMERIK|NCK|DeviceSet|Machines|Machine)",
        containers=r"^(DeviceSet|Machines)$",
        aliases={"produktname": "model", "seriennummer": "serial", "hersteller": "manufacturer"},
    ),
    dict(
        vendor="Fanuc",
        signals=r"fanuc|focas|30i|31i|32i|0i",
        anchors=r"fanuc|cnc|focas|controller|machine|deviceset",
        containers=r"^(DeviceSet|Machines)$",
        aliases={},
    ),
    dict(
        vendor="Index",
        signals=r"index[- ]?werke|\bindex\b|traub",
        anchors=r"index|traub|machine|cnc|deviceset",
        containers=r"^(DeviceSet|Machines)$",
        aliases={},
    ),
    dict(
        vendor="Beckhoff",
        signals=r"beckhoff|twincat",
        anchors=r"^(PLC|TwinCAT|Tc|DeviceSet|Machines)",
        containers=r"^(DeviceSet|Machines)$",
        aliases={},
    ),
    dict(
        vendor="B&R",
        signals=r"b&r|br-automation|bernecker",
        anchors=r"^(PLC|CPU|Machine|DeviceSet|Machines)",
        containers=r"^(DeviceSet|Machines)$",
        aliases={},
    ),
    dict(
        vendor="Heidenhain",
        signals=r"heidenhain|tnc",
        anchors=r"tnc|dnc|machine|deviceset",
        containers=r"^(DeviceSet|Machines)$",
        aliases={},
    ),
]

GENERIC_SKIP = {
    "Server", "ServerTypes", "DataTypes", "XmlSchema", "Client", "Aliases",
    "Locations", "Quantities", "Views", "Types", "Interfaces", "DeviceSet_",
    "ServerConfiguration", "HistoryServerCapabilities", "Namespaces",
}
NAME_HINTS = re.compile(
    r"machine|device|cnc|robot|press|lathe|mill|plc|line|station|cell|"
    r"drill|saw|oven|controller|unit|asset|equipment",
    re.I,
)
TYPE_HINTS = [
    (r"cnc|lathe|mill|drill|turn|machining|machine.?tool", "Machine Tool"),
    (r"robot", "Robot"),
    (r"press|imm|injection|mould", "Press / Moulding"),
    (r"plc|controller", "PLC"),
    (r"pack", "Packaging Machine"),
    (r"wood|saw", "Woodworking Machine"),
    (r"additive|3d.?print|am.?machine", "Additive Manufacturing"),
    (r"cmm|measur|hexagon|wenzel", "Coordinate Measuring Machine"),
]
PLACEHOLDERS = {
    "", "n/a", "na", "unknown", "none", "null", "-", "0",
    "undefined", "not available", "n.a.", "---",
}

GENERIC_FALLBACK_NAME = "Generic OPC-UA Machine"

IDENT_FOLDER_NAMES = {
    "identification", "machineidentification", "deviceidentification",
    "info", "machineinfo", "deviceinfo", "identity", "assetidentification",
}

# --------------------------------------------------------------------------- #
# Result type
# --------------------------------------------------------------------------- #

@dataclass
class MachineIdentity:
    name: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial: Optional[str] = None
    machine_type: Optional[str] = None
    software_version: Optional[str] = None
    status: str = "ok"              # Neu: Initialer Status ('ok', 'warning', 'error')
    error_code: Optional[str] = None # Neu: Optionaler Fehlercode bei Störung
    sources: dict = field(default_factory=dict)
    extra: dict = field(default_factory=dict)

    CORE = ("name", "manufacturer", "model", "serial")
    REQUIRED = ("name", "manufacturer", "machine_type")

    def get(self, f):
        return getattr(self, f)

    def set(self, f, value, source) -> bool:
        if value and not getattr(self, f):
            setattr(self, f, value)
            self.sources[f] = source
            return True
        return False

    @property
    def complete(self) -> bool:
        return all(getattr(self, f) for f in self.CORE)

    @property
    def has_required(self) -> bool:
        return all(getattr(self, f) for f in self.REQUIRED)

    @property
    def confidence(self) -> str:
        srcs = list(self.sources.values())
        if any(s.startswith("stage1") for s in srcs):
            return "high"
        if any(s.startswith("stage2") for s in srcs):
            return "medium"
        return "low"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "serial": self.serial,
            "machine_type": self.machine_type,
            "software_version": self.software_version,
            "status": self.status,       # Neu im Dictionary für den Autoscan
            "error_code": self.error_code, # Neu im Dictionary
            "confidence": self.confidence,
            "sources": self.sources,
            "extra": self.extra,
        }

# --------------------------------------------------------------------------- #
# Low-level helpers
# --------------------------------------------------------------------------- #

class _Ctx:
    def __init__(self, client: Client):
        self.client = client
        self.objects = client.get_objects_node()
        try:
            self.ns_array = client.get_namespace_array()
        except Exception:
            self.ns_array = []
        self.server = {}
        self._top = None

    def has_ns(self, uri_part: str) -> Optional[str]:
        for uri in self.ns_array:
            if uri_part.lower() in uri.lower():
                return uri
        return None

    def top_objects(self):
        if self._top is None:
            self._top = [k for k in kids(self.client, self.objects) if k[0] != 0]
        return self._top

def _norm(name: str) -> str:
    return re.sub(r"[\s_\-]", "", name.lower())

def kids(client, node):
    try:
        descs = node.get_children_descriptions()
    except Exception as exc:
        log.debug("browse failed: %s", exc)
        return []
    return [
        (d.BrowseName.NamespaceIndex, d.BrowseName.Name, d.NodeClass, client.get_node(d.NodeId))
        for d in descs
    ]

def read_text(node) -> Optional[str]:
    try:
        v = node.get_value()
    except Exception:
        return None
    if isinstance(v, ua.LocalizedText):
        v = v.Text
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        v = str(v)
    if isinstance(v, str):
        v = v.strip()
        return None if v.lower() in PLACEHOLDERS else v
    return None

def harvest(client, node, ident, source, max_depth=2, depth=0, aliases=None):
    table = {**ALIASES, **(aliases or {})}
    for _ns, name, ncls, child in kids(client, node):
        if ncls == ua.NodeClass.Variable:
            f = table.get(_norm(name))
            if f and not ident.get(f):
                ident.set(f, read_text(child), source)
        elif ncls == ua.NodeClass.Object and depth < max_depth:
            harvest(client, child, ident, source, max_depth, depth + 1, aliases)

def _harvest_identification_folders(client, parent_node, ident, source, aliases=None):
    for _ns, name, ncls, child in kids(client, parent_node):
        if ncls == ua.NodeClass.Object and _norm(name) in IDENT_FOLDER_NAMES:
            harvest(client, child, ident, source, max_depth=2, aliases=aliases)
            harvest(client, child, ident, source, max_depth=3, aliases=aliases)

# --------------------------------------------------------------------------- #
# Stage 1 - official standards (Multi-machine support)
# --------------------------------------------------------------------------- #

def _stage1_standard(ctx: _Ctx, identities: list[MachineIdentity], max_machines: int):
    c = ctx.client

    # 1a) Server BuildInfo
    for key, attr in (
        ("manufacturer", "ManufacturerName"),
        ("product", "ProductName"),
        ("version", "SoftwareVersion"),
        ("uri", "ProductUri"),
    ):
        oid = getattr(ua.ObjectIds, f"Server_ServerStatus_BuildInfo_{attr}", None)
        if oid is not None:
            val = read_text(c.get_node(ua.NodeId(oid)))
            if val:
                ctx.server[key] = val

    # 1b) Companion Specs present -> machine types
    companion_specs = []
    global_mtype = None
    for part, mtype in SPEC_TYPES.items():
        uri = ctx.has_ns(part)
        if uri:
            companion_specs.append(uri)
            if not global_mtype:
                global_mtype = mtype

    # 1c) OPC 40001 Machinery: Objects/Machines/<machine>/Identification
    machines = [k for k in ctx.top_objects() if k[1] == "Machines"]
    if machines and ctx.has_ns(MACHINERY_URI):
        found = [k for k in kids(c, machines[0][3]) if k[2] == ua.NodeClass.Object]
        for _ns, mname, _cls, mnode in found[:max_machines]:
            ident = MachineIdentity()
            ident.set("name", mname, "stage1:machinery")
            if global_mtype:
                ident.set("machine_type", global_mtype, "stage1:spec")
            for spec_uri in companion_specs:
                ident.extra.setdefault("companion_specs", []).append(spec_uri)

            harvest(c, mnode, ident, "stage1:machinery", max_depth=3)
            _harvest_identification_folders(c, mnode, ident, "stage1:machinery")
            identities.append(ident)

    # 1d) OPC 10000-100 DI: Objects/DeviceSet/<device>
    if not identities:
        devsets = [k for k in ctx.top_objects() if k[1] == "DeviceSet"]
        if devsets:
            found_devs = [k for k in kids(c, devsets[0][3]) if k[2] == ua.NodeClass.Object]
            for _ns, dname, _cls, dnode in found_devs[:max_machines]:
                ident = MachineIdentity()
                ident.set("name", dname, "stage1:di")
                if global_mtype:
                    ident.set("machine_type", global_mtype, "stage1:spec")
                for spec_uri in companion_specs:
                    ident.extra.setdefault("companion_specs", []).append(spec_uri)

                harvest(c, dnode, ident, "stage1:di", max_depth=2)
                _harvest_identification_folders(c, dnode, ident, "stage1:di")
                identities.append(ident)

# --------------------------------------------------------------------------- #
# Stage 2 - vendor patterns (Multi-machine support)
# --------------------------------------------------------------------------- #

def _stage2_vendor(ctx: _Ctx, identities: list[MachineIdentity], max_machines: int):
    signals = " ".join(list(ctx.server.values()) + list(ctx.ns_array)).lower()
    for prof in VENDOR_PROFILES:
        if not re.search(prof["signals"], signals):
            continue
        src = f"stage2:{prof['vendor']}"
        log.info("vendor profile matched: %s", prof["vendor"])

        for _ns, name, ncls, node in ctx.top_objects():
            if ncls != ua.NodeClass.Object or not re.search(prof["anchors"], name, re.I):
                continue

            if re.search(prof["containers"], name):
                device_kids = [k for k in kids(ctx.client, node) if k[2] == ua.NodeClass.Object]
                if not device_kids:
                    ident = MachineIdentity()
                    ident.set("manufacturer", prof["vendor"], src)
                    ident.set("name", name, src)
                    harvest(ctx.client, node, ident, src, max_depth=3, aliases=prof["aliases"])
                    _harvest_identification_folders(ctx.client, node, ident, src, aliases=prof["aliases"])
                    identities.append(ident)
                else:
                    for (_dns, dname, _dcls, dnode) in device_kids[:max_machines]:
                        ident = MachineIdentity()
                        ident.set("manufacturer", prof["vendor"], src)
                        ident.set("name", dname, src)
                        harvest(ctx.client, dnode, ident, src, max_depth=3, aliases=prof["aliases"])
                        _harvest_identification_folders(ctx.client, dnode, ident, src, aliases=prof["aliases"])
                        identities.append(ident)
            else:
                ident = MachineIdentity()
                ident.set("manufacturer", prof["vendor"], src)
                ident.set("name", name, src)
                harvest(ctx.client, node, ident, src, max_depth=3, aliases=prof["aliases"])
                _harvest_identification_folders(ctx.client, node, ident, src, aliases=prof["aliases"])
                identities.append(ident)

            if len(identities) >= max_machines:
                break
        if identities:
            break

# --------------------------------------------------------------------------- #
# Stage 3 - generic tree analysis
# --------------------------------------------------------------------------- #

def _stage3_generic(ctx: _Ctx, ident: MachineIdentity, max_depth=4, max_nodes=400):
    c = ctx.client
    queue = deque(
        (k, 1, k[1]) for k in ctx.top_objects() if k[1] not in GENERIC_SKIP
    )
    visited = 0
    best_obj = None
    candidates = {}

    while queue and visited < max_nodes:
        (_ns, name, ncls, node), depth, path = queue.popleft()
        visited += 1
        score = 1.0 / depth

        if ncls == ua.NodeClass.Variable:
            f = ALIASES.get(_norm(name))
            if f and not ident.get(f):
                val = read_text(node)
                if val and score > candidates.get(f, (0,))[0]:
                    candidates[f] = (score, val, path)
            continue

        if ncls == ua.NodeClass.Object:
            if NAME_HINTS.search(name):
                obj_score = score + 0.3
                if best_obj is None or obj_score > best_obj[0]:
                    best_obj = (obj_score, name, path)

            if depth < max_depth:
                for k in kids(c, node):
                    if k[1] not in GENERIC_SKIP:
                        queue.append((k, depth + 1, f"{path}/{k[1]}"))

    for f, (_score, val, path) in candidates.items():
        ident.set(f, val, f"stage3:{path}")

    if best_obj:
        ident.set("name", best_obj[1], f"stage3:{best_obj[2]}")
    elif ctx.top_objects() and not ident.name:
        ident.set("name", ctx.top_objects()[0][1], "stage3:first-object")

# --------------------------------------------------------------------------- #
# Public APIs
# --------------------------------------------------------------------------- #

def inspect_machines(host: str, port: int, max_machines: int = 5, timeout: float = 3.0) -> list[MachineIdentity]:
    """Returns a list of MachineIdentities (up to max_machines licensed slots) found on the server."""
    client = Client(f"opc.tcp://{host}:{port}", timeout=timeout)
    try:
        client.connect()
    except Exception as exc:
        log.warning("OPC UA connect failed: %s", exc)
        return []

    try:
        ctx = _Ctx(client)
        identities: list[MachineIdentity] = []

        # Stage 1: Official standards
        try:
            _stage1_standard(ctx, identities, max_machines=max_machines)
        except Exception:
            log.exception("Stage 1 failed")

        # Stage 2: Vendor patterns if Stage 1 found nothing
        if not identities:
            try:
                _stage2_vendor(ctx, identities, max_machines=max_machines)
            except Exception:
                log.exception("Stage 2 failed")

        # Stage 3: Generic tree analysis if still empty
        if not identities:
            try:
                ident = MachineIdentity()
                _stage3_generic(ctx, ident)
                if ident.name or ident.manufacturer:
                    identities.append(ident)
            except Exception:
                log.exception("Stage 3 failed")

        # Post-processing fallbacks for each discovered identity
        for ident in identities:
            ident.set("manufacturer", ctx.server.get("manufacturer"), "fallback:buildinfo")
            ident.set("software_version", ctx.server.get("version"), "fallback:buildinfo")
            ident.set("model", ctx.server.get("product"), "fallback:buildinfo")

            if not ident.machine_type:
                hay = f"{ident.name or ''} {ident.model or ''} {ident.manufacturer or ''}"
                for pattern, mtype in TYPE_HINTS:
                    if re.search(pattern, hay, re.I):
                        ident.set("machine_type", mtype, "fallback:name-hint")
                        break

            if not ident.name:
                ident.set("name", GENERIC_FALLBACK_NAME, "fallback:default")

        # Absolute fallback if completely empty
        if not identities:
            fallback = MachineIdentity(name=GENERIC_FALLBACK_NAME)
            fallback.sources["name"] = "fallback:default"
            identities.append(fallback)

        return identities
    finally:
        try:
            client.disconnect()
        except Exception:
            pass

def discover_machine(host: str, port: int, timeout: float = 3.0) -> Optional[MachineIdentity]:
    """Backward-compatible wrapper returning the primary (first) machine found."""
    results = inspect_machines(host, port, max_machines=1, timeout=timeout)
    return results[0] if results else None


def dump_tree(host: str, port: int, max_depth=4, max_nodes=300) -> list[str]:
    """Diagnostics: browse dump of a real machine."""
    client = Client(f"opc.tcp://{host}:{port}", timeout=3.0)
    client.connect()
    lines = []
    try:
        queue = deque([(client.get_objects_node(), 0, "Objects")])
        while queue and len(lines) < max_nodes:
            node, depth, label = queue.popleft()
            for ns, name, ncls, child in kids(client, node):
                p = f"{label}/{ns}:{name}"
                val = read_text(child) if ncls == ua.NodeClass.Variable else ""
                lines.append(f"{p}  [{ncls.name}] {val or ''}".rstrip())
                if ncls == ua.NodeClass.Object and depth + 1 < max_depth:
                    queue.append((child, depth + 1, p))
    finally:
        client.disconnect()
    return lines
```

## File: services/connector-box-poller/src/main.py
```python
"""
Realistischer E2E-Shopfloor-Test für 'Schwarzwald-Metallwaren':
1. Tenant via Gateway-API anlegen.
2. 2 Connector-Boxen registrieren und pairen (mit Fehlerbehandlung für Bestandsboxen).
3. Report-Export zur Verifikation.
"""
from __future__ import annotations

import time
import requests

GATEWAY_URL = "http://localhost:8080"
TENANT_ID = "schwarzwald-metallwaren"

def print_shopfloor_report():
    print(f"\n" + "="*60)
    print(f"  uretOS SHOPFLOOR REPORT - Tenant: {TENANT_ID}")
    print("="*60)

    try:
        resp = requests.get(f"{GATEWAY_URL}/v1/connector-boxes")
        if resp.status_code != 200:
            print(f"[ERROR] Konnte Connector-Boxen nicht abrufen: HTTP {resp.status_code}")
            return
        
        boxes = resp.json()
        tenant_boxes = [b for b in boxes if b.get("tenant_id") == TENANT_ID]
    except Exception as exc:
        print(f"[ERROR] Verbindungsfehler zum Gateway: {exc}")
        return

    if not tenant_boxes:
        print(f"\n[Info] Keine Connector-Boxen für Tenant '{TENANT_ID}' gefunden.")
        return

    total_machines_count = 0
    box_stats = []

    for box in tenant_boxes:
        hardware_id = box.get("hardware_id")
        box_id = box.get("box_id")
        status = box.get("status")

        print(f"\n📦 Connector Box: {hardware_id} (ID: {box_id})")
        print(f"   Status: {status.upper()}")

        machines_resp = requests.get(f"{GATEWAY_URL}/v1/connector-boxes/{hardware_id}/machines")
        if machines_resp.status_code == 200:
            machines = machines_resp.json()
            total_machines_count += len(machines)
            box_stats.append((hardware_id, len(machines)))
            
            print(f"   Zugeordnete Maschinen ({len(machines)} / Max. 5 Lizenz-Limit):")
            if not machines:
                print("     (Bisher keine Maschinen entdeckt)")
            for m in machines:
                print(f"     ├── Machine-ID : {m.get('machine_id')}")
                print(f"     │   Name       : {m.get('name')}")
        else:
            print(f"   [Warning] Konnte Maschinen für Box nicht laden: HTTP {machines_resp.status_code} - {machines_resp.text}")

    print("\n" + "-"*60)
    print(f"  ZUSAMMENFASSUNG:")
    print(f"  - Aktive Boxen     : {len(tenant_boxes)}")
    print(f"  - Total Maschinen  : {total_machines_count}")
    limit_ok = all(count <= 5 for _, count in box_stats)
    print(f"  - Lizenz-Status    : {'LIMIT EINGEHALTEN (<= 5 pro Box)' if limit_ok else 'WARNUNG: LIZENZLIMIT ÜBERSCHRITTEN!'}")
    print("="*60 + "\n")

def run_hierarchical_test():
    print("--- Starte realistisches Shopfloor-E2E-Setup ---")

    # 1. Tenant anlegen (ignoriert, falls schon da)
    print(f"\n[1/3] Provisioniere Tenant: {TENANT_ID}")
    resp = requests.post(f"{GATEWAY_URL}/v1/tenants", json={"tenant_id": TENANT_ID})
    print(f"Tenant-Status: HTTP {resp.status_code} - {resp.text}")

    # 2. Connector Boxen registrieren und pairen
    boxes = [
        {"hardware_id": "box-sw-01", "mac_address": "AA:BB:CC:DD:EE:01"},
        {"hardware_id": "box-sw-02", "mac_address": "AA:BB:CC:DD:EE:02"}
    ]

    for box in boxes:
        print(f"\n[2/3] Registriere & Paiere Box: {box['hardware_id']}")
        # Create (kann 400 geben, wenn Box schon existiert - das fangen wir ab)
        requests.post(f"{GATEWAY_URL}/v1/connector-boxes", json={**box, "tenant_id": TENANT_ID})
        
        # Pair
        resp_pair = requests.post(f"{GATEWAY_URL}/v1/connector-boxes/pair", json={"hardware_id": box["hardware_id"]})
        print(f"  -> Pairing-Status: HTTP {resp_pair.status_code} - {resp_pair.text}")

    print("\n[3/3] Setup aktiv. Warte auf mDNS-Discovery und Sync (ca. 8 Sekunden)...")
    time.sleep(8)

    # Report generieren
    print_shopfloor_report()

if __name__ == "__main__":
    run_hierarchical_test()
```

## File: services/connector-box-poller/Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

ENV PYTHONPATH=/app/src

CMD ["python", "src/main.py"]
```

## File: services/connector-box-poller/requirements.txt
```
requests>=2.31.0
opcua>=0.98.13
zeroconf>=0.39.0
```

## File: services/connector-box-query-service/app/cloudevents.py
```python
"""
Minimal CloudEvent v1.0 (uretOS dialect) envelope helper.

This module is intentionally duplicated per-service rather than shared as a
library, per uretOS's hyper-decoupled architecture principle. Any service
needing this logic should copy this file, not import it from elsewhere.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import jsonschema

_SCHEMA_PATH = Path(__file__).parent.parent / "contracts" / "cloudevent-v1.0.json"
_SCHEMA = json.loads(_SCHEMA_PATH.read_text())


def build_envelope(
    *,
    event_type: str,
    source: str,
    data: dict[str, Any],
    tenant_id: str,
    messagetype: str = "event",
    correlation_id: Optional[str] = None,
    subject: Optional[str] = None,
) -> dict[str, Any]:
    """Build a CloudEvent envelope dict ready to be published to RabbitMQ."""
    envelope = {
        "specversion": "1.0",
        "id": str(uuid.uuid4()),
        "source": source,
        "type": event_type,
        "datacontenttype": "application/json",
        "time": datetime.now(timezone.utc).isoformat(),
        "correlationid": correlation_id or str(uuid.uuid4()),
        "messagetype": messagetype,
        "tenantid": tenant_id,
        "data": data,
    }
    if subject:
        envelope["subject"] = subject
    validate_envelope(envelope)
    return envelope


def validate_envelope(envelope: dict[str, Any]) -> None:
    """Raises jsonschema.ValidationError if the envelope is malformed."""
    jsonschema.validate(instance=envelope, schema=_SCHEMA)


def loads(raw_body: bytes) -> dict[str, Any]:
    """Parse and validate a raw RabbitMQ message body into an envelope."""
    envelope = json.loads(raw_body)
    validate_envelope(envelope)
    return envelope
```

## File: services/connector-box-query-service/contracts/cloudevent-v1.0.json
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "uretOS CloudEvent v1.0 Specification",
  "description": "Standardized CloudEvent envelope for all asynchronous message exchanges across uretOS services. This file is a documentation/validation copy local to this service - it is intentionally NOT imported from a shared package (hyper-decoupled principle).",
  "type": "object",
  "required": [
    "specversion",
    "id",
    "source",
    "type",
    "datacontenttype",
    "time",
    "correlationid",
    "messagetype",
    "tenantid",
    "data"
  ],
  "properties": {
    "specversion": { "type": "string", "const": "1.0" },
    "id": { "type": "string", "format": "uuid" },
    "source": { "type": "string", "format": "uri-reference" },
    "type": { "type": "string" },
    "datacontenttype": { "type": "string", "const": "application/json" },
    "time": { "type": "string", "format": "date-time" },
    "correlationid": { "type": "string", "format": "uuid" },
    "messagetype": { "type": "string", "enum": ["event", "command", "query"] },
    "tenantid": {
      "type": "string",
      "minLength": 1,
      "description": "Identifies which tenant this message belongs to. Reserved value 'system' is used for super_admin-level operations such as tenant provisioning itself."
    },
    "subject": { "type": "string" },
    "data": { "type": "object" }
  }
}
```

## File: services/connector-box-query-service/Dockerfile
```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY contracts/ ./contracts/
COPY app/ ./app/

WORKDIR /app/app
CMD ["python", "main.py"]
```

## File: services/connector-box-query-service/requirements.txt
```
pika==1.3.2
jsonschema==4.23.0
psycopg[binary]==3.2.3
```

## File: services/gateway-api/contracts/cloudevent-v1.0.json
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "uretOS CloudEvent v1.0 Specification",
  "description": "Standardized CloudEvent envelope for all asynchronous message exchanges across uretOS services. This file is a documentation/validation copy local to this service - it is intentionally NOT imported from a shared package (hyper-decoupled principle).",
  "type": "object",
  "required": [
    "specversion",
    "id",
    "source",
    "type",
    "datacontenttype",
    "time",
    "correlationid",
    "messagetype",
    "tenantid",
    "data"
  ],
  "properties": {
    "specversion": { "type": "string", "const": "1.0" },
    "id": { "type": "string", "format": "uuid" },
    "source": { "type": "string", "format": "uri-reference" },
    "type": { "type": "string" },
    "datacontenttype": { "type": "string", "const": "application/json" },
    "time": { "type": "string", "format": "date-time" },
    "correlationid": { "type": "string", "format": "uuid" },
    "messagetype": { "type": "string", "enum": ["event", "command", "query"] },
    "tenantid": {
      "type": "string",
      "minLength": 1,
      "description": "Identifies which tenant this message belongs to. Reserved value 'system' is used for super_admin-level operations such as tenant provisioning itself."
    },
    "subject": { "type": "string" },
    "data": { "type": "object" }
  }
}
```

## File: services/gateway-api/tests/e2e_test_machines.py
```python
#!/usr/bin/env python3
"""
uretOS E2E-Test: Machine-Command-Pfad im Multi-Tenant-Setup.

Ablauf:
  0. Voraussetzungen: Gateway, Docker-Images (werden bei Bedarf geladen),
     machine-command-service läuft, hängt im Tenant-Netz und wartet auf Commands
  1. Tenant anlegen und in der Registry wiederfinden
  2. Connector-Box anlegen
  3. Handshake (mit Auto-Pairing) - Box gehört zum Test-Tenant
  4. Autoscan -> machine-command-service
  5. Persistenz: Maschinen liegen in der TENANT-DB und NICHT in der system-postgres
  6. Idempotenz: zweiter Autoscan erzeugt keine Duplikate
  7. Fehlerfälle liefern HTTP 400 mit Grund statt 504
  8. (optional, --query) Lesepfad über machine-query-service: pro Box, pro Tenant, Fehlerfälle

Aufruf:
  python3 e2e_test_machines.py            # Schreibpfad (Stufen 0-7)
  python3 e2e_test_machines.py --query    # zusätzlich Stufe 8

Konfiguration über Umgebungsvariablen (Defaults in Klammern):
  GATEWAY_URL          (http://localhost:8080)
  SYSTEM_PG_CONTAINER  (uretos-system-postgres)
  SYSTEM_PG_USER       (uretos_system)
  SYSTEM_PG_DB         (uretos_system)
"""
import argparse
import os
import subprocess
import sys
import time

import requests

GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://localhost:8080")
SYSTEM_PG_CONTAINER = os.environ.get("SYSTEM_PG_CONTAINER", "uretos-system-postgres")
SYSTEM_PG_USER = os.environ.get("SYSTEM_PG_USER", "uretos_system")
SYSTEM_PG_DB = os.environ.get("SYSTEM_PG_DB", "uretos_system")

MACHINE_CMD_CONTAINER = os.environ.get("MACHINE_CMD_CONTAINER", "uretos-machine-command-service")
QUERY_CONTAINER = os.environ.get("MACHINE_QUERY_CONTAINER", "uretos-machine-query-service")
TENANT_NET = "uretos-tenant-net"
REQUIRED_IMAGES = ["postgres:16-alpine", "redis:7-alpine"]

TEST_TENANT = "test-tenant-e2e"
TEST_HARDWARE_ID = "hw-box-e2e-001"
TEST_MAC = "AA:BB:CC:DD:EE:FF"

# Namensschema aus provisioning.py
TENANT_PG_CONTAINER = f"tenant-{TEST_TENANT}-postgres"
TENANT_PG_USER = f"tenant_{TEST_TENANT}"
TENANT_PG_DB = f"tenant_{TEST_TENANT}"

MOCK_MACHINES = [
    {
        "machine_id": "ns=2;i=1001",
        "name": "CNC Mill Alpha",
        "endpoint_url": "opc.tcp://192.168.1.50:4840",
        "vendor": "TestVendor",
    },
    {
        "machine_id": "ns=2;i=1002",
        "name": "Assembly Robot Beta",
        "endpoint_url": "opc.tcp://192.168.1.51:4840",
        "vendor": "TestVendor",
    },
]

failures: list[str] = []


class Abort(Exception):
    """Abbruch, wenn eine Voraussetzung für die folgenden Stufen fehlt."""


def ok(msg: str) -> None:
    print(f"  ✔ {msg}")


def fail(msg: str) -> None:
    print(f"  ✘ {msg}")
    failures.append(msg)


def skip(msg: str) -> None:
    print(f"  ⚠ übersprungen: {msg}")


def check(cond: bool, msg: str, detail: str = "") -> bool:
    if cond:
        ok(msg)
        return True
    fail(msg + (f"  ->  {detail}" if detail else ""))
    return False


def require(cond: bool, msg: str, detail: str = "") -> None:
    if not check(cond, msg, detail):
        raise Abort(msg)


def stage(title: str) -> None:
    print(f"\n=== {title} ===")


def post(path: str, payload: dict, timeout: int = 45) -> requests.Response:
    return requests.post(f"{GATEWAY_URL}{path}", json=payload, timeout=timeout)


def psql(container: str, user: str, db: str, sql: str):
    """Führt SQL per 'docker exec ... psql' aus. Rückgabe: (Zeilen | None, Fehlertext)."""
    proc = subprocess.run(
        ["docker", "exec", container, "psql", "-U", user, "-d", db, "-tA", "-F", "|", "-c", sql],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return None, proc.stderr.strip()
    return [line for line in proc.stdout.splitlines() if line.strip()], ""


def error_text(res: requests.Response) -> str:
    try:
        return str(res.json().get("error", res.text))
    except Exception:
        return res.text


# --------------------------------------------------------------------------- #
# Stufen
# --------------------------------------------------------------------------- #

def docker(*args: str):
    """Ruft die Docker-CLI auf. Rückgabe: (Exit-Code, stdout, stderr)."""
    proc = subprocess.run(["docker", *args], capture_output=True, text=True)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def require_tenant_db_code(container: str, service_dir: str) -> None:
    """Prüft, dass der Code im Image liegt und die Tenant-DB-Version der db.py enthält."""
    code, _, _ = docker("exec", container, "test", "-f", "/app/src/db.py")
    require(code == 0, "Code liegt im Image (/app/src/db.py)",
            f"Datei fehlt oder Container startet ständig neu: 'docker compose logs {service_dir}' prüfen; "
            f"vermutlich fehlt im Dockerfile von {service_dir} die Zeile 'COPY src/ ./src/'")
    code, _, _ = docker("exec", container, "grep", "-q", "_get_tenant_engine", "/app/src/db.py")
    require(code == 0, "Image enthält die Tenant-DB-Version der db.py",
            f"Alte db.py im Image: neue Datei nach services/{service_dir}/src/db.py kopieren "
            f"und 'docker compose up -d --build {service_dir}' ausführen")


def stage_0_preflight() -> None:
    stage("0. Voraussetzungen")
    healthy, last_error = False, ""
    for _ in range(30):  # nach 'docker compose up -d' braucht das Gateway einige Sekunden
        try:
            healthy = requests.get(f"{GATEWAY_URL}/healthz", timeout=5).status_code == 200
        except requests.RequestException as exc:
            last_error = str(exc)
        if healthy:
            break
        time.sleep(1)
    require(healthy, "Gateway erreichbar (GET /healthz -> 200)", last_error)

    code, _, err = docker("version", "--format", "{{.Server.Version}}")
    require(code == 0, "Docker-CLI erreichbar", err)

    # Der erste Tenant würde sonst am Gateway-Timeout (20 s) scheitern, wenn Docker erst pullen muss
    for image in REQUIRED_IMAGES:
        code, _, _ = docker("image", "inspect", image)
        if code != 0:
            print(f"  Image {image} fehlt -> docker pull (kann etwas dauern)")
            code, _, err = docker("pull", image)
        require(code == 0, f"Image {image} vorhanden", err)

    code, out, err = docker("inspect", "-f", "{{.State.Running}}", MACHINE_CMD_CONTAINER)
    require(code == 0 and out == "true", f"{MACHINE_CMD_CONTAINER} läuft",
            err or "Container läuft nicht: 'docker compose logs machine-command-service' prüfen")

    code, out, err = docker("inspect", "-f",
                            "{{range $name, $net := .NetworkSettings.Networks}}{{$name}} {{end}}",
                            MACHINE_CMD_CONTAINER)
    require(TENANT_NET in out.split(), f"{MACHINE_CMD_CONTAINER} hängt im Netz '{TENANT_NET}'",
            f"Netze: {out or err}. Fehlt 'networks: [default, tenant-net]' in der Compose-Datei?")

    require_tenant_db_code(MACHINE_CMD_CONTAINER, "machine-command-service")

    ready = False
    for _ in range(30):
        code, out, err = docker("logs", "--tail", "100", MACHINE_CMD_CONTAINER)
        if "Waiting for machine commands" in out + err:
            ready = True
            break
        time.sleep(1)
    require(ready, "machine-command-service wartet auf Commands (Log)",
            f"'docker logs {MACHINE_CMD_CONTAINER}' prüfen (Import-/DB-Fehler beim Start?)")


def tenant_in_registry() -> bool:
    res = requests.get(f"{GATEWAY_URL}/v1/tenants", timeout=30)
    if res.status_code != 200:
        return False
    for tenant in res.json():
        tenant_id = tenant.get("tenant_id") if isinstance(tenant, dict) else tenant
        if tenant_id == TEST_TENANT:
            return True
    return False


def stage_1_tenant() -> None:
    stage("1. Tenant anlegen")
    res = post("/v1/tenants", {"tenant_id": TEST_TENANT}, timeout=90)
    if res.status_code == 504:
        print("  Hinweis: Timeout beim Provisioning. Beim ersten Tenant lädt Docker die Images "
              "postgres:16-alpine und redis:7-alpine; vorab 'docker pull' ausführen.")
    require(res.status_code in (201, 400), "POST /v1/tenants -> 201 (neu) oder 400 (existiert)",
            f"{res.status_code}: {res.text}")

    # Die Registry wird asynchron vom tenant-command-service geschrieben -> kurz pollen
    found = False
    for _ in range(20):
        if tenant_in_registry():
            found = True
            break
        time.sleep(1)
    require(found, "Tenant steht in der Registry (system-postgres)",
            "Fehlt trotz Provisioning? Vermutlich alte Tenant-Container ohne Registry-Eintrag -> Reset (siehe Doku 12.3)")

    # Zugangsdaten der Tenant-Infrastruktur dürfen nie an Clients gehen
    if res.status_code == 201:
        check("password" not in res.text.lower(), "Antwort von POST /v1/tenants enthält keine Passwörter")
    else:
        skip("Tenant existierte schon (400): Passwort-Prüfung der Antwort geht nur bei frisch angelegtem Tenant")
    listing = requests.get(f"{GATEWAY_URL}/v1/tenants", timeout=30)
    check(listing.status_code == 200 and "password" not in listing.text.lower(),
          "GET /v1/tenants enthält keine Passwörter")


def stage_2_box() -> None:
    stage("2. Connector-Box anlegen")
    res = post("/v1/connector-boxes",
               {"tenant_id": TEST_TENANT, "hardware_id": TEST_HARDWARE_ID, "mac_address": TEST_MAC})
    require(res.status_code in (201, 400), "POST /v1/connector-boxes -> 201 (neu) oder 400 (existiert)",
            f"{res.status_code}: {res.text}")


def stage_3_handshake() -> str:
    stage("3. Handshake (mit Auto-Pairing)")
    res = post("/v1/connector-boxes/handshake", {"hardware_id": TEST_HARDWARE_ID})
    if res.status_code in (403, 404):
        print("  Box noch nicht gepairt -> Pairing")
        pair = post("/v1/connector-boxes/pair", {"hardware_id": TEST_HARDWARE_ID})
        require(pair.status_code == 200, "POST /v1/connector-boxes/pair -> 200", f"{pair.status_code}: {pair.text}")
        res = post("/v1/connector-boxes/handshake", {"hardware_id": TEST_HARDWARE_ID})

    require(res.status_code == 200, "Handshake -> 200", f"{res.status_code}: {res.text}")
    data = res.json()
    require(data.get("status") == "ok", "Handshake status == ok")
    require(data.get("tenant_id") == TEST_TENANT, f"Box gehört zu Tenant '{TEST_TENANT}'",
            f"tenant_id={data.get('tenant_id')}")
    box_id = str(data["box_id"])
    ok(f"box_id = {box_id}")
    return box_id


def stage_4_autoscan() -> None:
    stage("4. Autoscan -> machine-command-service")
    res = post("/v1/connector-boxes/autoscan", {"hardware_id": TEST_HARDWARE_ID, "machines": MOCK_MACHINES})
    require(res.status_code == 200, "Autoscan -> 200", f"{res.status_code}: {res.text}")
    data = res.json()
    check(data.get("status") == "success", "status == success")
    check(data.get("registered_count") == len(MOCK_MACHINES),
          f"registered_count == {len(MOCK_MACHINES)}", f"ist {data.get('registered_count')}")


def stage_5_persistence(box_id: str) -> None:
    stage("5. Persistenz in der Tenant-DB")
    rows, err = psql(TENANT_PG_CONTAINER, TENANT_PG_USER, TENANT_PG_DB,
                     "SELECT machine_id, name, box_id, tenant_id FROM machines ORDER BY machine_id")
    require(rows is not None, f"Abfrage in {TENANT_PG_CONTAINER} möglich", err)
    check(len(rows) == len(MOCK_MACHINES), f"genau {len(MOCK_MACHINES)} Maschinen in der Tenant-DB",
          f"gefunden: {len(rows)}")

    parsed = [row.split("|") for row in rows]
    names = {p[1] for p in parsed if len(p) == 4}
    for machine in MOCK_MACHINES:
        check(machine["name"] in names, f"Maschine '{machine['name']}' vorhanden")
    check(all(p[2].lower() == box_id.lower() for p in parsed), "box_id aller Maschinen passt zur Box")
    check(all(p[3] == TEST_TENANT for p in parsed), f"tenant_id aller Maschinen == '{TEST_TENANT}'")

    sys_rows, sys_err = psql(SYSTEM_PG_CONTAINER, SYSTEM_PG_USER, SYSTEM_PG_DB,
                             "SELECT to_regclass('public.machines')")
    if sys_rows is None:
        skip(f"system-postgres nicht abfragbar ({SYSTEM_PG_CONTAINER}): {sys_err}. "
             "Container-Name per SYSTEM_PG_CONTAINER setzen.")
    elif len(sys_rows) == 0:
        ok("Tabelle 'machines' existiert nicht in der system-postgres")
    else:
        count_rows, count_err = psql(SYSTEM_PG_CONTAINER, SYSTEM_PG_USER, SYSTEM_PG_DB,
                                     "SELECT count(*) FROM machines")
        if count_rows is None:
            fail(f"Zählen in system-postgres.machines nicht möglich: {count_err}")
        elif count_rows[0] == "0":
            skip("leere Tabelle 'machines' in der system-postgres (Altlast einer früheren Version, "
                 "kann mit DROP TABLE entfernt werden)")
        else:
            fail(f"system-postgres.machines enthält {count_rows[0]} Zeile(n) - Maschinen gehören "
                 "ausschließlich in die Tenant-DB")


def stage_6_idempotency() -> None:
    stage("6. Idempotenz (zweiter Autoscan)")
    res = post("/v1/connector-boxes/autoscan", {"hardware_id": TEST_HARDWARE_ID, "machines": MOCK_MACHINES})
    require(res.status_code == 200, "zweiter Autoscan -> 200", f"{res.status_code}: {res.text}")
    rows, err = psql(TENANT_PG_CONTAINER, TENANT_PG_USER, TENANT_PG_DB, "SELECT count(*) FROM machines")
    require(rows is not None, "Zählen der Maschinen möglich", err)
    check(rows[0] == str(len(MOCK_MACHINES)), f"weiterhin {len(MOCK_MACHINES)} Maschinen (keine Duplikate)",
          f"gefunden: {rows[0]}")


def stage_7_errors() -> None:
    stage("7. Fehlerfälle liefern 400/404 mit Grund (kein 504)")
    res = post("/v1/connector-boxes/autoscan", {"hardware_id": "gibt-es-nicht", "machines": []})
    # Hier von 400 auf 404 ändern:
    check(res.status_code == 404, "unbekannte hardware_id -> 404", f"{res.status_code}: {res.text}")
    check("not found" in error_text(res).lower(), "Fehlertext nennt 'not found'", error_text(res))

    res = post("/v1/connector-boxes/autoscan",
               {"hardware_id": TEST_HARDWARE_ID, "machines": [{"endpoint_url": "opc.tcp://x:4840"}]})
    check(res.status_code == 400, "Maschine ohne ID/Name -> 400", f"{res.status_code}: {res.text}")
    check("machine_id" in error_text(res), "Fehlertext nennt 'machine_id'", error_text(res))

def stage_8_query() -> None:
    stage("8. Lesepfad (machine-query-service)")

    # Voraussetzungen des Query-Service
    code, out, err = docker("inspect", "-f", "{{.State.Running}}", QUERY_CONTAINER)
    require(code == 0 and out == "true", f"{QUERY_CONTAINER} läuft",
            err or "Container läuft nicht: 'docker compose logs machine-query-service' prüfen")
    code, out, err = docker("inspect", "-f",
                            "{{range $name, $net := .NetworkSettings.Networks}}{{$name}} {{end}}",
                            QUERY_CONTAINER)
    require(TENANT_NET in out.split(), f"{QUERY_CONTAINER} hängt im Netz '{TENANT_NET}'",
            f"Netze: {out or err}. Fehlt 'networks: [default, tenant-net]' in der Compose-Datei?")
    require_tenant_db_code(QUERY_CONTAINER, "machine-query-service")

    ready = False
    for _ in range(30):
        code, out, err = docker("logs", "--tail", "100", QUERY_CONTAINER)
        if "Waiting for machine queries" in out + err:
            ready = True
            break
        time.sleep(1)
    require(ready, "machine-query-service wartet auf Queries (Log)",
            "'docker compose logs machine-query-service' prüfen (Import-/Startfehler?)")

    # a) pro Box (Tenant wird vom Gateway aus der Box ermittelt)
    res = requests.get(f"{GATEWAY_URL}/v1/connector-boxes/{TEST_HARDWARE_ID}/machines", timeout=45)
    require(res.status_code == 200, "GET /v1/connector-boxes/<hw>/machines -> 200",
            f"{res.status_code}: {res.text}")
    machines = res.json()
    check(len(machines) == len(MOCK_MACHINES), f"pro Box: genau {len(MOCK_MACHINES)} Maschinen",
          f"gefunden: {len(machines)}")
    names = {m.get("name") for m in machines}
    for machine in MOCK_MACHINES:
        check(machine["name"] in names, f"pro Box: '{machine['name']}' vorhanden")

    # b) pro Tenant
    res = requests.get(f"{GATEWAY_URL}/v1/machines", params={"tenant_id": TEST_TENANT}, timeout=45)
    require(res.status_code == 200, "GET /v1/machines?tenant_id=... -> 200", f"{res.status_code}: {res.text}")
    machines = res.json()
    check(len(machines) == len(MOCK_MACHINES), f"pro Tenant: genau {len(MOCK_MACHINES)} Maschinen",
          f"gefunden: {len(machines)}")
    check(all(m.get("tenant_id") == TEST_TENANT for m in machines),
          f"alle Maschinen gehören zu Tenant '{TEST_TENANT}'")

    # c) Fehlerfälle: klare Antwort statt Timeout
    res = requests.get(f"{GATEWAY_URL}/v1/machines", timeout=45)
    check(res.status_code == 400, "ohne tenant_id -> 400", f"{res.status_code}: {res.text}")

    res = requests.get(f"{GATEWAY_URL}/v1/machines", params={"tenant_id": "gibt-es-nicht"}, timeout=45)
    check(res.status_code == 404, "unbekannter Tenant -> 404", f"{res.status_code}: {res.text}")

    res = requests.get(f"{GATEWAY_URL}/v1/connector-boxes/gibt-es-nicht/machines", timeout=45)
    check(res.status_code == 404, "unbekannte Box -> 404", f"{res.status_code}: {res.text}")


# --------------------------------------------------------------------------- #

def main() -> int:
    parser = argparse.ArgumentParser(description="uretOS E2E: machine-command-service (Multi-Tenant)")
    parser.add_argument("--query", action="store_true",
                        help="zusätzlich den Lesepfad (machine-query-service) testen")
    args = parser.parse_args()

    try:
        stage_0_preflight()
        stage_1_tenant()
        stage_2_box()
        box_id = stage_3_handshake()
        stage_4_autoscan()
        stage_5_persistence(box_id)
        stage_6_idempotency()
        stage_7_errors()
        if args.query:
            stage_8_query()
        else:
            print("\n(Lesepfad nicht getestet - mit --query aktivieren)")
    except Abort as exc:
        print(f"\nABBRUCH: {exc}")
    except requests.RequestException as exc:
        fail(f"HTTP-Fehler: {exc}")

    print("\n" + "=" * 50)
    if failures:
        print(f"FEHLGESCHLAGEN: {len(failures)} Prüfung(en)")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("ERFOLGREICH")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

## File: services/gateway-api/Dockerfile
```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY contracts/ ./contracts/
COPY app/ ./app/

WORKDIR /app/app
EXPOSE 8080
CMD ["python", "main.py"]
```

## File: services/gateway-api/requirements.txt
```
flask==3.0.3
pika==1.3.2
jsonschema==4.23.0
```

## File: services/machine-command-service/contracts/cloudevent-v1.0.json
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "uretOS CloudEvent v1.0 Specification",
  "description": "Standardized CloudEvent envelope for all asynchronous message exchanges across uretOS services. This file is a documentation/validation copy local to this service - it is intentionally NOT imported from a shared package (hyper-decoupled principle).",
  "type": "object",
  "required": [
    "specversion",
    "id",
    "source",
    "type",
    "datacontenttype",
    "time",
    "correlationid",
    "messagetype",
    "tenantid",
    "data"
  ],
  "properties": {
    "specversion": { "type": "string", "const": "1.0" },
    "id": { "type": "string", "format": "uuid" },
    "source": { "type": "string", "format": "uri-reference" },
    "type": { "type": "string" },
    "datacontenttype": { "type": "string", "const": "application/json" },
    "time": { "type": "string", "format": "date-time" },
    "correlationid": { "type": "string", "format": "uuid" },
    "messagetype": { "type": "string", "enum": ["event", "command", "query"] },
    "tenantid": {
      "type": "string",
      "minLength": 1,
      "description": "Identifies which tenant this message belongs to. Reserved value 'system' is used for super_admin-level operations such as tenant provisioning itself."
    },
    "subject": { "type": "string" },
    "data": { "type": "object" }
  }
}
```

## File: services/machine-command-service/src/db.py
```python
"""
Database operations for machine-command-service.

Two databases are involved:

- system-postgres (READ ONLY usage here): resolves hardware_id -> box_id/tenant_id
  via `connector_boxes`, and tenant_id -> connection info via `tenants`.
- tenant-postgres (one instance per tenant): the `machines` table lives here.
  Engines are created lazily per tenant and cached.

The tenant is always derived from the connector box row in system-postgres,
never from the message payload, so a manipulated payload can not point a
write at another tenant's database.
"""
from __future__ import annotations

import logging
import os
import time

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from models import MachineModel

log = logging.getLogger("machine-command-service.db")

SYSTEM_DB_URL = os.environ.get(
    "SYSTEM_DB_URL",
    "postgresql+psycopg://uretos_system:uretos_system_dev_pass@system-postgres:5432/uretos_system",
)

# A freshly provisioned tenant-postgres container may not accept connections yet.
SCHEMA_RETRY_ATTEMPTS = int(os.environ.get("TENANT_DB_RETRY_ATTEMPTS", "6"))
SCHEMA_RETRY_DELAY_SECONDS = float(os.environ.get("TENANT_DB_RETRY_DELAY_SECONDS", "2"))

_system_engine = create_engine(SYSTEM_DB_URL, pool_pre_ping=True)
_tenant_engines: dict[str, Engine] = {}


class TenantNotFound(RuntimeError):
    pass


def init_db() -> None:
    """
    No schema creation here anymore: system-postgres is not ours to write to,
    and the machines table is created per tenant on first use.
    Only verifies that the system registry is reachable.
    """
    with _system_engine.connect() as conn:
        conn.execute(text("SELECT 1"))


def _ensure_tenant_schema(engine: Engine, tenant_id: str) -> None:
    for attempt in range(1, SCHEMA_RETRY_ATTEMPTS + 1):
        try:
            MachineModel.__table__.create(bind=engine, checkfirst=True)
            return
        except OperationalError:
            if attempt == SCHEMA_RETRY_ATTEMPTS:
                raise
            log.warning(
                "Tenant DB of '%s' not ready (attempt %d/%d), retrying...",
                tenant_id, attempt, SCHEMA_RETRY_ATTEMPTS,
            )
            time.sleep(SCHEMA_RETRY_DELAY_SECONDS)


def _get_tenant_engine(tenant_id: str) -> Engine:
    engine = _tenant_engines.get(tenant_id)
    if engine is not None:
        return engine

    with _system_engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT postgres_host, postgres_port, postgres_user, "
                "postgres_password, postgres_db FROM tenants WHERE tenant_id = :t"
            ),
            {"t": tenant_id},
        ).fetchone()

    if row is None:
        raise TenantNotFound(f"Tenant '{tenant_id}' not found in registry.")

    url = URL.create(
        "postgresql+psycopg",
        username=row.postgres_user,
        password=row.postgres_password,
        host=row.postgres_host,
        port=row.postgres_port,
        database=row.postgres_db,
    )
    engine = create_engine(url, pool_pre_ping=True)
    _ensure_tenant_schema(engine, tenant_id)

    _tenant_engines[tenant_id] = engine
    log.info("Tenant engine for '%s' ready", tenant_id)
    return engine


def register_machines_for_box(hardware_id: str, machines: list[dict]) -> tuple[list[dict], str | None, str | None]:
    try:
        with _system_engine.connect() as conn:
            box_row = conn.execute(
                text("SELECT box_id, tenant_id FROM connector_boxes WHERE hardware_id = :hw_id"),
                {"hw_id": hardware_id},
            ).fetchone()

        if not box_row:
            return [], f"Connector box with hardware_id '{hardware_id}' not found.", None

        box_id = str(box_row.box_id)
        tenant_id = str(box_row.tenant_id)

        engine = _get_tenant_engine(tenant_id)

        persisted = []
        with Session(engine) as db:
            for m in machines:
                machine_id = m.get("machine_id") or m.get("node_id") or m.get("name")
                if not machine_id:
                    db.rollback()
                    return [], "Machine entry without machine_id, node_id or name.", tenant_id

                name = m.get("name", "Unknown Machine")
                endpoint_url = m.get("endpoint_url", "")

                existing = db.query(MachineModel).filter_by(machine_id=machine_id, box_id=box_id).first()

                if existing:
                    existing.name = name
                    existing.endpoint_url = endpoint_url
                    existing.metadata_json = m
                else:
                    db.add(
                        MachineModel(
                            machine_id=machine_id,
                            box_id=box_id,
                            tenant_id=tenant_id,
                            name=name,
                            endpoint_url=endpoint_url,
                            metadata_json=m,
                        )
                    )

                persisted.append({"machine_id": machine_id, "name": name})

            db.commit()

        return persisted, None, tenant_id

    except Exception as e:
        log.exception("Machine registration failed for hardware_id=%s", hardware_id)
        return [], str(e), None
```

## File: services/machine-command-service/src/main.py
```python
"""
machine-command-service
"""
from __future__ import annotations

import json
import logging
import os

import pika

from cloudevents import build_envelope
from db import init_db, register_machines_for_box

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("machine-command-service")

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://uretos:uretos_dev_pass@rabbitmq:5672/")
EXCHANGE = "uretos.events"
QUEUE_NAME = "machine_command_queue"
SOURCE = "uretos/services/machine-command-service"

REGISTER_COMMAND = "uretos.machine.command.register"
REGISTERED_EVENT = "uretos.machine.event.registered"
REGISTRATION_FAILED_EVENT = "uretos.machine.event.registration_failed"


def publish_event(ch, response_type: str, response_data: dict, tenant_id: str, correlation_id):
    envelope_out = build_envelope(
        event_type=response_type,
        source=SOURCE,
        data=response_data,
        tenant_id=tenant_id,
        messagetype="event",
        correlation_id=correlation_id,
    )
    ch.basic_publish(
        exchange=EXCHANGE,
        routing_key=response_type,
        body=json.dumps(envelope_out).encode("utf-8"),
        properties=pika.BasicProperties(
            content_type="application/json",
            correlation_id=correlation_id,
        ),
    )


def callback(ch, method, properties, body):
    try:
        envelope = json.loads(body)
        event_type = envelope.get("type")
        correlation_id = envelope.get("correlationid")
        tenant_id = envelope.get("tenantid", "system")
        data = envelope.get("data", {})

        if event_type != REGISTER_COMMAND:
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        hardware_id = data.get("hardware_id")
        machines = data.get("machines", [])

        log.info("Processing machine registration for hardware_id=%s (Count: %d)", hardware_id, len(machines))

        result, error_reason, resolved_tenant_id = register_machines_for_box(hardware_id, machines)

        if error_reason:
            response_type = REGISTRATION_FAILED_EVENT
            response_data = {"reason": error_reason, "hardware_id": hardware_id}
            response_tenant_id = tenant_id  # "system" - Fehlerfall betrifft keinen konkreten Tenant-Stream
        else:
            response_type = REGISTERED_EVENT
            response_data = {"status": "success", "registered_count": len(machines), "machines": result}
            response_tenant_id = resolved_tenant_id  # echter Tenant, aufgelöst über hardware_id

        publish_event(ch, response_type, response_data, response_tenant_id, correlation_id)
        ch.basic_ack(delivery_tag=method.delivery_tag)
        log.info("Successfully finished machine registration for hardware_id=%s", hardware_id)

    except Exception as exc:
        log.exception("Error processing machine command message")

        try:
            envelope_in = json.loads(body)
            publish_event(
                ch,
                REGISTRATION_FAILED_EVENT,
                {"reason": f"Internal error: {exc}"},
                envelope_in.get("tenantid", "system"),
                envelope_in.get("correlationid"),
            )
        except Exception:
            log.exception("Could not publish failure event")

        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def main():
    log.info("Initializing database tables...")
    init_db()

    log.info("Starting machine-command-service consumer...")
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()

    channel.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    channel.queue_bind(queue=QUEUE_NAME, exchange=EXCHANGE, routing_key=REGISTER_COMMAND)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)

    log.info("Waiting for machine commands...")
    channel.start_consuming()


if __name__ == "__main__":
    main()
```

## File: services/machine-command-service/src/models.py
```python
"""
SQLAlchemy models for machine-command-service.
"""
from __future__ import annotations

from sqlalchemy import Column, DateTime, Integer, String, Text, UniqueConstraint, JSON, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class MachineModel(Base):
    __tablename__ = "machines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    machine_id = Column(String(255), nullable=False)
    box_id = Column(String(255), nullable=False)
    tenant_id = Column(String(255), nullable=False)
    name = Column(String(255))
    endpoint_url = Column(Text)
    metadata_json = Column(JSON, name="metadata")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("machine_id", "box_id", name="unique_machine_per_box"),
    )
```

## File: services/machine-command-service/Dockerfile
```dockerfile
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Abhängigkeiten kopieren und installieren
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY contracts/ ./contracts/

# Python-Module liegen direkt in /app/src
WORKDIR /app/src

CMD ["python", "main.py"]
```

## File: services/machine-query-service/contracts/cloudevent-v1.0.json
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "uretOS CloudEvent v1.0 Specification",
  "description": "Standardized CloudEvent envelope for all asynchronous message exchanges across uretOS services. This file is a documentation/validation copy local to this service - it is intentionally NOT imported from a shared package (hyper-decoupled principle).",
  "type": "object",
  "required": [
    "specversion",
    "id",
    "source",
    "type",
    "datacontenttype",
    "time",
    "correlationid",
    "messagetype",
    "tenantid",
    "data"
  ],
  "properties": {
    "specversion": { "type": "string", "const": "1.0" },
    "id": { "type": "string", "format": "uuid" },
    "source": { "type": "string", "format": "uri-reference" },
    "type": { "type": "string" },
    "datacontenttype": { "type": "string", "const": "application/json" },
    "time": { "type": "string", "format": "date-time" },
    "correlationid": { "type": "string", "format": "uuid" },
    "messagetype": { "type": "string", "enum": ["event", "command", "query"] },
    "tenantid": {
      "type": "string",
      "minLength": 1,
      "description": "Identifies which tenant this message belongs to. Reserved value 'system' is used for super_admin-level operations such as tenant provisioning itself."
    },
    "subject": { "type": "string" },
    "data": { "type": "object" }
  }
}
```

## File: services/machine-query-service/src/cloudevents.py
```python
"""
Minimal CloudEvent v1.0 (uretOS dialect) envelope helper.

This module is intentionally duplicated per-service rather than shared as a
library, per uretOS's hyper-decoupled architecture principle. Any service
needing this logic should copy this file, not import it from elsewhere.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import jsonschema

_SCHEMA_PATH = Path(__file__).parent.parent / "contracts" / "cloudevent-v1.0.json"
_SCHEMA = json.loads(_SCHEMA_PATH.read_text())


def build_envelope(
    event_type: str,
    source: str,
    data: dict[str, Any],
    tenant_id: str,
    messagetype: str = "event",
    correlation_id: Optional[str] = None,
    subject: Optional[str] = None,
) -> dict[str, Any]:
    """Build a CloudEvent envelope dict ready to be published to RabbitMQ."""
    envelope = {
        "specversion": "1.0",
        "id": str(uuid.uuid4()),
        "source": source,
        "type": event_type,
        "datacontenttype": "application/json",
        "time": datetime.now(timezone.utc).isoformat(),
        "correlationid": correlation_id or str(uuid.uuid4()),
        "messagetype": messagetype,
        "tenantid": tenant_id,
        "data": data,
    }
    if subject:
        envelope["subject"] = subject
    validate_envelope(envelope)
    return envelope


def validate_envelope(envelope: dict[str, Any]) -> None:
    """Raises jsonschema.ValidationError if the envelope is malformed."""
    jsonschema.validate(instance=envelope, schema=_SCHEMA)


def loads(raw_body: bytes) -> dict[str, Any]:
    """Parse and validate a raw RabbitMQ message body into an envelope."""
    envelope = json.loads(raw_body)
    validate_envelope(envelope)
    return envelope
```

## File: services/machine-query-service/src/db.py
```python
"""
Read-side database access for machine-query-service (multi-tenant).

Machines live in the per-tenant Postgres instance, not in system-postgres.
system-postgres is only used (read only) to look up a tenant's connection
info in the `tenants` table. Engines are created lazily per tenant and cached.

This service never creates or alters tables - the schema is owned by
machine-command-service. If a tenant has no `machines` table yet (nothing was
registered so far), the result is simply an empty list.

The tenant_id is supplied by the gateway (resolved from the connector box or,
until authentication exists, from the request). This service does not decide
which tenant a caller belongs to.
"""
from __future__ import annotations

import logging
import os

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import URL, Engine
from sqlalchemy.orm import Session

from models import MachineModel

log = logging.getLogger("machine-query-service.db")

SYSTEM_DB_URL = os.environ.get(
    "SYSTEM_DB_URL",
    "postgresql+psycopg://uretos_system:uretos_system_dev_pass@system-postgres:5432/uretos_system",
)

_system_engine = create_engine(SYSTEM_DB_URL, pool_pre_ping=True)
_tenant_engines: dict[str, Engine] = {}


class TenantNotFound(RuntimeError):
    pass


def _get_tenant_engine(tenant_id: str) -> Engine:
    engine = _tenant_engines.get(tenant_id)
    if engine is not None:
        return engine

    with _system_engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT postgres_host, postgres_port, postgres_user, "
                "postgres_password, postgres_db FROM tenants WHERE tenant_id = :t"
            ),
            {"t": tenant_id},
        ).fetchone()

    if row is None:
        raise TenantNotFound(f"Tenant '{tenant_id}' not found in registry.")

    url = URL.create(
        "postgresql+psycopg",
        username=row.postgres_user,
        password=row.postgres_password,
        host=row.postgres_host,
        port=row.postgres_port,
        database=row.postgres_db,
    )
    engine = create_engine(url, pool_pre_ping=True)
    _tenant_engines[tenant_id] = engine
    log.info("Tenant engine for '%s' ready", tenant_id)
    return engine


def _serialize(m: MachineModel) -> dict:
    return {
        "machine_id": m.machine_id,
        "box_id": m.box_id,
        "tenant_id": m.tenant_id,
        "name": m.name,
        "endpoint_url": m.endpoint_url,
        "metadata": m.metadata_json,
        "updated_at": m.updated_at.isoformat() if m.updated_at else None,
    }


def _fetch(tenant_id: str, box_id: str | None = None) -> list[dict]:
    engine = _get_tenant_engine(tenant_id)

    if not inspect(engine).has_table("machines"):
        return []

    with Session(engine) as db:
        query = db.query(MachineModel)
        if box_id is not None:
            # str(): box_id is a String(255) column - never bind a uuid.UUID here
            query = query.filter_by(box_id=str(box_id))
        return [_serialize(m) for m in query.order_by(MachineModel.machine_id).all()]


def get_all_machines(tenant_id: str) -> list[dict]:
    return _fetch(tenant_id)


def get_machines_by_box(tenant_id: str, box_id: str) -> list[dict]:
    return _fetch(tenant_id, box_id)
```

## File: services/machine-query-service/src/main.py
```python
"""
machine-query-service

Answers machine queries via Direct-Reply-To. Machines live in the per-tenant
database, so every query must carry the tenant_id in its data:

  uretos.machine.query.list     data: {"tenant_id": ...}
  uretos.machine.query.by_box   data: {"tenant_id": ..., "box_id": ...}

Reads only ever produce a single '<query_type>.result' event. Errors are
reported inside that event ("error_code" + "error") so that the gateway gets
a clear answer instead of running into its RPC timeout.
"""
from __future__ import annotations

import json
import logging
import os

import pika

from cloudevents import build_envelope
from db import TenantNotFound, get_all_machines, get_machines_by_box

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("machine-query-service")

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://uretos_system:uretos_system_dev_pass@rabbitmq:5672/")
EXCHANGE = "uretos.events"
QUEUE_NAME = "machine_query_queue"
SOURCE = "uretos/services/machine-query-service"

QUERY_LIST = "uretos.machine.query.list"
QUERY_BY_BOX = "uretos.machine.query.by_box"


def run_query(event_type: str, data: dict) -> dict:
    """Returns the response data: {"machines": [...]} or {"machines": [], "error_code", "error"}."""
    tenant_id = data.get("tenant_id")
    if not tenant_id:
        return {"machines": [], "error_code": "tenant_required", "error": "tenant_id is required"}

    try:
        if event_type == QUERY_LIST:
            return {"machines": get_all_machines(tenant_id)}

        if event_type == QUERY_BY_BOX:
            box_id = data.get("box_id")
            if not box_id:
                return {"machines": [], "error_code": "box_id_required", "error": "box_id is required"}
            return {"machines": get_machines_by_box(tenant_id, box_id)}

        return {"machines": [], "error_code": "unsupported_query", "error": f"Unsupported query '{event_type}'"}

    except TenantNotFound as exc:
        return {"machines": [], "error_code": "tenant_not_found", "error": str(exc)}
    except Exception as exc:
        log.exception("Machine query failed for tenant_id=%s", tenant_id)
        return {"machines": [], "error_code": "query_failed", "error": f"Query failed: {exc}"}


def callback(ch, method, properties, body):
    try:
        envelope = json.loads(body)
        event_type = envelope.get("type")
        correlation_id = envelope.get("correlationid")
        reply_to = properties.reply_to
        data = envelope.get("data", {})

        if not reply_to:
            log.error("Query received without AMQP reply_to - cannot answer, dropping")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            return

        log.info("Received query type=%s tenant_id=%s", event_type, data.get("tenant_id"))

        response_data = run_query(event_type, data)

        envelope_out = build_envelope(
            event_type=f"{event_type}.result",
            source=SOURCE,
            data=response_data,
            tenant_id=envelope.get("tenantid", "system"),
            messagetype="query",
            correlation_id=correlation_id,
        )

        ch.basic_publish(
            exchange="",
            routing_key=reply_to,
            body=json.dumps(envelope_out).encode("utf-8"),
            properties=pika.BasicProperties(
                content_type="application/json",
                correlation_id=correlation_id,
            ),
        )

        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception:
        log.exception("Error processing machine query")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        
def main():
    log.info("Starting machine-query-service consumer...")
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()

    channel.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)
    channel.queue_declare(queue=QUEUE_NAME, durable=True)

    channel.queue_bind(queue=QUEUE_NAME, exchange=EXCHANGE, routing_key=QUERY_LIST)
    channel.queue_bind(queue=QUEUE_NAME, exchange=EXCHANGE, routing_key=QUERY_BY_BOX)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)

    log.info("Waiting for machine queries...")
    channel.start_consuming()


if __name__ == "__main__":
    main()
```

## File: services/machine-query-service/src/models.py
```python
"""
SQLAlchemy models for machine-query-service.
"""
from __future__ import annotations

from sqlalchemy import Column, DateTime, Integer, String, Text, UniqueConstraint, JSON, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class MachineModel(Base):
    __tablename__ = "machines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    machine_id = Column(String(255), nullable=False)
    box_id = Column(String(255), nullable=False)
    tenant_id = Column(String(255), nullable=False)
    name = Column(String(255))
    endpoint_url = Column(Text)
    metadata_json = Column(JSON, name="metadata")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("machine_id", "box_id", name="unique_machine_per_box"),
    )
```

## File: services/machine-query-service/Dockerfile
```dockerfile
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY contracts/ ./contracts/

WORKDIR /app/src

CMD ["python", "main.py"]
```

## File: services/machine-query-service/requirements.txt
```
pika==1.3.2
jsonschema==4.23.0
psycopg[binary]==3.2.3
sqlalchemy==2.1.3
```

## File: services/shopfloor-bff-api/src/cloudevents.py
```python
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
import jsonschema

_SCHEMA_PATH = Path(__file__).resolve().parent.parent.parent / "contracts" / "cloudevent-v1.0.json"
if not _SCHEMA_PATH.exists():
    _SCHEMA_PATH = Path("/app/contracts/cloudevent-v1.0.json")

_SCHEMA = json.loads(_SCHEMA_PATH.read_text()) if _SCHEMA_PATH.exists() else {}

def build_envelope(
    event_type: str,
    source: str,
    data: dict[str, Any],
    tenant_id: str,
    messagetype: str = "query",
    correlation_id: Optional[str] = None,
) -> dict[str, Any]:
    envelope = {
        "specversion": "1.0",
        "id": str(uuid.uuid4()),
        "source": source,
        "type": event_type,
        "datacontenttype": "application/json",
        "time": datetime.now(timezone.utc).isoformat(),
        "correlationid": correlation_id or str(uuid.uuid4()),
        "messagetype": messagetype,
        "tenantid": tenant_id,
        "data": data,
    }
    if _SCHEMA:
        jsonschema.validate(instance=envelope, schema=_SCHEMA)
    return envelope
```

## File: services/shopfloor-bff-api/src/main.py
```python
"""
shopfloor-bff-api

Backend-for-Frontend (BFF) for the uretOS Shopfloor 3D Cockpit & Stream POC.
Exposes REST endpoints and Server-Sent Events (SSE) to deliver real-time
machine statuses and historical data to the frontend dashboard.
"""
from __future__ import annotations

import json
import logging
import os
from typing import AsyncGenerator

import pika
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("shopfloor-bff-api")

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://uretos:uretos_dev_pass@rabbitmq:5672/")
EXCHANGE = "uretos.events"

app = FastAPI(title="uretOS Shopfloor BFF API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/v1/shopfloor/stream")
async def shopfloor_stream(request: Request, tenant_id: str) -> EventSourceResponse:
    """
    Server-Sent Events (SSE) endpoint streaming real-time machine updates
    and snapshots for a specific tenant.
    """
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id query parameter is required")

    async def event_generator() -> AsyncGenerator[dict, None]:
        # Verbindung zu RabbitMQ aufbauen und exklusive Queue binden
        connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
        channel = connection.channel()
        channel.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)

        result = channel.queue_declare(queue="", exclusive=True)
        queue_name = result.method.queue

        # Bindings für relevante Events und Snapshots
        channel.queue_bind(queue=queue_name, exchange=EXCHANGE, routing_key="uretos.machine.event.#")
        channel.queue_bind(queue=queue_name, exchange=EXCHANGE, routing_key="uretos.shopfloor.snapshot")

        # Initialer Snapshot (Beispiel-Payload für den Stream-Start)
        initial_envelope = {
            "type": "uretos.shopfloor.snapshot",
            "data": {"machines": []}
        }
        yield {"data": json.dumps(initial_envelope)}

        try:
            while True:
                if await request.is_disconnected():
                    break
                
                method, properties, body = channel.basic_get(queue=queue_name, auto_ack=True)
                if body:
                    try:
                        event_data = json.loads(body)
                        # Nur Events für den angefragten Tenant durchlassen (oder System-Events)
                        event_tenant = event_data.get("tenantid") or event_data.get("tenant_id")
                        if not event_tenant or event_tenant == tenant_id or event_tenant == "system":
                            yield {"data": json.dumps(event_data)}
                    except Exception as e:
                        log.error("Failed to parse event body: %s", e)
                
                # Kurze Pause, um die CPU zu schonen
                import asyncio
                await asyncio.sleep(0.5)
        finally:
            connection.close()

    return EventSourceResponse(event_generator())


@app.get("/api/v1/machines/{machine_id}/history")
def machine_history(machine_id: str, limit: int = 14, x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID")):
    """
    Liefert die Historie einer spezifischen Maschine für die Timeline-Anzeige.
    """
    if not x_tenant_id:
        raise HTTPException(status_code=400, detail="X-Tenant-ID header is required")

    # Mock/Default-Historie für den POC, bis der Timescale-Query-Dienst voll angebunden ist
    mock_history = {
        "machine_id": machine_id,
        "history": []
    }
    return mock_history
```

## File: services/shopfloor-bff-api/Dockerfile
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY services/shopfloor-bff-api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY contracts/ ./contracts/
COPY services/shopfloor-bff-api/src/ ./src/
WORKDIR /app/src
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

## File: services/shopfloor-bff-api/requirements.txt
```
fastapi>=0.110.0
uvicorn>=0.28.0
pika>=1.3.2
jsonschema>=4.21.0
pydantic>=2.6.0
sse-starlette
```

## File: services/shopfloor-stream-service/contracts/cloudevent-v1.0.json
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "uretOS CloudEvent v1.0 Specification",
  "description": "Standardized CloudEvent envelope for all asynchronous message exchanges across uretOS services. This file is a documentation/validation copy local to this service - it is intentionally NOT imported from a shared package (hyper-decoupled principle).",
  "type": "object",
  "required": [
    "specversion",
    "id",
    "source",
    "type",
    "datacontenttype",
    "time",
    "correlationid",
    "messagetype",
    "tenantid",
    "data"
  ],
  "properties": {
    "specversion": { "type": "string", "const": "1.0" },
    "id": { "type": "string", "format": "uuid" },
    "source": { "type": "string", "format": "uri-reference" },
    "type": { "type": "string" },
    "datacontenttype": { "type": "string", "const": "application/json" },
    "time": { "type": "string", "format": "date-time" },
    "correlationid": { "type": "string", "format": "uuid" },
    "messagetype": { "type": "string", "enum": ["event", "command", "query"] },
    "tenantid": {
      "type": "string",
      "minLength": 1,
      "description": "Identifies which tenant this message belongs to. Reserved value 'system' is used for super_admin-level operations such as tenant provisioning itself."
    },
    "subject": { "type": "string" },
    "data": { "type": "object" }
  }
}
```

## File: services/shopfloor-stream-service/src/cloudevents.py
```python
"""
Minimal CloudEvent v1.0 (uretOS dialect) envelope helper.

This module is intentionally duplicated per-service rather than shared as a
library, per uretOS's hyper-decoupled architecture principle. Any service
needing this logic should copy this file, not import it from elsewhere.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import jsonschema

_SCHEMA_PATH = Path(__file__).parent.parent / "contracts" / "cloudevent-v1.0.json"
_SCHEMA = json.loads(_SCHEMA_PATH.read_text())


def build_envelope(
    event_type: str,
    source: str,
    data: dict[str, Any],
    tenant_id: str,
    messagetype: str = "event",
    correlation_id: Optional[str] = None,
    subject: Optional[str] = None,
) -> dict[str, Any]:
    """Build a CloudEvent envelope dict ready to be published to RabbitMQ."""
    envelope = {
        "specversion": "1.0",
        "id": str(uuid.uuid4()),
        "source": source,
        "type": event_type,
        "datacontenttype": "application/json",
        "time": datetime.now(timezone.utc).isoformat(),
        "correlationid": correlation_id or str(uuid.uuid4()),
        "messagetype": messagetype,
        "tenantid": tenant_id,
        "data": data,
    }
    if subject:
        envelope["subject"] = subject
    validate_envelope(envelope)
    return envelope


def validate_envelope(envelope: dict[str, Any]) -> None:
    """Raises jsonschema.ValidationError if the envelope is malformed."""
    jsonschema.validate(instance=envelope, schema=_SCHEMA)


def loads(raw_body: bytes) -> dict[str, Any]:
    """Parse and validate a raw RabbitMQ message body into an envelope."""
    envelope = json.loads(raw_body)
    validate_envelope(envelope)
    return envelope
```

## File: services/shopfloor-stream-service/Dockerfile
```dockerfile
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY contracts/ ./contracts/

WORKDIR /app/src

EXPOSE 8081
CMD ["python", "main.py"]
```

## File: services/shopfloor-stream-service/requirements.txt
```
flask==3.0.3
pika==1.3.2
jsonschema==4.23.0
```

## File: services/tenant-command-service/app/cloudevents.py
```python
"""
Minimal CloudEvent v1.0 (uretOS dialect) envelope helper.

This module is intentionally duplicated per-service rather than shared as a
library, per uretOS's hyper-decoupled architecture principle. Any service
needing this logic should copy this file, not import it from elsewhere.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import jsonschema

_SCHEMA_PATH = Path(__file__).parent.parent / "contracts" / "cloudevent-v1.0.json"
_SCHEMA = json.loads(_SCHEMA_PATH.read_text())


def build_envelope(
    *,
    event_type: str,
    source: str,
    data: dict[str, Any],
    tenant_id: str,
    messagetype: str = "event",
    correlation_id: Optional[str] = None,
    subject: Optional[str] = None,
) -> dict[str, Any]:
    """Build a CloudEvent envelope dict ready to be published to RabbitMQ."""
    envelope = {
        "specversion": "1.0",
        "id": str(uuid.uuid4()),
        "source": source,
        "type": event_type,
        "datacontenttype": "application/json",
        "time": datetime.now(timezone.utc).isoformat(),
        "correlationid": correlation_id or str(uuid.uuid4()),
        "messagetype": messagetype,
        "tenantid": tenant_id,
        "data": data,
    }
    if subject:
        envelope["subject"] = subject
    validate_envelope(envelope)
    return envelope


def validate_envelope(envelope: dict[str, Any]) -> None:
    """Raises jsonschema.ValidationError if the envelope is malformed."""
    jsonschema.validate(instance=envelope, schema=_SCHEMA)


def loads(raw_body: bytes) -> dict[str, Any]:
    """Parse and validate a raw RabbitMQ message body into an envelope."""
    envelope = json.loads(raw_body)
    validate_envelope(envelope)
    return envelope
```

## File: services/tenant-command-service/app/models.py
```python
"""
SQLAlchemy ORM model for the tenant registry - system-postgres.

No migration framework (Alembic) is used by deliberate choice. Since this
is early-stage development with no data worth preserving, schema changes
are handled by resetting the database (docker compose down -v) and letting
Base.metadata.create_all() rebuild it from scratch - not by altering
existing tables in place.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Tenant(Base):
    __tablename__ = "tenants"

    tenant_id: Mapped[str] = mapped_column(String, primary_key=True)
    status: Mapped[str] = mapped_column(String, default="active", server_default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    postgres_host: Mapped[str] = mapped_column(String)
    postgres_port: Mapped[int] = mapped_column(Integer)
    postgres_user: Mapped[str] = mapped_column(String)
    postgres_password: Mapped[str] = mapped_column(String)
    postgres_db: Mapped[str] = mapped_column(String)

    redis_host: Mapped[str] = mapped_column(String)
    redis_port: Mapped[int] = mapped_column(Integer)

    rabbitmq_vhost: Mapped[str] = mapped_column(String)
    rabbitmq_user: Mapped[str] = mapped_column(String)
    rabbitmq_password: Mapped[str] = mapped_column(String)
```

## File: services/tenant-command-service/contracts/cloudevent-v1.0.json
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "uretOS CloudEvent v1.0 Specification",
  "description": "Standardized CloudEvent envelope for all asynchronous message exchanges across uretOS services. This file is a documentation/validation copy local to this service - it is intentionally NOT imported from a shared package (hyper-decoupled principle).",
  "type": "object",
  "required": [
    "specversion",
    "id",
    "source",
    "type",
    "datacontenttype",
    "time",
    "correlationid",
    "messagetype",
    "tenantid",
    "data"
  ],
  "properties": {
    "specversion": { "type": "string", "const": "1.0" },
    "id": { "type": "string", "format": "uuid" },
    "source": { "type": "string", "format": "uri-reference" },
    "type": { "type": "string" },
    "datacontenttype": { "type": "string", "const": "application/json" },
    "time": { "type": "string", "format": "date-time" },
    "correlationid": { "type": "string", "format": "uuid" },
    "messagetype": { "type": "string", "enum": ["event", "command", "query"] },
    "tenantid": {
      "type": "string",
      "minLength": 1,
      "description": "Identifies which tenant this message belongs to. Reserved value 'system' is used for super_admin-level operations such as tenant provisioning itself."
    },
    "subject": { "type": "string" },
    "data": { "type": "object" }
  }
}
```

## File: services/tenant-command-service/Dockerfile
```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY contracts/ ./contracts/
COPY app/ ./app/

WORKDIR /app/app
CMD ["python", "main.py"]
```

## File: services/tenant-provisioning-service/app/init-extension.sql
```sql
CREATE EXTENSION IF NOT EXISTS timescaledb;
```

## File: services/tenant-provisioning-service/app/main.py
```python
"""
tenant-provisioning-service

Consumes:  uretos.tenant.command.create   (messagetype=command, tenantid="system")
Publishes: uretos.tenant.event.provisioned (messagetype=event,  tenantid=<new tenant>)
       or: uretos.tenant.event.provisioning_failed (messagetype=event, tenantid="system")

Only the super_admin level is expected to ever send the create-command, which
is why it travels under tenantid="system" - it is not itself tenant data.

Provisions three isolated things per tenant: a Postgres container, a Redis
container (both via docker-socket-proxy), and a RabbitMQ vhost+user (via the
RabbitMQ Management API) - DB isolation and messaging isolation together.
"""
from __future__ import annotations

import json
import logging
import os

import pika

from cloudevents import build_envelope, loads
from provisioning import (
    ProvisioningError,
    provision_tenant_infrastructure,
    provision_tenant_rabbitmq,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("tenant-provisioning-service")

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://uretos:uretos_dev_pass@rabbitmq:5672/")
EXCHANGE = "uretos.events"
COMMAND_QUEUE = "tenant-provisioning-service.tenant.command.create"
ROUTING_KEY_IN = "uretos.tenant.command.create"
SOURCE = "uretos/services/tenant-provisioning-service"


def handle_command(channel: pika.channel.Channel, method, properties, body: bytes) -> None:
    try:
        envelope = loads(body)
    except Exception:
        log.exception("Rejecting malformed message - not valid CloudEvent envelope")
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return

    correlation_id = envelope["correlationid"]
    tenant_id = envelope["data"].get("tenant_id")
    log.info("Received tenant creation command for tenant_id=%s", tenant_id)

    try:
        infra_info = provision_tenant_infrastructure(tenant_id)
        rabbitmq_info = provision_tenant_rabbitmq(tenant_id)
        infra_info["rabbitmq"] = rabbitmq_info
        out_type = "uretos.tenant.event.provisioned"
        out_tenant = tenant_id
        out_data = infra_info
        log.info("Tenant '%s' provisioned successfully (DB + messaging isolation)", tenant_id)
    except ProvisioningError as exc:
        log.error("Provisioning failed for tenant_id=%s: %s", tenant_id, exc)
        out_type = "uretos.tenant.event.provisioning_failed"
        out_tenant = "system"
        out_data = {"tenant_id": tenant_id, "reason": str(exc)}

    response = build_envelope(
        event_type=out_type,
        source=SOURCE,
        data=out_data,
        tenant_id=out_tenant,
        messagetype="event",
        correlation_id=correlation_id,
    )
    channel.basic_publish(
        exchange=EXCHANGE,
        routing_key=out_type,
        body=json.dumps(response).encode("utf-8"),
        properties=pika.BasicProperties(content_type="application/json"),
    )
    channel.basic_ack(delivery_tag=method.delivery_tag)


def main() -> None:
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()

    channel.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)
    channel.queue_declare(queue=COMMAND_QUEUE, durable=True)
    channel.queue_bind(queue=COMMAND_QUEUE, exchange=EXCHANGE, routing_key=ROUTING_KEY_IN)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=COMMAND_QUEUE, on_message_callback=handle_command)

    log.info("tenant-provisioning-service listening on '%s'", ROUTING_KEY_IN)
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        channel.stop_consuming()

    connection.close()


if __name__ == "__main__":
    main()
```

## File: services/tenant-query-service/app/cloudevents.py
```python
"""
Minimal CloudEvent v1.0 (uretOS dialect) envelope helper.

This module is intentionally duplicated per-service rather than shared as a
library, per uretOS's hyper-decoupled architecture principle. Any service
needing this logic should copy this file, not import it from elsewhere.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import jsonschema

_SCHEMA_PATH = Path(__file__).parent.parent / "contracts" / "cloudevent-v1.0.json"
_SCHEMA = json.loads(_SCHEMA_PATH.read_text())


def build_envelope(
    *,
    event_type: str,
    source: str,
    data: dict[str, Any],
    tenant_id: str,
    messagetype: str = "event",
    correlation_id: Optional[str] = None,
    subject: Optional[str] = None,
) -> dict[str, Any]:
    """Build a CloudEvent envelope dict ready to be published to RabbitMQ."""
    envelope = {
        "specversion": "1.0",
        "id": str(uuid.uuid4()),
        "source": source,
        "type": event_type,
        "datacontenttype": "application/json",
        "time": datetime.now(timezone.utc).isoformat(),
        "correlationid": correlation_id or str(uuid.uuid4()),
        "messagetype": messagetype,
        "tenantid": tenant_id,
        "data": data,
    }
    if subject:
        envelope["subject"] = subject
    validate_envelope(envelope)
    return envelope


def validate_envelope(envelope: dict[str, Any]) -> None:
    """Raises jsonschema.ValidationError if the envelope is malformed."""
    jsonschema.validate(instance=envelope, schema=_SCHEMA)


def loads(raw_body: bytes) -> dict[str, Any]:
    """Parse and validate a raw RabbitMQ message body into an envelope."""
    envelope = json.loads(raw_body)
    validate_envelope(envelope)
    return envelope
```

## File: services/tenant-query-service/app/main.py
```python
"""
tenant-query-service

Consumes: uretos.tenant.query.list (messagetype=query, tenantid="system")
Replies directly via RabbitMQ's Direct-Reply-To mechanism (AMQP
`reply_to` + `correlation_id` properties on the incoming message) -
no dedicated response queue or routing key needed for the reply itself.

Read-only - never writes to system-postgres.
"""
from __future__ import annotations

import json
import logging
import os

import pika

from cloudevents import build_envelope, loads
from db import list_tenants

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("tenant-query-service")

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://uretos:uretos_dev_pass@rabbitmq:5672/")
EXCHANGE = "uretos.events"
QUEUE = "tenant-query-service.tenant.query.list"
ROUTING_KEY_IN = "uretos.tenant.query.list"
SOURCE = "uretos/services/tenant-query-service"


def handle_query(channel: pika.channel.Channel, method, properties, body: bytes) -> None:
    try:
        envelope = loads(body)
    except Exception:
        log.exception("Rejecting malformed message - not valid CloudEvent envelope")
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return

    if not properties.reply_to:
        log.error("Query received without AMQP reply_to - cannot answer, dropping")
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return

    correlation_id = envelope["correlationid"]
    tenants = list_tenants()
    log.info("Answering tenant list query with %d tenant(s)", len(tenants))

    response = build_envelope(
        event_type="uretos.tenant.query.list.result",
        source=SOURCE,
        data={"tenants": tenants},
        tenant_id="system",
        messagetype="event",
        correlation_id=correlation_id,
    )
    channel.basic_publish(
        exchange="",
        routing_key=properties.reply_to,
        properties=pika.BasicProperties(
            correlation_id=properties.correlation_id,
            content_type="application/json",
        ),
        body=json.dumps(response).encode("utf-8"),
    )
    channel.basic_ack(delivery_tag=method.delivery_tag)


def main() -> None:
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()

    channel.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)
    channel.queue_declare(queue=QUEUE, durable=True)
    channel.queue_bind(queue=QUEUE, exchange=EXCHANGE, routing_key=ROUTING_KEY_IN)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=QUEUE, on_message_callback=handle_query)

    log.info("tenant-query-service listening on '%s'", ROUTING_KEY_IN)
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        channel.stop_consuming()

    connection.close()


if __name__ == "__main__":
    main()
```

## File: services/tenant-query-service/app/models.py
```python
"""
SQLAlchemy ORM model for the tenant registry - system-postgres.

No migration framework (Alembic) is used by deliberate choice. Since this
is early-stage development with no data worth preserving, schema changes
are handled by resetting the database (docker compose down -v) and letting
Base.metadata.create_all() rebuild it from scratch - not by altering
existing tables in place.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Tenant(Base):
    __tablename__ = "tenants"

    tenant_id: Mapped[str] = mapped_column(String, primary_key=True)
    status: Mapped[str] = mapped_column(String, default="active", server_default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    postgres_host: Mapped[str] = mapped_column(String)
    postgres_port: Mapped[int] = mapped_column(Integer)
    postgres_user: Mapped[str] = mapped_column(String)
    postgres_password: Mapped[str] = mapped_column(String)
    postgres_db: Mapped[str] = mapped_column(String)

    redis_host: Mapped[str] = mapped_column(String)
    redis_port: Mapped[int] = mapped_column(Integer)

    rabbitmq_vhost: Mapped[str] = mapped_column(String)
    rabbitmq_user: Mapped[str] = mapped_column(String)
    rabbitmq_password: Mapped[str] = mapped_column(String)
```

## File: services/tenant-query-service/contracts/cloudevent-v1.0.json
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "uretOS CloudEvent v1.0 Specification",
  "description": "Standardized CloudEvent envelope for all asynchronous message exchanges across uretOS services. This file is a documentation/validation copy local to this service - it is intentionally NOT imported from a shared package (hyper-decoupled principle).",
  "type": "object",
  "required": [
    "specversion",
    "id",
    "source",
    "type",
    "datacontenttype",
    "time",
    "correlationid",
    "messagetype",
    "tenantid",
    "data"
  ],
  "properties": {
    "specversion": { "type": "string", "const": "1.0" },
    "id": { "type": "string", "format": "uuid" },
    "source": { "type": "string", "format": "uri-reference" },
    "type": { "type": "string" },
    "datacontenttype": { "type": "string", "const": "application/json" },
    "time": { "type": "string", "format": "date-time" },
    "correlationid": { "type": "string", "format": "uuid" },
    "messagetype": { "type": "string", "enum": ["event", "command", "query"] },
    "tenantid": {
      "type": "string",
      "minLength": 1,
      "description": "Identifies which tenant this message belongs to. Reserved value 'system' is used for super_admin-level operations such as tenant provisioning itself."
    },
    "subject": { "type": "string" },
    "data": { "type": "object" }
  }
}
```

## File: services/tenant-query-service/Dockerfile
```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY contracts/ ./contracts/
COPY app/ ./app/

WORKDIR /app/app
CMD ["python", "main.py"]
```

## File: services/timescale-query-service/src/cloudevents.py
```python
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import jsonschema

# Versuche den Pfad flexibel zu finden (entweder relativ zu src oder im gemounteten Kontext)
_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "contracts" / "cloudevent-v1.0.json"
if not _SCHEMA_PATH.exists():
    # Fallback für andere Ordnerstrukturen im Container
    _SCHEMA_PATH = Path("/app/contracts/cloudevent-v1.0.json")

_SCHEMA = json.loads(_SCHEMA_PATH.read_text()) if _SCHEMA_PATH.exists() else {}


def build_envelope(
    event_type: str,
    source: str,
    data: dict[str, Any],
    tenant_id: str,
    messagetype: str = "event",
    correlation_id: Optional[str] = None,
    subject: Optional[str] = None,
) -> dict[str, Any]:
    envelope = {
        "specversion": "1.0",
        "id": str(uuid.uuid4()),
        "source": source,
        "type": event_type,
        "datacontenttype": "application/json",
        "time": datetime.now(timezone.utc).isoformat(),
        "correlationid": correlation_id or str(uuid.uuid4()),
        "messagetype": messagetype,
        "tenantid": tenant_id,
        "data": data,
    }
    if subject:
        envelope["subject"] = subject
    validate_envelope(envelope)
    return envelope


def validate_envelope(envelope: dict[str, Any]) -> None:
    if _SCHEMA:
        jsonschema.validate(instance=envelope, schema=_SCHEMA)


def loads(raw_body: bytes) -> dict[str, Any]:
    envelope = json.loads(raw_body)
    validate_envelope(envelope)
    return envelope
```

## File: services/timescale-query-service/src/db.py
```python
from __future__ import annotations

import logging
import os

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import URL, Engine
from sqlalchemy.orm import Session

from models import MachineStateModel

log = logging.getLogger("timescale-query-service.db")

SYSTEM_DB_URL = os.environ.get(
    "SYSTEM_DB_URL",
    "postgresql+psycopg://uretos_system:uretos_system_dev_pass@system-postgres:5432/uretos_system",
)

_system_engine = create_engine(SYSTEM_DB_URL, pool_pre_ping=True)
_tenant_engines: dict[str, Engine] = {}


class TenantNotFound(RuntimeError):
    pass


def _get_tenant_engine(tenant_id: str) -> Engine:
    engine = _tenant_engines.get(tenant_id)
    if engine is not None:
        return engine

    with _system_engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT postgres_host, postgres_port, postgres_user, "
                "postgres_password, postgres_db FROM tenants WHERE tenant_id = :t"
            ),
            {"t": tenant_id},
        ).fetchone()

    if row is None:
        raise TenantNotFound(f"Tenant '{tenant_id}' not found in registry.")

    url = URL.create(
        "postgresql+psycopg",
        username=row.postgres_user,
        password=row.postgres_password,
        host=row.postgres_host,
        port=row.postgres_port,
        database=row.postgres_db,
    )
    engine = create_engine(url, pool_pre_ping=True)
    _tenant_engines[tenant_id] = engine
    log.info("Tenant engine for '%s' ready", tenant_id)
    return engine


def get_machine_history(tenant_id: str, machine_id: str, limit: int = 50) -> list[dict]:
    engine = _get_tenant_engine(tenant_id)

    if not inspect(engine).has_table("machine_states"):
        return []

    with Session(engine) as db:
        rows = (
            db.query(MachineStateModel)
            .filter_by(machine_id=machine_id)
            .order_by(MachineStateModel.time.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "time": r.time.isoformat() if r.time else None,
                "status": r.status,
                "error_code": r.error_code,
            }
            for r in rows
        ]
```

## File: services/timescale-query-service/src/main.py
```python
from __future__ import annotations

import json
import logging
import os

import pika

from cloudevents import build_envelope
from db import TenantNotFound, get_machine_history

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("timescale-query-service")

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://uretos_system:uretos_system_dev_pass@rabbitmq:5672/")
EXCHANGE = "uretos.events"
QUEUE_NAME = "timescale_query_queue"
SOURCE = "uretos/services/timescale-query-service"

QUERY_HISTORY = "uretos.timescale.query.history"


def run_query(event_type: str, data: dict) -> dict:
    tenant_id = data.get("tenant_id")
    if not tenant_id:
        return {"history": [], "error_code": "tenant_required", "error": "tenant_id is required"}

    machine_id = data.get("machine_id")
    if not machine_id:
        return {"history": [], "error_code": "machine_id_required", "error": "machine_id is required"}

    limit = data.get("limit", 50)

    try:
        if event_type == QUERY_HISTORY:
            history = get_machine_history(tenant_id, machine_id, limit=limit)
            return {"history": history}

        return {"history": [], "error_code": "unsupported_query", "error": f"Unsupported query '{event_type}'"}

    except TenantNotFound as exc:
        return {"history": [], "error_code": "tenant_not_found", "error": str(exc)}
    except Exception as exc:
        log.exception("Timescale query failed for tenant_id=%s, machine_id=%s", tenant_id, machine_id)
        return {"history": [], "error_code": "query_failed", "error": f"Query failed: {exc}"}


def callback(ch, method, properties, body):
    try:
        envelope = json.loads(body)
        event_type = envelope.get("type")
        correlation_id = envelope.get("correlationid")
        reply_to = properties.reply_to
        data = envelope.get("data", {})

        if not reply_to:
            log.error("Query received without AMQP reply_to - cannot answer, dropping")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            return

        log.info("Received query type=%s tenant_id=%s machine_id=%s", event_type, data.get("tenant_id"), data.get("machine_id"))

        response_data = run_query(event_type, data)

        envelope_out = build_envelope(
            event_type=f"{event_type}.result",
            source=SOURCE,
            data=response_data,
            tenant_id=envelope.get("tenantid", "system"),
            messagetype="query",
            correlation_id=correlation_id,
        )

        ch.basic_publish(
            exchange="",
            routing_key=reply_to,
            body=json.dumps(envelope_out).encode("utf-8"),
            properties=pika.BasicProperties(
                content_type="application/json",
                correlation_id=correlation_id,
            ),
        )

        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception:
        log.exception("Error processing timescale query")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def main():
    log.info("Starting timescale-query-service consumer...")
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()

    channel.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)
    channel.queue_declare(queue=QUEUE_NAME, durable=True)

    channel.queue_bind(queue=QUEUE_NAME, exchange=EXCHANGE, routing_key=QUERY_HISTORY)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)

    log.info("Waiting for timescale queries...")
    channel.start_consuming()


if __name__ == "__main__":
    main()
```

## File: services/timescale-query-service/src/models.py
```python
from __future__ import annotations

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class MachineStateModel(Base):
    __tablename__ = "machine_states"

    id = Column(Integer, primary_key=True, autoincrement=True)
    machine_id = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False)
    error_code = Column(String(50))
    time = Column(DateTime(timezone=True), nullable=False)
```

## File: services/timescale-query-service/Dockerfile
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY services/timescale-query-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY contracts/ ./contracts/
COPY services/timescale-query-service/src/ ./src/
WORKDIR /app/src
CMD ["python", "main.py"]
```

## File: services/timescale-query-service/requirements.txt
```
pika==1.3.2
jsonschema==4.23.0
sqlalchemy>=2.0.0
psycopg[binary]>=3.2.0
```

## File: services/timescale-writer-service/contracts/cloudevent-v1.0.json
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "uretOS CloudEvent v1.0 Specification",
  "description": "Standardized CloudEvent envelope for all asynchronous message exchanges across uretOS services. This file is a documentation/validation copy local to this service - it is intentionally NOT imported from a shared package (hyper-decoupled principle).",
  "type": "object",
  "required": [
    "specversion",
    "id",
    "source",
    "type",
    "datacontenttype",
    "time",
    "correlationid",
    "messagetype",
    "tenantid",
    "data"
  ],
  "properties": {
    "specversion": { "type": "string", "const": "1.0" },
    "id": { "type": "string", "format": "uuid" },
    "source": { "type": "string", "format": "uri-reference" },
    "type": { "type": "string" },
    "datacontenttype": { "type": "string", "const": "application/json" },
    "time": { "type": "string", "format": "date-time" },
    "correlationid": { "type": "string", "format": "uuid" },
    "messagetype": { "type": "string", "enum": ["event", "command", "query"] },
    "tenantid": {
      "type": "string",
      "minLength": 1,
      "description": "Identifies which tenant this message belongs to. Reserved value 'system' is used for super_admin-level operations such as tenant provisioning itself."
    },
    "subject": { "type": "string" },
    "data": { "type": "object" }
  }
}
```

## File: services/timescale-writer-service/src/contracts/cloudevent-v1.0.json
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "uretOS CloudEvent v1.0 Specification",
  "description": "Standardized CloudEvent envelope for all asynchronous message exchanges across uretOS services. This file is a documentation/validation copy local to this service - it is intentionally NOT imported from a shared package (hyper-decoupled principle).",
  "type": "object",
  "required": [
    "specversion",
    "id",
    "source",
    "type",
    "datacontenttype",
    "time",
    "correlationid",
    "messagetype",
    "tenantid",
    "data"
  ],
  "properties": {
    "specversion": { "type": "string", "const": "1.0" },
    "id": { "type": "string", "format": "uuid" },
    "source": { "type": "string", "format": "uri-reference" },
    "type": { "type": "string" },
    "datacontenttype": { "type": "string", "const": "application/json" },
    "time": { "type": "string", "format": "date-time" },
    "correlationid": { "type": "string", "format": "uuid" },
    "messagetype": { "type": "string", "enum": ["event", "command", "query"] },
    "tenantid": {
      "type": "string",
      "minLength": 1,
      "description": "Identifies which tenant this message belongs to. Reserved value 'system' is used for super_admin-level operations such as tenant provisioning itself."
    },
    "subject": { "type": "string" },
    "data": { "type": "object" }
  }
}
```

## File: services/timescale-writer-service/src/cloudevents.py
```python
"""
Minimal CloudEvent v1.0 (uretOS dialect) envelope helper.

This module is intentionally duplicated per-service rather than shared as a
library, per uretOS's hyper-decoupled architecture principle. Any service
needing this logic should copy this file, not import it from elsewhere.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import jsonschema

#_SCHEMA_PATH = Path(__file__).parent.parent / "contracts" / "cloudevent-v1.0.json"
_SCHEMA_PATH = Path(__file__).parent / "contracts" / "cloudevent-v1.0.json"
_SCHEMA = json.loads(_SCHEMA_PATH.read_text())


def build_envelope(
    *,
    event_type: str,
    source: str,
    data: dict[str, Any],
    tenant_id: str,
    messagetype: str = "event",
    correlation_id: Optional[str] = None,
    subject: Optional[str] = None,
) -> dict[str, Any]:
    """Build a CloudEvent envelope dict ready to be published to RabbitMQ."""
    envelope = {
        "specversion": "1.0",
        "id": str(uuid.uuid4()),
        "source": source,
        "type": event_type,
        "datacontenttype": "application/json",
        "time": datetime.now(timezone.utc).isoformat(),
        "correlationid": correlation_id or str(uuid.uuid4()),
        "messagetype": messagetype,
        "tenantid": tenant_id,
        "data": data,
    }
    if subject:
        envelope["subject"] = subject
    validate_envelope(envelope)
    return envelope


def validate_envelope(envelope: dict[str, Any]) -> None:
    """Raises jsonschema.ValidationError if the envelope is malformed."""
    jsonschema.validate(instance=envelope, schema=_SCHEMA)


def loads(raw_body: bytes) -> dict[str, Any]:
    """Parse and validate a raw RabbitMQ message body into an envelope."""
    envelope = json.loads(raw_body)
    validate_envelope(envelope)
    return envelope
```

## File: services/timescale-writer-service/src/db.py
```python
"""
Database operations for timescale-writer-service using SQLAlchemy ORM.
"""
from __future__ import annotations

import logging
import os
import time

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from models import MachineStateModel

logger = logging.getLogger("timescale-writer.db")

SYSTEM_DB_URL = os.environ.get(
    "SYSTEM_DB_URL",
    "postgresql+psycopg://uretos_system:uretos_system_dev_pass@system-postgres:5432/uretos_system",
)

SCHEMA_RETRY_ATTEMPTS = int(os.environ.get("TENANT_DB_RETRY_ATTEMPTS", "6"))
SCHEMA_RETRY_DELAY_SECONDS = float(os.environ.get("TENANT_DB_RETRY_DELAY_SECONDS", "2"))

_system_engine = create_engine(SYSTEM_DB_URL, pool_pre_ping=True)
_tenant_engines: dict[str, Engine] = {}


class TenantNotFound(RuntimeError):
    pass


def init_db() -> None:
    """Verifiziert die Erreichbarkeit der System-DB."""
    with _system_engine.connect() as conn:
        conn.execute(text("SELECT 1"))


def _ensure_tenant_schema(engine: Engine, tenant_id: str) -> None:
    """Erstellt die Tabelle deklarativ über SQLAlchemy und konfiguriert sie als Hypertable."""
    for attempt in range(1, SCHEMA_RETRY_ATTEMPTS + 1):
        try:
            # SQLAlchemy-Modell erzeugt die Tabelle konform zu Postgres-Standards
            MachineStateModel.__table__.create(bind=engine, checkfirst=True)

            # TimescaleDB Hypertable & Indizes über raw connection initialisieren
            with engine.begin() as conn:
                conn.execute(text("SELECT create_hypertable('machine_states', 'time', if_not_exists => TRUE);"))
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_machine_states_latest 
                    ON machine_states (tenant_id, machine_id, time DESC);
                """))
            return
        except OperationalError:
            if attempt == SCHEMA_RETRY_ATTEMPTS:
                raise
            logger.warning(
                "Tenant DB of '%s' not ready (attempt %d/%d), retrying...",
                tenant_id, attempt, SCHEMA_RETRY_ATTEMPTS,
            )
            time.sleep(SCHEMA_RETRY_DELAY_SECONDS)
        except Exception as e:
            # Falls TimescaleDB in der Tenant-Instanz evtl. zickt oder schon Hypertable ist
            logger.warning(f"Hinweis bei Hypertable-Initialisierung für Tenant {tenant_id}: {e}")
            return


def _get_tenant_engine(tenant_id: str) -> Engine:
    engine = _tenant_engines.get(tenant_id)
    if engine is not None:
        return engine

    with _system_engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT postgres_host, postgres_port, postgres_user, "
                "postgres_password, postgres_db FROM tenants WHERE tenant_id = :t"
            ),
            {"t": tenant_id},
        ).fetchone()

    if row is None:
        raise TenantNotFound(f"Tenant '{tenant_id}' not found in registry.")

    url = URL.create(
        "postgresql+psycopg",
        username=row.postgres_user,
        password=row.postgres_password,
        host=row.postgres_host,
        port=row.postgres_port,
        database=row.postgres_db,
    )
    
    engine = create_engine(url, pool_pre_ping=True)
    _ensure_tenant_schema(engine, tenant_id)

    _tenant_engines[tenant_id] = engine
    logger.info("Tenant engine for '%s' ready via SQLAlchemy ORM", tenant_id)
    return engine


def insert_machine_state(tenant_id: str, machine_id: str, status: str, error_code: str | None) -> None:
    """Schreibt Maschinenzustände typsicher über eine SQLAlchemy Session."""
    engine = _get_tenant_engine(tenant_id)
    with Session(engine) as session:
        state = MachineStateModel(
            tenant_id=tenant_id,
            machine_id=machine_id,
            status=status,
            error_code=error_code,
        )
        session.add(state)
        session.commit()
```

## File: services/timescale-writer-service/src/main.py
```python
"""
timescale-writer-service

Consumes machine status and telemetry events from RabbitMQ and writes them
into the respective per-tenant TimescaleDB hypertable.
"""
from __future__ import annotations

import logging
import os

import pika

from cloudevents import loads
from db import TenantNotFound, insert_machine_state

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("timescale-writer-service")

RABBITMQ_URL = os.environ.get(
    "RABBITMQ_URL", "amqp://uretos_system:uretos_system_dev_pass@rabbitmq:5672/"
)
EXCHANGE = "uretos.events"
QUEUE_NAME = "timescale_writer_queue"
ROUTING_KEY = "uretos.machine.event.status_changed"


def callback(ch, method, properties, body):
    try:
        envelope = loads(body)
        data = envelope.get("data", {})
        tenant_id = envelope.get("tenantid") or data.get("tenant_id")
        machine_id = data.get("machine_id") or envelope.get("subject")
        status = data.get("status")
        error_code = data.get("error_code")

        if not tenant_id or not machine_id or not status:
            log.error("Invalid event payload - missing tenant_id, machine_id or status. Dropping.")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            return

        log.info("Received status event for machine_id=%s tenant_id=%s status=%s", machine_id, tenant_id, status)

        insert_machine_state(tenant_id, machine_id, status, error_code)
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except TenantNotFound as exc:
        log.error("Tenant not found: %s. Dropping event.", exc)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    except Exception:
        log.exception("Error processing machine status event")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def main():
    log.info("Starting timescale-writer-service consumer...")
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()

    channel.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    channel.queue_bind(queue=QUEUE_NAME, exchange=EXCHANGE, routing_key=ROUTING_KEY)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)

    log.info("Waiting for machine events on '%s'...", ROUTING_KEY)
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        channel.stop_consuming()
    connection.close()


if __name__ == "__main__":
    main()
```

## File: services/timescale-writer-service/src/models.py
```python
"""
SQLAlchemy model for machine_states time-series data.
"""
from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class MachineStateModel(Base):
    __tablename__ = "machine_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        nullable=False
    )
    tenant_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    machine_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String, nullable=True)
```

## File: services/timescale-writer-service/Dockerfile
```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY contracts/ ./contracts/
COPY src/ .

CMD ["python", "main.py"]
```

## File: services/timescale-writer-service/requirements.txt
```
pika==1.3.2
psycopg[binary]==3.2.3
sqlalchemy==2.0.35
jsonschema==4.23.0
pydantic==2.9.2
```

## File: tools/app.py
```python
"""
uretOS Connector Box Simulator - throwaway internal tool.

Simulates a physical uretOS Connector box booting, discovering OPC-UA machines
(up to the licensed limit), trying a handshake first, falling back to pairing
if unknown (404) or pending (403), and persisting discovered machines via the
autoscan endpoint.

Runtime operational status is pushed separately via
POST /v1/connector-boxes/machine-status (not only at boot).
"""
import logging
import os
import time

import requests
import streamlit as st

from discovery import inspect_machines

logging.basicConfig(level=logging.INFO)

GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://localhost:8080")
OPC_UA_HOST = os.environ.get("OPC_UA_HOST", "localhost")
OPC_UA_PORT = int(os.environ.get("OPC_UA_PORT", "4840"))
MAX_LICENSED_MACHINES = 5  # Lizenz-Limit für Maschinen pro Connector Box

LED_OFF = "#333"
LED_GREEN = "#3ddc84"
LED_RED = "#e5484d"

STATUS_OPTIONS = ["ok", "warning", "error"]

BOX_CSS = """
<style>
.uretos-box {
    background: linear-gradient(180deg, #2b2b2e, #1a1a1c);
    border-radius: 14px;
    padding: 28px 32px;
    width: 480px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.4);
    font-family: 'Courier New', monospace;
    color: #ddd;
}
.uretos-title {
    font-size: 15px;
    letter-spacing: 3px;
    color: #aaa;
    margin-bottom: 16px;
}
.uretos-title b { color: #fff; }
.uretos-display {
    background: #0a0f0a;
    border: 2px solid #111;
    border-radius: 4px;
    padding: 14px 18px;
    font-size: 18px;
    line-height: 1.6;
    color: #3ddc84;
    white-space: pre;
    min-height: 56px;
    margin-bottom: 18px;
    text-shadow: 0 0 4px rgba(61,220,132,0.6);
}
.uretos-leds {
    display: flex;
    gap: 24px;
}
.uretos-led-row {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    color: #bbb;
}
.uretos-led-dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    display: inline-block;
}
</style>
"""


def render_box(display_line1, display_line2, leds):
    dots = "".join(
        '<div class="uretos-led-row"><span class="uretos-led-dot" '
        'style="background:' + leds[name] + '"></span>' + name + '</div>'
        for name in ["POWER", "NETWORK", "URETOS", "ERROR"]
    )
    html = (
        BOX_CSS
        + '<div class="uretos-box">'
        + '<div class="uretos-title"><b>URETOS</b> CONNECTOR</div>'
        + '<div class="uretos-display">' + display_line1 + "\n" + display_line2 + "</div>"
        + '<div class="uretos-leds">' + dots + "</div>"
        + "</div>"
    )
    html = str(html) if html is not None else ""
    return html


def push_machine_status(hardware_id: str, machines: list[dict]) -> requests.Response:
    """
    Push operational status to the gateway.

    Only send entries whose status actually changed (caller filters).
    Gateway → machine.command.update_status → status_changed → shopfloor SSE.
    """
    return requests.post(
        GATEWAY_URL + "/v1/connector-boxes/machine-status",
        json={"hardware_id": hardware_id, "machines": machines},
        timeout=25,
    )


def build_status_payload(tracked: list[dict]) -> list[dict]:
    """Build gateway payload; prefer machine_id, fall back to serial/name."""
    payload = []
    for m in tracked:
        entry = {"status": m["status"]}
        if m.get("machine_id"):
            entry["machine_id"] = m["machine_id"]
        if m.get("serial"):
            entry["serial"] = m["serial"]
        if m.get("name"):
            entry["name"] = m["name"]
        payload.append(entry)
    return payload


def main():
    st.title("uretOS Connector Box Simulator")
    st.caption(
        "Boot · OPC-UA Discovery · Handshake/Pair · Autoscan · "
        "Live Status-Push (machine-status)"
    )

    hardware_id = st.text_input("Hardware ID", help="Beispiel: tennant-c-20260928-u31c")
    boot_clicked = st.button("Boot & Connect")

    box_placeholder = st.empty()

    leds = {"POWER": LED_OFF, "NETWORK": LED_OFF, "URETOS": LED_OFF, "ERROR": LED_OFF}
    box_placeholder.markdown(render_box("URETOS CONNECTOR", "READY", leds), unsafe_allow_html=True)

    if boot_clicked and hardware_id:
        # 1. Power On
        leds["POWER"] = LED_GREEN
        box_placeholder.markdown(render_box("BOOTING...", "HARDWARE INIT", leds), unsafe_allow_html=True)
        time.sleep(0.4)

        # 2. Network Connection
        leds["NETWORK"] = LED_GREEN
        box_placeholder.markdown(render_box("NETWORKING...", "DHCP / LINK UP", leds), unsafe_allow_html=True)
        time.sleep(0.4)

        # 3. OPC UA Discovery & Metadata Read (Multi-Machine)
        box_placeholder.markdown(render_box("DISCOVERING...", f"SCANNING :{OPC_UA_PORT}", leds), unsafe_allow_html=True)
        time.sleep(0.6)

        identities = inspect_machines(OPC_UA_HOST, OPC_UA_PORT, max_machines=MAX_LICENSED_MACHINES)

        if identities:
            primary_name = str(identities[0].name)[:18].upper()
            count_str = f"FOUND: {len(identities)} MACHINES"
            box_placeholder.markdown(render_box(count_str, primary_name, leds), unsafe_allow_html=True)
        else:
            box_placeholder.markdown(render_box("DISCOVERY WARN", "NO OPC-UA SERVER", leds), unsafe_allow_html=True)
        time.sleep(0.8)

        # 4. Handshake first, fallback to pairing
        try:
            box_placeholder.markdown(render_box("HANDSHAKE...", "VERIFYING TOKEN", leds), unsafe_allow_html=True)
            response = requests.post(
                GATEWAY_URL + "/v1/connector-boxes/handshake",
                json={"hardware_id": hardware_id},
                timeout=25,
            )

            if response.status_code in (404, 403):
                box_placeholder.markdown(render_box("PAIRING...", "INITIAL REGISTRATION", leds), unsafe_allow_html=True)
                response = requests.post(
                    GATEWAY_URL + "/v1/connector-boxes/pair",
                    json={"hardware_id": hardware_id},
                    timeout=25,
                )
                action_msg = "Box erfolgreich gepaired & online!"
            else:
                action_msg = "Handshake erfolgreich durchgeführt!"

        except requests.RequestException as exc:
            leds["ERROR"] = LED_RED
            box_placeholder.markdown(render_box("GATEWAY UNREACHABLE", str(exc)[:32], leds), unsafe_allow_html=True)
            st.error("Could not reach gateway-api: " + str(exc))
            return

        if response.status_code == 200:
            # 5. Autoscan (identity only — once at boot)
            registered_machines = []
            try:
                scan_response = requests.post(
                    GATEWAY_URL + "/v1/connector-boxes/autoscan",
                    json={
                        "hardware_id": hardware_id,
                        "machines": [m.to_dict() for m in identities],
                    },
                    timeout=25,
                )
                if scan_response.status_code == 200:
                    st.toast("Erkannte Maschinen erfolgreich mit Box-Kontext persistiert!", icon="💾")
                    scan_data = scan_response.json()
                    registered_machines = scan_data.get("machines") or []
                else:
                    st.warning("Maschinen-Persistenz ergab Status: " + str(scan_response.status_code))
            except requests.RequestException as exc:
                st.warning(f"Konnte Maschinen-Autoscan nicht senden: {exc}")

            # Track machines for live status UI (merge discovery + registration ids)
            tracked = []
            for idx, ident in enumerate(identities):
                d = ident.to_dict()
                reg = registered_machines[idx] if idx < len(registered_machines) else {}
                if isinstance(reg, dict):
                    machine_id = reg.get("machine_id") or reg.get("id")
                else:
                    machine_id = None
                tracked.append({
                    "machine_id": machine_id,
                    "name": d.get("name"),
                    "serial": d.get("serial"),
                    "status": d.get("status") or "ok",
                    "last_pushed_status": None,  # force initial push
                })

            # 6. Initial status push (after registration)
            box_placeholder.markdown(render_box("STATUS PUSH...", "INITIAL ONLINE", leds), unsafe_allow_html=True)
            try:
                status_resp = push_machine_status(hardware_id, build_status_payload(tracked))
                if status_resp.status_code == 200:
                    for m in tracked:
                        m["last_pushed_status"] = m["status"]
                    st.toast("Initialer Status (ok) an Gateway gemeldet", icon="📡")
                else:
                    st.warning(
                        f"Status-Push fehlgeschlagen: HTTP {status_resp.status_code} — "
                        f"{status_resp.text[:120]}"
                    )
            except requests.RequestException as exc:
                st.warning(f"Status-Push nicht erreichbar: {exc}")

            data = response.json()
            leds["URETOS"] = LED_GREEN
            box_placeholder.markdown(render_box(hardware_id[:20], "ONLINE & STREAMING", leds), unsafe_allow_html=True)
            st.success(f"{action_msg} Erkannte Maschinen: **{len(identities)}**")

            # Persist in session for live status controls below
            st.session_state["box_online"] = True
            st.session_state["hardware_id"] = hardware_id
            st.session_state["tracked_machines"] = tracked
            st.session_state["leds"] = leds

            with st.expander(f"Discovery details ({len(identities)} Maschinen)", expanded=False):
                for idx, m in enumerate(identities):
                    st.markdown(f"**Maschine {idx + 1}: {m.name}**")
                    st.json(m.to_dict())

            st.json(data)
        else:
            leds["ERROR"] = LED_RED
            try:
                reason = response.json().get("error", "Unknown error")
            except ValueError:
                reason = f"HTTP {response.status_code}"
            box_placeholder.markdown(render_box("FAILED", reason[:28], leds), unsafe_allow_html=True)
            st.error(reason)
            st.session_state["box_online"] = False

    # -------------------------------------------------------------------------
    # Live status panel (after successful boot, survives reruns via session_state)
    # -------------------------------------------------------------------------
    if st.session_state.get("box_online") and st.session_state.get("tracked_machines"):
        st.divider()
        st.subheader("Live Maschinen-Status")
        st.caption(
            "Simuliert OPC-UA-Statusänderungen. Nur bei Änderung wird "
            "`POST /v1/connector-boxes/machine-status` aufgerufen."
        )

        hid = st.session_state["hardware_id"]
        tracked = st.session_state["tracked_machines"]
        changed = []

        for i, m in enumerate(tracked):
            label = m.get("name") or m.get("serial") or m.get("machine_id") or f"Machine {i+1}"
            cols = st.columns([3, 2])
            with cols[0]:
                st.write(f"**{label}**")
                if m.get("machine_id"):
                    st.caption(f"id: `{m['machine_id']}`")
            with cols[1]:
                new_status = st.selectbox(
                    "Status",
                    STATUS_OPTIONS,
                    index=STATUS_OPTIONS.index(m["status"]) if m["status"] in STATUS_OPTIONS else 0,
                    key=f"status_select_{i}",
                )
                if new_status != m["status"]:
                    m["status"] = new_status
                if m["status"] != m.get("last_pushed_status"):
                    changed.append(m)

        st.session_state["tracked_machines"] = tracked

        if st.button("Status-Änderungen pushen", type="primary", disabled=len(changed) == 0):
            box_placeholder.markdown(
                render_box("STATUS PUSH...", f"{len(changed)} UPDATE(S)", st.session_state.get("leds", leds)),
                unsafe_allow_html=True,
            )
            try:
                resp = push_machine_status(hid, build_status_payload(changed))
                if resp.status_code == 200:
                    for m in changed:
                        m["last_pushed_status"] = m["status"]
                    st.session_state["tracked_machines"] = tracked
                    st.success(f"{len(changed)} Status-Update(s) gesendet")
                    box_placeholder.markdown(
                        render_box(hid[:20], "ONLINE & STREAMING", st.session_state.get("leds", leds)),
                        unsafe_allow_html=True,
                    )
                else:
                    st.error(f"HTTP {resp.status_code}: {resp.text[:200]}")
            except requests.RequestException as exc:
                st.error(f"Gateway nicht erreichbar: {exc}")

        if changed:
            st.info(f"{len(changed)} Maschine(n) mit unpushtem Status — Button drücken zum Senden.")
        else:
            st.caption("Alle Status-Werte sind bereits an den Gateway gepusht.")


if __name__ == "__main__":
    main()
```

## File: scripts/reset-dev.sh
```bash
#!/usr/bin/env bash
set -euo pipefail

echo "--- Starte uretOS Dev-Reset ---"

# 1. Laufende Tenant-Container (Postgres & Redis) direkt stoppen und entfernen
containers=$(docker ps -aq --filter "name=tenant-")
if [ -n "$containers" ]; then
  echo "Entferne alte Tenant-Container..."
  docker rm -f $containers
fi

# 2. Docker Compose Services stoppen und ALLE Volumes (inkl. RabbitMQ & System-Postgres) löschen
echo "Stoppe Docker Compose Stack und bereinige Volumes..."
docker compose down -v

# 3. Restliche Tenant-Volumes manuell bereinigen (falls welche übrig sind)
volumes=$(docker volume ls -q --filter "name=tenant-")
if [ -n "$volumes" ]; then
  echo "Entferne verwaiste Tenant-Volumes..."
  docker volume rm $volumes
fi

# 4. TimescaleDB Test-Images optional bereinigen (optional, sorgt für frischen Pull)
images=$(docker images -q "timescale/timescaledb" 2>/dev/null || true)
if [ -n "$images" ]; then
  echo "Bereinige TimescaleDB Cache-Images..."
  docker rmi -f $images || true
fi

echo "--- Reset abgeschlossen! Umgebung ist wieder komplett sauber. ---"
```

## File: services/connector-box-command-service/app/db.py
```python
"""
System-Postgres access for the connector-box registry - WRITE SIDE ONLY.

This service is the single writer for the `connector_boxes` table. Each box
is mandatorily linked to a tenant at creation time (no "unassigned" boxes -
boxes are only built after a customer order comes in).
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
import psycopg

SYSTEM_DB_URL = os.environ.get(
    "SYSTEM_DB_URL",
    "postgresql://uretos_system:uretos_system_dev_pass@system-postgres:5432/uretos_system",
)
JWT_SECRET = os.environ.get("CONNECTOR_BOX_JWT_SECRET", "uretos_dev_jwt_secret_change_me")
PAIRING_TOKEN_TTL_HOURS = 72

_SCHEMA = """
CREATE TABLE IF NOT EXISTS connector_boxes (
    box_id          UUID PRIMARY KEY,
    tenant_id       TEXT NOT NULL REFERENCES tenants(tenant_id),
    hardware_id     TEXT NOT NULL UNIQUE,
    mac_address     TEXT NOT NULL UNIQUE,
    pairing_token   TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending_pairing',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


class ConnectorBoxError(RuntimeError):
    pass


def ensure_schema() -> None:
    with psycopg.connect(SYSTEM_DB_URL) as conn:
        conn.execute(_SCHEMA)
        conn.commit()


def _build_pairing_token(box_id: str, tenant_id: str, hardware_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "box_id": box_id,
        "tenant_id": tenant_id,
        "hardware_id": hardware_id,
        "iat": now,
        "exp": now + timedelta(hours=PAIRING_TOKEN_TTL_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def insert_connector_box(tenant_id: str, hardware_id: str, mac_address: str) -> dict[str, Any]:
    box_id = str(uuid.uuid4())
    pairing_token = _build_pairing_token(box_id, tenant_id, hardware_id)

    try:
        with psycopg.connect(SYSTEM_DB_URL) as conn:
            conn.execute(
                """
                INSERT INTO connector_boxes
                    (box_id, tenant_id, hardware_id, mac_address, pairing_token)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (box_id, tenant_id, hardware_id, mac_address, pairing_token),
            )
            conn.commit()
    except psycopg.errors.ForeignKeyViolation as exc:
        raise ConnectorBoxError(f"Tenant '{tenant_id}' does not exist") from exc
    except psycopg.errors.UniqueViolation as exc:
        raise ConnectorBoxError(
            f"hardware_id '{hardware_id}' or mac_address '{mac_address}' "
            "already registered to another box"
        ) from exc

    return {
        "box_id": box_id,
        "tenant_id": tenant_id,
        "hardware_id": hardware_id,
        "mac_address": mac_address,
        "pairing_token": pairing_token,
        "status": "pending_pairing",
        "pairing_token_expires_in_hours": PAIRING_TOKEN_TTL_HOURS,
    }
# ergänzen in services/connector-box-command-service/app/db.py

def pair_connector_box(hardware_id: str) -> dict[str, Any]:
    """
    Looks up a box by hardware_id and transitions pending_pairing -> paired.
    Returns the box's pairing_token so the (simulated) device receives its
    identity for the first time. Raises ConnectorBoxError if the
    hardware_id is unknown or the box is not in pending_pairing state
    (pairing is a one-time transition, not idempotent).
    """
    with psycopg.connect(SYSTEM_DB_URL) as conn:
        row = conn.execute(
            """
            SELECT box_id, tenant_id, status, pairing_token
            FROM connector_boxes
            WHERE hardware_id = %s
            FOR UPDATE
            """,
            (hardware_id,),
        ).fetchone()

        if row is None:
            raise ConnectorBoxError(f"Unknown hardware_id '{hardware_id}'")

        box_id, tenant_id, status, pairing_token = row
        if status != "pending_pairing":
            raise ConnectorBoxError(
                f"Box '{hardware_id}' is not in pending_pairing state "
                f"(current status: '{status}')"
            )

        conn.execute(
            "UPDATE connector_boxes SET status = 'paired' WHERE hardware_id = %s",
            (hardware_id,),
        )
        conn.commit()

    return {
        "box_id": str(box_id),
        "tenant_id": tenant_id,
        "hardware_id": hardware_id,
        "pairing_token": pairing_token,
        "status": "paired",
    }
```

## File: services/connector-box-command-service/app/main.py
```python
"""
connector-box-command-service

Consumes:
  uretos.connectorbox.command.create (messagetype=command, tenantid="system")
    -> Publishes uretos.connectorbox.event.created / .creation_failed

  uretos.connectorbox.command.pair (messagetype=command, tenantid="system")
    -> Simulated device boot: box presents only its hardware_id, service
       verifies the registry match and transitions pending_pairing -> paired.
    -> Publishes uretos.connectorbox.event.paired / .pairing_failed

Only the super_admin level / the (simulated) device itself is expected to
send these commands.
"""
from __future__ import annotations

import json
import logging
import os

import pika

from cloudevents import build_envelope, loads
from db import ConnectorBoxError, ensure_schema, insert_connector_box, pair_connector_box

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("connector-box-command-service")

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://uretos:uretos_dev_pass@rabbitmq:5672/")
EXCHANGE = "uretos.events"
SOURCE = "uretos/services/connector-box-command-service"

CREATE_QUEUE = "connector-box-command-service.connectorbox.command.create"
CREATE_ROUTING_KEY = "uretos.connectorbox.command.create"
CREATE_REQUIRED_FIELDS = ("tenant_id", "hardware_id", "mac_address")

PAIR_QUEUE = "connector-box-command-service.connectorbox.command.pair"
PAIR_ROUTING_KEY = "uretos.connectorbox.command.pair"
PAIR_REQUIRED_FIELDS = ("hardware_id",)


def _publish_response(channel, response) -> None:
    channel.basic_publish(
        exchange=EXCHANGE,
        routing_key=response["type"],
        body=json.dumps(response).encode("utf-8"),
        properties=pika.BasicProperties(content_type="application/json"),
    )


def handle_create(channel: pika.channel.Channel, method, properties, body: bytes) -> None:
    try:
        envelope = loads(body)
    except Exception:
        log.exception("Rejecting malformed message - not valid CloudEvent envelope")
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return

    correlation_id = envelope["correlationid"]
    data = envelope["data"]
    missing = [f for f in CREATE_REQUIRED_FIELDS if not data.get(f)]

    if missing:
        log.error("Rejecting create command - missing required fields: %s", missing)
        response = build_envelope(
            event_type="uretos.connectorbox.event.creation_failed",
            source=SOURCE,
            data={"reason": f"Missing required fields: {missing}"},
            tenant_id="system",
            messagetype="event",
            correlation_id=correlation_id,
        )
    else:
        try:
            box_info = insert_connector_box(
                tenant_id=data["tenant_id"],
                hardware_id=data["hardware_id"],
                mac_address=data["mac_address"],
            )
            log.info("Connector box '%s' created for tenant '%s'", box_info["box_id"], data["tenant_id"])
            response = build_envelope(
                event_type="uretos.connectorbox.event.created",
                source=SOURCE,
                data=box_info,
                tenant_id=data["tenant_id"],
                messagetype="event",
                correlation_id=correlation_id,
            )
        except ConnectorBoxError as exc:
            log.error("Connector box creation failed: %s", exc)
            response = build_envelope(
                event_type="uretos.connectorbox.event.creation_failed",
                source=SOURCE,
                data={"reason": str(exc)},
                tenant_id="system",
                messagetype="event",
                correlation_id=correlation_id,
            )

    _publish_response(channel, response)
    channel.basic_ack(delivery_tag=method.delivery_tag)


def handle_pair(channel: pika.channel.Channel, method, properties, body: bytes) -> None:
    try:
        envelope = loads(body)
    except Exception:
        log.exception("Rejecting malformed message - not valid CloudEvent envelope")
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return

    correlation_id = envelope["correlationid"]
    data = envelope["data"]
    missing = [f for f in PAIR_REQUIRED_FIELDS if not data.get(f)]

    if missing:
        log.error("Rejecting pair command - missing required fields: %s", missing)
        response = build_envelope(
            event_type="uretos.connectorbox.event.pairing_failed",
            source=SOURCE,
            data={"reason": f"Missing required fields: {missing}"},
            tenant_id="system",
            messagetype="event",
            correlation_id=correlation_id,
        )
    else:
        try:
            box_info = pair_connector_box(hardware_id=data["hardware_id"])
            log.info("Connector box '%s' paired (tenant '%s')", box_info["hardware_id"], box_info["tenant_id"])
            response = build_envelope(
                event_type="uretos.connectorbox.event.paired",
                source=SOURCE,
                data=box_info,
                tenant_id=box_info["tenant_id"],
                messagetype="event",
                correlation_id=correlation_id,
            )
        except ConnectorBoxError as exc:
            log.error("Connector box pairing failed: %s", exc)
            response = build_envelope(
                event_type="uretos.connectorbox.event.pairing_failed",
                source=SOURCE,
                data={"reason": str(exc)},
                tenant_id="system",
                messagetype="event",
                correlation_id=correlation_id,
            )

    _publish_response(channel, response)
    channel.basic_ack(delivery_tag=method.delivery_tag)


def main() -> None:
    ensure_schema()

    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()
    channel.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)

    channel.queue_declare(queue=CREATE_QUEUE, durable=True)
    channel.queue_bind(queue=CREATE_QUEUE, exchange=EXCHANGE, routing_key=CREATE_ROUTING_KEY)

    channel.queue_declare(queue=PAIR_QUEUE, durable=True)
    channel.queue_bind(queue=PAIR_QUEUE, exchange=EXCHANGE, routing_key=PAIR_ROUTING_KEY)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=CREATE_QUEUE, on_message_callback=handle_create)
    channel.basic_consume(queue=PAIR_QUEUE, on_message_callback=handle_pair)

    log.info("connector-box-command-service listening on '%s' and '%s'", CREATE_ROUTING_KEY, PAIR_ROUTING_KEY)
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        channel.stop_consuming()

    connection.close()


if __name__ == "__main__":
    main()
```

## File: services/connector-box-query-service/app/db.py
```python
"""
System-Postgres access for the connector-box registry - READ SIDE ONLY.

This service never writes to the `connector_boxes` table -
connector-box-command-service is the single writer, per uretOS's CQRS
convention.
"""
from __future__ import annotations

import os
from typing import Any

import psycopg
from psycopg.rows import dict_row

SYSTEM_DB_URL = os.environ.get(
    "SYSTEM_DB_URL",
    "postgresql://uretos_system:uretos_system_dev_pass@system-postgres:5432/uretos_system",
)

def get_connector_box_by_hardware_id(hardware_id: str) -> dict[str, Any] | None:
    with psycopg.connect(SYSTEM_DB_URL, row_factory=dict_row) as conn:
        row = conn.execute(
            """
            SELECT box_id, tenant_id, hardware_id, mac_address, status, created_at
            FROM connector_boxes
            WHERE hardware_id = %s
            """,
            (hardware_id,),
        ).fetchone()
    if not row:
        return None
    row["box_id"] = str(row["box_id"])
    row["created_at"] = row["created_at"].isoformat()
    return row

def list_connector_boxes() -> list[dict[str, Any]]:
    """
    Returns connector-box registry entries WITHOUT the pairing_token -
    the token is a credential, and a query response should never carry
    secrets, same reasoning as leaving passwords out of the tenant list.
    """
    with psycopg.connect(SYSTEM_DB_URL, row_factory=dict_row) as conn:
        rows = conn.execute(
            """
            SELECT box_id, tenant_id, hardware_id, mac_address, status, created_at
            FROM connector_boxes
            ORDER BY created_at DESC
            """
        ).fetchall()
    for row in rows:
        row["box_id"] = str(row["box_id"])
        row["created_at"] = row["created_at"].isoformat()
    return rows
```

## File: services/connector-box-query-service/app/main.py
```python
"""
connector-box-query-service

Consumes: 
  - uretos.connectorbox.query.list
  - uretos.connectorbox.query.by_hardware_id
Replies directly via RabbitMQ's Direct-Reply-To mechanism.

Read-only - never writes to system-postgres.
"""
from __future__ import annotations

import json
import logging
import os

import pika

from cloudevents import build_envelope, loads
from db import get_connector_box_by_hardware_id, list_connector_boxes

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("connector-box-query-service")

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://uretos:uretos_dev_pass@rabbitmq:5672/")
EXCHANGE = "uretos.events"
SOURCE = "uretos/services/connector-box-query-service"


def handle_list_query(channel: pika.channel.Channel, method, properties, body: bytes) -> None:
    try:
        envelope = loads(body)
    except Exception:
        log.exception("Rejecting malformed message - not valid CloudEvent envelope")
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return

    if not properties.reply_to:
        log.error("Query received without AMQP reply_to - cannot answer, dropping")
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return

    correlation_id = envelope["correlationid"]
    boxes = list_connector_boxes()
    log.info("Answering connector-box list query with %d box(es)", len(boxes))

    response = build_envelope(
        event_type="uretos.connectorbox.query.list.result",
        source=SOURCE,
        data={"connector_boxes": boxes},
        tenant_id="system",
        messagetype="event",
        correlation_id=correlation_id,
    )
    channel.basic_publish(
        exchange="",
        routing_key=properties.reply_to,
        properties=pika.BasicProperties(
            correlation_id=properties.correlation_id,
            content_type="application/json",
        ),
        body=json.dumps(response).encode("utf-8"),
    )
    channel.basic_ack(delivery_tag=method.delivery_tag)


def handle_hardware_id_query(channel: pika.channel.Channel, method, properties, body: bytes) -> None:
    try:
        envelope = loads(body)
    except Exception:
        log.exception("Rejecting malformed message - not valid CloudEvent envelope")
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return

    if not properties.reply_to:
        log.error("Query received without AMQP reply_to - cannot answer, dropping")
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return

    correlation_id = envelope["correlationid"]
    data = envelope.get("data", {})
    hardware_id = data.get("hardware_id")

    box = get_connector_box_by_hardware_id(hardware_id) if hardware_id else None
    log.info("Answering hardware_id query for '%s': found=%s", hardware_id, box is not None)

    response = build_envelope(
        event_type="uretos.connectorbox.query.by_hardware_id.result",
        source=SOURCE,
        data={"connector_box": box},
        tenant_id="system",
        messagetype="event",
        correlation_id=correlation_id,
    )
    channel.basic_publish(
        exchange="",
        routing_key=properties.reply_to,
        properties=pika.BasicProperties(
            correlation_id=properties.correlation_id,
            content_type="application/json",
        ),
        body=json.dumps(response).encode("utf-8"),
    )
    channel.basic_ack(delivery_tag=method.delivery_tag)


def main() -> None:
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()

    channel.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)

    # Queue für den List-Query
    queue_list = "connector-box-query-service.connectorbox.query.list"
    channel.queue_declare(queue=queue_list, durable=True)
    channel.queue_bind(queue=queue_list, exchange=EXCHANGE, routing_key="uretos.connectorbox.query.list")
    channel.basic_consume(queue=queue_list, on_message_callback=handle_list_query, auto_ack=False)

    # Queue für den Hardware-ID-Query
    queue_hw = "connector-box-query-service.connectorbox.query.hardware_id"
    channel.queue_declare(queue=queue_hw, durable=True)
    channel.queue_bind(queue=queue_hw, exchange=EXCHANGE, routing_key="uretos.connectorbox.query.by_hardware_id")
    channel.basic_consume(queue=queue_hw, on_message_callback=handle_hardware_id_query, auto_ack=False)

    channel.basic_qos(prefetch_count=1)
    log.info("connector-box-query-service listening for queries...")
    
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        channel.stop_consuming()

    connection.close()


if __name__ == "__main__":
    main()
```

## File: services/gateway-api/app/cloudevents.py
```python
"""
Minimal CloudEvent v1.0 (uretOS dialect) envelope helper.

This module is intentionally duplicated per-service rather than shared as a
library, per uretOS's hyper-decoupled architecture principle. Any service
needing this logic should copy this file, not import it from elsewhere.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import jsonschema

_SCHEMA_PATH = Path(__file__).parent.parent / "contracts" / "cloudevent-v1.0.json"
_SCHEMA = json.loads(_SCHEMA_PATH.read_text())


def build_envelope(
    event_type: str,
    source: str,
    data: dict[str, Any],
    tenant_id: str,
    messagetype: str = "event",
    correlation_id: Optional[str] = None,
    subject: Optional[str] = None,
) -> dict[str, Any]:
    """Build a CloudEvent envelope dict ready to be published to RabbitMQ."""
    envelope = {
        "specversion": "1.0",
        "id": str(uuid.uuid4()),
        "source": source,
        "type": event_type,
        "datacontenttype": "application/json",
        "time": datetime.now(timezone.utc).isoformat(),
        "correlationid": correlation_id or str(uuid.uuid4()),
        "messagetype": messagetype,
        "tenantid": tenant_id,
        "data": data,
    }
    if subject:
        envelope["subject"] = subject
    validate_envelope(envelope)
    return envelope


def validate_envelope(envelope: dict[str, Any]) -> None:
    """Raises jsonschema.ValidationError if the envelope is malformed."""
    jsonschema.validate(instance=envelope, schema=_SCHEMA)


def loads(raw_body: bytes) -> dict[str, Any]:
    """Parse and validate a raw RabbitMQ message body into an envelope."""
    envelope = json.loads(raw_body)
    validate_envelope(envelope)
    return envelope
```

## File: services/machine-command-service/src/cloudevents.py
```python
"""
Minimal CloudEvent v1.0 (uretOS dialect) envelope helper.

This module is intentionally duplicated per-service rather than shared as a
library, per uretOS's hyper-decoupled architecture principle. Any service
needing this logic should copy this file, not import it from elsewhere.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import jsonschema

_SCHEMA_PATH = Path(__file__).parent.parent / "contracts" / "cloudevent-v1.0.json"
_SCHEMA = json.loads(_SCHEMA_PATH.read_text())


def build_envelope(
    event_type: str,
    source: str,
    data: dict[str, Any],
    tenant_id: str,
    messagetype: str = "event",
    correlation_id: Optional[str] = None,
    subject: Optional[str] = None,
) -> dict[str, Any]:
    """Build a CloudEvent envelope dict ready to be published to RabbitMQ."""
    envelope = {
        "specversion": "1.0",
        "id": str(uuid.uuid4()),
        "source": source,
        "type": event_type,
        "datacontenttype": "application/json",
        "time": datetime.now(timezone.utc).isoformat(),
        "correlationid": correlation_id or str(uuid.uuid4()),
        "messagetype": messagetype,
        "tenantid": tenant_id,
        "data": data,
    }
    if subject:
        envelope["subject"] = subject
    validate_envelope(envelope)
    return envelope


def validate_envelope(envelope: dict[str, Any]) -> None:
    """Raises jsonschema.ValidationError if the envelope is malformed."""
    jsonschema.validate(instance=envelope, schema=_SCHEMA)


def loads(raw_body: bytes) -> dict[str, Any]:
    """Parse and validate a raw RabbitMQ message body into an envelope."""
    envelope = json.loads(raw_body)
    validate_envelope(envelope)
    return envelope
```

## File: services/machine-command-service/requirements.txt
```
pika==1.4.4
sqlalchemy==2.1.3
psycopg[binary]==3.3.6
jsonschema==4.23.0
```

## File: services/tenant-command-service/app/db.py
```python
"""
System-Postgres access for the tenant registry - WRITE SIDE ONLY.

This service is the single writer for the `tenants` table, per uretOS's
CQRS convention. Reading happens exclusively through tenant-query-service.

Uses SQLAlchemy ORM instead of hand-written SQL. No migration framework
(Alembic) - schema changes during this early stage are handled by
resetting the database (docker compose down -v), not by altering
existing tables in place.
"""
from __future__ import annotations

import os
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from models import Base, Tenant

SYSTEM_DB_URL = os.environ.get(
    "SYSTEM_DB_URL",
    "postgresql+psycopg://uretos_system:uretos_system_dev_pass@system-postgres:5432/uretos_system",
)

_engine = create_engine(SYSTEM_DB_URL)


def ensure_schema() -> None:
    Base.metadata.create_all(_engine)


def insert_tenant(infra_info: dict[str, Any]) -> None:
    pg = infra_info["postgres"]
    redis = infra_info["redis"]
    rabbitmq = infra_info["rabbitmq"]

    tenant = Tenant(
        tenant_id=infra_info["tenant_id"],
        postgres_host=pg["internal_host"],
        postgres_port=pg["port"],
        postgres_user=pg["user"],
        postgres_password=pg["password"],
        postgres_db=pg["database"],
        redis_host=redis["internal_host"],
        redis_port=redis["port"],
        rabbitmq_vhost=rabbitmq["vhost"],
        rabbitmq_user=rabbitmq["user"],
        rabbitmq_password=rabbitmq["password"],
    )

    with Session(_engine) as session:
        session.add(tenant)
        session.commit()
```

## File: services/tenant-command-service/requirements.txt
```
pika==1.3.2
jsonschema==4.23.0
psycopg[binary]==3.2.3
sqlalchemy==2.0.35
```

## File: services/tenant-provisioning-service/requirements.txt
```
pika==1.3.2
docker==7.1.0
jsonschema==4.23.0
requests==2.32.3
psycopg[binary]==3.2.3
```

## File: services/tenant-query-service/app/db.py
```python
"""
System-Postgres access for the tenant registry - READ SIDE ONLY.

This service never writes to the `tenants` table - tenant-command-service
is the single writer, per uretOS's CQRS convention.

Uses SQLAlchemy ORM. No secrets (postgres_password, rabbitmq_password) are
ever included in query responses - same reasoning as never returning
credentials from a read endpoint, regardless of who's currently asking.
"""
from __future__ import annotations

import os
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from models import Tenant

SYSTEM_DB_URL = os.environ.get(
    "SYSTEM_DB_URL",
    "postgresql+psycopg://uretos_system:uretos_system_dev_pass@system-postgres:5432/uretos_system",
)

_engine = create_engine(SYSTEM_DB_URL)


def list_tenants() -> list[dict[str, Any]]:
    with Session(_engine) as session:
        tenants = session.scalars(select(Tenant).order_by(Tenant.created_at.desc())).all()
        return [
            {
                "tenant_id": t.tenant_id,
                "status": t.status,
                "created_at": t.created_at.isoformat(),
                "postgres_host": t.postgres_host,
                "postgres_db": t.postgres_db,
                "redis_host": t.redis_host,
                "rabbitmq_vhost": t.rabbitmq_vhost,
                "rabbitmq_user": t.rabbitmq_user,
            }
            for t in tenants
        ]
```

## File: services/tenant-query-service/requirements.txt
```
pika==1.3.2
jsonschema==4.23.0
psycopg[binary]==3.2.3
sqlalchemy==2.0.35
```

## File: tools/admin-panel/requirements.txt
```
streamlit==1.38.0
requests==2.32.3
```

## File: tools/connector-box-simulator/discovery.py
```python
"""
discovery.py - Multi-machine OPC UA identity discovery for the uretOS Connector Box.

Goal: find name, manufacturer, model, serial number and machine type for up to 
N licensed machines (supporting umati multi-machine instances as well as 1:1 production servers).

  Stage 1  Official standards   BuildInfo, OPC 40001 Machinery (Machines/Identification),
                                OPC 10000-100 DI (DeviceSet), Companion-Spec namespaces -> type
  Stage 2  Vendor patterns      data-driven profiles (Siemens, Index, Fanuc, ...) - see VENDOR_PROFILES
  Stage 3  Generic tree scan    bounded BFS, scores properties/objects by name
"""
from __future__ import annotations

import logging
import re
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

from opcua import Client, ua

log = logging.getLogger("uretos.discovery")

# --------------------------------------------------------------------------- #
# Configuration / knowledge tables
# --------------------------------------------------------------------------- #

MACHINERY_URI = "http://opcfoundation.org/UA/Machinery/"
DI_URI = "http://opcfoundation.org/UA/DI/"

SPEC_TYPES = {
    "/UA/MachineTool/": "Machine Tool",
    "/UA/Robotics/": "Robot",
    "/UA/PackML/": "Packaging Machine",
    "/UA/PlasticsRubber/": "Plastics/Rubber Machine",
    "/UA/Woodworking/": "Woodworking Machine",
    "/UA/Weihenstephan/": "Food & Beverage Machine",
    "/UA/AdditiveManufacturing/": "Additive Manufacturing",
    "/UA/GMS/": "Coordinate Measuring Machine",
}

ALIASES = {
    # ---------- manufacturer ----------
    "manufacturer": "manufacturer",
    "manufacturername": "manufacturer",
    "vendorname": "manufacturer",
    "hersteller": "manufacturer",
    "herstellername": "manufacturer",
    "companyname": "manufacturer",
    "oem": "manufacturer",
    "supplier": "manufacturer",
    "vendor": "manufacturer",

    # ---------- model ----------
    "model": "model",
    "modelname": "model",
    "productname": "model",
    "typedesignation": "model",
    "typename": "model",
    "maschinentyp": "model",
    "produktname": "model",

    # ---------- serial ----------
    "serialnumber": "serial",
    "serialno": "serial",
    "seriennummer": "serial",
    "serial": "serial",
    "sernr": "serial",
    "sn": "serial",
    "serialnr": "serial",

    # ---------- name ----------
    "machinename": "name",
    "devicename": "name",
    "componentname": "name",
    "assetname": "name",
    "equipmentname": "name",
    "unitname": "name",
    "displayname": "name",
    "label": "name",
    "name": "name",

    # ---------- machine type ----------
    "deviceclass": "machine_type",
    "machinetype": "machine_type",
    "machinecategory": "machine_type",
    "equipmentclass": "machine_type",
    "maschinenklasse": "machine_type",
    "category": "machine_type",
    "class": "machine_type",

    # ---------- software ----------
    "softwarerevision": "software_version",
    "softwareversion": "software_version",
    "firmwareversion": "software_version",
    "revision": "software_version",
    "swversion": "software_version",
}

VENDOR_PROFILES = [
    dict(
        vendor="Siemens",
        signals=r"siemens|simatic|sinumerik|sinamics",
        anchors=r"^(PLC|SIMATIC|S7|Sinumerik|SINUMERIK|NCK|DeviceSet|Machines|Machine)",
        containers=r"^(DeviceSet|Machines)$",
        aliases={"produktname": "model", "seriennummer": "serial", "hersteller": "manufacturer"},
    ),
    dict(
        vendor="Fanuc",
        signals=r"fanuc|focas|30i|31i|32i|0i",
        anchors=r"fanuc|cnc|focas|controller|machine|deviceset",
        containers=r"^(DeviceSet|Machines)$",
        aliases={},
    ),
    dict(
        vendor="Index",
        signals=r"index[- ]?werke|\bindex\b|traub",
        anchors=r"index|traub|machine|cnc|deviceset",
        containers=r"^(DeviceSet|Machines)$",
        aliases={},
    ),
    dict(
        vendor="Beckhoff",
        signals=r"beckhoff|twincat",
        anchors=r"^(PLC|TwinCAT|Tc|DeviceSet|Machines)",
        containers=r"^(DeviceSet|Machines)$",
        aliases={},
    ),
    dict(
        vendor="B&R",
        signals=r"b&r|br-automation|bernecker",
        anchors=r"^(PLC|CPU|Machine|DeviceSet|Machines)",
        containers=r"^(DeviceSet|Machines)$",
        aliases={},
    ),
    dict(
        vendor="Heidenhain",
        signals=r"heidenhain|tnc",
        anchors=r"tnc|dnc|machine|deviceset",
        containers=r"^(DeviceSet|Machines)$",
        aliases={},
    ),
]

GENERIC_SKIP = {
    "Server", "ServerTypes", "DataTypes", "XmlSchema", "Client", "Aliases",
    "Locations", "Quantities", "Views", "Types", "Interfaces", "DeviceSet_",
    "ServerConfiguration", "HistoryServerCapabilities", "Namespaces",
}
NAME_HINTS = re.compile(
    r"machine|device|cnc|robot|press|lathe|mill|plc|line|station|cell|"
    r"drill|saw|oven|controller|unit|asset|equipment",
    re.I,
)
TYPE_HINTS = [
    (r"cnc|lathe|mill|drill|turn|machining|machine.?tool", "Machine Tool"),
    (r"robot", "Robot"),
    (r"press|imm|injection|mould", "Press / Moulding"),
    (r"plc|controller", "PLC"),
    (r"pack", "Packaging Machine"),
    (r"wood|saw", "Woodworking Machine"),
    (r"additive|3d.?print|am.?machine", "Additive Manufacturing"),
    (r"cmm|measur|hexagon|wenzel", "Coordinate Measuring Machine"),
]
PLACEHOLDERS = {
    "", "n/a", "na", "unknown", "none", "null", "-", "0",
    "undefined", "not available", "n.a.", "---",
}

GENERIC_FALLBACK_NAME = "Generic OPC-UA Machine"

IDENT_FOLDER_NAMES = {
    "identification", "machineidentification", "deviceidentification",
    "info", "machineinfo", "deviceinfo", "identity", "assetidentification",
}

# --------------------------------------------------------------------------- #
# Result type
# --------------------------------------------------------------------------- #

@dataclass
class MachineIdentity:
    name: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial: Optional[str] = None
    machine_type: Optional[str] = None
    software_version: Optional[str] = None
    status: str = "ok"              # Neu: Initialer Status ('ok', 'warning', 'error')
    error_code: Optional[str] = None # Neu: Optionaler Fehlercode bei Störung
    sources: dict = field(default_factory=dict)
    extra: dict = field(default_factory=dict)

    CORE = ("name", "manufacturer", "model", "serial")
    REQUIRED = ("name", "manufacturer", "machine_type")

    def get(self, f):
        return getattr(self, f)

    def set(self, f, value, source) -> bool:
        if value and not getattr(self, f):
            setattr(self, f, value)
            self.sources[f] = source
            return True
        return False

    @property
    def complete(self) -> bool:
        return all(getattr(self, f) for f in self.CORE)

    @property
    def has_required(self) -> bool:
        return all(getattr(self, f) for f in self.REQUIRED)

    @property
    def confidence(self) -> str:
        srcs = list(self.sources.values())
        if any(s.startswith("stage1") for s in srcs):
            return "high"
        if any(s.startswith("stage2") for s in srcs):
            return "medium"
        return "low"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "serial": self.serial,
            "machine_type": self.machine_type,
            "software_version": self.software_version,
            "status": self.status,       # Neu im Dictionary für den Autoscan
            "error_code": self.error_code, # Neu im Dictionary
            "confidence": self.confidence,
            "sources": self.sources,
            "extra": self.extra,
        }

# --------------------------------------------------------------------------- #
# Low-level helpers
# --------------------------------------------------------------------------- #

class _Ctx:
    def __init__(self, client: Client):
        self.client = client
        self.objects = client.get_objects_node()
        try:
            self.ns_array = client.get_namespace_array()
        except Exception:
            self.ns_array = []
        self.server = {}
        self._top = None

    def has_ns(self, uri_part: str) -> Optional[str]:
        for uri in self.ns_array:
            if uri_part.lower() in uri.lower():
                return uri
        return None

    def top_objects(self):
        if self._top is None:
            self._top = [k for k in kids(self.client, self.objects) if k[0] != 0]
        return self._top

def _norm(name: str) -> str:
    return re.sub(r"[\s_\-]", "", name.lower())

def kids(client, node):
    try:
        descs = node.get_children_descriptions()
    except Exception as exc:
        log.debug("browse failed: %s", exc)
        return []
    return [
        (d.BrowseName.NamespaceIndex, d.BrowseName.Name, d.NodeClass, client.get_node(d.NodeId))
        for d in descs
    ]

def read_text(node) -> Optional[str]:
    try:
        v = node.get_value()
    except Exception:
        return None
    if isinstance(v, ua.LocalizedText):
        v = v.Text
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        v = str(v)
    if isinstance(v, str):
        v = v.strip()
        return None if v.lower() in PLACEHOLDERS else v
    return None

def harvest(client, node, ident, source, max_depth=2, depth=0, aliases=None):
    table = {**ALIASES, **(aliases or {})}
    for _ns, name, ncls, child in kids(client, node):
        if ncls == ua.NodeClass.Variable:
            f = table.get(_norm(name))
            if f and not ident.get(f):
                ident.set(f, read_text(child), source)
        elif ncls == ua.NodeClass.Object and depth < max_depth:
            harvest(client, child, ident, source, max_depth, depth + 1, aliases)

def _harvest_identification_folders(client, parent_node, ident, source, aliases=None):
    for _ns, name, ncls, child in kids(client, parent_node):
        if ncls == ua.NodeClass.Object and _norm(name) in IDENT_FOLDER_NAMES:
            harvest(client, child, ident, source, max_depth=2, aliases=aliases)
            harvest(client, child, ident, source, max_depth=3, aliases=aliases)

# --------------------------------------------------------------------------- #
# Stage 1 - official standards (Multi-machine support)
# --------------------------------------------------------------------------- #

def _stage1_standard(ctx: _Ctx, identities: list[MachineIdentity], max_machines: int):
    c = ctx.client

    # 1a) Server BuildInfo
    for key, attr in (
        ("manufacturer", "ManufacturerName"),
        ("product", "ProductName"),
        ("version", "SoftwareVersion"),
        ("uri", "ProductUri"),
    ):
        oid = getattr(ua.ObjectIds, f"Server_ServerStatus_BuildInfo_{attr}", None)
        if oid is not None:
            val = read_text(c.get_node(ua.NodeId(oid)))
            if val:
                ctx.server[key] = val

    # 1b) Companion Specs present -> machine types
    companion_specs = []
    global_mtype = None
    for part, mtype in SPEC_TYPES.items():
        uri = ctx.has_ns(part)
        if uri:
            companion_specs.append(uri)
            if not global_mtype:
                global_mtype = mtype

    # 1c) OPC 40001 Machinery: Objects/Machines/<machine>/Identification
    machines = [k for k in ctx.top_objects() if k[1] == "Machines"]
    if machines and ctx.has_ns(MACHINERY_URI):
        found = [k for k in kids(c, machines[0][3]) if k[2] == ua.NodeClass.Object]
        for _ns, mname, _cls, mnode in found[:max_machines]:
            ident = MachineIdentity()
            ident.set("name", mname, "stage1:machinery")
            if global_mtype:
                ident.set("machine_type", global_mtype, "stage1:spec")
            for spec_uri in companion_specs:
                ident.extra.setdefault("companion_specs", []).append(spec_uri)

            harvest(c, mnode, ident, "stage1:machinery", max_depth=3)
            _harvest_identification_folders(c, mnode, ident, "stage1:machinery")
            identities.append(ident)

    # 1d) OPC 10000-100 DI: Objects/DeviceSet/<device>
    if not identities:
        devsets = [k for k in ctx.top_objects() if k[1] == "DeviceSet"]
        if devsets:
            found_devs = [k for k in kids(c, devsets[0][3]) if k[2] == ua.NodeClass.Object]
            for _ns, dname, _cls, dnode in found_devs[:max_machines]:
                ident = MachineIdentity()
                ident.set("name", dname, "stage1:di")
                if global_mtype:
                    ident.set("machine_type", global_mtype, "stage1:spec")
                for spec_uri in companion_specs:
                    ident.extra.setdefault("companion_specs", []).append(spec_uri)

                harvest(c, dnode, ident, "stage1:di", max_depth=2)
                _harvest_identification_folders(c, dnode, ident, "stage1:di")
                identities.append(ident)

# --------------------------------------------------------------------------- #
# Stage 2 - vendor patterns (Multi-machine support)
# --------------------------------------------------------------------------- #

def _stage2_vendor(ctx: _Ctx, identities: list[MachineIdentity], max_machines: int):
    signals = " ".join(list(ctx.server.values()) + list(ctx.ns_array)).lower()
    for prof in VENDOR_PROFILES:
        if not re.search(prof["signals"], signals):
            continue
        src = f"stage2:{prof['vendor']}"
        log.info("vendor profile matched: %s", prof["vendor"])

        for _ns, name, ncls, node in ctx.top_objects():
            if ncls != ua.NodeClass.Object or not re.search(prof["anchors"], name, re.I):
                continue

            if re.search(prof["containers"], name):
                device_kids = [k for k in kids(ctx.client, node) if k[2] == ua.NodeClass.Object]
                if not device_kids:
                    ident = MachineIdentity()
                    ident.set("manufacturer", prof["vendor"], src)
                    ident.set("name", name, src)
                    harvest(ctx.client, node, ident, src, max_depth=3, aliases=prof["aliases"])
                    _harvest_identification_folders(ctx.client, node, ident, src, aliases=prof["aliases"])
                    identities.append(ident)
                else:
                    for (_dns, dname, _dcls, dnode) in device_kids[:max_machines]:
                        ident = MachineIdentity()
                        ident.set("manufacturer", prof["vendor"], src)
                        ident.set("name", dname, src)
                        harvest(ctx.client, dnode, ident, src, max_depth=3, aliases=prof["aliases"])
                        _harvest_identification_folders(ctx.client, dnode, ident, src, aliases=prof["aliases"])
                        identities.append(ident)
            else:
                ident = MachineIdentity()
                ident.set("manufacturer", prof["vendor"], src)
                ident.set("name", name, src)
                harvest(ctx.client, node, ident, src, max_depth=3, aliases=prof["aliases"])
                _harvest_identification_folders(ctx.client, node, ident, src, aliases=prof["aliases"])
                identities.append(ident)

            if len(identities) >= max_machines:
                break
        if identities:
            break

# --------------------------------------------------------------------------- #
# Stage 3 - generic tree analysis
# --------------------------------------------------------------------------- #

def _stage3_generic(ctx: _Ctx, ident: MachineIdentity, max_depth=4, max_nodes=400):
    c = ctx.client
    queue = deque(
        (k, 1, k[1]) for k in ctx.top_objects() if k[1] not in GENERIC_SKIP
    )
    visited = 0
    best_obj = None
    candidates = {}

    while queue and visited < max_nodes:
        (_ns, name, ncls, node), depth, path = queue.popleft()
        visited += 1
        score = 1.0 / depth

        if ncls == ua.NodeClass.Variable:
            f = ALIASES.get(_norm(name))
            if f and not ident.get(f):
                val = read_text(node)
                if val and score > candidates.get(f, (0,))[0]:
                    candidates[f] = (score, val, path)
            continue

        if ncls == ua.NodeClass.Object:
            if NAME_HINTS.search(name):
                obj_score = score + 0.3
                if best_obj is None or obj_score > best_obj[0]:
                    best_obj = (obj_score, name, path)

            if depth < max_depth:
                for k in kids(c, node):
                    if k[1] not in GENERIC_SKIP:
                        queue.append((k, depth + 1, f"{path}/{k[1]}"))

    for f, (_score, val, path) in candidates.items():
        ident.set(f, val, f"stage3:{path}")

    if best_obj:
        ident.set("name", best_obj[1], f"stage3:{best_obj[2]}")
    elif ctx.top_objects() and not ident.name:
        ident.set("name", ctx.top_objects()[0][1], "stage3:first-object")

# --------------------------------------------------------------------------- #
# Public APIs
# --------------------------------------------------------------------------- #

def inspect_machines(host: str, port: int, max_machines: int = 5, timeout: float = 3.0) -> list[MachineIdentity]:
    """Returns a list of MachineIdentities (up to max_machines licensed slots) found on the server."""
    client = Client(f"opc.tcp://{host}:{port}", timeout=timeout)
    try:
        client.connect()
    except Exception as exc:
        log.warning("OPC UA connect failed: %s", exc)
        return []

    try:
        ctx = _Ctx(client)
        identities: list[MachineIdentity] = []

        # Stage 1: Official standards
        try:
            _stage1_standard(ctx, identities, max_machines=max_machines)
        except Exception:
            log.exception("Stage 1 failed")

        # Stage 2: Vendor patterns if Stage 1 found nothing
        if not identities:
            try:
                _stage2_vendor(ctx, identities, max_machines=max_machines)
            except Exception:
                log.exception("Stage 2 failed")

        # Stage 3: Generic tree analysis if still empty
        if not identities:
            try:
                ident = MachineIdentity()
                _stage3_generic(ctx, ident)
                if ident.name or ident.manufacturer:
                    identities.append(ident)
            except Exception:
                log.exception("Stage 3 failed")

        # Post-processing fallbacks for each discovered identity
        for ident in identities:
            ident.set("manufacturer", ctx.server.get("manufacturer"), "fallback:buildinfo")
            ident.set("software_version", ctx.server.get("version"), "fallback:buildinfo")
            ident.set("model", ctx.server.get("product"), "fallback:buildinfo")

            if not ident.machine_type:
                hay = f"{ident.name or ''} {ident.model or ''} {ident.manufacturer or ''}"
                for pattern, mtype in TYPE_HINTS:
                    if re.search(pattern, hay, re.I):
                        ident.set("machine_type", mtype, "fallback:name-hint")
                        break

            if not ident.name:
                ident.set("name", GENERIC_FALLBACK_NAME, "fallback:default")

        # Absolute fallback if completely empty
        if not identities:
            fallback = MachineIdentity(name=GENERIC_FALLBACK_NAME)
            fallback.sources["name"] = "fallback:default"
            identities.append(fallback)

        return identities
    finally:
        try:
            client.disconnect()
        except Exception:
            pass

def discover_machine(host: str, port: int, timeout: float = 3.0) -> Optional[MachineIdentity]:
    """Backward-compatible wrapper returning the primary (first) machine found."""
    results = inspect_machines(host, port, max_machines=1, timeout=timeout)
    return results[0] if results else None


def dump_tree(host: str, port: int, max_depth=4, max_nodes=300) -> list[str]:
    """Diagnostics: browse dump of a real machine."""
    client = Client(f"opc.tcp://{host}:{port}", timeout=3.0)
    client.connect()
    lines = []
    try:
        queue = deque([(client.get_objects_node(), 0, "Objects")])
        while queue and len(lines) < max_nodes:
            node, depth, label = queue.popleft()
            for ns, name, ncls, child in kids(client, node):
                p = f"{label}/{ns}:{name}"
                val = read_text(child) if ncls == ua.NodeClass.Variable else ""
                lines.append(f"{p}  [{ncls.name}] {val or ''}".rstrip())
                if ncls == ua.NodeClass.Object and depth + 1 < max_depth:
                    queue.append((child, depth + 1, p))
    finally:
        client.disconnect()
    return lines
```

## File: tools/connector-box-simulator/requirements.txt
```
streamlit==1.38.0
requests==2.32.3
opcua==0.98.13
```

## File: services/shopfloor-stream-service/src/main.py
```python
"""
shopfloor-stream-service

Bridges RabbitMQ machine events to SSE streams for uretOS modules (Cockpit
and others) that need live shopfloor state - without those modules ever
touching RabbitMQ or machine-command-service/machine-query-service directly.

Two RabbitMQ touchpoints:
  1. A background thread subscribes to uretos.machine.event.* and fans out
     each event to all SSE clients currently connected for that tenant.
  2. On a new SSE connection, a one-off RPC call to machine-query-service
     (uretos.machine.query.list) fetches the current machine snapshot, sent
     as the first SSE message before live events follow.

In-memory only, single-instance pub/sub (dict tenant_id -> set of queues).
No Redis, no persistence - acceptable at the current scale; revisit if this
service ever needs to run as more than one replica.

Endpoint:
  GET /v1/shopfloor/stream?tenant_id=<id>   (SSE)
  GET /healthz
"""
from __future__ import annotations

import json
import logging
import os
import queue
import threading
import time
import uuid

import pika
from flask import Flask, Response, jsonify, request

from cloudevents import build_envelope, loads

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("shopfloor-stream-service")

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://uretos_system:uretos_system_dev_pass@rabbitmq:5672/")
EXCHANGE = "uretos.events"
QUEUE_NAME = "shopfloor-stream-service.machine.events"
SOURCE = "uretos/services/shopfloor-stream-service"
SNAPSHOT_TIMEOUT_SECONDS = 15
KEEPALIVE_SECONDS = 20

# Future telemetry events get added to this tuple once that stage starts.
MACHINE_EVENT_ROUTING_KEYS = (
    "uretos.machine.event.registered",
    "uretos.machine.event.status_changed",
)

app = Flask(__name__)

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response

_subscribers: dict[str, set] = {}
_subscribers_lock = threading.Lock()


def _subscribe(tenant_id: str) -> "queue.Queue":
    q: "queue.Queue" = queue.Queue()
    with _subscribers_lock:
        _subscribers.setdefault(tenant_id, set()).add(q)
    return q


def _unsubscribe(tenant_id: str, q: "queue.Queue") -> None:
    with _subscribers_lock:
        subs = _subscribers.get(tenant_id)
        if subs is not None:
            subs.discard(q)
            if not subs:
                _subscribers.pop(tenant_id, None)


def _publish_to_subscribers(tenant_id: str, payload: dict) -> None:
    with _subscribers_lock:
        subs = list(_subscribers.get(tenant_id, ()))
    for q in subs:
        q.put(payload)


def _consume_machine_events() -> None:
    """Runs in a background thread for the lifetime of the process.
    Reconnects on any failure instead of letting the whole service die."""
    while True:
        try:
            connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
            channel = connection.channel()
            channel.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)
            channel.queue_declare(queue=QUEUE_NAME, durable=True)
            for routing_key in MACHINE_EVENT_ROUTING_KEYS:
                channel.queue_bind(queue=QUEUE_NAME, exchange=EXCHANGE, routing_key=routing_key)

            def on_message(ch, method, properties, body):
                try:
                    envelope = loads(body)
                except Exception:
                    log.exception("Dropping malformed machine event")
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                    return

                tenant_id = envelope.get("tenantid")
                if tenant_id and tenant_id != "system":
                    _publish_to_subscribers(tenant_id, envelope)
                ch.basic_ack(delivery_tag=method.delivery_tag)

            channel.basic_qos(prefetch_count=10)
            channel.basic_consume(queue=QUEUE_NAME, on_message_callback=on_message)
            log.info("shopfloor-stream-service consuming machine events...")
            channel.start_consuming()

        except Exception:
            log.exception("RabbitMQ consumer crashed - reconnecting in 5s")
            time.sleep(5)


def _fetch_snapshot(tenant_id: str) -> list[dict]:
    """One-off RPC call to machine-query-service for the current machine list."""
    correlation_id = str(uuid.uuid4())
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()
    channel.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)

    envelope_out = build_envelope(
        event_type="uretos.machine.query.list",
        source=SOURCE,
        data={"tenant_id": tenant_id},
        tenant_id=tenant_id,
        messagetype="query",
        correlation_id=correlation_id,
    )

    result_holder: dict = {}

    def on_response(ch, method, properties, body):
        if properties.correlation_id == correlation_id:
            result_holder["envelope"] = json.loads(body)
            ch.stop_consuming()

    channel.basic_consume(queue="amq.rabbitmq.reply-to", on_message_callback=on_response, auto_ack=True)
    channel.basic_publish(
        exchange=EXCHANGE,
        routing_key="uretos.machine.query.list",
        properties=pika.BasicProperties(
            reply_to="amq.rabbitmq.reply-to",
            correlation_id=correlation_id,
            content_type="application/json",
        ),
        body=json.dumps(envelope_out).encode("utf-8"),
    )

    connection.process_data_events(time_limit=SNAPSHOT_TIMEOUT_SECONDS)
    connection.close()

    envelope_in = result_holder.get("envelope")
    if envelope_in is None:
        log.warning("Snapshot query timed out for tenant_id=%s", tenant_id)
        return []
    return envelope_in.get("data", {}).get("machines", [])


@app.route("/v1/shopfloor/stream", methods=["GET"])
def stream():
    tenant_id = request.args.get("tenant_id")
    if not tenant_id:
        return jsonify({"error": "tenant_id query parameter is required"}), 400

    def event_stream():
        snapshot = _fetch_snapshot(tenant_id)
        snapshot_envelope = build_envelope(
            event_type="uretos.shopfloor.snapshot",
            source=SOURCE,
            data={"machines": snapshot},
            tenant_id=tenant_id,
            messagetype="event",
        )
        yield f"data: {json.dumps(snapshot_envelope)}\n\n"

        q = _subscribe(tenant_id)
        log.info("SSE client connected for tenant_id=%s", tenant_id)
        try:
            while True:
                try:
                    payload = q.get(timeout=KEEPALIVE_SECONDS)
                    yield f"data: {json.dumps(payload)}\n\n"
                except queue.Empty:
                    yield ": keep-alive\n\n"
        finally:
            _unsubscribe(tenant_id, q)
            log.info("SSE client disconnected for tenant_id=%s", tenant_id)

    return Response(
        event_stream(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/healthz", methods=["GET"])
def healthz():
    return jsonify({"status": "ok"}), 200


def main() -> None:
    consumer_thread = threading.Thread(target=_consume_machine_events, daemon=True)
    consumer_thread.start()
    app.run(host="0.0.0.0", port=8081, threaded=True)


if __name__ == "__main__":
    main()
```

## File: services/tenant-command-service/app/main.py
```python
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
```

## File: services/tenant-provisioning-service/app/provisioning.py
```python
"""
Per-tenant infrastructure provisioning.

Talks to the Docker Engine API *through* docker-socket-proxy (never the raw
socket) to create one isolated Postgres container (with TimescaleDB enabled 
via post-start exec_run with pg_isready check) and one isolated Redis 
container per tenant. Also creates an isolated RabbitMQ vhost + user per 
tenant via the RabbitMQ Management HTTP API.
"""
from __future__ import annotations

import os
import re
import secrets
import logging
import time

import docker
import requests

logger = logging.getLogger("tenant-provisioning")

DOCKER_HOST = "tcp://uretos-docker-proxy:2375"
NETWORK_NAME = "uretos-tenant-net"

RABBITMQ_MGMT_URL = os.environ.get("RABBITMQ_MGMT_URL", "http://rabbitmq:15672")
RABBITMQ_ADMIN_USER = os.environ.get("RABBITMQ_ADMIN_USER", "uretos")
RABBITMQ_ADMIN_PASSWORD = os.environ.get("RABBITMQ_ADMIN_PASSWORD", "uretos_dev_pass")

_TENANT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,30}[a-z0-9]$")


class ProvisioningError(RuntimeError):
    pass


def _validate_tenant_id(tenant_id: str) -> None:
    if not _TENANT_ID_RE.match(tenant_id):
        raise ProvisioningError(
            f"tenant_id '{tenant_id}' invalid - must be lowercase "
            "alphanumeric/hyphen, 3-32 chars, used directly in container "
            "and volume names."
        )


def _client() -> docker.DockerClient:
    return docker.DockerClient(base_url=DOCKER_HOST)


def provision_tenant_infrastructure(tenant_id: str) -> dict:
    """
    Creates an isolated Postgres (TimescaleDB) + Redis container pair for one tenant.
    Returns connection info for the provisioning-event's data payload.
    """
    _validate_tenant_id(tenant_id)
    client = _client()

    pg_name = f"tenant-{tenant_id}-postgres"
    redis_name = f"tenant-{tenant_id}-redis"

    for name in (pg_name, redis_name):
        try:
            client.containers.get(name)
            raise ProvisioningError(
                f"Container '{name}' already exists - refusing to "
                "re-provision an existing tenant."
            )
        except docker.errors.NotFound:
            pass

    _ensure_network(client)

    db_password = secrets.token_urlsafe(24)
    pg_container = client.containers.run(
        image="timescale/timescaledb:latest-pg16",
        name=pg_name,
        detach=True,
        network=NETWORK_NAME,
        environment={
            "POSTGRES_USER": f"tenant_{tenant_id}",
            "POSTGRES_PASSWORD": db_password,
            "POSTGRES_DB": f"tenant_{tenant_id}",
        },
        volumes={
            f"{pg_name}-data": {"bind": "/var/lib/postgresql/data", "mode": "rw"},
        },
        restart_policy={"Name": "unless-stopped"},
    )

    # Robustes Warten, bis Postgres bereit ist, danach TimescaleDB-Extension aktivieren
    postgres_ready = False
    for _ in range(20):
        exec_res = pg_container.exec_run("pg_isready")
        if exec_res.exit_code == 0:
            postgres_ready = True
            break
        time.sleep(1)

    if not postgres_ready:
        raise ProvisioningError("Timed out waiting for tenant Postgres to become ready.")

    ext_res = pg_container.exec_run(
        f"psql -U tenant_{tenant_id} -d tenant_{tenant_id} -c 'CREATE EXTENSION IF NOT EXISTS timescaledb;'"
    )
    if ext_res.exit_code != 0:
        raise ProvisioningError(f"Failed to create TimescaleDB extension: {ext_res.output.decode()}")

    redis_container = client.containers.run(
        image="redis:7-alpine",
        name=redis_name,
        detach=True,
        network=NETWORK_NAME,
        volumes={f"{redis_name}-data": {"bind": "/data", "mode": "rw"}},
        restart_policy={"Name": "unless-stopped"},
        command="redis-server --appendonly yes",
    )

    return {
        "tenant_id": tenant_id,
        "postgres": {
            "container_name": pg_name,
            "container_id": pg_container.id,
            "internal_host": pg_name,
            "port": 5432,
            "user": f"tenant_{tenant_id}",
            "password": db_password,
            "database": f"tenant_{tenant_id}",
        },
        "redis": {
            "container_name": redis_name,
            "container_id": redis_container.id,
            "internal_host": redis_name,
            "port": 6379,
        },
    }


def _ensure_network(client: docker.DockerClient) -> None:
    try:
        client.networks.get(NETWORK_NAME)
    except docker.errors.NotFound:
        client.networks.create(NETWORK_NAME, driver="bridge")


def provision_tenant_rabbitmq(tenant_id: str) -> dict:
    """
    Creates an isolated RabbitMQ vhost + a user scoped exclusively to it,
    via the Management HTTP API.
    """
    auth = (RABBITMQ_ADMIN_USER, RABBITMQ_ADMIN_PASSWORD)
    vhost_name = f"tenant-{tenant_id}"
    rabbitmq_user = f"tenant_{tenant_id}"
    rabbitmq_password = secrets.token_urlsafe(24)

    vhost_response = requests.put(
        f"{RABBITMQ_MGMT_URL}/api/vhosts/{vhost_name}", auth=auth, timeout=10
    )
    if vhost_response.status_code not in (201, 204):
        raise ProvisioningError(f"Failed to create RabbitMQ vhost: {vhost_response.text}")

    user_response = requests.put(
        f"{RABBITMQ_MGMT_URL}/api/users/{rabbitmq_user}",
        auth=auth,
        json={"password": rabbitmq_password, "tags": ""},
        timeout=10,
    )
    if user_response.status_code not in (201, 204):
        raise ProvisioningError(f"Failed to create RabbitMQ user: {user_response.text}")

    permission_response = requests.put(
        f"{RABBITMQ_MGMT_URL}/api/permissions/{vhost_name}/{rabbitmq_user}",
        auth=auth,
        json={"configure": ".*", "write": ".*", "read": ".*"},
        timeout=10,
    )
    if permission_response.status_code not in (201, 204):
        raise ProvisioningError(f"Failed to set RabbitMQ permissions: {permission_response.text}")

    return {
        "vhost": vhost_name,
        "user": rabbitmq_user,
        "password": rabbitmq_password,
    }
```

## File: tools/connector-box-simulator/app.py
```python
"""
uretOS Connector Box Simulator - throwaway internal tool.

Simulates a physical uretOS Connector box booting, discovering OPC-UA machines
(up to the licensed limit), trying a handshake first, falling back to pairing
if unknown (404) or pending (403), and persisting discovered machines via the
autoscan endpoint.
"""
import logging
import os
import time

import requests
import streamlit as st

from discovery import inspect_machines

logging.basicConfig(level=logging.INFO)

GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://localhost:8080")
OPC_UA_HOST = os.environ.get("OPC_UA_HOST", "localhost")
OPC_UA_PORT = int(os.environ.get("OPC_UA_PORT", "4840"))
MAX_LICENSED_MACHINES = 5  # Lizenz-Limit für Maschinen pro Connector Box

LED_OFF = "#333"
LED_GREEN = "#3ddc84"
LED_RED = "#e5484d"

BOX_CSS = """
<style>
.uretos-box {
    background: linear-gradient(180deg, #2b2b2e, #1a1a1c);
    border-radius: 14px;
    padding: 28px 32px;
    width: 480px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.4);
    font-family: 'Courier New', monospace;
    color: #ddd;
}
.uretos-title {
    font-size: 15px;
    letter-spacing: 3px;
    color: #aaa;
    margin-bottom: 16px;
}
.uretos-title b { color: #fff; }
.uretos-display {
    background: #0a0f0a;
    border: 2px solid #111;
    border-radius: 4px;
    padding: 14px 18px;
    font-size: 18px;
    line-height: 1.6;
    color: #3ddc84;
    white-space: pre;
    min-height: 56px;
    margin-bottom: 18px;
    text-shadow: 0 0 4px rgba(61,220,132,0.6);
}
.uretos-leds {
    display: flex;
    gap: 24px;
}
.uretos-led-row {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    color: #bbb;
}
.uretos-led-dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    display: inline-block;
}
</style>
"""


def render_box(display_line1, display_line2, leds):
    dots = "".join(
        '<div class="uretos-led-row"><span class="uretos-led-dot" '
        'style="background:' + leds[name] + '"></span>' + name + '</div>'
        for name in ["POWER", "NETWORK", "URETOS", "ERROR"]
    )
    html = (
        BOX_CSS
        + '<div class="uretos-box">'
        + '<div class="uretos-title"><b>URETOS</b> CONNECTOR</div>'
        + '<div class="uretos-display">' + display_line1 + "\n" + display_line2 + "</div>"
        + '<div class="uretos-leds">' + dots + "</div>"
        + "</div>"
    )
    html = str(html) if html is not None else ""
    return html


def main():
    st.title("uretOS Connector Box Simulator")
    st.caption("Simuliert Geräte-Boot, OPC-UA Multi-Maschinen-Discovery, Smart Handshake, Auto-Pairing und Maschinen-Persistenz")

    # Session State initialisieren, damit Daten bei Reruns erhalten bleiben
    if "is_online" not in st.session_state:
        st.session_state.is_online = False
    if "identities" not in st.session_state:
        st.session_state.identities = []
    if "box_data" not in st.session_state:
        st.session_state.box_data = {}
    if "leds" not in st.session_state:
        st.session_state.leds = {"POWER": LED_OFF, "NETWORK": LED_OFF, "URETOS": LED_OFF, "ERROR": LED_OFF}

    hardware_id = st.text_input("Hardware ID", value="edc701f0-bf8c-4024-b23e-d90499caafca", help="Beispiel: tennant-c-20260928-u31c")
    boot_clicked = st.button("Boot & Connect")

    box_placeholder = st.empty()

    if boot_clicked and hardware_id:
        st.session_state.leds = {"POWER": LED_OFF, "NETWORK": LED_OFF, "URETOS": LED_OFF, "ERROR": LED_OFF}
        
        # 1. Power On
        st.session_state.leds["POWER"] = LED_GREEN
        box_placeholder.markdown(render_box("BOOTING...", "HARDWARE INIT", st.session_state.leds), unsafe_allow_html=True)
        time.sleep(0.4)

        # 2. Network Connection
        st.session_state.leds["NETWORK"] = LED_GREEN
        box_placeholder.markdown(render_box("NETWORKING...", "DHCP / LINK UP", st.session_state.leds), unsafe_allow_html=True)
        time.sleep(0.4)

        # 3. OPC UA Discovery & Metadata Read (Multi-Machine)
        box_placeholder.markdown(render_box("DISCOVERING...", f"SCANNING :{OPC_UA_PORT}", st.session_state.leds), unsafe_allow_html=True)
        time.sleep(0.6)

        identities = inspect_machines(OPC_UA_HOST, OPC_UA_PORT, max_machines=MAX_LICENSED_MACHINES)
        st.session_state.identities = identities

        if identities:
            primary_name = str(identities[0].name)[:18].upper()
            count_str = f"FOUND: {len(identities)} MACHINES"
            box_placeholder.markdown(render_box(count_str, primary_name, st.session_state.leds), unsafe_allow_html=True)
        else:
            box_placeholder.markdown(render_box("DISCOVERY WARN", "NO OPC-UA SERVER", st.session_state.leds), unsafe_allow_html=True)
        time.sleep(0.8)

        # 4. Smart Gateway Communication
        try:
            box_placeholder.markdown(render_box("HANDSHAKE...", "VERIFYING TOKEN", st.session_state.leds), unsafe_allow_html=True)
            response = requests.post(
                GATEWAY_URL + "/v1/connector-boxes/handshake",
                json={"hardware_id": hardware_id},
                timeout=25,
            )

            if response.status_code in (404, 403):
                box_placeholder.markdown(render_box("PAIRING...", "INITIAL REGISTRATION", st.session_state.leds), unsafe_allow_html=True)
                response = requests.post(
                    GATEWAY_URL + "/v1/connector-boxes/pair",
                    json={"hardware_id": hardware_id},
                    timeout=25,
                )
                action_msg = "Box erfolgreich gepaired & online!"
            else:
                action_msg = "Handshake erfolgreich durchgeführt!"

        except requests.RequestException as exc:
            st.session_state.leds["ERROR"] = LED_RED
            box_placeholder.markdown(render_box("GATEWAY UNREACHABLE", str(exc)[:32], st.session_state.leds), unsafe_allow_html=True)
            st.error("Could not reach gateway-api: " + str(exc))
            st.session_state.is_online = False
            return

        if response.status_code == 200:
            # 5. Autoscan / Maschinen an Gateway zur Persistenz übergeben
            try:
                scan_response = requests.post(
                    GATEWAY_URL + "/v1/connector-boxes/autoscan",
                    json={
                        "hardware_id": hardware_id,
                        "machines": [m.to_dict() for m in identities],
                    },
                    timeout=25,
                )
                if scan_response.status_code == 200:
                    st.toast("Erkannte Maschinen erfolgreich mit Box-Kontext persistiert!", icon="💾")
                else:
                    st.warning("Maschinen-Persistenz ergab Status: " + str(scan_response.status_code))
            except requests.RequestException as exc:
                st.warning(f"Konnte Maschinen-Autoscan nicht senden: {exc}")

            st.session_state.box_data = response.json()
            st.session_state.leds["URETOS"] = LED_GREEN
            st.session_state.is_online = True
        else:
            st.session_state.leds["ERROR"] = LED_RED
            try:
                reason = response.json().get("error", "Unknown error")
            except ValueError:
                reason = f"HTTP {response.status_code}"
            box_placeholder.markdown(render_box("FAILED", reason[:28], st.session_state.leds), unsafe_allow_html=True)
            st.error(reason)
            st.session_state.is_online = False

    # UI-Darstellung basierend auf dem Session State (bleibt bei Widget-Interaktionen stabil)
    if st.session_state.is_online:
        box_placeholder.markdown(render_box(hardware_id[:20], "ONLINE & STREAMING", st.session_state.leds), unsafe_allow_html=True)
        st.success(f"Box online! Erkannte Maschinen: **{len(st.session_state.identities)}**")

        with st.expander(f"Discovery details ({len(st.session_state.identities)} Maschinen)", expanded=False):
            for idx, m in enumerate(st.session_state.identities):
                st.markdown(f"**Maschine {idx + 1}: {m.name}**")
                st.json(m.to_dict())

        # --- Live Status Control Panel ---
        st.divider()
        st.subheader("🛠️ Live Status Control Panel")

        identities = st.session_state.identities
        if identities:
            machine_options = { (m.name or f"Machine-{i}"): m for i, m in enumerate(identities) }
            selected_machine_name = st.selectbox("Maschine auswählen", options=list(machine_options.keys()))
            selected_machine = machine_options[selected_machine_name]

            status_options = {"OK (Grün)": "ok", "WARNING (Gelb)": "warning", "ERROR (Rot)": "error"}
            selected_status_label = st.selectbox("Neuer Status", options=list(status_options.keys()))
            new_status = status_options[selected_status_label]

            error_code = st.text_input("Fehlercode (optional)", value="" if new_status == "ok" else "E-500: Beispiel-Fehler")

            if st.button("Status an Gateway senden"):
                machine_id_to_send = selected_machine.name or "BasicMachineTool"
                tenant_id = st.session_state.box_data.get("tenant_id", "test-tenant-e2e")

                try:
                    status_resp = requests.patch(
                        f"{GATEWAY_URL}/v1/machines/{machine_id_to_send}/status",
                        json={
                            "tenant_id": tenant_id,
                            "status": new_status,
                            "error_code": error_code if new_status != "ok" else None
                        },
                        timeout=10
                    )
                    if status_resp.status_code == 200:
                        st.toast(f"Status für {machine_id_to_send} erfolgreich auf '{new_status}' aktualisiert!", icon="⚡")
                    else:
                        st.warning(f"Fehler beim Update: {status_resp.status_code} - {status_resp.text}")
                except requests.RequestException as exc:
                    st.error(f"Konnte Gateway nicht erreichen: {exc}")
    else:
        box_placeholder.markdown(render_box("URETOS CONNECTOR", "READY", st.session_state.leds), unsafe_allow_html=True)


if __name__ == "__main__":
    main()
```

## File: tools/shopfloor-stream-poc/index.html
```html
<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<title>uretOS Shopfloor Stream POC</title>
<style>
  body {
    background: #050608;
    color: #e6f9ff;
    font-family: "Courier New", monospace;
    padding: 24px;
  }
  h1 { font-size: 16px; letter-spacing: 2px; color: #aaa; }
  #controls { margin-bottom: 20px; }
  input, button {
    font-family: inherit;
    background: #0a0e12;
    color: #e6f9ff;
    border: 1px solid #00e5ff;
    padding: 6px 10px;
  }
  button { cursor: pointer; }
  #status { margin-left: 12px; color: #6b8a94; font-size: 12px; }
  .grid {
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
    margin-top: 20px;
  }
  .card {
    border: 1px solid #00e5ff;
    background: rgba(10,14,18,0.8);
    box-shadow: 0 0 12px 0 rgba(0,229,255,0.2);
    padding: 14px 18px;
    min-width: 300px;
    max-width: 400px;
  }
  .card .name { color: #00e5ff; font-size: 14px; margin-bottom: 6px; }
  .card .field { font-size: 12px; color: #9fd; margin-bottom: 2px; }
  
  /* Status-Styling */
  .status-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 8px;
    padding-top: 6px;
    border-top: 1px dashed #1a2634;
  }
  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    display: inline-block;
  }
  .status-dot.ok { background: #3fb950; box-shadow: 0 0 6px rgba(63, 185, 80, 0.6); }
  .status-dot.warning { background: #d29922; box-shadow: 0 0 6px rgba(210, 153, 34, 0.6); }
  .status-dot.error { background: #f85149; box-shadow: 0 0 6px rgba(248, 81, 73, 0.6); }

  .status-text.ok { color: #3fb950; }
  .status-text.warning { color: #d29922; }
  .status-text.error { color: #f85149; }

  /* Timeline / Tilesbar Chart Styling */
  .timeline-container {
    margin-top: 12px;
    border-top: 1px solid #1a2634;
    padding-top: 8px;
  }
  .timeline-label {
    font-size: 10px;
    color: #6b8a94;
    margin-bottom: 4px;
    display: flex;
    justify-content: space-between;
  }
  .timeline-tilesbar {
    display: flex;
    gap: 3px;
    height: 16px;
    width: 100%;
    background: #050608;
    padding: 2px;
    border: 1px solid #1a2634;
    border-radius: 2px;
    box-sizing: border-box;
  }
  .tile {
    flex: 1;
    height: 100%;
    border-radius: 1px;
    cursor: pointer;
    transition: opacity 0.2s;
  }
  .tile:hover { opacity: 0.7; }
  .tile.ok { background: #3fb950; }
  .tile.warning { background: #d29922; }
  .tile.error { background: #f85149; }
  .tile.unknown { background: #333; }

  .error-code {
    font-size: 11px;
    color: #f85149;
    margin-top: 4px;
    background: rgba(248, 81, 73, 0.1);
    padding: 2px 4px;
    border-radius: 2px;
  }

  .card.flash { animation: flash 1s ease; }
  @keyframes flash {
    0% { box-shadow: 0 0 24px 4px #00e5ff; }
    100% { box-shadow: 0 0 12px 0 rgba(0,229,255,0.2); }
  }
  #log {
    margin-top: 24px;
    font-size: 11px;
    color: #556;
    max-height: 200px;
    overflow-y: auto;
    border-top: 1px solid #222;
    padding-top: 10px;
  }
</style>
</head>
<body>

<h1>uretOS · SHOPFLOOR STREAM POC</h1>

<div id="controls">
  <input id="tenantInput" value="test-tenant-e2e" />
  <button onclick="connect()">Connect</button>
  <span id="status">disconnected</span>
</div>

<div class="grid" id="machineGrid"></div>

<div id="log"></div>

<script>
const STREAM_URL = "http://localhost:8081/v1/shopfloor/stream";
const HISTORY_URL = "http://localhost:8888/api/v1/machines"; // Über Traefik / BFF
let machines = {};
let eventSource = null;

function log(msg) {
  const el = document.getElementById("log");
  const line = document.createElement("div");
  line.textContent = new Date().toLocaleTimeString() + "  " + msg;
  el.prepend(line);
}

async function fetchMachineHistory(tenantId, machineId, cardElement) {
  try {
    const response = await fetch(`${HISTORY_URL}/${machineId}/history?limit=15`, {
      headers: { "X-Tenant-ID": tenantId }
    });
    if (!response.ok) return;
    const data = await response.json();
    
    const historyContainer = cardElement.querySelector('.timeline-tilesbar');
    if (!historyContainer) return;
    historyContainer.innerHTML = "";

    const historyItems = data.history || [];
    if (historyItems.length === 0) {
      historyContainer.innerHTML = '<div style="font-size:9px; color:#556; text-align:center; width:100%;">Keine Historie</div>';
      return;
    }

    // Älteste bis neueste sortieren für den Zeitstrahl von links nach rechts
    historyItems.reverse().forEach(item => {
      const tile = document.createElement("div");
      const statusClass = (item.status || 'unknown').toLowerCase();
      tile.className = `tile ${statusClass}`;
      
      const timeStr = new Date(item.time).toLocaleTimeString();
      const errStr = item.error_code ? ` (${item.error_code})` : '';
      tile.title = `${timeStr} - Status: ${item.status.toUpperCase()}${errStr}`;
      
      historyContainer.appendChild(tile);
    });
  } catch (err) {
    console.error("Fehler beim Laden der Historie für", machineId, err);
  }
}

function renderGrid() {
  const grid = document.getElementById("machineGrid");
  const tenantId = document.getElementById("tenantInput").value.trim();
  
  grid.innerHTML = "";
  Object.values(machines).forEach(m => {
    const status = (m.status || 'ok').toLowerCase();
    const card = document.createElement("div");
    card.className = "card" + (m._flash ? " flash" : "");
    card.id = `card-${m.machine_id}`;
    
    let errorHtml = '';
    if (m.error_code) {
      errorHtml = `<div class="error-code">⚠️ ${m.error_code}</div>`;
    }

    card.innerHTML = `
      <div class="name">${m.name || m.machine_id}</div>
      <div class="field">ID: ${m.machine_id}</div>
      <div class="field">Box: ${m.box_id || "-"}</div>
      <div class="status-row">
        <span class="status-dot ${status}"></span>
        <span class="field status-text ${status}">STATUS: ${status.toUpperCase()}</span>
      </div>
      ${errorHtml}
      <div class="timeline-container">
        <div class="timeline-label">
          <span>Status-Historie (letzte Einträge)</span>
          <span>live &rarr;</span>
        </div>
        <div class="timeline-tilesbar">
          <div style="font-size:9px; color:#556; text-align:center; width:100%;">Lade...</div>
        </div>
      </div>
    `;
    grid.appendChild(card);
    m._flash = false;

    // Historie asynchron per BFF-API laden
    fetchMachineHistory(tenantId, m.machine_id, card);
  });
}

function connect() {
  if (eventSource) {
    eventSource.close();
  }
  const tenantId = document.getElementById("tenantInput").value.trim();
  if (!tenantId) return;

  machines = {};
  renderGrid();
  document.getElementById("status").textContent = "connecting...";

  eventSource = new EventSource(`${STREAM_URL}?tenant_id=${encodeURIComponent(tenantId)}`);

  eventSource.onopen = () => {
    document.getElementById("status").textContent = "connected";
    log("SSE connected for tenant " + tenantId);
  };

  eventSource.onerror = () => {
    document.getElementById("status").textContent = "error/reconnecting";
  };

  eventSource.onmessage = (event) => {
    const envelope = JSON.parse(event.data);

    if (envelope.type === "uretos.shopfloor.snapshot") {
      (envelope.data.machines || []).forEach(m => { machines[m.machine_id] = m; });
      renderGrid();
    }

    if (envelope.type === "uretos.machine.event.registered") {
      (envelope.data.machines || []).forEach(m => {
        machines[m.machine_id] = { ...machines[m.machine_id], ...m, _flash: true };
      });
      renderGrid();
    }

    if (envelope.type === "uretos.machine.event.status_changed") {
      const update = envelope.data;
      if (machines[update.machine_id]) {
        machines[update.machine_id].status = update.status;
        machines[update.machine_id].error_code = update.error_code || null;
        machines[update.machine_id]._flash = true;
        renderGrid();
        log(`Status update for ${update.machine_id}: ${update.status}`);
      }
    }
  };
}
</script>

</body>
</html>
```

## File: .gitignore
```
# --- Python ---
__pycache__/
*.py[cod]
*.egg-info/
.venv/
venv/
env/

# --- Docker / build artifacts ---
*.zip
*.tar
*.tar.gz

# --- Env / secrets ---
.env
*.local.env

# --- OS / editor ---
.DS_Store
.vscode/
.idea/

# --- Logs ---
*.log.DS_Store
**/.DS_Store
docker_compose_infografik.html
ChatGPT Image*.png
docker_compose_infografik.html
ChatGPT Image*.png

# AI / agent folders
.agents/
.claude/
```

## File: services/gateway-api/app/main.py
```python
"""
gateway-api

First REST-facing entry point into uretOS. External clients (physical
connector boxes, the admin panel, later possibly other clients) call this
HTTP API instead of ever touching RabbitMQ directly - this service is the
only thing that translates REST calls into internal CloudEvent commands
and queries.

Endpoints:
  POST /v1/tenants
  GET  /v1/tenants
  POST /v1/connector-boxes
  GET  /v1/connector-boxes
  POST /v1/connector-boxes/pair
  POST /v1/connector-boxes/handshake
  POST /v1/connector-boxes/autoscan
  GET  /v1/connector-boxes/<hardware_id>/machines
  GET  /v1/machines?tenant_id=<tenant_id>
  GET  /healthz

Machines live in the per-tenant database, so machine queries always carry a
tenant_id: for a box it is resolved from the box itself, for the tenant-wide
list it is a required query parameter (until authentication provides it).
"""
from __future__ import annotations

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone

import pika
from flask import Flask, jsonify, request

from cloudevents import build_envelope

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("gateway-api")

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://uretos:uretos_dev_pass@rabbitmq:5672/")
EXCHANGE = "uretos.events"
SOURCE = "uretos/services/gateway-api"
TIMEOUT_SECONDS = int(os.environ.get("GATEWAY_RPC_TIMEOUT_SECONDS", "20"))

app = Flask(__name__)


def publish_command_and_wait(command_type: str, data: dict, success_type: str, failure_type: str):
    """
    Fire a command, listen on a temporary exclusive queue bound to the two
    possible outcome routing keys. Not true RabbitMQ RPC (no reply-to) -
    used for commands, which have distinct success/failure event types.
    """
    correlation_id = str(uuid.uuid4())
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()
    channel.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)

    result = channel.queue_declare(queue="", exclusive=True)
    listen_queue = result.method.queue
    for routing_key in (success_type, failure_type):
        channel.queue_bind(queue=listen_queue, exchange=EXCHANGE, routing_key=routing_key)

    envelope_out = build_envelope(
        event_type=command_type,
        source=SOURCE,
        data=data,
        tenant_id="system",
        messagetype="command",
        correlation_id=correlation_id,
    )
    channel.basic_publish(
        exchange=EXCHANGE,
        routing_key=command_type,
        body=json.dumps(envelope_out).encode("utf-8"),
        properties=pika.BasicProperties(content_type="application/json"),
    )

    deadline = time.monotonic() + TIMEOUT_SECONDS
    envelope_in = None
    while time.monotonic() < deadline:
        method, properties, body = channel.basic_get(queue=listen_queue, auto_ack=True)
        if body is None:
            time.sleep(0.2)
            continue
        candidate = json.loads(body)
        if candidate.get("correlationid") == correlation_id:
            envelope_in = candidate
            break

    connection.close()
    return envelope_in


def query_rpc(query_type: str, data: dict):
    """
    True RabbitMQ RPC via Direct-Reply-To, for query-services that only
    ever answer with a single '<query_type>.result' event type - no
    separate failure routing key exists for reads.
    """
    correlation_id = str(uuid.uuid4())
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()
    channel.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)

    envelope_out = build_envelope(
        event_type=query_type,
        source=SOURCE,
        data=data,
        tenant_id="system",
        messagetype="query",
        correlation_id=correlation_id,
    )

    result_holder = {}

    def on_response(ch, method, properties, body):
        if properties.correlation_id == correlation_id:
            result_holder["envelope"] = json.loads(body)
            ch.stop_consuming()

    channel.basic_consume(queue="amq.rabbitmq.reply-to", on_message_callback=on_response, auto_ack=True)
    channel.basic_publish(
        exchange=EXCHANGE,
        routing_key=query_type,
        properties=pika.BasicProperties(
            reply_to="amq.rabbitmq.reply-to",
            correlation_id=correlation_id,
            content_type="application/json",
        ),
        body=json.dumps(envelope_out).encode("utf-8"),
    )

    connection.process_data_events(time_limit=TIMEOUT_SECONDS)
    connection.close()

    return result_holder.get("envelope")


def machine_query_error_response(data: dict):
    """Maps the error_code of a machine query result to an HTTP response."""
    status = {
        "tenant_required": 400,
        "box_id_required": 400,
        "tenant_not_found": 404,
    }.get(data.get("error_code"), 500)
    return jsonify({"error": data.get("error", "Machine query failed")}), status


def public_tenant_view(provisioned_data: dict) -> dict:
    """
    What an external client may learn about a freshly provisioned tenant.

    The provisioned event also carries infrastructure credentials (Postgres and
    RabbitMQ passwords). Those are meant for tenant-command-service only (tenant
    registry in system-postgres) and must never leave the platform. Whitelist
    instead of blacklist: new fields in the event stay private by default.
    """
    return {"tenant_id": provisioned_data.get("tenant_id"), "status": "provisioned"}


@app.route("/v1/connector-boxes/pair", methods=["POST"])
def pair_connector_box():
    payload = request.get_json(silent=True) or {}
    hardware_id = payload.get("hardware_id")

    if not hardware_id:
        return jsonify({"error": "hardware_id is required"}), 400

    log.info("Pairing request for hardware_id=%s", hardware_id)
    envelope = publish_command_and_wait(
        "uretos.connectorbox.command.pair",
        {"hardware_id": hardware_id},
        "uretos.connectorbox.event.paired",
        "uretos.connectorbox.event.pairing_failed",
    )

    if envelope is None:
        return jsonify({"error": "Timed out waiting for pairing result"}), 504

    if envelope["type"] == "uretos.connectorbox.event.paired":
        return jsonify(envelope["data"]), 200

    # NOTE: kept simple for now - all failure reasons map to 400.
    # Distinguishing "unknown hardware_id" (404) from "already paired" (409)
    # by parsing the reason string would be more correct but more brittle;
    # revisit once the gateway has more than one consumer of this response.
    return jsonify({"error": envelope["data"].get("reason", "Pairing failed")}), 400


@app.route("/v1/machines", methods=["GET"])
def list_all_machines():
    # Machines live in the per-tenant database -> a tenant is always required.
    # Until authentication provides it, it is passed as a query parameter.
    tenant_id = request.args.get("tenant_id")
    if not tenant_id:
        return jsonify({"error": "tenant_id query parameter is required"}), 400

    envelope = query_rpc("uretos.machine.query.list", {"tenant_id": tenant_id})
    if envelope is None:
        return jsonify({"error": "Timed out waiting for query result"}), 504

    data = envelope.get("data", {})
    if data.get("error_code"):
        return machine_query_error_response(data)
    return jsonify(data.get("machines", [])), 200


@app.route("/v1/connector-boxes/<hardware_id>/machines", methods=["GET"])
def list_machines_by_hardware_id(hardware_id: str):
    # The box (system-postgres) is the authoritative source for box_id AND tenant_id.
    box_env = query_rpc("uretos.connectorbox.query.by_hardware_id", {"hardware_id": hardware_id})
    if box_env is None:
        return jsonify({"error": "Timed out waiting for query result"}), 504

    box = box_env.get("data", {}).get("connector_box")
    if not box:
        return jsonify({"error": "Connector box not found"}), 404

    envelope = query_rpc(
        "uretos.machine.query.by_box",
        {"box_id": box["box_id"], "tenant_id": box["tenant_id"]},
    )
    if envelope is None:
        return jsonify({"error": "Timed out waiting for query result"}), 504

    data = envelope.get("data", {})
    if data.get("error_code"):
        return machine_query_error_response(data)
    return jsonify(data.get("machines", [])), 200


@app.route("/v1/connector-boxes/autoscan", methods=["POST"])
def register_autoscan_machines():
    payload = request.get_json(silent=True) or {}
    hardware_id = payload.get("hardware_id")
    machines = payload.get("machines", [])

    if not hardware_id:
        return jsonify({"error": "hardware_id is required"}), 400

    # Pairing-Status selbst prüfen statt sich auf Handshake-vor-Autoscan beim Aufrufer zu verlassen
    box_env = query_rpc("uretos.connectorbox.query.by_hardware_id", {"hardware_id": hardware_id})
    if box_env is None:
        return jsonify({"error": "Timed out waiting for query result"}), 504

    box = box_env.get("data", {}).get("connector_box")
    if not box:
        return jsonify({"error": "Connector box not found"}), 404

    if box.get("status") != "paired":
        return jsonify({"error": "Box is not paired yet", "status": box.get("status")}), 403

    log.info("Autoscan registration request for hardware_id=%s, machines_count=%d", hardware_id, len(machines))

    envelope = publish_command_and_wait(
        "uretos.machine.command.register",
        {"hardware_id": hardware_id, "machines": machines},
        "uretos.machine.event.registered",
        "uretos.machine.event.registration_failed",
    )

    if envelope is None:
        return jsonify({"error": "Timed out waiting for machine registration result"}), 504

    if envelope["type"] == "uretos.machine.event.registered":
        return jsonify(envelope["data"]), 200

    return jsonify({"error": envelope["data"].get("reason", "Machine registration failed")}), 400
@app.route("/v1/connector-boxes/handshake", methods=["POST"])
def connector_box_handshake():
    data = request.get_json(silent=True) or {}
    hardware_id = data.get("hardware_id")

    if not hardware_id:
        return jsonify({"error": "hardware_id is required"}), 400

    # Gezielter RPC-Query an den Query-Service statt Listen-Abfrage
    envelope = query_rpc("uretos.connectorbox.query.by_hardware_id", {"hardware_id": hardware_id})
    if envelope is None:
        return jsonify({"error": "Timed out waiting for query result"}), 504

    box = envelope.get("data", {}).get("connector_box")

    if not box:
        return jsonify({"error": "Box not found, initial pairing required", "status": "pending_pairing"}), 404

    if box.get("status") != "paired":
        return jsonify({"error": "Box is not paired yet", "status": box.get("status")}), 403

    log.info("Handshake successful for box: %s", hardware_id)
    return jsonify({
        "status": "ok",
        "box_id": box.get("box_id"),
        "tenant_id": box.get("tenant_id"),
        "message": "Handshake accepted. Proceed with autoscan."
    }), 200


@app.route("/v1/connector-boxes", methods=["POST"])
def create_connector_box():
    payload = request.get_json(silent=True) or {}
    tenant_id = payload.get("tenant_id")
    hardware_id = payload.get("hardware_id")
    mac_address = payload.get("mac_address")

    if not tenant_id or not hardware_id or not mac_address:
        return jsonify({"error": "tenant_id, hardware_id, and mac_address are required"}), 400

    log.info("Connector box creation request for tenant_id=%s, hardware_id=%s", tenant_id, hardware_id)
    envelope = publish_command_and_wait(
        "uretos.connectorbox.command.create",
        {"tenant_id": tenant_id, "hardware_id": hardware_id, "mac_address": mac_address},
        "uretos.connectorbox.event.created",
        "uretos.connectorbox.event.creation_failed",
    )

    if envelope is None:
        return jsonify({"error": "Timed out waiting for creation result"}), 504

    if envelope["type"] == "uretos.connectorbox.event.created":
        return jsonify(envelope["data"]), 201

    return jsonify({"error": envelope["data"].get("reason", "Creation failed")}), 400


@app.route("/v1/connector-boxes", methods=["GET"])
def list_connector_boxes():
    envelope = query_rpc("uretos.connectorbox.query.list", {})
    if envelope is None:
        return jsonify({"error": "Timed out waiting for query result"}), 504
    return jsonify(envelope["data"]["connector_boxes"]), 200


@app.route("/v1/tenants", methods=["POST"])
def create_tenant():
    payload = request.get_json(silent=True) or {}
    tenant_id = payload.get("tenant_id")

    if not tenant_id:
        return jsonify({"error": "tenant_id is required"}), 400

    log.info("Tenant creation request for tenant_id=%s", tenant_id)
    envelope = publish_command_and_wait(
        "uretos.tenant.command.create",
        {"tenant_id": tenant_id},
        "uretos.tenant.event.provisioned",
        "uretos.tenant.event.provisioning_failed",
    )

    if envelope is None:
        return jsonify({"error": "Timed out waiting for provisioning result"}), 504

    if envelope["type"] == "uretos.tenant.event.provisioned":
        return jsonify(public_tenant_view(envelope["data"])), 201

    return jsonify({"error": envelope["data"].get("reason", "Provisioning failed")}), 400


@app.route("/v1/tenants", methods=["GET"])
def list_tenants():
    envelope = query_rpc("uretos.tenant.query.list", {})
    if envelope is None:
        return jsonify({"error": "Timed out waiting for query result"}), 504
    return jsonify(envelope["data"]["tenants"]), 200

@app.route("/v1/machines/<machine_id>/status", methods=["PATCH"])
def update_machine_status(machine_id: str):
    payload = request.get_json(silent=True) or {}
    status = payload.get("status")  # "ok", "warning", "error"
    error_code = payload.get("error_code")
    tenant_id = payload.get("tenant_id")

    if not status or not tenant_id:
        return jsonify({"error": "status and tenant_id are required"}), 400

    if status not in ("ok", "warning", "error"):
        return jsonify({"error": "Invalid status value. Must be 'ok', 'warning', or 'error'"}), 400

    log.info("Status update request for machine_id=%s, status=%s", machine_id, status)

    # CloudEvent für den Statuswechsel erzeugen und über RabbitMQ publizieren
    envelope_out = build_envelope(
        event_type="uretos.machine.event.status_changed",
        source=SOURCE,
        data={
            "machine_id": machine_id,
            "tenant_id": tenant_id,
            "status": status,
            "error_code": error_code,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        tenant_id=tenant_id,
        messagetype="event",
    )

    try:
        connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
        channel = connection.channel()
        channel.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)
        channel.basic_publish(
            exchange=EXCHANGE,
            routing_key="uretos.machine.event.status_changed",
            body=json.dumps(envelope_out).encode("utf-8"),
            properties=pika.BasicProperties(content_type="application/json"),
        )
        connection.close()
    except Exception as exc:
        log.error("Failed to publish machine status event: %s", exc)
        return jsonify({"error": "Internal broker error"}), 500

    return jsonify({"success": True, "machine_id": machine_id, "status": status}), 200
    
@app.route("/healthz", methods=["GET"])
def healthz():
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
```

## File: tools/admin-panel/app.py
```python
"""
uretOS super_admin panel - throwaway internal tool.

Calls gateway-api's REST endpoints exclusively - no direct RabbitMQ access.
This makes the admin panel an ordinary external client, same as the
connector-box simulator, rather than a special case.

Run with:
    streamlit run app.py
"""
import os

import requests
import streamlit as st

GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://localhost:8080")
SUPER_ADMIN_USER = os.environ.get("SUPER_ADMIN_USER", "admin")
SUPER_ADMIN_PASSWORD = os.environ.get("SUPER_ADMIN_PASSWORD", "changeme")
TIMEOUT_SECONDS = 30


def login_screen():
    st.title("uretOS super_admin")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username == SUPER_ADMIN_USER and password == SUPER_ADMIN_PASSWORD:
            st.session_state["logged_in"] = True
            st.rerun()
        else:
            st.error("Invalid credentials")


def refresh_tenants():
    try:
        response = requests.get(GATEWAY_URL + "/v1/tenants", timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        st.session_state["tenants_cache"] = response.json()
    except requests.RequestException as exc:
        st.error("Could not reach gateway-api: " + str(exc))
        st.session_state["tenants_cache"] = []


def render_tenant_tab():
    st.subheader("Create tenant")
    tenant_id = st.text_input("Tenant ID (lowercase, alphanumeric, hyphens)", help="Beispiel: acme-gmbh")
    if st.button("Provision tenant") and tenant_id:
        with st.spinner("Provisioning " + tenant_id + " ..."):
            try:
                response = requests.post(
                    GATEWAY_URL + "/v1/tenants",
                    json={"tenant_id": tenant_id},
                    timeout=TIMEOUT_SECONDS,
                )
            except requests.RequestException as exc:
                st.error("Could not reach gateway-api: " + str(exc))
                return

        if response.status_code == 201:
            st.success("Tenant " + tenant_id + " provisioned")
            st.json(response.json())
            refresh_tenants()
        else:
            st.error("Provisioning failed: " + str(response.json().get("error")))

    st.divider()
    st.subheader("Existing tenants")
    if st.button("Refresh tenant list") or "tenants_cache" not in st.session_state:
        refresh_tenants()

    if st.session_state.get("tenants_cache"):
        st.table(st.session_state["tenants_cache"])
    else:
        st.caption("No tenants yet.")


def refresh_connector_boxes():
    try:
        response = requests.get(GATEWAY_URL + "/v1/connector-boxes", timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        st.session_state["boxes_cache"] = response.json()
    except requests.RequestException as exc:
        st.error("Could not reach gateway-api: " + str(exc))
        st.session_state["boxes_cache"] = []


def _generate_hardware_id():
    import random
    import string
    from datetime import datetime, timezone

    tenant_id = st.session_state.get("connector_box_tenant_select", "tenant")
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
    st.session_state["hardware_id_input"] = tenant_id + "-" + date_part + "-" + suffix


def render_connector_box_tab():
    st.subheader("Create connector box")

    if "tenants_cache" not in st.session_state:
        refresh_tenants()
    tenant_ids = [t["tenant_id"] for t in st.session_state.get("tenants_cache", [])]

    if not tenant_ids:
        st.caption("No tenants available yet - create a tenant in the Tenants tab first.")
    else:
        tenant_id = st.selectbox("Tenant", tenant_ids, key="connector_box_tenant_select")

        col1, col2 = st.columns([3, 1])
        with col1:
            hardware_id = st.text_input(
                "Hardware ID", help="Beispiel: HW-2026-000123", key="hardware_id_input"
            )
        with col2:
            st.write("")
            st.write("")
            st.button("Auto-generate", on_click=_generate_hardware_id)

        mac_address = st.text_input("MAC address", help="Beispiel: AA:BB:CC:DD:EE:FF")

        if st.button("Create connector box") and hardware_id and mac_address:
            with st.spinner("Creating connector box ..."):
                try:
                    response = requests.post(
                        GATEWAY_URL + "/v1/connector-boxes",
                        json={"tenant_id": tenant_id, "hardware_id": hardware_id, "mac_address": mac_address},
                        timeout=TIMEOUT_SECONDS,
                    )
                except requests.RequestException as exc:
                    st.error("Could not reach gateway-api: " + str(exc))
                    response = None

            if response is not None:
                if response.status_code == 201:
                    st.success("Connector box created for tenant " + tenant_id)
                    st.json(response.json())
                    st.caption("Pairing token is only shown once here - it is not returned by list queries.")
                    refresh_connector_boxes()
                else:
                    st.error("Creation failed: " + str(response.json().get("error")))

    st.divider()
    st.subheader("Existing connector boxes")
    if st.button("Refresh connector box list") or "boxes_cache" not in st.session_state:
        refresh_connector_boxes()

    if st.session_state.get("boxes_cache"):
        st.table(st.session_state["boxes_cache"])
    else:
        st.caption("No connector boxes yet.")


def admin_screen():
    st.title("uretOS - Admin Panel")
    st.caption("super_admin panel - throwaway internal tool")

    if st.button("Logout"):
        st.session_state["logged_in"] = False
        st.rerun()

    st.divider()
    tab_tenants, tab_boxes = st.tabs(["Tenants", "Connector Boxes"])
    with tab_tenants:
        render_tenant_tab()
    with tab_boxes:
        render_connector_box_tab()


def main():
    if not st.session_state.get("logged_in"):
        login_screen()
    else:
        admin_screen()


if __name__ == "__main__":
    main()
```

## File: docker-compose.yml
```yaml
include:
  - shopfloor.yaml

services:
  rabbitmq:
    image: rabbitmq:3.13-management-alpine
    container_name: uretos-rabbitmq
    ports:
      - "5672:5672"
      - "15672:15672"   # management UI, dev only
    volumes:
      - ./infra/rabbitmq/definitions.json:/etc/rabbitmq/definitions.json:ro
      - ./infra/rabbitmq/rabbitmq.conf:/etc/rabbitmq/conf.d/10-defaults.conf:ro
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "-q", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - default
      - tenant-net

  docker-socket-proxy:
    image: tecnativa/docker-socket-proxy:latest
    container_name: uretos-docker-proxy
    privileged: true
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
    environment:
      CONTAINERS: 1
      POST: 1
      IMAGES: 1
      EXEC: 1
      NETWORKS: 1
      VOLUMES: 1
    restart: unless-stopped
    networks:
      - default

  system-postgres:
    image: postgres:16-alpine
    container_name: uretos-system-postgres
    ports:
    - "5432:5432"
    environment:
      POSTGRES_USER: uretos_system
      POSTGRES_PASSWORD: uretos_system_dev_pass
      POSTGRES_DB: uretos_system
    volumes:
      - system-postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U uretos_system"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - default
      - tenant-net

  tenant-provisioning-service:
    build: ./services/tenant-provisioning-service
    container_name: uretos-tenant-provisioning-service
    depends_on:
      rabbitmq:
        condition: service_healthy
      docker-socket-proxy:
        condition: service_started
      system-postgres:
        condition: service_healthy
    environment:
      RABBITMQ_URL: "amqp://uretos_system:uretos_system_dev_pass@rabbitmq:5672/"
      RABBITMQ_MGMT_URL: "http://rabbitmq:15672"
      RABBITMQ_ADMIN_USER: "uretos"
      RABBITMQ_ADMIN_PASSWORD: "uretos_dev_pass"
    restart: unless-stopped
    networks:
      - default

  tenant-command-service:
    build: ./services/tenant-command-service
    container_name: uretos-tenant-command-service
    depends_on:
      rabbitmq:
        condition: service_healthy
      system-postgres:
        condition: service_healthy
    environment:
      RABBITMQ_URL: "amqp://uretos_system:uretos_system_dev_pass@rabbitmq:5672/"
      SYSTEM_DB_URL: "postgresql+psycopg://uretos_system:uretos_system_dev_pass@system-postgres:5432/uretos_system"
    restart: unless-stopped
    networks:
      - default

  tenant-query-service:
    build: ./services/tenant-query-service
    container_name: uretos-tenant-query-service
    depends_on:
      rabbitmq:
        condition: service_healthy
      system-postgres:
        condition: service_healthy
    environment:
      RABBITMQ_URL: "amqp://uretos_system:uretos_system_dev_pass@rabbitmq:5672/"
      SYSTEM_DB_URL: "postgresql+psycopg://uretos_system:uretos_system_dev_pass@system-postgres:5432/uretos_system"
    restart: unless-stopped
    networks:
      - default

  connector-box-command-service:
    build: ./services/connector-box-command-service
    container_name: uretos-connector-box-command-service
    depends_on:
      rabbitmq:
        condition: service_healthy
      system-postgres:
        condition: service_healthy
    environment:
      RABBITMQ_URL: "amqp://uretos_system:uretos_system_dev_pass@rabbitmq:5672/"
      SYSTEM_DB_URL: "postgresql://uretos_system:uretos_system_dev_pass@system-postgres:5432/uretos_system"
      CONNECTOR_BOX_JWT_SECRET: "uretos_dev_jwt_secret_change_me"
    restart: unless-stopped
    networks:
      - default

  connector-box-query-service:
    build: ./services/connector-box-query-service
    container_name: uretos-connector-box-query-service
    depends_on:
      rabbitmq:
        condition: service_healthy
      system-postgres:
        condition: service_healthy
    environment:
      RABBITMQ_URL: "amqp://uretos_system:uretos_system_dev_pass@rabbitmq:5672/"
      SYSTEM_DB_URL: "postgresql://uretos_system:uretos_system_dev_pass@system-postgres:5432/uretos_system"
    restart: unless-stopped
    networks:
      - default

  gateway-api:
    build: ./services/gateway-api
    container_name: uretos-gateway-api
    ports:
      - "8080:8080"
    depends_on:
      rabbitmq:
        condition: service_healthy
    environment:
      RABBITMQ_URL: "amqp://uretos_system:uretos_system_dev_pass@rabbitmq:5672/"
    restart: unless-stopped
    networks:
      - default
      - tenant-net

  machine-command-service:
    build: ./services/machine-command-service
    container_name: uretos-machine-command-service
    depends_on:
      rabbitmq:
        condition: service_healthy
      system-postgres:
        condition: service_healthy
    environment:
      RABBITMQ_URL: "amqp://uretos_system:uretos_system_dev_pass@rabbitmq:5672/"
      SYSTEM_DB_URL: "postgresql+psycopg://uretos_system:uretos_system_dev_pass@system-postgres:5432/uretos_system"
    networks:
      - default
      - tenant-net
    restart: unless-stopped

  machine-query-service:
    build: ./services/machine-query-service
    container_name: uretos-machine-query-service
    depends_on:
      rabbitmq:
        condition: service_healthy
      system-postgres:
        condition: service_healthy
    environment:
      RABBITMQ_URL: "amqp://uretos_system:uretos_system_dev_pass@rabbitmq:5672/"
      SYSTEM_DB_URL: "postgresql+psycopg://uretos_system:uretos_system_dev_pass@system-postgres:5432/uretos_system"
    networks:
      - default
      - tenant-net
    restart: unless-stopped

  shopfloor-stream-service:
    build: ./services/shopfloor-stream-service
    container_name: uretos-shopfloor-stream-service
    ports:
      - "8081:8081"
    depends_on:
      rabbitmq:
        condition: service_healthy
    environment:
      RABBITMQ_URL: "amqp://uretos_system:uretos_system_dev_pass@rabbitmq:5672/"
    restart: unless-stopped
    networks:
      - default
      - tenant-net
  
  timescale-writer-service:
    build:
      context: ./services/timescale-writer-service
      dockerfile: Dockerfile
    container_name: timescale-writer-service
    environment:
      - RABBITMQ_URL=amqp://uretos_system:uretos_system_dev_pass@rabbitmq:5672/
      - SYSTEM_DB_URL=postgresql+psycopg://uretos_system:uretos_system_dev_pass@system-postgres:5432/uretos_system
    networks:
      - default
      - tenant-net
    restart: unless-stopped
    depends_on:
      rabbitmq:
        condition: service_healthy
      system-postgres:
        condition: service_healthy

  timescale-query-service:
    build:
      context: .
      dockerfile: services/timescale-query-service/Dockerfile
    container_name: uretos-timescale-query
    environment:
      - RABBITMQ_URL=amqp://uretos_system:uretos_system_dev_pass@rabbitmq:5672/
      - SYSTEM_DB_URL=postgresql+psycopg://uretos_system:uretos_system_dev_pass@system-postgres:5432/uretos_system
    networks:
      - default
      - tenant-net
    restart: unless-stopped
    depends_on:
      rabbitmq:
        condition: service_healthy
      system-postgres:
        condition: service_healthy

  shopfloor-bff-api:
    build:
      context: .
      dockerfile: services/shopfloor-bff-api/Dockerfile
    container_name: uretos-shopfloor-bff-api
    environment:
      - RABBITMQ_URL=amqp://uretos_system:uretos_system_dev_pass@rabbitmq:5672/
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.shopfloor-bff.rule=PathPrefix(`/api/v1/machines`)"
      - "traefik.http.routers.shopfloor-bff.entrypoints=web"
      - "traefik.http.services.shopfloor-bff.loadbalancer.server.port=8080"
      - "traefik.docker.network=uretos-core-net"
    networks:
      - default
      - tenant-net
    restart: unless-stopped
    depends_on:
      rabbitmq:
        condition: service_healthy
      timescale-query-service:
        condition: service_started

  traefik:
    image: traefik:v3.6
    container_name: uretos-traefik
    command:
      - "--api.insecure=true"
      - "--providers.docker=true"
      - "--providers.docker.endpoint=http://uretos-docker-proxy:2375"
      - "--providers.docker.exposedbydefault=false"
      - "--entrypoints.web.address=:80"
    ports:
      - "8888:80"
      - "8090:8080"
    networks:
      - default
      - tenant-net
    restart: unless-stopped
    depends_on:
      - docker-socket-proxy

  connector-box-poller:
    build: ./services/connector-box-poller
    container_name: uretos-connector-box-poller
    environment:
      - GATEWAY_URL=http://gateway-api:8080
      - POLL_INTERVAL_SECONDS=5
      - TENANT_ID=test-tenant-e2e
    networks:
      - default
      - tenant-net
    restart: unless-stopped
    depends_on:
      - gateway-api

networks:
  tenant-net:
    driver: bridge

volumes:
  system-postgres-data:
```
