#!/usr/bin/env python3
"""
sim-control: kleine Test-Oberflaeche, um die OPC-UA-Maschinensimulatoren direkt zu steuern.

Prinzip: Der Zustand wird NICHT ueber die uretOS-API gesetzt, sondern direkt am Simulator
(HTTP-Control-Schnittstelle /opc/state, /opc/set), erreicht per `docker exec` im jeweiligen
Simulator-Container. Dadurch ist weder eine Container-IP noch ein Port-Mapping auf den Host noetig.

Maschinen werden automatisch gefunden: alle laufenden Container, deren Name mit
SIMCTL_PREFIX beginnt (Default "uretos-machine-") UND die MACHINE_NAME in ihrer Umgebung
setzen (so werden Dienste wie uretos-machine-command-service ausgeschlossen).
MACHINE_NAME, PORT und CONTROL_PORT werden aus der Container-Umgebung gelesen.

Nur Python-Standardbibliothek. Start:  python server.py   ->  http://127.0.0.1:8099
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

HOST = os.environ.get("SIMCTL_HOST", "127.0.0.1")
PORT = int(os.environ.get("SIMCTL_PORT", "8099"))
CONTAINER_PREFIX = os.environ.get("SIMCTL_PREFIX", "uretos-machine-")
DISCOVERY_TTL_SEC = 5.0
DOCKER_TIMEOUT_SEC = 6.0
INDEX_FILE = Path(__file__).with_name("index.html")


# ---------------------------------------------------------------- Docker-Zugriff

class DockerError(RuntimeError):
    pass


def run_docker(args: list[str], timeout: float = DOCKER_TIMEOUT_SEC) -> str:
    try:
        res = subprocess.run(["docker", *args], capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as exc:
        raise DockerError("docker CLI nicht gefunden") from exc
    except subprocess.TimeoutExpired as exc:
        raise DockerError(f"docker {args[0]}: Timeout nach {timeout:.0f}s") from exc
    if res.returncode != 0:
        lines = (res.stderr or res.stdout).strip().splitlines()
        raise DockerError(lines[-1] if lines else f"docker {args[0]}: exit {res.returncode}")
    return res.stdout


# ---------------------------------------------------------------- Maschinen-Discovery

_discovery_lock = threading.Lock()
_discovery_cache: tuple[float, list[dict]] | None = None


def discover_machines() -> list[dict]:
    """Findet laufende Simulator-Container und liest Name/Ports aus deren Umgebung."""
    out = run_docker(["ps", "--filter", f"name={CONTAINER_PREFIX}", "--format", "{{.Names}}"])
    names = sorted(n.strip() for n in out.splitlines() if n.strip().startswith(CONTAINER_PREFIX))
    if not names:
        return []

    machines: list[dict] = []
    for item in json.loads(run_docker(["inspect", *names])):
        container = (item.get("Name") or "").lstrip("/")
        env = dict(e.split("=", 1) for e in (item.get("Config", {}).get("Env") or []) if "=" in e)
        # Der Namens-Prefix allein reicht nicht (z.B. uretos-machine-command-service):
        # nur Container mit MACHINE_NAME in der Umgebung sind Simulatoren.
        if "MACHINE_NAME" not in env:
            continue
        try:
            opc_port = int(env.get("PORT", "4840"))
            control_port = int(env.get("CONTROL_PORT", str(opc_port + 4000)))
        except ValueError:
            continue
        machines.append(
            {
                "container": container,
                "machine_name": env.get("MACHINE_NAME", container),
                "opc_port": opc_port,
                "control_port": control_port,
            }
        )
    return sorted(machines, key=lambda m: m["machine_name"])


def get_machines(force: bool = False) -> list[dict]:
    global _discovery_cache
    with _discovery_lock:
        now = time.monotonic()
        if not force and _discovery_cache and now - _discovery_cache[0] < DISCOVERY_TTL_SEC:
            return _discovery_cache[1]
        machines = discover_machines()
        _discovery_cache = (now, machines)
        return machines


# ---------------------------------------------------------------- Zugriff auf die Sim-Control-API

# Laeuft im Simulator-Container (dort ist Python vorhanden). Parameter kommen per argv,
# nichts wird in den Code interpoliert.
_CONTROL_SCRIPT = """
import sys, json, urllib.request, urllib.error
method, url, body = sys.argv[1], sys.argv[2], sys.argv[3]
data = body.encode() if body else None
headers = {"Content-Type": "application/json"} if data else {}
req = urllib.request.Request(url, data=data, method=method, headers=headers)
try:
    with urllib.request.urlopen(req, timeout=3) as r:
        print(json.dumps({"code": r.status, "body": r.read().decode()}))
except urllib.error.HTTPError as e:
    print(json.dumps({"code": e.code, "body": e.read().decode()}))
