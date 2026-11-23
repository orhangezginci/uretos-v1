"""
shopfloor-bff-api

Backend-for-Frontend (BFF) für das uretOS Shopfloor 3D Cockpit & Stream.
Liefert per REST und SSE Stammdaten, Status-Updates und Live-Telemetrie
der Connector-Boxen und zugewiesenen Maschinen.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import threading
import urllib.error
import urllib.parse
import urllib.request
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import pika
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("shopfloor-bff-api")

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://uretos:uretos_dev_pass@rabbitmq:5672/")
EXCHANGE = "uretos.events"
STATUS_EVENT = "uretos.machine.event.status_changed"
TELEMETRY_EVENT = "uretos.machine.event.telemetry"

GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://gateway-api:8080").rstrip("/")
MAX_MACHINES_PER_BOX = int(os.environ.get("MAX_MACHINES_PER_BOX", "5"))
BOX_ONLINE_SECONDS = int(os.environ.get("BOX_ONLINE_SECONDS", "150"))

TENANT_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{2,62}$")
MACHINE_STATUSES = ("ok", "warning", "error")


# -----------------------------------------------------------------------------
# In-Memory Caching & Broadcast Queues
# -----------------------------------------------------------------------------

class StatusCache:
    """In-Memory Cache für den letzten bekannten Maschinenstatus."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data: dict[tuple[str, str], dict] = {}

    def set(self, tenant_id: str, machine_id: str, status: str, error_code: str | None, at: str | None) -> None:
        with self._lock:
            self._data[(tenant_id, machine_id)] = {"status": status, "error_code": error_code, "at": at}

    def get(self, tenant_id: str, machine_id: str) -> dict | None:
        with self._lock:
            entry = self._data.get((tenant_id, machine_id))
            return dict(entry) if entry else None


