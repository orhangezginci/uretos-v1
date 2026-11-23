#!/usr/bin/env python3
"""
uretOS Connector Box - OPC-UA Auto-Discovery & Registrierung über die gateway-api

Läuft nativ auf der Box (systemd, ab Boot). Ablauf:
  1. Handshake mit dem Gateway (Box muss angelegt + gepairt sein)
  2. Alle SCAN_INTERVAL Sekunden: Kandidaten finden (mDNS + TCP-Portscan), per OPC-UA identifizieren
     (DI/Machinery: DeviceSet -> Identification)
  3. Maschinen, die laut Tenant-Liste (GET /v1/machines) bereits einer ANDEREN Box gehören, überspringen;
     alle übrigen EINZELN über POST /v1/connector-boxes/autoscan registrieren, bis MAX_MACHINES erreicht
  3b. Status der zugewiesenen Maschinen melden (erreichbar = ok, sonst error/UNREACHABLE)
  4. ALLE gefundenen Maschinen (auch nicht zugewiesene, mit Status + Grund) als Snapshot an das Gateway melden
     (POST /v1/connector-boxes/discovered) und nach STATE_DIR/discovered_machines.json schreiben
  5. Zugewiesene Maschinen nach STATE_DIR/assigned_machines.json schreiben

Zusätzlich: ein Heartbeat-Thread meldet der Box alle HEARTBEAT_SECONDS den Status 'connected' an das Gateway,
unabhängig vom Scan-Zyklus. Damit bleibt der Gateway-Status aktuell (Box gilt als online), auch wenn
SCAN_INTERVAL größer ist als das Online-Fenster des Cockpits/BFF.

Box-Status-Werte (GET/POST /v1/connector-boxes/status):
  - 'scanning'  : Box scannt gerade das Netz (vom Scan-Zyklus gesetzt, für active-scan-Entzerrung)
  - 'connected' : Box lebt und ist mit dem Gateway verbunden (Heartbeat + Ende jedes Scan-Zyklus)
Maschinenstatus ('idle'/'warning'/'error'/'emergency_stop') werden über einen anderen Endpoint gemeldet
(PATCH /v1/machines/<id>/status) und haben im Box-Status nichts zu suchen.

WICHTIG: Exklusivität (1 Maschine = 1 Box) und das Lizenzlimit MÜSSEN vom Backend (machine-command-service)
erzwungen werden. Die Prüfungen hier (Tenant-Liste, eigenes Limit) sind nur Vorabprüfungen: sie sind nicht
atomar (zwei Boxen, die gleichzeitig starten, können sich überholen) und schützen die Lizenz nicht gegen
einen anderen oder fehlerhaften Client.

Abhängigkeiten: pip install opcua zeroconf psutil   (zeroconf und psutil sind optional)
"""
from __future__ import annotations

import ipaddress
import json
import logging
import os
import random
import signal
import socket
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from opcua import Client

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("opc-discovery")


# --------------------------------------------------------------------------- Config
def _ports(spec: str) -> list[int]:
    ports: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            ports.extend(range(int(a), int(b) + 1))
        elif part:
            ports.append(int(part))
    return sorted(set(ports))


BOX_ID = os.environ.get("BOX_HARDWARE_ID", f"box-{uuid.getnode():012x}")
GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://gateway-api:8080").rstrip("/")
AUTO_PAIR = os.environ.get("AUTO_PAIR", "false").lower() == "true"
MAX_MACHINES = int(os.environ.get("MAX_MACHINES", "5"))
SCAN_CIDR = os.environ.get("SCAN_CIDR", "")  # z.B. "192.168.10.0/24" oder "127.0.0.1/32"
SCAN_PORTS = _ports(os.environ.get("SCAN_PORTS", "4840"))
SCAN_INTERVAL = int(os.environ.get("SCAN_INTERVAL_SECONDS", "60"))
RETRY_REJECTED_SECONDS = int(os.environ.get("RETRY_REJECTED_SECONDS", "600"))
CONNECT_TIMEOUT = float(os.environ.get("PORT_TIMEOUT_SECONDS", "0.4"))
MAX_SCAN_HOSTS = 1024  # Sicherheitsgrenze, größere Netze werden auf /24 reduziert
STATE_DIR = Path(os.environ.get("STATE_DIR", "/var/lib/uretos/connector-box"))
HEARTBEAT_SECONDS = int(os.environ.get("HEARTBEAT_SECONDS", "30"))

