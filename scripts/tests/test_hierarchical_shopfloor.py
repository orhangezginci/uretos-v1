"""
Vollautomatisches E2E-Shopfloor-Testskript für 'Schwarzwald-Metallwaren':
Setzt die Umgebung bei jedem Start komplett auf 0 zurück (Clean Reset via Docker),
provisioniert den Tenant, paired die Boxen und prüft die Maschinen direkt in der Tenant-DB.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time

import requests

GATEWAY_URL = "http://localhost:8080"
TENANT_ID = "schwarzwald-metallwaren"
REQUEST_TIMEOUT = 10
HEALTH_TIMEOUT_SECONDS = 90


def cleanup_tenant_resources():
    """Entfernt zur Laufzeit vom Provisioning-Service angelegte Container und Volumes."""
    prefix = f"tenant-{TENANT_ID}"

    ids = subprocess.run(
        ["docker", "ps", "-aq", "--filter", f"name={prefix}"],
        capture_output=True, text=True, check=True,
    ).stdout.split()
    if ids:
        print(f"Entferne {len(ids)} Tenant-Container ({prefix}*)...")
        subprocess.run(["docker", "rm", "-f", "-v", *ids], check=True, stdout=subprocess.DEVNULL)

    vols = subprocess.run(
        ["docker", "volume", "ls", "-q", "--filter", f"name={prefix}"],
        capture_output=True, text=True, check=True,
    ).stdout.split()
    if vols:
        print(f"Entferne {len(vols)} Tenant-Volumes ({prefix}*)...")
        subprocess.run(["docker", "volume", "rm", "-f", *vols], check=True, stdout=subprocess.DEVNULL)


def wait_for_gateway(timeout: int = HEALTH_TIMEOUT_SECONDS):
    """Pollt das Gateway, bis es antwortet."""
    print(f"Warte auf Gateway ({GATEWAY_URL}), max. {timeout}s...")
    deadline = time.time() + timeout
    last_error = None
    while time.time() < deadline:
        try:
            resp = requests.get(f"{GATEWAY_URL}/v1/connector-boxes", timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                return
            last_error = f"HTTP {resp.status_code}"
        except requests.RequestException as exc:
            last_error = str(exc)
        time.sleep(2)
    raise RuntimeError(f"Gateway nicht bereit nach {timeout}s (letzter Fehler: {last_error})")


def post_with_retry(path: str, payload: dict, what: str, timeout: int = 45):
    """POST mit Retry bei 4xx/5xx für event-consistent Endpoints."""
    deadline = time.time() + timeout
    attempt = 0
    while True:
        attempt += 1
        resp = requests.post(f"{GATEWAY_URL}{path}", json=payload, timeout=REQUEST_TIMEOUT)
        if resp.status_code in (200, 201, 202):
            print(f"  -> {what}: HTTP {resp.status_code} - {resp.text} (Versuch {attempt})")
            return resp
        if time.time() >= deadline:
            raise SystemExit(
                f"[FAIL] {what} fehlgeschlagen nach {attempt} Versuchen: "
                f"HTTP {resp.status_code} - {resp.text}"
            )
        print(f"  .. {what}: HTTP {resp.status_code} - {resp.text} -> Retry in 2s")
        time.sleep(2)


def get_machines_with_retry(hardware_id: str, timeout: int = 45):
    """Prüft direkt in der Tenant-PostgreSQL-Datenbank, ob Maschinen für die Box existieren."""
    deadline = time.time() + timeout
    container_name = f"tenant-{TENANT_ID}-postgres"
    
    while True:
        try:
            # SQL-Abfrage direkt im Tenant-Postgres-Container ausführen
            cmd = [
                "docker", "exec", container_name,
                "psql", "-U", "postgres", "-d", f"tenant_{TENANT_ID}",
                "-t", "-A", "-F", ",",
                "SELECT machine_id, name, manufacturer, model, machine_type FROM machines;"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            lines = result.stdout.strip().split("\n")
            
            machines = []
            for line in lines:
                if not line.strip():
                    continue
                parts = line.split(",")
                if len(parts) >= 5:
                    machines.append({
                        "machine_id": parts[0],
                        "name": parts[1],
                        "manufacturer": parts[2],
                        "model": parts[3],
                        "machine_type": parts[4]
                    })
            
            if machines:
                return machines
        except Exception:
            # Container oder Tabellen evtl. noch im Start begriffen
            pass

        if time.time() >= deadline:
            return []
        time.sleep(3)


def reset_and_start_docker():
    print("--- [0/3] Setze Umgebung komplett auf 0 zurück (Clean Reset) ---")
    try:
        cleanup_tenant_resources()
        print("Fahre alte Container herunter und lösche Volumes...")
        subprocess.run(
            ["docker", "compose", "down", "-v", "--remove-orphans"],
            check=True, stdout=subprocess.DEVNULL,
        )
        cleanup_tenant_resources()
        time.sleep(3)

        print("Starte Docker-Stack frisch...")
        subprocess.run(["docker", "compose", "up", "-d"], check=True, stdout=subprocess.DEVNULL)

        wait_for_gateway()
        time.sleep(5)
        print("  -> Umgebung ist bereit und sauber aufgesetzt!\n")
    except Exception as exc:
        print(f"[ERROR] Konnte Docker-Umgebung nicht starten: {exc}")
        sys.exit(1)


def print_shopfloor_report():
    print("\n" + "=" * 60)
    print(f"  uretOS SHOPFLOOR REPORT - Tenant: {TENANT_ID}")
    print("=" * 60)

    try:
        resp = requests.get(f"{GATEWAY_URL}/v1/connector-boxes", timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            print(f"[ERROR] Konnte Connector-Boxen nicht abrufen: HTTP {resp.status_code}")
            return False

        boxes = resp.json()
        tenant_boxes = [b for b in boxes if b.get("tenant_id") == TENANT_ID]
    except Exception as exc:
        print(f"[ERROR] Verbindungsfehler zum Gateway: {exc}")
        return False

    if not tenant_boxes:
        print(f"\n[Info] Keine Connector-Boxen für Tenant '{TENANT_ID}' gefunden.")
        return False

    total_machines_count = 0
    box_stats = []

    for box in tenant_boxes:
        hardware_id = box.get("hardware_id")
        box_id = box.get("box_id")
        status = box.get("status") or "unknown"

        print(f"\n📦 Connector Box: {hardware_id} (ID: {box_id})")
        print(f"   Status: {status.upper()}")

        # Maschinen direkt aus der Tenant-Datenbank abrufen
        machines = get_machines_with_retry(hardware_id, timeout=45)
        total_machines_count += len(machines)
        box_stats.append((hardware_id, len(machines)))

        print(f"   Zugeordnete Maschinen ({len(machines)} / Max. 5 Lizenz-Limit):")
        if not machines:
            print("     (Bisher keine Maschinen in der DB entdeckt)")
        for m in machines:
            print(f"     ├── Machine-ID : {m.get('machine_id')}")
            print(f"     │   Name       : {m.get('name')}")
            print(f"     │   Hersteller : {m.get('manufacturer')}")

    limit_ok = all(count <= 5 for _, count in box_stats)

    print("\n" + "-" * 60)
    print("  ZUSAMMENFASSUNG:")
    print(f"  - Aktive Boxen     : {len(tenant_boxes)}")
    print(f"  - Total Maschinen  : {total_machines_count}")
    print(f"  - Lizenz-Status    : {'LIMIT EINGEHALTEN (<= 5 pro Box)' if limit_ok else 'WARNUNG: LIZENZLIMIT ÜBERSCHRITTEN!'}")
    print("=" * 60 + "\n")
    return limit_ok


def run_hierarchical_test():
    reset_and_start_docker()

    print("--- Starte realistisches Shopfloor-E2E-Setup ---")

    print(f"\n[1/3] Provisioniere Tenant: {TENANT_ID}")
    tenant_success = False
    for attempt in range(1, 6):
        resp = requests.post(
            f"{GATEWAY_URL}/v1/tenants",
            json={"tenant_id": TENANT_ID},
            timeout=60,
        )
        if resp.status_code in (200, 201, 202):
            print(f"Tenant-Status: HTTP {resp.status_code} - {resp.text} (Versuch {attempt})")
            tenant_success = True
            break
        print(f"  .. Tenant-Provisioning war noch nicht bereit (HTTP {resp.status_code}): {resp.text}")
        print(f"  .. Nächster Versuch in 3 Sekunden (Versuch {attempt}/5)...")
        time.sleep(3)

    if not tenant_success:
        raise SystemExit(f"[FAIL] Tenant-Provisioning nach 5 Versuchen fehlgeschlagen.")

    boxes = [
        {"hardware_id": "box-sw-01", "mac_address": "AA:BB:CC:DD:EE:01"},
        {"hardware_id": "box-sw-02", "mac_address": "AA:BB:CC:DD:EE:02"},
    ]

    for box in boxes:
        print(f"\n[2/3] Registriere & Paire Box: {box['hardware_id']}")
        post_with_retry(
            "/v1/connector-boxes",
            {**box, "tenant_id": TENANT_ID},
            what=f"Registrierung {box['hardware_id']}",
        )
        post_with_retry(
            "/v1/connector-boxes/pair",
            {"hardware_id": box["hardware_id"]},
            what=f"Pairing {box['hardware_id']}",
        )

    print("\n[3/3] Setup aktiv. Warte auf mDNS-Discovery und Sync...")
    time.sleep(10)

    ok = print_shopfloor_report()
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    run_hierarchical_test()