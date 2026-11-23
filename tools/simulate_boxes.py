#!/usr/bin/env python3
"""
uretOS E2E-Pipeline-Test mit simulierten Connector Boxen (Pendant zu run_e2e_pipeline.sh, aber mit
opc_discovery.py als Box und mit harten Prüfungen statt sleep + Hoffen).

Pipeline:   [0] Preflight  ->  [1] gründlich aufräumen  ->  [2] Tenant provisionieren
            ->  [3] Boxen anlegen + pairen  ->  [4] Boxen starten + warten  ->  [5] validieren + Report

Reihenfolge wie run_e2e_pipeline.sh: System-DB-Zeilen -> Container/Volumes -> POST /v1/tenants -> 30s Ruhe ohne
Zugriff auf den Tenant -> Bereitschaftsprüfung; alte Poller laufen bis NACH der Provisionierung weiter.

Aufräumen (nur für den angegebenen Tenant; erst Inventur, dann Löschen, dann Nachprüfung):
  - alte Poller-Container (connector-box-01/02/poller) werden nach der Provisionierung gestoppt
  - Tenant-Docker-Ressourcen (tenant-<id>-*: Container inkl. Volumes, Netze; Compose-Services sind tabu)
  - RabbitMQ-vhosts/-User des Tenants nur mit --purge-rabbitmq (Standard: NICHT, wie run_e2e_pipeline.sh -
    laufende Services können Verbindungen/Zugangsdaten zum Tenant-vhost zwischenspeichern)
  - System-DB: ALLE Tabellen mit Spalte tenant_id (FK-Reihenfolge wird automatisch aufgelöst)
  - lokaler Box-State (sim_state/)
  Danach muss der Tenant frisch provisioniert eine LEERE Maschinenliste haben, sonst Abbruch.
  --plan zeigt nur die Inventur. Ohne --yes wird im Terminal die Tenant-ID zur Bestätigung abgefragt.

Woher kommt das "Soll" (welche Maschinen sollte es geben)?
  (nichts angeben)        Discovery-Modus: Soll = was die Boxen selbst finden (funktioniert ohne Vorwissen)
  --shopfloor FILE        Soll aus der shopfloor.yaml der Sim (zusätzlich: Ports werden vorab geprüft)
  --expected-file FILE    Soll aus JSON: [{"name": "...", "serial": "...", "uid": "..."}]

Generische Prüfungen (unabhängig vom Soll):
  - eine Maschine gehört höchstens einer Box, keine Box über dem Lizenzlimit
  - keine gefundene Maschine bleibt unzugewiesen, solange eine Box, die sie sieht, noch Kapazität hat
  - Tenant-weite Maschinenliste ohne Duplikate und konsistent mit den Box-Listen
  - System-DB: erwartete Anzahl connector_boxes-Zeilen
  - Zuordnung wird aus der Tenant-DB (Tabelle machines, wie verify_autoscan_db.sh) gelesen und gegen die API geprüft
  - Backend-Probes: der SERVER muss einen Doppel-Claim und eine Maschine über dem Lizenzlimit selbst ablehnen
    (unabhängig vom Client - MAX_MACHINES_PER_BOX im Poller schützt die Lizenz nicht, wenn nur der Client prüft)
  - Cockpit-API (BFF, GET /api/v1/shopfloor): zeigt je Box dieselben Maschinen wie die Tenant-DB, mit Hersteller und
    Status (--bff-url off schaltet das ab; das BFF muss VOR dem Lauf laufen, sonst kennt es keine Status-Events)
  - Stabilität: ein Folgezyklus ändert nichts
  Nur mit Soll zusätzlich: wurden alle erwarteten Maschinen entdeckt?

Voraussetzungen: docker compose up -d (Gateway, RabbitMQ, system-postgres, Maschinen), `pip install opcua`,
opc_discovery.py liegt daneben.
Beispiele:
  python3 simulate_boxes.py --plan                               # nur zeigen, was aufgeräumt würde
  python3 simulate_boxes.py --yes --shopfloor shopfloor.yaml     # kompletter Lauf wie run_e2e_pipeline.sh
  python3 simulate_boxes.py meinTenant --boxes 1 --yes           # Lizenzgrenze: 8 Maschinen, 1 Box
  python3 simulate_boxes.py --reuse-tenant                       # ohne Aufräumen/Provisionieren (Tenant existiert)
  python3 simulate_boxes.py --scan-cidr auto --scan-ports 4840   # Boxen erkennen das echte Netz selbst
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import uuid
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
OLD_POLLERS = ["uretos-connector-box-01", "uretos-connector-box-02", "uretos-connector-box-poller"]


# --------------------------------------------------------------------------- Helfer
def http(gateway: str, method: str, path: str, body: dict | None = None, timeout: int = 70):
    req = urllib.request.Request(
        gateway + path, method=method, headers={"Content-Type": "application/json"},
        data=json.dumps(body).encode() if body is not None else None,
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"null")
        except ValueError:
            return e.code, None


def load_expected_yaml(path: Path) -> list[dict]:
    """Liest MACHINE_NAME / SERIAL / PORT aus shopfloor.yaml (ohne PyYAML)."""
    machines, cur = [], {}
    for line in path.read_text().splitlines():
        for key in ("MACHINE_NAME", "SERIAL", "PORT"):
            m = re.search(rf"{key}=(\S+)", line)
            if m:
                cur[key] = m.group(1)
        if "PORT" in cur and "MACHINE_NAME" in cur:
            machines.append({
                "name": cur["MACHINE_NAME"], "serial": cur.get("SERIAL", ""),
                "port": int(cur["PORT"]), "uid": f"urn:uretos:machine:{cur['MACHINE_NAME']}",
            })
            cur = {}
    return machines


def load_expected_json(path: Path) -> list[dict]:
    out = []
    for i, x in enumerate(json.loads(path.read_text())):
        out.append({"name": x.get("name") or x.get("uid") or f"machine-{i + 1}",
                    "serial": x.get("serial") or x.get("serial_number") or "",
                    "uid": x.get("uid") or "", "port": x.get("port")})
    return out


def mkey(m: dict) -> str:
    return m["uid"] or f"name:{m['name']}"


def flatten(o):
    if isinstance(o, dict):
        for v in o.values():
            yield from flatten(v)
    elif isinstance(o, (list, tuple)):
        for v in o:
            yield from flatten(v)
    elif o is not None:
        yield str(o)


def match_machine(entry, expected: list[dict]) -> dict | None:
    """Ordnet einen Eintrag (Server-Liste oder Discovered-Report) GENAU einer Maschine zu. Reihenfolge:
    exakte uid, exakte Seriennr., exakter Name, uid als Teilstring. Nur eindeutige Treffer zählen
    (doppelte Maschinennamen im echten Shopfloor dürfen nichts vermischen)."""
    vals = set(flatten(entry))
    tests = (
        lambda m: m["uid"] and m["uid"] in vals,
        lambda m: m["serial"] and m["serial"] in vals,
        lambda m: m["name"] in vals,
        lambda m: m["uid"] and any(m["uid"] in v for v in vals),
    )
    for t in tests:
        hits = [m for m in expected if t(m)]
        if len(hits) == 1:
            return hits[0]
    return None


def expected_from_discovered(disc: dict[str, list | None]) -> list[dict]:
    seen: dict[str, dict] = {}
    for entries in disc.values():
        for e in entries or []:
            if e["uid"] in seen:
                continue
            port = re.search(r":(\d+)$", e.get("endpoint_url") or "")
            seen[e["uid"]] = {"name": e.get("name") or e["uid"], "serial": e.get("serial_number") or "",
                              "uid": e["uid"], "port": int(port.group(1)) if port else None}
    return sorted(seen.values(), key=lambda x: (x["port"] or 0, x["name"]))


def port_open(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(1)
        return s.connect_ex(("127.0.0.1", port)) == 0


def running_containers() -> list[str]:
    try:
        out = subprocess.run(["docker", "ps", "--format", "{{.Names}}"], capture_output=True, text=True, timeout=10)
        return out.stdout.split()
    except Exception:
        return []


def fake_mac(box_id: str) -> str:
    h = hashlib.md5(box_id.encode()).digest()
    return "02:00:00:%02x:%02x:%02x" % (h[0], h[1], h[2])


def ensure_box(gw: str, box_id: str, tenant: str) -> str:
    code, data = http(gw, "POST", "/v1/connector-boxes/handshake", {"hardware_id": box_id})
    if code == 200:
        return "bereits angelegt und gepairt"
    note = "neu angelegt + gepairt"
    if code == 404:
        code, data = http(gw, "POST", "/v1/connector-boxes",
                          {"tenant_id": tenant, "hardware_id": box_id, "mac_address": fake_mac(box_id)})
        if code not in (200, 201):
            raise RuntimeError(f"Box {box_id} anlegen fehlgeschlagen (HTTP {code}): {data}\n"
                               f"  -> existiert der Tenant '{tenant}'? (POST /v1/tenants) oder --tenant angeben")
    elif code != 403:
        raise RuntimeError(f"Handshake für {box_id}: HTTP {code}: {data}")
    code, data = http(gw, "POST", "/v1/connector-boxes/pair", {"hardware_id": box_id})
    if code != 200:
        raise RuntimeError(f"Pairing {box_id} fehlgeschlagen (HTTP {code}): {data}")
    code, data = http(gw, "POST", "/v1/connector-boxes/handshake", {"hardware_id": box_id})
    if code != 200:
        raise RuntimeError(f"Handshake nach Pairing {box_id}: HTTP {code}: {data}")
    return note


def all_box_ids(gw: str, sim_ids: list[str]) -> list[str]:
    ids = list(sim_ids)
    code, data = http(gw, "GET", "/v1/connector-boxes")
    if code == 200 and isinstance(data, list):
        for b in data:
            hw = b.get("hardware_id") if isinstance(b, dict) else None
            if hw and hw not in ids:
                ids.append(hw)
    return ids


def fetch_assignments(gw: str, box_ids: list[str]) -> tuple[dict[str, list], list[str]]:
    result, errors = {}, []
    for b in box_ids:
        code, data = http(gw, "GET", f"/v1/connector-boxes/{b}/machines")
        if code == 200 and isinstance(data, list):
            result[b] = data
        else:
            result[b] = []
            errors.append(f"{b}: HTTP {code}")
    return result, errors


def owners_from(assign: dict[str, list], expected: list[dict]):
    owners = {mkey(m): set() for m in expected}
    unknown: dict[str, list] = {}
    for box, entries in assign.items():
        for e in entries:
            m = match_machine(e, expected)
            if m:
                owners[mkey(m)].add(box)
            else:
                unknown.setdefault(box, []).append(e)
    return owners, unknown


def read_machines(path: Path) -> list[dict] | None:
    """None = Datei existiert (noch) nicht."""
    try:
        return json.loads(path.read_text()).get("machines", [])
    except (OSError, ValueError):
        return None


def read_discovered(state_root: Path, sim_ids: list[str]) -> dict[str, list | None]:
    return {b: read_machines(state_root / b / "discovered_machines.json") for b in sim_ids}


def log_stats(log_file: Path) -> dict[str, int]:
    text = log_file.read_text(errors="replace") if log_file.exists() else ""
    return {
        "registriert": text.count("Maschine registriert:"),
        "abgelehnt": text.count("abgelehnt ("),
        "fremd": text.count("gehört bereits Box"),
        "limit": text.count("Lizenzlimit"),
        "fehler": text.count(" ERROR "),
    }


# --------------------------------------------------------------------------- Aufräumen & Provisionierung
TENANT_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{2,62}$")
SYSTEM_PG = "uretos-system-postgres"
STACK_INFRA_USERS = {"guest", "uretos_system"}


def sh(cmd: list[str], timeout: int = 60, input: str | None = None) -> tuple[int, str, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, input=input)
        return p.returncode, p.stdout, p.stderr
    except FileNotFoundError:
        return 127, "", f"{cmd[0]} nicht gefunden"
    except subprocess.TimeoutExpired:
        return 124, "", "Timeout"


def psql(sql: str) -> tuple[int, str, str]:
    return sh(["docker", "exec", "-i", SYSTEM_PG, "psql", "-U", "uretos_system", "-d", "uretos_system", "-At", "-c", sql])


def tenant_pattern(tenant: str) -> re.Pattern:
    """Tenant-ID als eigenständiges Token; '-' und '_' sind austauschbar (DB-Namen ersetzen oft '-' durch '_')."""
    core = "".join("[-_]" if ch in "-_" else re.escape(ch) for ch in tenant)
    return re.compile(rf"(?<![a-z0-9]){core}(?![a-z0-9])", re.I)


def rabbit(a, method: str, path: str):
    user, _, pw = a.rabbit_admin.partition(":")
    req = urllib.request.Request(a.rabbit_url + path, method=method)
    req.add_header("Authorization", "Basic " + base64.b64encode(f"{user}:{pw}".encode()).decode())
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            body = r.read()
            return r.status, (json.loads(body) if body else None)
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception:
        return 0, None


def db_inventory(tenant: str) -> dict[str, int] | None:
    """Zeilenanzahl pro Tabelle (alle Basistabellen mit Spalte tenant_id). None = System-DB nicht abfragbar."""
    rc, out, _ = psql(
        "SELECT DISTINCT c.table_name FROM information_schema.columns c "
        "JOIN information_schema.tables t USING (table_schema, table_name) "
        "WHERE c.table_schema='public' AND c.column_name='tenant_id' AND t.table_type='BASE TABLE'")
    if rc != 0:
        return None
    inv: dict[str, int] = {}
    for t in sorted(out.split(), key=lambda t: (t == "tenants", t)):  # tenants zuletzt
        rc, o, _ = psql(f"SELECT count(*) FROM \"{t}\" WHERE tenant_id='{tenant}'")
        if rc == 0 and o.strip().isdigit():
            inv[t] = int(o)
    return inv


def db_clean(tenant: str, inv: dict[str, int]) -> list[str]:
    """Löscht Tenant-Zeilen; FK-Verletzungen werden durch Wiederholung aufgelöst. Rückgabe: nicht löschbare Tabellen."""
    pending = [t for t, c in inv.items() if c > 0]
    while pending:
        failed = [t for t in pending if psql(f"DELETE FROM \"{t}\" WHERE tenant_id='{tenant}'")[0] != 0]
        if len(failed) == len(pending):  # kein Fortschritt mehr
            return failed
        pending = failed
    return []


def build_inventory(tenant: str, a) -> dict:
    pat = tenant_pattern(tenant)
    inv: dict = {"db": db_inventory(tenant), "containers": [], "volumes": [], "networks": [], "vhosts": [], "users": []}
    rc, out, _ = sh(["docker", "ps", "-a", "--format", '{{.Names}}|{{.Label "com.docker.compose.service"}}'])
    for line in out.splitlines():
        name, _, svc = line.partition("|")
        if name and not svc and pat.search(name):  # Compose-Services (Kernstack, Sim) sind tabu
            inv["containers"].append(name)
    for kind, key in (("volume", "volumes"), ("network", "networks")):
        _, out, _ = sh(["docker", kind, "ls", "--format", "{{.Name}}"])
        inv[key] = [n for n in out.split() if pat.search(n)]
    if a.purge_rabbitmq:
        code, vh = rabbit(a, "GET", "/api/vhosts")
        if code == 200 and isinstance(vh, list):
            inv["vhosts"] = [v["name"] for v in vh if pat.search(v.get("name", ""))]
        code, us = rabbit(a, "GET", "/api/users")
        if code == 200 and isinstance(us, list):
            keep = STACK_INFRA_USERS | {a.rabbit_admin.partition(":")[0]}
            inv["users"] = [u["name"] for u in us if pat.search(u.get("name", "")) and u["name"] not in keep]
    return inv


def inventory_empty(inv: dict) -> bool:
    return not any(v for k, v in inv.items() if k != "db") and not any((inv["db"] or {}).values())


def print_inventory(inv: dict) -> None:
    rows = [("Docker-Container", inv["containers"]), ("Docker-Volumes", inv["volumes"]),
            ("Docker-Netze", inv["networks"]), ("RabbitMQ-vhosts", inv["vhosts"]), ("RabbitMQ-User", inv["users"]),
            ("System-DB-Zeilen", [f"{t}={c}" for t, c in (inv["db"] or {}).items() if c])]
    for label, items in rows:
        if items:
            print(f"    {label}: {', '.join(items)}")


def cleanup_tenant(tenant: str, a, inv: dict) -> tuple[bool, str, dict]:
    """Reihenfolge wie in euren Skripten: erst System-DB-Zeilen (run_e2e_pipeline.sh Schritt 1), dann Container/Volumes
    (provision_tenant.sh), RabbitMQ nur auf Wunsch."""
    problems: list[str] = []
    stuck = db_clean(tenant, inv["db"] or {})
    if stuck:
        problems.append("DB-Tabellen nicht löschbar: " + ", ".join(stuck))
    for key, cmd in (("containers", ["docker", "rm", "-f", "-v"]), ("volumes", ["docker", "volume", "rm", "-f"]),
                     ("networks", ["docker", "network", "rm"])):
        for name in inv[key]:
            rc, _, err = sh([*cmd, name])
            if rc != 0:
                problems.append(f"{key[:-1]} {name}: {err.strip()[:80]}")
    for v in inv["vhosts"]:
        rabbit(a, "DELETE", "/api/vhosts/" + urllib.parse.quote(v, safe=""))
    for u in inv["users"]:
        rabbit(a, "DELETE", "/api/users/" + urllib.parse.quote(u, safe=""))
    after = build_inventory(tenant, a)
    rows = sum((inv["db"] or {}).values())
    summary = (f"entfernt: {len(inv['containers'])} Container, {len(inv['volumes'])} Volumes, {len(inv['networks'])} Netze, "
               f"{len(inv['vhosts'])} vhosts, {len(inv['users'])} RabbitMQ-User, {rows} DB-Zeilen")
    return inventory_empty(after) and not problems, summary + (" | PROBLEME: " + "; ".join(problems) if problems else ""), after


def tenant_db_names(tenant: str) -> tuple[str, str]:
    """Konvention aus provision_tenant.sh / verify_autoscan_db.sh: Container tenant-<id>-postgres, DB und User tenant_<id mit _>."""
    return f"tenant-{tenant}-postgres", "tenant_" + tenant.replace("-", "_")


def tenant_psql(tenant: str, sql: str, sep: str = "|") -> tuple[int, str, str]:
    container, ident = tenant_db_names(tenant)
    return sh(["docker", "exec", "-i", container, "psql", "-U", ident, "-d", ident, "-t", "-A", "-F", sep, "-c", sql])


def tenant_db_machines(tenant: str) -> list[dict] | None:
    """Zeilen der Tabelle machines (dieselbe Abfrage wie verify_autoscan_db.sh). None = Tenant-DB nicht abfragbar."""
    rc, out, _ = tenant_psql(
        tenant, "SELECT machine_id, box_id, name, metadata->>'manufacturer', metadata->>'machine_type' "
                "FROM machines ORDER BY box_id, machine_id", sep="\x1f")
    if rc != 0:
        return None
    rows = []
    for line in out.splitlines():
        p = line.split("\x1f")
        if len(p) == 5:
            rows.append({"machine_id": p[0], "box_id": p[1], "name": p[2], "manufacturer": p[3], "machine_type": p[4]})
    return rows


def box_name_map(gw: str) -> dict[str, str]:
    """box_id / hardware_id -> hardware_id (die DB-Spalte box_id kann beides sein)."""
    code, data = http(gw, "GET", "/v1/connector-boxes")
    out: dict[str, str] = {}
    if code == 200 and isinstance(data, list):
        for e in data:
            if isinstance(e, dict) and e.get("hardware_id"):
                for k in (e.get("box_id"), e.get("id"), e["hardware_id"]):
                    if k:
                        out[str(k)] = e["hardware_id"]
    return out


def group_rows(rows: list[dict], boxmap: dict[str, str], sim_ids: list[str]) -> tuple[dict[str, list], set[str]]:
    grouped: dict[str, list] = {b: [] for b in sim_ids}
    unresolved: set[str] = set()
    for r in rows:
        box = boxmap.get(r["box_id"])
        if box is None:
            unresolved.add(r["box_id"])
            box = r["box_id"]
        grouped.setdefault(box, []).append(r)
    return grouped, unresolved


SECRET_SKIP = ("$2", "gAAAA", "scram-sha-256$", "enc:", "ENC(")


def _flatten_strings(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from _flatten_strings(v, f"{path}.{k}" if path else k)
    elif isinstance(o, str):
        yield path, o


def registry_pg_credentials(tenant: str) -> tuple[dict | None, str]:
    """Postgres-Zugangsdaten des Tenants aus der Registry (system-postgres, Tabelle tenants).
    Die Werte bleiben im Speicher; angezeigt werden nur Feldnamen. Zuordnung per Namensheuristik."""
    rc, out, _ = psql(f"SELECT row_to_json(t) FROM tenants t WHERE tenant_id='{tenant}'")
    if rc != 0 or not out.strip():
        return None, "keine Registry-Zeile für den Tenant"
    try:
        items = list(_flatten_strings(json.loads(out.strip().splitlines()[0])))
    except ValueError:
        return None, "Registry-Zeile nicht lesbar"

    def pick(pattern: str):
        c = [(p, v) for p, v in items if re.search(pattern, p, re.I) and not re.search(r"rabbit|amqp|mq|redis", p, re.I)]
        c.sort(key=lambda pv: 0 if re.search(r"postgres|pg|db", pv[0], re.I) else 1)
        return c[0] if c else (None, None)

    (fu, user), (fp, pw), (fd, db) = pick("user"), pick("pass"), pick(r"(^|[._])(db|database|dbname|db_name)")
    if not pw:
        return None, "kein Passwort-Feld in der Registry-Zeile gefunden"
    return {"user": user, "password": pw, "db": db, "fields": [f for f in (fu, fp, fd) if f]}, ""


def pg_tcp_auth(container: str, host: str, user: str, db: str, password: str) -> tuple[bool, str]:
    """Meldet sich per TCP an der Tenant-DB an (Passwort wird über stdin übergeben, nie über die Kommandozeile)."""
    rc, out, err = sh(["docker", "exec", "-i", container, "sh", "-c",
                       'read -r PGPASSWORD; export PGPASSWORD; exec psql -h "$1" -U "$2" -d "$3" -t -A -c "SELECT 1"',
                       "sh", host, user, db], input=password + "\n")
    text = (err or out).strip()
    return rc == 0 and out.strip() == "1", (text.splitlines()[0][:160] if text else "")


def registry_credential_check(tenant: str, real_ip: str | None, api_error: str) -> list[str]:
    """Passen die Zugangsdaten aus der Registry zur frischen Tenant-DB? Trennt 'Cache im Service' von 'Provisionierung inkonsistent'."""
    creds, why = registry_pg_credentials(tenant)
    if not creds:
        return [f"Registry-Zugangsdaten nicht prüfbar ({why})"]
    pw = creds["password"]
    if pw.startswith(SECRET_SKIP):
        return ["Registry-Passwort wirkt verschlüsselt/gehasht – direkter Test nicht möglich"]
    container, ident = tenant_db_names(tenant)
    user, db = creds["user"] or ident, creds["db"] or ident
    lines = [f"Registry-Felder für den Test: {', '.join(creds['fields'])} (nur Feldnamen, keine Werte)"]
    m = re.search(r'for user "([^"]+)"', api_error)
    if m:
        lines.append(f"User in der Fehlermeldung: {m.group(1)} | User in der Registry: {user} → "
                     + ("gleich" if m.group(1) == user else "VERSCHIEDEN (der Service nutzt einen anderen User als die Registry)"))
    if not real_ip:
        return lines + ["Passwort-Test übersprungen (keine Container-IP)"]
    good, gerr = pg_tcp_auth(container, real_ip, user, db, pw)
    bad, _ = pg_tcp_auth(container, real_ip, user, db, "falsch-" + uuid.uuid4().hex)
    if bad:
        lines.append("Passwort-Test nicht aussagekräftig: die Tenant-DB verlangt über diesen Pfad kein Passwort (pg_hba)")
    elif good:
        lines.append("Registry-Passwort FUNKTIONIERT gegen die Tenant-DB (TCP, Passwort wird erzwungen) → Registry und DB sind konsistent")
        lines.append("→ Befund: Der Service benutzt NICHT die aktuellen Registry-Zugangsdaten (zwischengespeichert/veraltet). "
                     "Das spricht für einen Fehler im machine-query-service bei der Neuanlage eines Tenants mit gleicher ID.")
    else:
        lines.append(f"Registry-Passwort wird von der Tenant-DB ABGELEHNT ({gerr}) → Registry und Tenant-DB haben verschiedene Passwörter")
        lines.append("→ Befund: Die Provisionierung hat DB und Registry inkonsistent angelegt (oder die Registry-Zeile gehört zu einer "
                     "anderen Provisionierung). Logs: docker logs uretos-tenant-provisioning-service / uretos-tenant-command-service")
    return lines


def diagnose_tenant_db(tenant: str, api_error: str) -> list[str]:
    """Fakten zur Ursache, wenn die Machine-Query die Tenant-DB nicht erreicht. Gibt KEINE Zugangsdaten aus."""
    out: list[str] = []
    container, _ = tenant_db_names(tenant)
    _, o, _ = sh(["docker", "ps", "-a", "--filter", f"name=^{container}$", "--format", "{{.Names}}: {{.Status}}"])
    out.append(f"Container: {o.strip() or 'nicht gefunden'}")
    rc, o, _ = sh(["docker", "inspect", "-f", "{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}", container])
    real_ips = o.split() if rc == 0 else []
    out.append(f"IP des Tenant-Postgres laut Docker: {', '.join(real_ips) or '–'}")
    m = re.search(r'server at "?([0-9.]+)', api_error)
    err_ip = m.group(1) if m else None
    if err_ip:
        same = err_ip in real_ips
        out.append(f"IP in der Fehlermeldung der Machine-Query: {err_ip} → "
                   + ("stimmt mit dem Container überein" if same else "WEICHT vom Container ab"))
    rc, o, e = tenant_psql(tenant, "SELECT 1")
    direct_ok = rc == 0
    out.append("Direkter Zugriff per docker exec: " + ("OK" if direct_ok else f"FEHLER ({(e or o).strip()[:120]})"))
    rc, o, _ = psql(f"SELECT count(*) FROM tenants WHERE tenant_id='{tenant}' AND tenants::text LIKE '%{container}%'")
    if rc == 0 and o.strip().isdigit():
        out.append(f"Tenant-Registry (system-postgres) verweist per Hostname '{container}' auf die DB: "
                   + ("ja (die IP ist dann egal, sie wird per Docker-DNS aufgelöst)" if int(o) else "nein (anderer Name oder IP)"))
    if err_ip and real_ips and err_ip not in real_ips:
        out.append("→ Verdacht: Der Service nutzt eine veraltete Tenant-Verbindung (Cache) oder die Registry hat eine falsche IP. "
                   "Abhilfe zum Testen: --restart-services machine-query-service,machine-command-service")
    elif "password authentication failed" in api_error and direct_ok:
        out.extend(registry_credential_check(tenant, real_ips[0] if real_ips else None, api_error))
        out.append("→ Gegenprobe: docker restart uretos-machine-query-service uretos-machine-command-service, "
                   "danach curl 'http://localhost:8080/v1/machines?tenant_id=" + tenant + "'")
    return out


def provision_tenant(gw: str, tenant: str, timeout: int, docker_ok: bool, quiet: int = 0) -> int:
    """Legt den Tenant an und wartet aktiv auf Bereitschaft (statt sleep 30).
    Bereit = GET /v1/machines liefert 200 + Liste (die Machine-Query kann also die Tenant-DB lesen).
    Zusätzlich wird die Tenant-DB direkt abgefragt; ist sie nach 30s nicht abfragbar (z.B. abweichende Namen),
    geht es mit der API-Sicht weiter. Rückgabe: Anzahl bereits vorhandener Maschinen (frisch muss 0 sein)."""
    try:
        code, data = http(gw, "POST", "/v1/tenants", {"tenant_id": tenant}, timeout=75)
    except Exception as exc:
        raise RuntimeError(f"Tenant-Provisionierung nicht gestartet: {exc}")
    print(f"    POST /v1/tenants → HTTP {code} {json.dumps(data)[:160]}")
    if code == 504:
        print("    Gateway-Timeout - Provisionierung läuft vermutlich weiter, warte auf Bereitschaft ...")
    elif code not in (200, 201, 202):
        raise RuntimeError(f"Tenant-Provisionierung abgelehnt (HTTP {code}): {data}\n"
                           f"  -> Reste eines alten Tenants? Aufräumen prüfen (--plan)")
    if quiet > 0:  # run_e2e_pipeline.sh: "sleep 30" - in dieser Zeit greift NICHTS auf den Tenant zu
        print(f"    Ruhezeit {quiet}s ohne Zugriff auf den Tenant (wie sleep 30 in run_e2e_pipeline.sh) ...")
        time.sleep(quiet)
    start = time.time()
    deadline = start + timeout
    last = {"api": "–", "db": "–", "api_full": ""}
    api_ok_since: float | None = None
    diagnosed = False
    n = 0
    while time.time() < deadline:
        n += 1
        api_ok, count = False, 0
        try:
            code, data = http(gw, "GET", f"/v1/machines?tenant_id={urllib.parse.quote(tenant)}", timeout=75)
            api_ok = code == 200 and isinstance(data, list)
            full = "" if api_ok else (str(data.get("error", data)) if isinstance(data, dict) else str(data))
            last["api_full"] = full
            if api_ok:
                last["api"] = f"HTTP {code}"
            else:  # den aussagekräftigen Teil zeigen (Ziel-IP + FATAL-Text), nicht den Anfang der Meldung
                ip_m = re.search(r'server at "?([0-9.]+)', full)
                fatal = re.search(r"FATAL:\s+([^\n]+)", full)
                last["api"] = f"HTTP {code} " + (f"→ {ip_m.group(1)} " if ip_m else "") + (
                    f"FATAL: {fatal.group(1)[:110]}" if fatal else full[:110] + "…")
            count = len(data) if api_ok else 0
        except Exception as exc:
            last["api"] = last["api_full"] = f"Fehler: {exc}"
        if api_ok:
            api_ok_since = api_ok_since or time.time()
            if not docker_ok:
                return count
            rc, out, err = tenant_psql(tenant, "SELECT count(*) FROM machines")
            if rc == 0 and out.strip().isdigit():
                return int(out.strip())
            if 'relation "machines" does not exist' in err:
                print("    Hinweis: Tabelle machines existiert noch nicht (API liefert bereits 200) – als leer gewertet")
                return count
            last["db"] = f"rc={rc} {(err or out).strip()[:160]}"
            if time.time() - api_ok_since >= 30:
                print(f"    ⚠ Tenant-DB nicht abfragbar ({last['db']}) – fahre mit API-Sicht fort, DB-Prüfungen entfallen")
                return count
        elif docker_ok and not diagnosed and time.time() - start >= 30:
            diagnosed = True
            print(f"    Vollständiger Fehler der API: {last['api_full'][:700]}")
            print("    Diagnose:")
            for line in diagnose_tenant_db(tenant, last["api_full"]):
                print(f"      - {line}")
        if diagnosed and not api_ok and time.time() - start >= 60 and "password authentication failed" in last["api_full"]:
            raise RuntimeError(
                "Abbruch nach 60s: dauerhafter Zugangsdaten-Fehler der Machine-Query gegen die frische Tenant-DB "
                "(kein vorübergehender Zustand).\n  Vollständiger Fehler: " + last["api_full"][:300] + "\n"
                "  Test: docker restart uretos-machine-query-service uretos-machine-command-service  und danach erneut "
                "starten (oder --restart-services machine-query-service,machine-command-service).\n"
                "  Hilft der Neustart, behalten die Services nach dem Neuanlegen eines Tenants mit gleicher ID veraltete "
                "Zugangsdaten - das ist ein Produktfehler und kein Testproblem.")
        if n % 3 == 1:
            print(f"    ... warte ({time.time() - start:.0f}s) API: {last['api']}")
        time.sleep(5)
    diag = ""
    if docker_ok and not diagnosed:
        diag = "\n  Diagnose:\n" + "\n".join(f"    - {l}" for l in diagnose_tenant_db(tenant, last["api_full"]))
    raise RuntimeError(
        f"Tenant '{tenant}' nach {timeout}s nicht bereit.\n"
        f"  Letzter Fehler der API: {last['api_full'][:700]}{diag}\n"
        f"  Weiter prüfen:\n"
        f"    docker logs uretos-tenant-provisioning-service --tail 40\n"
        f"    docker logs uretos-machine-query-service --tail 40")


PROBE_DROP = ("uid", "state", "reason")
REJECTED = (400, 403, 409, 422)


def run_probes(a, tenant: str, owners_by_box: dict[str, list], disc: dict, expected: list[dict],
               sim_ids: list[str], use_db: bool) -> tuple[list[tuple[bool, str]], list[str]]:
    """Negativtests direkt gegen den Server: ein Client, der sich NICHT an die Regeln hält, muss abgewiesen werden.
    Die Payload ist exakt die, die opc_discovery.py für diese Maschine sendet (aus dem Discovered-Snapshot)."""
    results: list[tuple[bool, str]] = []
    notes: list[str] = []
    templates: dict[str, dict] = {}
    for entries in disc.values():
        for e in entries or []:
            m = match_machine(e, expected)
            if m:
                templates.setdefault(mkey(m), {k: v for k, v in e.items() if k not in PROBE_DROP})
    counts = {b: len(owners_by_box.get(b, [])) for b in sim_ids}

    def total() -> int | None:
        rows = tenant_db_machines(tenant) if use_db else None
        if rows is not None:
            return len(rows)
        code, data = http(a.gateway, "GET", f"/v1/machines?tenant_id={urllib.parse.quote(tenant)}")
        return len(data) if code == 200 and isinstance(data, list) else None

    def claim(box: str, payload: dict) -> tuple[int, str | None]:
        try:
            code, data = http(a.gateway, "POST", "/v1/connector-boxes/autoscan", {"hardware_id": box, "machines": [payload]})
        except Exception:
            return 0, None
        return code, (data.get("error_code") if isinstance(data, dict) else None)

    before = total()
    victim = thief = None  # irgendein Paar (Besitzer-Box mit Maschine, andere Box mit freier Kapazität)
    for owner_box in sim_ids:
        for e in owners_by_box.get(owner_box, []):
            m = match_machine(e, expected)
            other = next((b for b in sim_ids if b != owner_box and counts[b] < a.max), None)
            if m and mkey(m) in templates and other:
                victim, thief = (owner_box, m), other
                break
        if victim:
            break
    if victim and thief:
        code, ec = claim(thief, templates[mkey(victim[1])])
        ok = code in REJECTED and ec in (None, "machine_taken")  # ec None = älteres Gateway ohne Fehlercode
        results.append((ok, f"Server lehnt Doppel-Claim ab: {thief} will '{victim[1]['name']}' (gehört {victim[0]}) → HTTP {code}"
                        + (f" {ec}" if ec else "")
                        + ("" if ok else " – NICHT (oder aus dem falschen Grund) abgelehnt, Exklusivität wird nicht serverseitig erzwungen")))
    else:
        notes.append("Exklusivitäts-Probe übersprungen (braucht ≥2 Boxen: eine mit Maschine, eine mit freier Kapazität)")

    full = next((b for b in sim_ids if counts[b] >= a.max), None)
    if full and templates:
        tag = uuid.uuid4().hex[:6]
        probe = dict(next(iter(templates.values())))
        for k, v in (("machine_id", f"urn:uretos:probe:{tag}"), ("name", f"PROBE-LIMIT-{tag}"), ("serial_number", f"PROBE-{tag}"),
                     ("endpoint_url", "opc.tcp://127.0.0.1:1"), ("product_instance_uri", f"urn:uretos:probe:{tag}")):
            if k in probe:
                probe[k] = v
        code, ec = claim(full, probe)
        ok = code in REJECTED and ec in (None, "box_limit_reached")
        results.append((ok, f"Server lehnt {a.max + 1}. Maschine für {full} ab (Limit {a.max}) → HTTP {code}"
                        + (f" {ec}" if ec else "")
                        + ("" if ok else " – NICHT (oder aus dem falschen Grund) abgelehnt, das Lizenzlimit wird nicht serverseitig erzwungen "
                                         "(Probe-Maschine PROBE-LIMIT-" + tag + " liegt jetzt im Tenant)")))
    else:
        notes.append(f"Limit-Probe übersprungen (keine Box hat {a.max} Maschinen; --boxes 1 oder weniger Boxen nutzen)")

    if results:
        time.sleep(3)  # asynchrone Verarbeitung abwarten
        after = total()
        if before is not None and after is not None:
            results.append((after == before, f"Probes haben den Maschinenbestand nicht verändert ({before} → {after})"))
    return results, notes


# --------------------------------------------------------------------------- Report
def pipeline_section(ctx: dict) -> list[str]:
    return ["## Pipeline", ""] + [f"- {n}" for n in ctx["pipeline"]] + [""]


def build_report(ctx: dict) -> tuple[str, bool]:
    a, expected, sim_ids = ctx["args"], ctx["expected"], ctx["sim_ids"]
    api_assign, local, disc = ctx["assign"], ctx["local"], ctx["disc"]
    db_assign, db_rows = ctx.get("db_assign"), ctx.get("db_rows")
    assign = {**api_assign, **db_assign} if db_assign is not None else api_assign
    owners, unknown = owners_from(assign, expected)

    # Wer hat welche Maschine gesehen (aus den Discovered-Snapshots der Boxen)?
    seen: dict[str, dict[str, tuple[str, str]]] = {mkey(m): {} for m in expected}
    for b, entries in disc.items():
        for e in entries or []:
            m = match_machine(e, expected)
            if m:
                seen[mkey(m)][b] = (e.get("state", "?"), e.get("reason", ""))

    shown: dict[str, str] = {}
    for m in expected:
        k = mkey(m)
        if owners[k]:
            shown[k] = ", ".join(sorted(owners[k]))
        else:  # Fallback: lokaler State der Boxen, falls die Server-Liste nicht zuordenbar ist
            loc = sorted(b for b, ms in local.items() if any(match_machine(x, expected) is m for x in ms))
            if loc:
                owners[k] = set(loc)
            shown[k] = (", ".join(loc) + " *") if loc else "— nicht zugewiesen —"

    counts = {b: len(v) for b, v in assign.items()}
    for b, ms in local.items():
        counts[b] = max(counts.get(b, 0), len(ms))

    lines = [
        "# uretOS Box-Simulation – Zuweisungsreport",
        "",
        f"- Zeitpunkt: {datetime.now():%Y-%m-%d %H:%M:%S}",
        f"- Gateway: {a.gateway} | Tenant: {ctx['tenant']}",
        f"- Soll: {ctx['soll_src']}",
        f"- Zuordnung gelesen aus: {'Tenant-DB (Tabelle machines)' if db_assign is not None else 'Gateway-API'}",
        f"- Boxen: {', '.join(sim_ids)} | Limit pro Box: {a.max}",
        f"- Laufzeit: {ctx['duration']:.0f}s ({ctx['reason']})",
        "",
        *pipeline_section(ctx),
        "## Maschine → Box",
        "",
        "| Maschine | Port | Seriennr. | Gesehen von | Zugewiesen an |",
        "|---|---|---|---|---|",
    ]
    for m in expected:
        k = mkey(m)
        lines.append(f"| {m['name']} | {m['port'] or '–'} | {m['serial'] or '–'} | "
                     f"{', '.join(sorted(seen[k])) or '–'} | {shown[k]} |")
    lines.append("")
    if any(s.endswith("*") for s in shown.values()):
        lines += ["`*` = nur aus dem lokalen Box-State, in der Server-Liste nicht zuordenbar.", ""]

    if db_rows:
        lines += ["## Maschinen in der Tenant-DB", "", "| machine_id | Box | Name | Hersteller | Typ |", "|---|---|---|---|---|"]
        for r in db_rows:
            lines.append(f"| {r['machine_id']} | {ctx['boxmap'].get(r['box_id'], r['box_id'])} | {r['name']} | "
                         f"{r['manufacturer'] or '–'} | {r['machine_type'] or '–'} |")
        lines.append("")

    lines += ["## Box → Maschinen", "", "| Box | Anzahl | Maschinen |", "|---|---|---|"]
    for b in counts:
        names = [m["name"] for m in expected if b in owners[mkey(m)]]
        if names or b in sim_ids:
            tag = "" if b in sim_ids else " (nicht Teil der Simulation)"
            lines.append(f"| {b}{tag} | {counts[b]}/{a.max} | {', '.join(names) or '—'} |")
    lines.append("")

    # Gefunden, aber nicht zugewiesen
    unassigned = [m for m in expected if not owners[mkey(m)] and seen[mkey(m)]]
    undiscovered = [m for m in expected if not seen[mkey(m)] and not owners[mkey(m)]]
    unnecessary = [m for m in unassigned if any(counts.get(b, 0) < a.max for b in seen[mkey(m)])]
    if unassigned:
        lines += ["## Gefunden, aber nicht zugewiesen", "", "| Maschine | Box → Status (Grund) |", "|---|---|"]
        for m in unassigned:
            detail = "; ".join(f"{b}: {st}" + (f" ({why})" if why else "") for b, (st, why) in sorted(seen[mkey(m)].items()))
            lines.append(f"| {m['name']} | {detail} |")
        lines.append("")

    multi = [m["name"] for m in expected if len(owners[mkey(m)]) > 1]
    over = [b for b, c in counts.items() if c > a.max]
    checks = [
        (not multi, "Jede Maschine ist höchstens einer Box zugewiesen" + (f" – VERLETZT: {', '.join(multi)}" if multi else "")),
        (not over, f"Keine Box über dem Limit von {a.max}" + (f" – VERLETZT: {', '.join(over)}" if over else "")),
        (not unnecessary, "Keine Maschine unzugewiesen, solange eine sehende Box noch Kapazität hat" +
         (f" – VERLETZT: {', '.join(m['name'] for m in unnecessary)}" if unnecessary else
          (f" ({len(unassigned)} wegen Lizenzgrenze offen)" if unassigned else ""))),
    ]
    if ctx["soll_given"]:
        checks.append((not undiscovered, f"Alle {len(expected)} erwarteten Maschinen wurden entdeckt" +
                       (f" – NICHT entdeckt: {', '.join(m['name'] for m in undiscovered)}" if undiscovered else "")))
    tm = ctx.get("tenant_machines")
    if tm is not None:
        per_machine: dict[str, int] = {}
        for e in tm:
            m = match_machine(e, expected)
            if m:
                per_machine[mkey(m)] = per_machine.get(mkey(m), 0) + 1
        dups = [m["name"] for m in expected if per_machine.get(mkey(m), 0) > 1]
        checks.append((not dups, "Tenant-weite Maschinenliste ohne Duplikate" +
                       (f" – DUPLIKATE: {', '.join(dups)}" if dups else f" ({len(tm)} Einträge)")))
        if ctx["fresh"]:
            box_sum = sum(len(assign.get(b, [])) for b in sim_ids)
            checks.append((len(tm) == box_sum, f"Tenant-Liste ({len(tm)}) = Summe der Box-Listen ({box_sum})"))
    if ctx.get("db_boxes") is not None and ctx["fresh"]:
        checks.append((ctx["db_boxes"] == len(sim_ids),
                       f"System-DB: {ctx['db_boxes']} connector_boxes-Zeilen für den Tenant (erwartet {len(sim_ids)})"))
    if db_assign is not None:
        mism = [b for b in sim_ids if len(api_assign.get(b, [])) != len(db_assign.get(b, []))]
        checks.append((not mism, "Gateway-API und Tenant-DB stimmen pro Box überein" +
                       (f" – ABWEICHUNG: {', '.join(mism)}" if mism else "")))
        nomfr = [r["name"] for r in db_rows if not r["manufacturer"]]
        checks.append((not nomfr, "Hersteller (metadata.manufacturer) ist in der DB befüllt" +
                       (f" – LEER bei: {', '.join(nomfr)} (Payload-Feldnamen in to_payload() prüfen)" if nomfr else "")))
    checks.extend(ctx.get("probes", []))
    bff = ctx.get("bff")
    if bff is not None and bff["data"] is None:
        checks.append((False, f"Cockpit-API (BFF) erreichbar – HTTP {bff['code']}: Route /api/v1/shopfloor in Traefik, "
                              f"GATEWAY_URL am BFF und --bff-url prüfen (oder --bff-url off)"))
    elif bff is not None:
        ov_boxes = {b.get("hardware_id"): b for b in bff["data"].get("boxes", [])}
        wrong = [b for b in sim_ids if sorted(e.get("name") or "" for e in assign.get(b, []))
                 != sorted(m.get("name") or "" for m in ov_boxes.get(b, {}).get("machines", []))]
        shown = [m for bx in ov_boxes.values() for m in bx.get("machines", [])]
        no_mfr = [m.get("name") for m in shown if not m.get("manufacturer")]
        no_status = [m.get("name") for m in shown if m.get("status") not in ("ok", "warning", "error")]
        offline = [b for b in sim_ids if not ov_boxes.get(b, {}).get("online")]
        checks.append((not wrong, "Cockpit-API zeigt je Box dieselben Maschinen wie die Tenant-DB" +
                       (f" – ABWEICHUNG bei: {', '.join(wrong)}" if wrong else "")))
        checks.append((not no_mfr, "Cockpit-API liefert den Hersteller aller Maschinen" +
                       (f" – FEHLT bei: {', '.join(map(str, no_mfr))} (Feldnamen in normalize_machine prüfen)" if no_mfr else "")))
        checks.append((not no_status, "Alle Maschinen haben im Cockpit einen Status (ok/warning/error)" +
                       (f" – UNBEKANNT: {', '.join(map(str, no_status))} (lief das BFF schon während des Laufs? Meldet die Box den Status?)" if no_status else "")))
        checks.append((not offline, "Alle Boxen erscheinen im Cockpit als online" +
                       (f" – OFFLINE: {', '.join(offline)} (GET /v1/connector-boxes/status im Gateway vorhanden?)" if offline else "")))
    checks.append((ctx["stable"], "Stabil nach Folgezyklus (keine Änderung, keine Doppelregistrierung)"))
    lines += ["## Prüfungen", ""] + [f"- {'✅' if ok else '❌'} {txt}" for ok, txt in checks] + [""]

    lines += ["## Log-Auswertung", "", "| Box | Registriert | Vorab übersprungen (Fremdbesitz) | Vom Server abgelehnt | Limit-Meldungen | Fehler |", "|---|---|---|---|---|---|"]
    for b in sim_ids:
        s = ctx["logs"][b]
        lines.append(f"| {b} | {s['registriert']} | {s['fremd']} | {s['abgelehnt']} | {s['limit']} | {s['fehler']} |")
    lines.append("")

    notes = []
    if ctx["errors"]:
        notes.append("Maschinenliste nicht abrufbar: " + "; ".join(ctx["errors"]))
    if unknown:
        ex = next(iter(unknown.values()))[0]
        n = sum(len(v) for v in unknown.values())
        notes.append(f"{n} Server-Einträge ließen sich keiner Maschine zuordnen (Feldnamen?). Beispiel: `{json.dumps(ex)}`")
    if ctx["dead"]:
        notes.append("Box-Prozess vorzeitig beendet: " + ", ".join(ctx["dead"]) + " (siehe box.log)")
    if any(v is None for v in disc.values()):
        notes.append("Mind. eine Box hat keinen Discovered-Snapshot geschrieben (kein Zyklus abgeschlossen?).")
    if ctx.get("unresolved"):
        notes.append("box_id in der Tenant-DB nicht auf eine Hardware-ID auflösbar: " + ", ".join(sorted(ctx["unresolved"])))
    if db_rows and all(not r["machine_type"] for r in db_rows):
        notes.append("machine_type ist bei allen Maschinen leer – erwartet euer Register-Handler dieses Feld (der alte Poller hat es evtl. gesetzt)?")
    notes += ctx.get("probe_notes", [])
    if getattr(a, "restart_services", ""):
        notes.append("Dieser Lauf nutzte --restart-services (" + a.restart_services + "). Das verdeckt den bekannten Fehler: nach dem "
                     "Neuanlegen eines Tenants mit gleicher ID behalten die Services veraltete Tenant-Zugangsdaten. "
                     "Ohne das Flag muss die Pipeline durchlaufen, sobald der Fehler im Produkt behoben ist.")
    if notes:
        lines += ["## Hinweise", ""] + [f"- {n}" for n in notes] + [""]
    lines.append(f"Logs: `{ctx['state_root']}/<box>/box.log`")
    return "\n".join(lines), all(ok for ok, _ in checks)


# --------------------------------------------------------------------------- Main
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tenant", nargs="?", default="schwarzwald-metallwaren", help="Tenant-ID (Std wie run_e2e_pipeline.sh)")
    ap.add_argument("--gateway", default="http://localhost:8080")
    ap.add_argument("--boxes", type=int, default=2)
    ap.add_argument("--box-prefix", default="sim-box-", help="Hardware-IDs: <prefix>01, <prefix>02 ...")
    ap.add_argument("--max", type=int, default=5, help="Lizenzlimit pro Box")
    ap.add_argument("--shopfloor", default=None, help="Soll aus shopfloor.yaml")
    ap.add_argument("--expected-file", default=None, help="Soll aus JSON-Datei")
    ap.add_argument("--scan-cidr", default="127.0.0.1/32",
                    help="Sim: Maschinen sind auf Loopback veröffentlicht. 'auto' = Boxen erkennen das Netz selbst")
    ap.add_argument("--scan-ports", default=None, help="z.B. 4840-4850 (Std: aus Soll abgeleitet, sonst 4840-4850)")
    ap.add_argument("--script", default=str(HERE / "opc_discovery.py"))
    ap.add_argument("--interval", type=int, default=15, help="Scan-Intervall der Boxen in Sekunden")
    ap.add_argument("--stagger", type=int, default=0, help="Sekunden Versatz zwischen Box-Starts (0 = gleichzeitig)")
    ap.add_argument("--timeout", type=int, default=180)
    ap.add_argument("--settle", type=int, default=None, help="Wartezeit für Stabilitätscheck (Std: interval+5)")
    ap.add_argument("--provision-timeout", type=int, default=240)
    ap.add_argument("--provision-quiet", type=int, default=30,
                    help="Sekunden Ruhe nach POST /v1/tenants ohne Zugriff auf den Tenant (Std 30, wie run_e2e_pipeline.sh)")
    ap.add_argument("--state-dir", default=str(HERE / "sim_state"))
    ap.add_argument("--keep-state", action="store_true", help="lokalen Box-State nicht löschen")
    ap.add_argument("--keep-pollers", action="store_true", help="alte Poller-Container NICHT stoppen")
    ap.add_argument("--reuse-tenant", action="store_true", help="kein Aufräumen/Provisionieren, Tenant existiert bereits")
    ap.add_argument("--bff-url", default="http://localhost:8888",
                    help="Basis-URL des Cockpit-BFF (über Traefik); 'off' = Prüfung überspringen")
    ap.add_argument("--no-probes", action="store_true", help="Backend-Negativtests (Exklusivität/Limit) überspringen")
    ap.add_argument("--plan", action="store_true", help="nur Inventur des Aufräumens zeigen, nichts verändern")
    ap.add_argument("--yes", action="store_true", help="Löschen ohne Rückfrage bestätigen (für CI)")
    ap.add_argument("--restart-services", default="",
                    help="Container, die nach dem Aufräumen und vor der Provisionierung neu gestartet werden, z.B. "
                         "machine-query-service,machine-command-service (Workaround für veraltete Tenant-Verbindungen)")
    ap.add_argument("--purge-rabbitmq", action="store_true",
                    help="auch RabbitMQ-vhosts/-User des Tenants löschen (Std: aus; kann laufende Services stören)")
    ap.add_argument("--rabbit-url", default="http://localhost:15672")
    ap.add_argument("--rabbit-admin", default="uretos:uretos_dev_pass", help="user:passwort (Dev-Default aus docker-compose.yml)")
    a = ap.parse_args()
    tenant = a.tenant
    settle = a.interval + 5 if a.settle is None else a.settle
    pipeline: list[str] = []

    print("=" * 60 + f"\n  uretOS E2E Pipeline (Box-Simulation) - Tenant: {tenant}\n" + "=" * 60)

    # ---- [0] Preflight (VOR dem Löschen, damit ein Fehler hier nichts zerstört)
    print("[0/5] Preflight ...")
    if not TENANT_RE.match(tenant):
        print("❌ Tenant-ID muss ^[a-z0-9][a-z0-9_-]{2,62}$ entsprechen")
        return 2
    try:
        import opcua  # noqa: F401
    except ImportError:
        print("❌ Modul 'opcua' fehlt:  pip install opcua zeroconf psutil")
        return 2
    if not Path(a.script).exists():
        print(f"❌ {a.script} nicht gefunden")
        return 2

    expected: list[dict] | None = None
    if a.shopfloor:
        expected, soll_src = load_expected_yaml(Path(a.shopfloor)), f"shopfloor.yaml ({a.shopfloor})"
    elif a.expected_file:
        expected, soll_src = load_expected_json(Path(a.expected_file)), f"JSON ({a.expected_file})"
    else:
        soll_src = "Discovery-Modus (Soll = von den Boxen gefundene Maschinen)"
    if expected is not None and not expected:
        print("❌ Soll-Datei enthält keine Maschinen")
        return 2

    try:
        http(a.gateway, "GET", "/healthz", timeout=5)
    except Exception as exc:
        print(f"❌ Gateway {a.gateway} nicht erreichbar ({exc}) – läuft 'docker compose up -d'?")
        return 2
    if expected and not a.plan:
        down = [m for m in expected if m["port"] and not port_open(m["port"])]
        if down:
            print("❌ Maschinen nicht erreichbar: " + ", ".join(f"{m['name']}:{m['port']}" for m in down))
            print("   -> docker compose up -d   (Ports müssen auf dem Host veröffentlicht sein)")
            return 2
    docker_ok = sh(["docker", "version", "--format", "{{.Server.Version}}"])[0] == 0
    if not a.reuse_tenant and not docker_ok:
        print("❌ Docker nicht verfügbar – für das Aufräumen nötig (oder --reuse-tenant)")
        return 2
    print(f"  ✓ Gateway ok | Soll: {soll_src}")

    # ---- [1/5] Aufräumen
    print("[1/5] Aufräumen ...")
    t_clean = time.time()
    if not a.reuse_tenant:
        inv = build_inventory(tenant, a)
        if inv["db"] is None:
            print(f"❌ System-DB nicht abfragbar (läuft {SYSTEM_PG}?)")
            return 2
        if a.plan:
            print("  Inventur (--plan, es wird NICHTS verändert):")
            print_inventory(inv) if not inventory_empty(inv) else print("    nichts aufzuräumen")
            return 0
        if not inventory_empty(inv):
            print(f"  Für Tenant '{tenant}' gefunden:")
            print_inventory(inv)
            if not a.yes:
                if not sys.stdin.isatty():
                    print("❌ Nicht-interaktiv: mit --yes bestätigen (oder --plan zum Ansehen)")
                    return 2
                if input("  Unwiderruflich löschen? Zur Bestätigung Tenant-ID eingeben: ").strip() != tenant:
                    print("  abgebrochen")
                    return 2
    elif a.plan:
        print("  --plan hat mit --reuse-tenant nichts zu tun (es wird nichts aufgeräumt)")
        return 0

    if not a.reuse_tenant:
        if inventory_empty(inv):
            note = "Aufräumen: nichts vorhanden"
        else:
            ok, summary, after = cleanup_tenant(tenant, a, inv)
            note = f"Aufräumen: {summary}"
            if not ok:
                print(f"❌ Aufräumen unvollständig: {summary}")
                print("   Verbleibend:")
                print_inventory(after)
                return 2
        pipeline.append(f"{note} ({time.time() - t_clean:.0f}s)")
        print(f"  ✓ {note}")
    state_root = Path(a.state_dir)
    state_root.mkdir(parents=True, exist_ok=True)
    sim_ids = [f"{a.box_prefix}{i:02d}" for i in range(1, a.boxes + 1)]
    for b in sim_ids:
        d = state_root / b
        if d.exists() and not a.keep_state:
            shutil.rmtree(d)

    # ---- [2/5] Tenant provisionieren
    if a.restart_services and not a.reuse_tenant:
        names = [n if n.startswith("uretos-") else f"uretos-{n}" for n in a.restart_services.split(",") if n.strip()]
        rc, _, err = sh(["docker", "restart", *names], timeout=180)
        if rc != 0:
            print(f"❌ Neustart fehlgeschlagen: {err.strip()[:200]}")
            return 2
        pipeline.append(f"Services neu gestartet (WORKAROUND, siehe Hinweise): {', '.join(names)}")
        print(f"  ✓ neu gestartet: {', '.join(names)} (warte 8s)")
        time.sleep(8)
    print("[2/5] Tenant provisionieren ...")
    if a.reuse_tenant:
        print("  übersprungen (--reuse-tenant)")
        pipeline.append("Tenant wiederverwendet (kein Aufräumen, keine Provisionierung)")
    else:
        t_prov = time.time()
        try:
            existing = provision_tenant(a.gateway, tenant, a.provision_timeout, docker_ok, a.provision_quiet)
        except RuntimeError as exc:
            print(f"❌ {exc}")
            return 2
        if existing:
            print(f"❌ Frischer Tenant hat bereits {existing} Maschine(n) – Alt-Daten in der Tenant-DB, die das "
                  f"Aufräumen nicht gefunden hat (Ressourcen heißen anders als die Tenant-ID?). Manuell bereinigen.")
            return 2
        pipeline.append(f"Tenant provisioniert, Tenant-DB leer und erreichbar nach {time.time() - t_prov:.0f}s")
        print(f"  ✓ bereit nach {time.time() - t_prov:.0f}s, Maschinenliste leer")

    # ---- [3/5] Boxen anlegen + pairen
    if not a.keep_pollers:  # wie in run_e2e_pipeline.sh: alte Poller laufen bis NACH der Provisionierung weiter
        pollers = [c for c in running_containers() if c in OLD_POLLERS]
        if pollers:
            sh(["docker", "stop", *pollers])
            pipeline.append(f"Alte Poller gestoppt (nach der Provisionierung): {', '.join(pollers)}")
            print(f"  ✓ alte Poller gestoppt: {', '.join(pollers)}")
    print("[3/5] Boxen anlegen und pairen ...")
    try:
        for b in sim_ids:
            note = ensure_box(a.gateway, b, tenant)
            pipeline.append(f"{b}: {note}")
            print(f"  ✓ {b}: {note}")
    except RuntimeError as exc:
        print(f"❌ {exc}")
        return 2
    baseline, _ = fetch_assignments(a.gateway, all_box_ids(a.gateway, sim_ids))
    for b, v in baseline.items():
        if v:
            print(f"  Ausgangslage: {b} besitzt bereits {len(v)} Maschine(n)")
    other_owned: set[str] = set()
    if expected:
        base_owners, _ = owners_from(baseline, expected)
        other_owned = {k for k, bs in base_owners.items() if bs - set(sim_ids)}

    # ---- [4/5] Boxen starten
    ports = a.scan_ports
    if not ports:
        pp = [m["port"] for m in (expected or []) if m.get("port")]
        ports = f"{min(pp)}-{max(pp) + 3}" if pp else "4840-4850"
    procs: dict[str, subprocess.Popen] = {}
    logs_f = {}
    for b in sim_ids:
        (state_root / b).mkdir(parents=True, exist_ok=True)
        logs_f[b] = open(state_root / b / "box.log", "w")
    print(f"[4/5] Starte {len(sim_ids)} Boxen {'gleichzeitig' if not a.stagger else f'versetzt um {a.stagger}s'} "
          f"(Intervall {a.interval}s, Ports {ports}) ...")
    t0 = time.time()
    for i, b in enumerate(sim_ids):
        if i and a.stagger:
            time.sleep(a.stagger)
        env = {
            **os.environ, "PYTHONUNBUFFERED": "1", "BOX_HARDWARE_ID": b, "GATEWAY_URL": a.gateway,
            "SCAN_PORTS": ports, "STATE_DIR": str(state_root / b), "MAX_MACHINES": str(a.max),
            "SCAN_INTERVAL_SECONDS": str(a.interval), "RETRY_REJECTED_SECONDS": str(a.interval * 2),
        }
        if a.scan_cidr != "auto":
            env["SCAN_CIDR"] = a.scan_cidr
        procs[b] = subprocess.Popen([sys.executable, a.script], env=env, stdout=logs_f[b], stderr=subprocess.STDOUT)

    reason, dead, stable = "Timeout", [], True
    last_sig, last_change = None, time.time()
    assign: dict[str, list] = {}
    errors: list[str] = []
    try:
        while True:
            time.sleep(5)
            assign, errors = fetch_assignments(a.gateway, sim_ids)
            disc = read_discovered(state_root, sim_ids)
            exp = expected or expected_from_discovered(disc)
            owners, _ = owners_from(assign, exp)
            assigned = {k for k, bs in owners.items() if bs}
            sig = (tuple(sorted((b, len(v)) for b, v in assign.items())), tuple(sorted(assigned)),
                   tuple(sorted((b, tuple(sorted(e["uid"] for e in (v or [])))) for b, v in disc.items())))
            if sig != last_sig:
                last_sig, last_change = sig, time.time()
            idle = time.time() - last_change
            print(f"  t={time.time() - t0:3.0f}s  " + "  ".join(f"{b}: {len(v)}" for b, v in assign.items())
                  + f"  → {len(assigned)}/{len(exp)} zugewiesen")
            dead = [b for b, p in procs.items() if p.poll() is not None]
            if len(dead) == len(procs):
                reason = "alle Box-Prozesse beendet"
                break
            if expected and len(assigned | other_owned) >= len(expected):
                reason = "alle erwarteten Maschinen zugewiesen"
                break
            cycles_done = all(v is not None for v in disc.values())
            if (cycles_done and idle > a.interval + 10) or idle > 3 * a.interval + 15:
                reason = "keine Änderung mehr"
                break
            if time.time() - t0 > a.timeout:
                break

        if settle > 0 and len(dead) < len(procs):
            print(f"  ▶ Stabilitätscheck ({settle}s) ...")
            before = {b: log_stats(state_root / b / "box.log")["registriert"] for b in sim_ids}
            time.sleep(settle)
            after, errors = fetch_assignments(a.gateway, sim_ids)
            stable = ({b: len(v) for b, v in after.items()} == {b: len(v) for b, v in assign.items()}
                      and before == {b: log_stats(state_root / b / "box.log")["registriert"] for b in sim_ids})
            assign = after
    except KeyboardInterrupt:
        reason, stable = "abgebrochen (Ctrl+C)", False
    finally:
        for p in procs.values():
            if p.poll() is None:
                p.send_signal(signal.SIGTERM)
        for p in procs.values():
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()
        for f in logs_f.values():
            f.close()

    # ---- [5/5] Validierung + Report
    print("[5/5] Validierung ...")
    boxmap = box_name_map(a.gateway)
    final_all, errs2 = fetch_assignments(a.gateway, all_box_ids(a.gateway, sim_ids))
    disc = read_discovered(state_root, sim_ids)
    exp_final = expected or expected_from_discovered(disc)
    db_rows = tenant_db_machines(tenant) if docker_ok else None
    db_assign, unresolved = group_rows(db_rows, boxmap, sim_ids) if db_rows is not None else (None, set())
    code, tdata = http(a.gateway, "GET", f"/v1/machines?tenant_id={urllib.parse.quote(tenant)}")
    tenant_machines = tdata if code == 200 and isinstance(tdata, list) else None
    db_boxes = None
    if docker_ok:
        rc, out, _ = psql(f"SELECT count(*) FROM connector_boxes WHERE tenant_id='{tenant}'")
        db_boxes = int(out.strip()) if rc == 0 and out.strip().isdigit() else None
    bff = None
    if a.bff_url != "off":
        try:
            bcode, bdata = http(a.bff_url, "GET", f"/api/v1/shopfloor?tenant_id={urllib.parse.quote(tenant)}", timeout=20)
        except Exception as exc:
            bcode, bdata = 0, str(exc)
        bff = {"code": bcode, "data": bdata if bcode == 200 and isinstance(bdata, dict) else None}
    probes: list[tuple[bool, str]] = []
    probe_notes: list[str] = []
    if not a.no_probes:
        print("  ▶ Backend-Probes (Exklusivität + Limit direkt gegen den Server) ...")
        probes, probe_notes = run_probes(a, tenant, db_assign if db_assign is not None else final_all,
                                         disc, exp_final, sim_ids, docker_ok)
    ctx = {
        "args": a, "tenant": tenant, "fresh": not a.reuse_tenant, "pipeline": pipeline,
        "expected": exp_final, "soll_given": expected is not None,
        "soll_src": soll_src, "sim_ids": sim_ids, "assign": final_all, "disc": disc, "errors": errors + errs2,
        "tenant_machines": tenant_machines, "db_boxes": db_boxes, "db_rows": db_rows, "db_assign": db_assign,
        "boxmap": boxmap, "unresolved": unresolved, "bff": bff, "probes": probes, "probe_notes": probe_notes,
        "local": {b: read_machines(state_root / b / "assigned_machines.json") or [] for b in sim_ids},
        "duration": time.time() - t0, "reason": reason, "stable": stable,
        "logs": {b: log_stats(state_root / b / "box.log") for b in sim_ids},
        "dead": dead, "state_root": str(state_root),
    }
    report, ok = build_report(ctx)
    path = state_root / f"sim_report_{datetime.now():%Y%m%d_%H%M%S}.md"
    path.write_text(report)
    print("\n" + report + f"\n\n📄 Report gespeichert: {path}")
    print("=" * 60 + f"\n  {'[SUCCESS] E2E Pipeline erfolgreich abgeschlossen!' if ok else '[FAILED] Prüfungen fehlgeschlagen (siehe Report)'}\n" + "=" * 60)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