URI_DI = "http://opcfoundation.org/UA/DI/"
LIMIT_HINTS = ("limit", "maximum", "max ", "lizenz", "license", "quota")
stop = threading.Event()


# --------------------------------------------------------------------------- Modell
@dataclass
class Machine:
    uid: str  # stabile Identität (NICHT die IP, DHCP kann sich ändern)
    endpoint: str
    name: str
    manufacturer: str
    model: str
    serial: str
    strong_identity: bool


def to_payload(m: Machine) -> dict:
    """ANNAHME: Feldnamen für uretos.machine.command.register - mit dem machine-command-service abgleichen!"""
    return {
        "machine_id": m.uid,  # stabile Identität; ohne dieses Feld nimmt der Server den Namen (nicht eindeutig!)
        "name": m.name,
        "manufacturer": m.manufacturer,
        "model": m.model,
        "serial_number": m.serial,
        "endpoint_url": m.endpoint,
        "product_instance_uri": m.uid if m.strong_identity else None,
    }


def discovered_entry(m: Machine, state: str, reason: str) -> dict:
    """Eintrag des Discovered-Reports. state: assigned | limit | rejected"""
    return {"uid": m.uid, **to_payload(m), "state": state, "reason": reason}


def _text(v) -> str:
    return str(getattr(v, "Text", v) or "").strip()


# --------------------------------------------------------------------------- Discovery
def _local_networks() -> list[tuple[str, ipaddress.IPv4Network]]:
    """Liefert (eigene IP, Netz) Paare."""
    if SCAN_CIDR:
        return [("", ipaddress.ip_network(c.strip(), strict=False)) for c in SCAN_CIDR.split(",")]
    result: list[tuple[str, ipaddress.IPv4Network]] = []
    try:
        import psutil

        for iface, addrs in psutil.net_if_addrs().items():
            if iface.startswith(("lo", "docker", "br-", "veth")):
                continue
            for a in addrs:
                if a.family == socket.AF_INET and a.netmask:
                    result.append((a.address, ipaddress.ip_network(f"{a.address}/{a.netmask}", strict=False)))
    except ImportError:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("10.255.255.255", 1))
            ip = s.getsockname()[0]
            result.append((ip, ipaddress.ip_network(f"{ip}/24", strict=False)))
        except OSError:
            pass
        finally:
            s.close()
    return result


def _port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(CONNECT_TIMEOUT)
        return s.connect_ex((host, port)) == 0


def scan_ports() -> set[tuple[str, int]]:
    targets: list[tuple[str, int]] = []
    for own_ip, net in _local_networks():
        if net.num_addresses > MAX_SCAN_HOSTS:
            if not own_ip:
                log.warning("SCAN_CIDR %s ist zu groß (>%d Hosts), übersprungen", net, MAX_SCAN_HOSTS)
                continue
            net = ipaddress.ip_network(f"{own_ip}/24", strict=False)
            log.warning("Netz zu groß, reduziere Scan auf %s", net)
        hosts = list(net.hosts()) or [net.network_address]
        for h in hosts:
            if str(h) == own_ip:
                continue
            for p in SCAN_PORTS:
                targets.append((str(h), p))
    if not targets:
        return set()
    log.info("Portscan: %d Ziele", len(targets))
    with ThreadPoolExecutor(max_workers=128) as pool:
        flags = list(pool.map(lambda t: _port_open(*t), targets))
    return {t for t, ok in zip(targets, flags) if ok}


def scan_mdns(timeout: float = 4.0) -> set[tuple[str, int]]:
    try:
        from zeroconf import ServiceBrowser, Zeroconf
    except ImportError:
        return set()
    names: list[str] = []

    class Listener:
        def add_service(self, zc, type_, name):
            names.append(name)

        def update_service(self, zc, type_, name):
            pass

        def remove_service(self, zc, type_, name):
            pass

    found: set[tuple[str, int]] = set()
    zc = Zeroconf()
    try:
        ServiceBrowser(zc, "_opcua-tcp._tcp.local.", Listener())
        time.sleep(timeout)
        for name in names:
            info = zc.get_service_info("_opcua-tcp._tcp.local.", name, timeout=2000)
            if info and info.port:
                for addr in info.parsed_addresses():
                    found.add((addr, info.port))
    except Exception as exc:
        log.debug("mDNS Fehler: %s", exc)
    finally:
        zc.close()
    return found