class TelemetryCache:
    """In-Memory Cache für die neuesten Telemetriedaten pro Maschine (z. B. Temperatur)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data: dict[tuple[str, str], dict] = {}

    def set(self, tenant_id: str, machine_id: str, telemetry: dict) -> None:
        with self._lock:
            self._data[(tenant_id, machine_id)] = {
                "telemetry": telemetry,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

    def get(self, tenant_id: str, machine_id: str) -> dict | None:
        with self._lock:
            entry = self._data.get((tenant_id, machine_id))
            return dict(entry) if entry else None


status_cache = StatusCache()
telemetry_cache = TelemetryCache()

# Thread-safe Liste für aktive SSE-Client-Warteschlangen
client_queues: list[asyncio.Queue] = []
client_queues_lock = threading.Lock()


def broadcast_event(event_type: str, data: dict) -> None:
    """Sendet ein Event an alle zurzeit verbundenen SSE-Clients."""
    payload = json.dumps({"type": event_type, "data": data})
    with client_queues_lock:
        for q in client_queues:
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                pass


# -----------------------------------------------------------------------------
# RabbitMQ Event-Consumer
# -----------------------------------------------------------------------------

def handle_status_event(envelope: dict) -> None:
    data = envelope.get("data") or {}
    tenant_id = envelope.get("tenantid") or data.get("tenant_id")
    machine_id = data.get("machine_id")
    status = data.get("status")
    if tenant_id and machine_id and status in MACHINE_STATUSES:
        status_cache.set(tenant_id, machine_id, status, data.get("error_code"), data.get("timestamp"))
        broadcast_event(
            "status_update",
            {
                "tenant_id": tenant_id,
                "machine_id": machine_id,
                "status": status,
                "error_code": data.get("error_code"),
                "timestamp": data.get("timestamp") or datetime.now(timezone.utc).isoformat(),
            },
        )


def handle_telemetry_event(envelope: dict) -> None:
    data = envelope.get("data") or {}
    tenant_id = envelope.get("tenantid") or data.get("tenant_id")
    machine_id = data.get("machine_id")
    telemetry = data.get("telemetry") or data
    if tenant_id and machine_id:
        telemetry_cache.set(tenant_id, machine_id, telemetry)
        broadcast_event(
            "telemetry_update",
            {
                "tenant_id": tenant_id,
                "machine_id": machine_id,
                "telemetry": telemetry,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )


def _consume_events(stop: threading.Event) -> None:
    while not stop.is_set():
        try:
            connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
            channel = connection.channel()
            channel.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)
            queue = channel.queue_declare(queue="", exclusive=True).method.queue

            # Höre auf alle Maschinen-Events (Status + Telemetrie)
            channel.queue_bind(queue=queue, exchange=EXCHANGE, routing_key="uretos.machine.event.#")
            log.info("BFF Event-Consumer mit RabbitMQ verbunden (uretos.machine.event.#)")

            for method, _props, body in channel.consume(queue, auto_ack=True, inactivity_timeout=1):
                if stop.is_set():
                    break
                if body is None:
                    continue
                try:
                    envelope = json.loads(body)
                    routing_key = method.routing_key
                    if routing_key == STATUS_EVENT:
                        handle_status_event(envelope)
                    elif routing_key == TELEMETRY_EVENT or "telemetry" in routing_key:
                        handle_telemetry_event(envelope)
                except Exception:
                    log.exception("Fehler beim Verarbeiten des Events in der BFF")
            connection.close()
        except Exception as exc:
            log.warning("BFF Event-Consumer Verbindung verloren (%s) - Reconnect in 5s", exc)
            stop.wait(5)


# -----------------------------------------------------------------------------
# Gateway Service Helper
# -----------------------------------------------------------------------------

class GatewayError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status = status
        self.detail = detail


def _gw_get(path: str, timeout: int = 10):
    req = urllib.request.Request(GATEWAY_URL + path, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        raise GatewayError(e.code, f"gateway {path.split('?')[0]}: HTTP {e.code}")
    except Exception as exc:
        raise GatewayError(502, f"gateway {path.split('?')[0]}: {exc}")


def _gw_get_optional(path: str):
    try:
        return _gw_get(path)
    except GatewayError as exc:
        log.warning("Optionale Gateway-Daten nicht verfügbar: %s", exc.detail)
        return None


def _as_dict(value) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except ValueError:
            return {}
    return {}


def _first(*values):
    for v in values:
        if v not in (None, ""):
            return v
    return None


def normalize_machine(entry: dict) -> dict:
    meta = _as_dict(entry.get("metadata") or entry.get("metadata_json") or entry.get("meta"))
    machine_id = _first(entry.get("machine_id"), meta.get("machine_id"))
    return {
        "machine_id": machine_id,
        "name": _first(entry.get("name"), meta.get("name"), machine_id),
        "manufacturer": _first(entry.get("manufacturer"), meta.get("manufacturer")),
        "model": _first(entry.get("model"), meta.get("model")),
        "serial_number": _first(entry.get("serial_number"), meta.get("serial_number"), meta.get("serial")),
        "machine_type": _first(entry.get("machine_type"), meta.get("machine_type")),
        "endpoint_url": _first(entry.get("endpoint_url"), meta.get("endpoint_url")),
        "_box": _first(entry.get("box_id"), entry.get("hardware_id")),
    }


def _resolve_box_online(box: dict, st: dict, assigned_machines: list[dict]) -> tuple[bool, str | None, int | None]:
    age = st.get("age_seconds")
    if age is not None:
        online = age < BOX_ONLINE_SECONDS
        return online, st.get("status") if online else None, round(age)

    # Fallback, wenn /v1/connector-boxes/status kein age_seconds liefert
    has_live_data = any(m.get("telemetry") is not None for m in assigned_machines)
    if box.get("status") == "paired" and (len(assigned_machines) > 0 or has_live_data):
        return True, st.get("status") or "active", None

    return False, None, None


def build_overview(
    tenant_id: str,
    boxes: list,
    machines: list,
    box_status: dict | None,
    cache: StatusCache,
    tel_cache: TelemetryCache,
) -> dict:
    boxes = [b for b in (boxes or []) if isinstance(b, dict)]
    normalized = [normalize_machine(m) for m in (machines or []) if isinstance(m, dict)]

    if any("tenant_id" in b for b in boxes):
        boxes = [b for b in boxes if b.get("tenant_id") == tenant_id]
    else:
        referenced = {str(m["_box"]) for m in normalized if m["_box"]}
        boxes = [b for b in boxes if str(b.get("box_id")) in referenced or str(b.get("hardware_id")) in referenced]

    views: list[dict] = []
    by_key: dict[str, dict] = {}
    box_raw_by_hw: dict[str, dict] = {}
    status_map = box_status if isinstance(box_status, dict) else {}

    for b in boxes:
        hardware_id = b.get("hardware_id") or str(b.get("box_id"))
        view = {
            "box_id": b.get("box_id"),
            "hardware_id": hardware_id,
            "pairing_status": b.get("status"),
            "online": False,
            "activity": None,
            "last_seen_seconds": None,
            "machine_limit": MAX_MACHINES_PER_BOX,
            "machines": [],
        }
        views.append(view)
        box_raw_by_hw[hardware_id] = b
        for key in (b.get("box_id"), b.get("hardware_id")):
            if key:
                by_key[str(key)] = view

    unassigned: list[dict] = []
    for m in normalized:
        box_key = m.pop("_box")
        cached_status = cache.get(tenant_id, m["machine_id"]) if m["machine_id"] else None
        cached_telemetry = tel_cache.get(tenant_id, m["machine_id"]) if m["machine_id"] else None

        m["status"] = cached_status["status"] if cached_status else "ok"
        m["error_code"] = cached_status["error_code"] if cached_status else None
        m["status_at"] = cached_status["at"] if cached_status else None
        m["telemetry"] = cached_telemetry["telemetry"] if cached_telemetry else None

        target = by_key.get(str(box_key)) if box_key else None
        (target["machines"] if target else unassigned).append(m)

    for view in views:
        hw = view["hardware_id"]
        st = status_map.get(hw) or status_map.get(str(view.get("box_id"))) or {}
        online, activity, last_seen = _resolve_box_online(box_raw_by_hw[hw], st, view["machines"])
        view["online"] = online
        view["activity"] = activity
        view["last_seen_seconds"] = last_seen
        view["machines"].sort(key=lambda m: (m["name"] or ""))

    views.sort(key=lambda v: v["hardware_id"])
    return {
        "tenant_id": tenant_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "box_count": len(views),
        "machine_count": sum(len(v["machines"]) for v in views),
        "boxes": views,
        "unassigned": unassigned,
    }


# -----------------------------------------------------------------------------
# FastAPI Lifecycle & Routes
# -----------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(_app: FastAPI):
    stop = threading.Event()
    threading.Thread(target=_consume_events, args=(stop,), daemon=True, name="bff-event-consumer").start()
    yield
    stop.set()


app = FastAPI(title="uretOS Shopfloor BFF API", version="1.2.0", lifespan=lifespan)

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


@app.get("/api/v1/shopfloor")
async def shopfloor_overview(tenant_id: str):
    if not TENANT_RE.match(tenant_id):
        raise HTTPException(status_code=400, detail="Ungültige tenant_id")
    try:
        boxes, machines, box_status = await asyncio.gather(
            asyncio.to_thread(_gw_get, "/v1/connector-boxes"),
            asyncio.to_thread(_gw_get, f"/v1/machines?tenant_id={urllib.parse.quote(tenant_id)}"),
            asyncio.to_thread(_gw_get_optional, "/v1/connector-boxes/status"),
        )
    except GatewayError as exc:
        log.warning("Overview für '%s' fehlgeschlagen: %s", tenant_id, exc.detail)
        raise HTTPException(status_code=404 if exc.status == 404 else 502, detail=exc.detail)
    return build_overview(tenant_id, boxes, machines, box_status, status_cache, telemetry_cache)


@app.get("/api/v1/shopfloor/stream")
async def shopfloor_stream(request: Request, tenant_id: str):
    """Server-Sent Events (SSE) Stream für Live-Status und Telemetrie im 3D-Cockpit."""
    if not TENANT_RE.match(tenant_id):
        raise HTTPException(status_code=400, detail="Ungültige tenant_id")

    q = asyncio.Queue(maxsize=100)
    with client_queues_lock:
        client_queues.append(q)

    async def event_generator():
        try:
            # Initialer Handshake für SSE-Verbindung
            yield {"event": "connected", "data": json.dumps({"status": "connected", "tenant_id": tenant_id})}
            while True:
                if await request.is_disconnected():
                    break
                try:
                    msg = await asyncio.wait_for(q.get(), timeout=15.0)
                    yield {"event": "message", "data": msg}
                except asyncio.TimeoutError:
                    # Ping alle 15s als Keep-Alive
                    yield {"event": "ping", "data": json.dumps({"time": datetime.now(timezone.utc).isoformat()})}
        finally:
            with client_queues_lock:
                if q in client_queues:
                    client_queues.remove(q)

    return EventSourceResponse(event_generator())