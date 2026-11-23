import os
import time
import logging
import subprocess
import threading
import math
import requests
from typing import Optional
from zeroconf import ServiceBrowser, ServiceListener, Zeroconf
from opc_inspector import inspect_machines

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("uretos.poller")



# Handler-Filter: unterdrückt alle Records der OPC-UA-Bibliotheken unterhalb von WARNING.
# "opcua" = python-opcua (von opc_inspector.py genutzt), "asyncua" = asyncua (Poller).
class SilenceOpcUaLibs(logging.Filter):
    _PREFIXES = ("opcua", "asyncua")

    def filter(self, record: logging.LogRecord) -> bool:
        return not (record.name.startswith(self._PREFIXES) and record.levelno < logging.WARNING)


for _handler in logging.root.handlers:
    _handler.addFilter(SilenceOpcUaLibs())


GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://gateway-api:8080")
HARDWARE_ID = os.environ.get("BOX_HARDWARE_ID", os.environ.get("HARDWARE_ID", "sim-box-01"))
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL_SECONDS", 10))
HARD_MAX_MACHINES = 5  # Physische Obergrenze der Box

# Automatische Verteilung: Jede Box beansprucht beim Gateway zunächst nur ihren fairen Anteil
# (Maschinen / Anzahl gepairter Boxen im Tenant). Erst nach TAKEOVER_AFTER_SECONDS darf sie über den
# fairen Anteil hinaus freie Maschinen übernehmen (z. B. weil eine andere Box ausgefallen ist).
# Von anderen Boxen belegte Maschinen werden frühestens nach CLAIM_RETRY_SECONDS erneut versucht.
CLAIM_RETRY_SECONDS = int(os.environ.get("CLAIM_RETRY_SECONDS", 60))
TAKEOVER_AFTER_SECONDS = int(os.environ.get("TAKEOVER_AFTER_SECONDS", 120))
# Nach dem Pairing erst kurz warten, bevor Maschinen beansprucht werden, damit gleichzeitig startende Boxen
# sich gegenseitig als gepairt sehen und der faire Anteil für alle gleich berechnet wird.
INITIAL_CLAIM_DELAY_SECONDS = int(os.environ.get("INITIAL_CLAIM_DELAY_SECONDS", 15))


class OpcUaMdnsListener(ServiceListener):
    """Sammelt alle im lokalen Netzwerk angekündigten OPC-UA-Endpunkte per mDNS."""

    def __init__(self):
        self._lock = threading.Lock()
        self._endpoints: dict[str, tuple[str, int]] = {}

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        info = zc.get_service_info(type_, name)
        if not info or not info.addresses:
            return
        ip = ".".join(str(b) for b in info.addresses[0])
        port = info.port
        with self._lock:
            if name not in self._endpoints:
                log.info("mDNS Service erkannt: %s -> opc.tcp://%s:%d", name, ip, port)
            self._endpoints[name] = (ip, port)

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        self.add_service(zc, type_, name)

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        with self._lock:
            if name in self._endpoints:
                log.info("mDNS Service entfernt: %s", name)
                del self._endpoints[name]

    def get_endpoints(self) -> list[tuple[str, int]]:
        with self._lock:
            # Deterministische Sortierung für reproduzierbare Auswahl innerhalb des Lizenzlimits
            return [self._endpoints[k] for k in sorted(self._endpoints.keys())]