def identify(host: str, port: int) -> list[Machine]:
    """Verbindet per OPC-UA und liest DI/Machinery Identification. Leere Liste = kein OPC-UA Server."""
    endpoint = f"opc.tcp://{host}:{port}"
    client = Client(endpoint, timeout=4)
    try:
        client.connect()
    except Exception as exc:
        log.debug("%s: kein OPC-UA (%s)", endpoint, exc)
        return []

    machines: list[Machine] = []
    try:
        try:
            idx = client.get_namespace_index(URI_DI)
            deviceset = client.get_objects_node().get_child([f"{idx}:DeviceSet"])
            for node in deviceset.get_children():
                try:
                    ident = node.get_child([f"{idx}:Identification"])
                except Exception:
                    continue
                vals: dict[str, str] = {}
                for key in ("Manufacturer", "Model", "SerialNumber", "ProductInstanceUri"):
                    try:
                        vals[key] = _text(ident.get_child([f"{idx}:{key}"]).get_value())
                    except Exception:
                        vals[key] = ""
                name = node.get_browse_name().Name
                if vals["ProductInstanceUri"]:
                    uid, strong = vals["ProductInstanceUri"], True
                elif vals["Manufacturer"] and vals["SerialNumber"]:
                    uid, strong = f"{vals['Manufacturer']}:{vals['Model']}:{vals['SerialNumber']}", True
                else:
                    uid, strong = f"endpoint:{host}:{port}/{name}", False
                machines.append(
                    Machine(uid, endpoint, name, vals["Manufacturer"], vals["Model"], vals["SerialNumber"], strong)
                )
        except Exception as exc:
            log.debug("%s: kein DeviceSet (%s)", endpoint, exc)

        if not machines:  # OPC-UA Server ohne DI-Struktur -> schwache Identität über Endpoint
            machines.append(Machine(f"endpoint:{host}:{port}", endpoint, endpoint, "", "", "", False))
    finally:
        try:
            client.disconnect()
        except Exception:
            pass
    return machines


def discover() -> dict[str, Machine]:
    candidates = scan_mdns() | scan_ports()
    log.info("%d Kandidaten (mDNS + Portscan)", len(candidates))
    with ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(lambda t: identify(*t), sorted(candidates)))
    machines: dict[str, Machine] = {}
    for lst in results:
        for m in lst:
            machines.setdefault(m.uid, m)  # dedupe: gleiche Maschine über mehrere IPs/mDNS
    return machines