"""


def control_request(machine: dict, method: str, path: str, payload: dict | None = None) -> tuple[int, dict]:
    """HTTP-Aufruf gegen die Control-Schnittstelle eines Simulators via docker exec."""
    url = f"http://127.0.0.1:{machine['control_port']}{path}"
    body = json.dumps(payload) if payload is not None else ""
    out = run_docker(
        ["exec", machine["container"], "python", "-c", _CONTROL_SCRIPT, method, url, body]
    )
    wrapper = json.loads(out)
    return int(wrapper["code"]), (json.loads(wrapper["body"]) if wrapper["body"] else {})


def collect_machines() -> list[dict]:
    """Alle Maschinen inkl. aktuellem Simulator-Zustand (parallel abgefragt)."""
    machines = get_machines()

    def one(m: dict) -> dict:
        entry = dict(m, state=None, error=None)
        try:
            code, data = control_request(m, "GET", "/opc/state")
            if code == 200:
                entry["state"] = data
            else:
                entry["error"] = f"Simulator antwortet mit HTTP {code}"
        except (DockerError, ValueError, KeyError) as exc:
            entry["error"] = str(exc)
        return entry

    if not machines:
        return []
    with ThreadPoolExecutor(max_workers=min(8, len(machines))) as pool:
        return list(pool.map(one, machines))


# ---------------------------------------------------------------- Status setzen

# Nur diese Felder duerfen ueber die Oberflaeche gesetzt werden (Fokus: Status).
# Erweiterbar, z.B. um "temperature", "machinery_item_state", "machinery_operation_mode".
ALLOWED_SET_KEYS = ("status", "device_health", "temperature", "resume_auto_temp")
TEMP_MIN_C, TEMP_MAX_C = -50.0, 400.0


def find_machine(machine_name: str) -> dict | None:
    for force in (False, True):  # zweiter Versuch mit frischer Discovery
        for m in get_machines(force=force):
            if m["machine_name"] == machine_name:
                return m
    return None


def set_machine(machine_name: str, payload) -> tuple[int, dict]:
    """Setzt Werte direkt am Simulator. Wertepruefung macht der Simulator (HTTP 400 wird durchgereicht)."""
    if not isinstance(payload, dict) or not payload:
        return 400, {"ok": False, "error": "Body muss ein nicht-leeres JSON-Objekt sein", "allowed": list(ALLOWED_SET_KEYS)}
    unknown = sorted(set(payload) - set(ALLOWED_SET_KEYS))
    if unknown:
        return 400, {"ok": False, "error": f"Nicht erlaubte Felder: {unknown}", "allowed": list(ALLOWED_SET_KEYS)}
    if any(v is None or v == "" for v in payload.values()):
        return 400, {"ok": False, "error": "Leere Werte sind nicht erlaubt", "allowed": list(ALLOWED_SET_KEYS)}
    if "temperature" in payload:
        t = payload["temperature"]
        if isinstance(t, bool) or not isinstance(t, (int, float)) or not math.isfinite(t):
            return 400, {"ok": False, "error": "temperature muss eine endliche Zahl sein"}
        if not TEMP_MIN_C <= t <= TEMP_MAX_C:
            return 400, {"ok": False, "error": f"temperature muss zwischen {TEMP_MIN_C:.0f} und {TEMP_MAX_C:.0f} °C liegen"}
    if "resume_auto_temp" in payload and payload["resume_auto_temp"] is not True:
        return 400, {"ok": False, "error": "resume_auto_temp darf nur true sein"}

    try:
        machine = find_machine(machine_name)
    except DockerError as exc:
        return 503, {"ok": False, "error": str(exc)}
    if machine is None:
        return 404, {"ok": False, "error": f"Unbekannte Maschine: {machine_name}"}

    try:
        code, sim = control_request(machine, "POST", "/opc/set", payload)
        if code != 200:
            return code, {"ok": False, "machine": machine_name, "error": sim.get("error", f"Simulator: HTTP {code}")}
        _, state = control_request(machine, "GET", "/opc/state")
    except (DockerError, ValueError, KeyError) as exc:
        return 502, {"ok": False, "machine": machine_name, "error": str(exc)}
    return 200, {"ok": True, "machine": machine_name, "updated": sim.get("updated", {}), "state": state}


# ---------------------------------------------------------------- HTTP-Server

class Handler(BaseHTTPRequestHandler):
    def _json(self, code: int, body: dict) -> None:
        raw = json.dumps(body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        path = urlparse(self.path).path

        if path in ("/", "/index.html"):
            if not INDEX_FILE.exists():
                self._json(404, {"ok": False, "error": "index.html fehlt (kommt in einem spaeteren Schritt)"})
                return
            content = INDEX_FILE.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        if path == "/api/machines":
            try:
                self._json(200, {"ok": True, "machines": collect_machines()})
            except DockerError as exc:
                self._json(503, {"ok": False, "error": str(exc)})
            return

        self._json(404, {"ok": False, "error": "not found"})

    def do_POST(self) -> None:
        parts = [unquote(p) for p in urlparse(self.path).path.strip("/").split("/")]
        if not (len(parts) == 4 and parts[0] == "api" and parts[1] == "machines" and parts[3] == "set"):
            self._json(404, {"ok": False, "error": "not found"})
            return

        length = int(self.headers.get("Content-Length", "0") or 0)
        if length > 4096:
            self._json(413, {"ok": False, "error": "Body zu gross"})
            return
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
        except ValueError as exc:
            self._json(400, {"ok": False, "error": f"Ungueltiges JSON: {exc}"})
            return

        code, body = set_machine(parts[2], payload)
        self._json(code, body)

    def log_message(self, fmt: str, *args) -> None:
        return


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"sim-control laeuft auf http://{HOST}:{PORT}  (Container-Prefix: {CONTAINER_PREFIX})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()