def perform_handshake() -> tuple[bool, int, str, Optional[str]]:
    """
    Führt Handshake (und bei Bedarf initiales Pairing) mit der Gateway-API aus.
    Liefert (erfolgreich, erlaubtes_maschinenlimit, lizenz_status, tenant_id).
    """
    try:
        resp = requests.post(
            f"{GATEWAY_URL}/v1/connector-boxes/handshake",
            json={"hardware_id": HARDWARE_ID},
            timeout=10,
        )
        if resp.status_code in (404, 403):
            log.info("Box unbekannt oder noch nicht gepaired (HTTP %s). Starte Pairing...", resp.status_code)
            pair_resp = requests.post(
                f"{GATEWAY_URL}/v1/connector-boxes/pair",
                json={"hardware_id": HARDWARE_ID},
                timeout=10,
            )
            if pair_resp.status_code == 200:
                log.info("Initiales Pairing erfolgreich. Wiederhole Handshake für Lizenzabruf...")
                resp = requests.post(
                    f"{GATEWAY_URL}/v1/connector-boxes/handshake",
                    json={"hardware_id": HARDWARE_ID},
                    timeout=10,
                )

        if resp.status_code == 200:
            data = resp.json()
            tenant_id = data.get("tenant_id")
            licensing = data.get("licensing", {})
            raw_limit = int(licensing.get("max_machines", HARD_MAX_MACHINES))
            license_status = licensing.get("status", "active")

            if license_status != "active":
                return True, 0, license_status, tenant_id

            allowed_limit = max(0, min(raw_limit, HARD_MAX_MACHINES))
            return True, allowed_limit, license_status, tenant_id

        log.warning("Gateway-Handshake fehlgeschlagen mit Status %s", resp.status_code)
        return False, 0, "unreachable", None

    except Exception as exc:
        log.warning("Gateway nicht erreichbar (%s)", exc)
        return False, 0, "unreachable", None


def stop_all_workers(active_workers: dict[str, subprocess.Popen]) -> None:
    """Beendet alle laufenden Telemetrie-Subprozesse sauber."""
    for m_id, proc in list(active_workers.items()):
        if proc.poll() is None:
            log.info("Stoppe Telemetrie-Poller-Subprozess für Maschine: %s", m_id)
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        del active_workers[m_id]


def stop_excess_workers(active_workers: dict[str, subprocess.Popen], allowed_ids: set[str]) -> None:
    """Beendet Worker von Maschinen, die nicht mehr im lizenzierten Kontingent liegen."""
    for m_id, proc in list(active_workers.items()):
        if m_id not in allowed_ids:
            if proc.poll() is None:
                log.info("Stoppe nicht mehr lizenzierten Worker für Maschine: %s", m_id)
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
            del active_workers[m_id]


def machine_id_of(m) -> str:
    return m.name or m.uid or "UnknownMachine"


def discover_all(endpoints: list[tuple[str, int]]) -> tuple[dict, dict[str, str]]:
    """Inspiziert ALLE per mDNS gefundenen Endpoints (ohne Lizenzkappung) und liefert Maschinen + Endpoint-URLs."""
    machines: dict = {}
    endpoint_of: dict[str, str] = {}
    for host, port in endpoints:
        try:
            found = inspect_machines(host, port, max_machines=50)
        except Exception as exc:
            log.warning("Inspektion von %s:%d fehlgeschlagen: %s", host, port, exc)
            continue
        for m in found:
            mid = machine_id_of(m)
            machines[mid] = m
            endpoint_of[mid] = f"opc.tcp://{host}:{port}"
    return machines, endpoint_of


def register_machines(machines: list) -> tuple[str, str]:
    """
    Registriert Maschinen für diese Box beim Gateway. Das Gateway entscheidet verbindlich:
      200                      -> ok     (Maschine gehört dieser Box)
      409 machine_taken        -> taken  (gehört bereits einer anderen Box)
      409 box_limit_reached    -> limit  (Lizenz-/Hardwarelimit dieser Box erreicht)
      sonst                    -> error
    """
    try:
        resp = requests.post(
            f"{GATEWAY_URL}/v1/connector-boxes/autoscan",
            json={"hardware_id": HARDWARE_ID, "machines": [m.to_dict() for m in machines]},
            timeout=15,
        )
    except Exception as exc:
        return "error", str(exc)

    if resp.status_code == 200:
        return "ok", ""
    if resp.status_code == 409:
        try:
            code = resp.json().get("error_code")
        except ValueError:
            code = None
        if code == "machine_taken":
            return "taken", resp.text
        if code == "box_limit_reached":
            return "limit", resp.text
    return "error", f"HTTP {resp.status_code}: {resp.text[:200]}"