# --------------------------------------------------------------------------- Gateway-Client
class Gateway:
    """Dünner Client für die gateway-api. HTTP-Fehlercodes werden zurückgegeben, nicht geworfen;
    nur Netzwerkfehler (Gateway nicht erreichbar) werfen."""

    report_enabled = True
    tenant_id: str | None = None
    box_uuid: str | None = None

    def _req(self, method: str, path: str, body: dict | None = None):
        req = urllib.request.Request(
            GATEWAY_URL + path, method=method, headers={"Content-Type": "application/json"},
            data=json.dumps(body).encode() if body is not None else None,
        )
        try:  # Gateway-RPC-Timeout ist 60 s -> etwas länger warten
            with urllib.request.urlopen(req, timeout=70) as r:
                return r.status, json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            try:
                return e.code, json.loads(e.read() or b"{}")
            except ValueError:
                return e.code, {}

    def handshake(self):
        return self._req("POST", "/v1/connector-boxes/handshake", {"hardware_id": BOX_ID})

    def pair(self):
        return self._req("POST", "/v1/connector-boxes/pair", {"hardware_id": BOX_ID})

    def tenant_machines(self) -> list[dict] | None:
        """Alle Maschinen des Tenants (aller Boxen). None = nicht verfügbar."""
        if not self.tenant_id:
            return None
        code, data = self._req("GET", f"/v1/machines?tenant_id={urllib.parse.quote(self.tenant_id)}")
        return data if code == 200 and isinstance(data, list) else None

    def list_machines(self) -> list[dict]:
        code, data = self._req("GET", f"/v1/connector-boxes/{BOX_ID}/machines")
        if code != 200 or not isinstance(data, list):
            raise RuntimeError(f"Maschinenliste nicht abrufbar (HTTP {code})")
        return data

    def register(self, m: Machine) -> tuple[str, str]:
        """Registriert genau EINE Maschine. Rückgabe: ('ok'|'rejected'|'limit'|'notpaired', reason).
        Wirft bei 5xx/504 (transient)."""
        code, data = self._req(
            "POST", "/v1/connector-boxes/autoscan", {"hardware_id": BOX_ID, "machines": [to_payload(m)]}
        )
        reason = str(data.get("error", "")) if isinstance(data, dict) else ""
        error_code = data.get("error_code") if isinstance(data, dict) else None
        if code == 200:
            return "ok", ""
        if code in (400, 409):  # 409 + error_code (neu); ältere Gateways liefern 400 ohne Code -> Textheuristik
            if error_code == "box_limit_reached" or (not error_code and any(h in reason.lower() for h in LIMIT_HINTS)):
                return "limit", reason
            return "rejected", reason
        if code in (403, 404):
            return "notpaired", reason
        raise RuntimeError(f"Gateway HTTP {code}: {reason}")

    def set_status(self, status: str) -> None:
        try:
            self._req("POST", "/v1/connector-boxes/status", {"hardware_id": BOX_ID, "status": status})
        except Exception as exc:
            log.debug("Status-Update fehlgeschlagen: %s", exc)

    def report_discovered(self, entries: list[dict]) -> None:
        """Best effort: meldet ALLE gefundenen Maschinen inkl. Zuweisungsstatus (Snapshot).
        Darf den Scan-/Zuweisungsprozess nie stören; ältere Gateways ohne den Endpoint werden erkannt."""
        if not self.report_enabled:
            return
        try:
            code, data = self._req("POST", "/v1/connector-boxes/discovered",
                                   {"hardware_id": BOX_ID, "machines": entries})
        except Exception as exc:
            log.debug("Discovered-Report fehlgeschlagen: %s", exc)
            return
        if code == 404 and not (isinstance(data, dict) and data.get("error")):
            log.info("Gateway kennt /discovered nicht - Discovered-Report deaktiviert")
            self.report_enabled = False
        elif code not in (200, 202):
            log.warning("Discovered-Report abgelehnt (HTTP %d): %s", code, data)

    def report_machine_status(self, machine_id: str, status: str, error_code: str | None) -> None:
        """Meldet den Status einer ZUGEWIESENEN Maschine (ok | warning | error) -> Event status_changed. Best effort."""
        if not self.tenant_id:
            return
        try:
            code, data = self._req("PATCH", f"/v1/machines/{urllib.parse.quote(machine_id, safe='')}/status",
                                   {"status": status, "error_code": error_code, "tenant_id": self.tenant_id})
            if code != 200:
                log.debug("Statusmeldung für %s abgelehnt (HTTP %d): %s", machine_id, code, data)
        except Exception as exc:
            log.debug("Statusmeldung für %s fehlgeschlagen: %s", machine_id, exc)

    def active_scanner(self) -> str | None:
        try:
            code, data = self._req("GET", "/v1/connector-boxes/active-scan")
            return data.get("active_scanner") if code == 200 else None
        except Exception:
            return None


# --------------------------------------------------------------------------- Heartbeat
def heartbeat_loop(gw: Gateway, stop_event: threading.Event) -> None:
    """Meldet der Box unabhängig vom Scan-Zyklus alle HEARTBEAT_SECONDS den Status 'connected'.
    Damit bleibt der Gateway-Status aktuell (Box gilt als online), auch wenn der Scan-Zyklus
    länger dauert als das Online-Fenster des Cockpits/BFF oder ein Zyklus übersprungen wird.

    'scanning' wird hier NICHT gesendet - das bleibt dem Scan-Zyklus vorbehalten (active-scan-
    Entzerrung). 'idle'/'warning'/'error'/'emergency_stop' sind MASCHINENstatus und werden über
    PATCH /v1/machines/<id>/status gemeldet, nicht als Box-Status.

    Fehler sind unkritisch: ein verlorener Heartbeat darf den Scan nicht stören."""
    log.info("Heartbeat-Thread gestartet (alle %ds, Status 'connected')", HEARTBEAT_SECONDS)
    while not stop_event.is_set():
        try:
            gw.set_status("connected")
        except Exception as exc:
            log.debug("Heartbeat fehlgeschlagen: %s", exc)
        stop_event.wait(HEARTBEAT_SECONDS)
    log.info("Heartbeat-Thread beendet")


