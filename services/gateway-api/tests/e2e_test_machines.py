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