def count_paired_boxes(tenant_id: Optional[str]) -> int:
    """Anzahl gepairter Boxen im Tenant (mindestens 1). Fällt bei Fehlern auf 1 zurück."""
    try:
        resp = requests.get(f"{GATEWAY_URL}/v1/connector-boxes", timeout=10)
        if resp.status_code != 200:
            return 1
        n = sum(
            1 for b in resp.json()
            if b.get("status") == "paired" and (tenant_id is None or b.get("tenant_id") == tenant_id)
        )
        return max(1, n)
    except Exception:
        return 1


def claim_target(total_machines: int, boxes: int, limit: int, uptime_seconds: float) -> int:
    """Wie viele Maschinen diese Box jetzt halten darf: fairer Anteil, nach Karenzzeit das volle Lizenzlimit."""
    fair_share = min(limit, math.ceil(total_machines / max(1, boxes)))
    return limit if uptime_seconds >= TAKEOVER_AFTER_SECONDS else fair_share


def sync_owned_machines(owned: set[str], discovered: dict) -> None:
    """Meldet die bereits gehaltenen Maschinen erneut (Heartbeat/Update) und gibt verlorene frei."""
    visible = [discovered[i] for i in sorted(owned) if i in discovered]
    if not visible:
        return
    outcome, detail = register_machines(visible)
    if outcome == "ok":
        return
    if outcome in ("taken", "limit"):
        # Batch abgelehnt: einzeln prüfen und Maschinen, die inzwischen anderen gehören, verwerfen
        for m in visible:
            single, _ = register_machines([m])
            if single == "taken":
                log.warning("Maschine %s gehört inzwischen einer anderen Box.", machine_id_of(m))
                owned.discard(machine_id_of(m))
    else:
        log.warning("Synchronisation der eigenen Maschinen fehlgeschlagen: %s", detail)


def claim_new_machines(owned: set[str], discovered: dict, target: int, taken_at: dict[str, float], now: float) -> None:
    """Beansprucht beim Gateway freie Maschinen, bis `target` erreicht ist (das Gateway verhindert Doppelbelegung)."""
    for mid in sorted(discovered):
        if len(owned) >= target:
            return
        if mid in owned:
            continue
        last = taken_at.get(mid)
        if last is not None and now - last < CLAIM_RETRY_SECONDS:
            continue
        outcome, detail = register_machines([discovered[mid]])
        if outcome == "ok":
            owned.add(mid)
            taken_at.pop(mid, None)
            log.info("Maschine %s übernommen (%d/%d).", mid, len(owned), target)
        elif outcome == "taken":
            taken_at[mid] = now
        elif outcome == "limit":
            log.info("Boxlimit laut Gateway erreicht, keine weiteren Maschinen.")
            return
        else:
            log.warning("Übernahme von Maschine %s fehlgeschlagen: %s", mid, detail)
            return