# --------------------------------------------------------------------------- Hauptlogik
def ensure_ready(gw: Gateway) -> bool:
    code, data = gw.handshake()
    if code == 200:
        gw.tenant_id, gw.box_uuid = data.get("tenant_id"), data.get("box_id")
        return True
    if code == 403 and AUTO_PAIR:
        pcode, pdata = gw.pair()
        log.info("Auto-Pairing: HTTP %d %s", pcode, pdata)
        return pcode == 200
    log.warning("Box noch nicht bereit (HTTP %d: %s) - warte auf Anlage/Pairing", code, data.get("error", ""))
    return False


def _values(o):
    if isinstance(o, dict):
        for v in o.values():
            yield from _values(v)
    elif isinstance(o, (list, tuple)):
        for v in o:
            yield from _values(v)
    elif o is not None:
        yield str(o)


def foreign_owner(m: Machine, entries: list[dict], my_ids: set[str]) -> str | None:
    """Box, der die Maschine laut Tenant-Liste bereits gehört (None = frei oder meine). Zuordnung über uid/Seriennr./Name."""
    for e in entries:
        vals = set(_values(e))
        if m.uid in vals or (m.serial and m.serial in vals) or m.name in vals:
            owner = str(e.get("box_id") or e.get("hardware_id") or "unbekannt") if isinstance(e, dict) else "unbekannt"
            if owner not in my_ids:
                return owner
    return None


_foreign_logged: set[str] = set()


def wait_for_turn(gw: Gateway) -> None:
    """Weiche Entzerrung: wenn eine andere Box gerade scannt, kurz warten. KEIN echter Lock (check-then-set)."""
    for _ in range(6):
        other = gw.active_scanner()
        if other in (None, BOX_ID) or stop.is_set():
            return
        log.info("Box %s scannt gerade, warte kurz", other)
        stop.wait(random.uniform(5, 15))


def load_state() -> dict[str, dict]:
    try:
        data = json.loads((STATE_DIR / "assigned_machines.json").read_text())
        return {m["uid"]: m for m in data.get("machines", [])}
    except (OSError, ValueError, KeyError):
        return {}


def _write_state(filename: str, payload: dict) -> None:
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        tmp = STATE_DIR / (filename + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2))
        tmp.replace(STATE_DIR / filename)
    except OSError as exc:
        log.warning("State %s konnte nicht geschrieben werden: %s", filename, exc)


def save_state(mine: dict[str, dict]) -> None:
    _write_state("assigned_machines.json", {"box": BOX_ID, "machines": list(mine.values())})


def save_discovered(entries: list[dict]) -> None:
    _write_state("discovered_machines.json", {
        "box": BOX_ID, "updated_at": datetime.now(timezone.utc).isoformat(), "machines": entries,
    })


def cycle(gw: Gateway, mine: dict[str, dict], skip_until: dict[str, tuple[float, str]]) -> None:
    wait_for_turn(gw)
    gw.set_status("scanning")  # Box-Status: scannt gerade (für active-scan-Entzerrung)
    try:
        found = discover()
    finally:
        gw.set_status("connected")  # Box-Status: lebt und ist mit dem Gateway verbunden
    log.info("%d OPC-UA Maschine(n) im Netz gefunden", len(found))

    # Was das Backend bereits für diese Box kennt (Feldnamen der Antwort sind eine ANNAHME)
    server = gw.list_machines()
    server_keys = {
        str(e[k]) for e in server if isinstance(e, dict)
        for k in ("product_instance_uri", "uid", "serial_number", "serial") if e.get(k)
    }
    for uid, m in found.items():
        if uid in server_keys or m.serial in server_keys:
            mine[uid] = asdict(m)  # bekannt, Endpoint ggf. aktualisieren (IP-Wechsel)
    for uid in mine:
        if uid not in found:
            log.warning("Zugewiesene Maschine %s aktuell nicht erreichbar (Zuweisung bleibt bestehen)", uid)

    assigned = max(len(mine), len(server))
    tenant_list = gw.tenant_machines()
    if tenant_list is None:
        log.warning("Tenant-Maschinenliste nicht verfügbar - Vorabprüfung auf Fremdbesitz entfällt")
    my_ids = {BOX_ID} | ({gw.box_uuid} if gw.box_uuid else set())
    now = time.time()
    states: dict[str, tuple[str, str]] = {uid: ("assigned", "") for uid in found if uid in mine}
    free: list[Machine] = []
    for uid, m in found.items():
        if uid in mine:
            continue
        other = foreign_owner(m, tenant_list, my_ids) if tenant_list is not None else None
        if other:
            states[uid] = ("rejected", f"gehört bereits Box {other}")
            if uid not in _foreign_logged:
                _foreign_logged.add(uid)
                log.info("Maschine %s gehört bereits Box %s - übersprungen", m.uid, other)
            continue
        until, why = skip_until.get(uid, (0.0, ""))
        if until > now:
            states[uid] = ("rejected", why)  # kürzlich abgelehnt, noch nicht erneut versuchen
        else:
            free.append(m)
    random.shuffle(free)  # weniger Kollisionen, wenn mehrere Boxen gleichzeitig starten

    limit_hit = False
    for m in free:
        if limit_hit or assigned >= MAX_MACHINES:
            if not limit_hit:
                log.info("Lizenzlimit erreicht (%d/%d Maschinen)", assigned, MAX_MACHINES)
            limit_hit = True
            states[m.uid] = ("limit", f"Box-Limit {MAX_MACHINES} erreicht")
            continue
        result, reason = gw.register(m)
        if result == "ok":
            mine[m.uid] = asdict(m)
            assigned += 1
            states[m.uid] = ("assigned", "")
            log.info("Maschine registriert: %s (%s, %s) [%d/%d]%s", m.name, m.uid, m.endpoint, assigned,
                     MAX_MACHINES, "" if m.strong_identity else "  WARNUNG: schwache Identität")
        elif result == "limit":
            log.info("Backend meldet Lizenzlimit: %s", reason)
            limit_hit = True
            states[m.uid] = ("limit", reason)
        elif result == "notpaired":
            raise RuntimeError(f"Box nicht (mehr) gepairt: {reason}")
        else:
            log.info("Maschine %s abgelehnt (%s) - nächster Versuch in %ds", m.uid, reason, RETRY_REJECTED_SECONDS)
            skip_until[m.uid] = (now + RETRY_REJECTED_SECONDS, reason)
            states[m.uid] = ("rejected", reason)

    entries = [discovered_entry(m, *states[uid]) for uid, m in found.items()]
    save_discovered(entries)
    gw.report_discovered(entries)
    save_state(mine)
    # Status der zugewiesenen Maschinen: erreichbar (im Scan gefunden) -> ok, sonst error/UNREACHABLE.
    # Wird jeden Zyklus gemeldet, damit ein neu gestartetes Cockpit/BFF den Stand binnen eines Intervalls wieder kennt.
    # ACHTUNG: das ist MASCHINENstatus (PATCH /v1/machines/<id>/status), nicht Box-Status.
    for uid in mine:
        reachable = uid in found
        gw.report_machine_status(uid, "ok" if reachable else "error", None if reachable else "UNREACHABLE")


def main() -> None:
    gw = Gateway()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    log.info("Box %s startet (gateway=%s, max=%d, ports=%s, heartbeat=%ds)",
             BOX_ID, GATEWAY_URL, MAX_MACHINES, SCAN_PORTS, HEARTBEAT_SECONDS)

    mine = load_state()
    skip_until: dict[str, tuple[float, str]] = {}

    # Heartbeat-Thread läuft parallel zum Scan-Zyklus und hält den Box-Status aktuell.
    heartbeat = threading.Thread(target=heartbeat_loop, args=(gw, stop), daemon=True, name="heartbeat")
    heartbeat.start()

    delay = 5
    while not stop.is_set():
        try:
            if not ensure_ready(gw):
                stop.wait(delay)
                delay = min(delay * 2, 60)
                continue
            cycle(gw, mine, skip_until)
            delay = 5
            stop.wait(SCAN_INTERVAL)
        except Exception as exc:  # Gateway nicht erreichbar, 5xx, ... -> Backoff, nie abstürzen
            log.error("Zyklus fehlgeschlagen: %s (Retry in %ds)", exc, delay)
            stop.wait(delay)
            delay = min(delay * 2, SCAN_INTERVAL)
    log.info("Beendet.")


if __name__ == "__main__":
    main()