def main() -> None:
    log.info("Initialisiere uretOS Connector-Box Edge Poller...")
    log.info("Starte Shopfloor-Poller für Box: %s", HARDWARE_ID)

    zeroconf = Zeroconf()
    listener = OpcUaMdnsListener()
    browser = ServiceBrowser(zeroconf, "_opcua-tcp._tcp.local.", listener)

    # 1. Initialer Pairing- & Lizenz-Handshake
    log.info("Warte auf Pairing-Handshake für Box: %s", HARDWARE_ID)
    paired = False
    max_licensed_machines = 0
    tenant_id: Optional[str] = None

    while not paired:
        ok, limit, status, tid = perform_handshake()
        if ok:
            paired = True
            max_licensed_machines = limit
            tenant_id = tid
            log.info(
                "Handshake abgeschlossen für Box %s (Lizenzstatus: %s, max_machines: %d)",
                HARDWARE_ID,
                status,
                max_licensed_machines,
            )
        else:
            time.sleep(5)

    # 2. Hauptschleife: Lizenz-Sync, mDNS-Inspektion, Maschinen beanspruchen & Subprozess-Verwaltung
    active_workers: dict[str, subprocess.Popen] = {}
    owned: set[str] = set()                 # vom Gateway dieser Box zugesprochene Maschinen
    taken_at: dict[str, float] = {}         # Maschine -> Zeitpunkt, zu dem sie als "belegt" gemeldet wurde
    known_endpoints: dict[str, str] = {}
    last_summary = None
    started_at = time.monotonic()

    try:
        while True:
            try:
                # Periodischer Handshake, damit Lizenzänderungen / Sperrungen (0) im Betrieb greifen
                ok, limit, status, tid = perform_handshake()
                if ok:
                    if limit != max_licensed_machines:
                        log.info(
                            "Lizenzkontingent aktualisiert: %d -> %d (Status: %s)",
                            max_licensed_machines,
                            limit,
                            status,
                        )
                    max_licensed_machines = limit
                    tenant_id = tid or tenant_id

                if max_licensed_machines == 0:
                    log.warning(
                        "Lizenzkontingent für Box %s ist 0 (Status: %s). Stoppe alle aktiven Worker.",
                        HARDWARE_ID,
                        status,
                    )
                    stop_all_workers(active_workers)
                    time.sleep(POLL_INTERVAL)
                    continue

                endpoints = listener.get_endpoints()
                if not endpoints:
                    log.info("Keine OPC-UA mDNS-Services im Netzwerk gefunden.")
                    time.sleep(POLL_INTERVAL)
                    continue

                discovered, endpoint_of = discover_all(endpoints)
                known_endpoints.update(endpoint_of)
                if not discovered:
                    log.warning("Keine gültigen OPC-UA Maschinen-Knoten bei der Inspektion gefunden.")
                    time.sleep(POLL_INTERVAL)
                    continue

                now = time.monotonic()
                sync_owned_machines(owned, discovered)

                boxes = count_paired_boxes(tenant_id)
                target = claim_target(len(discovered), boxes, max_licensed_machines, now - started_at)
                if now - started_at >= INITIAL_CLAIM_DELAY_SECONDS:
                    claim_new_machines(owned, discovered, target, taken_at, now)

                # Harte Kappung auf das lizenzierte Kontingent (max. 5)
                active_ids = sorted(owned)[:max_licensed_machines]

                summary = (tuple(active_ids), target, boxes)
                if summary != last_summary:
                    log.info(
                        "Zuweisung Box %s: %d/%d Maschinen (Ziel %d bei %d Box(en), %d im Netz gefunden): %s",
                        HARDWARE_ID,
                        len(active_ids),
                        max_licensed_machines,
                        target,
                        boxes,
                        len(discovered),
                        ", ".join(active_ids) or "-",
                    )
                    last_summary = summary

                for m_id in active_ids:
                    endpoint_url = known_endpoints.get(m_id)

                    # Fallback falls kein mDNS-Mapping existiert
                    if not endpoint_url:
                        safe_host = m_id.lower().replace("_", "-")
                        if not safe_host.startswith("machine-"):
                            safe_host = safe_host.replace("cnc-", "machine-")
                        endpoint_url = f"opc.tcp://{safe_host}:4840"

                    if m_id not in active_workers or active_workers[m_id].poll() is not None:
                        log.info("Starte nativen Telemetrie-Poller-Subprozess für Maschine: %s bei %s", m_id, endpoint_url)
                        cmd = [
                            "python", "telemetry_poller.py",
                            "--machine", m_id,
                            "--endpoint", endpoint_url
                        ]
                        proc = subprocess.Popen(cmd)
                        active_workers[m_id] = proc

                stop_excess_workers(active_workers, set(active_ids))

            except Exception as exc:
                log.error("Fehler in der Polling-/Inspektionsschleife: %s", exc)

            time.sleep(POLL_INTERVAL)
    finally:
        stop_all_workers(active_workers)
        browser.cancel()
        zeroconf.close()


if __name__ == "__main__":
    main()