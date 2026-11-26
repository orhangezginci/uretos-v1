#!/usr/bin/env python3
import argparse
import asyncio
import logging
import os
import re
import time
from collections import deque

import requests
from asyncua import Client, ua

# 1. Grundlegendes Logging konfigurieren
logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("telemetry-poller")
log.setLevel(logging.INFO)


# 2. Handler-Filter: unterdrückt alle asyncua-Records unterhalb von WARNING,
#    unabhängig davon, wann der jeweilige Sub-Logger erzeugt wurde.
class SilenceAsyncua(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return not (record.name.startswith("asyncua") and record.levelno < logging.WARNING)


for _handler in logging.root.handlers:
    _handler.addFilter(SilenceAsyncua())

_raw_gateway = os.environ.get("GATEWAY_URL", "http://gateway-api:8080").rstrip("/")
if _raw_gateway.endswith("/v1/telemetry"):
    BASE_GATEWAY_URL = _raw_gateway.removesuffix("/v1/telemetry")
elif _raw_gateway.endswith("/v1"):
    BASE_GATEWAY_URL = _raw_gateway.removesuffix("/v1")
else:
    BASE_GATEWAY_URL = _raw_gateway

TELEMETRY_URL = f"{BASE_GATEWAY_URL}/v1/telemetry"
BOX_HARDWARE_ID = os.environ.get("BOX_HARDWARE_ID", "sim-box-01")
POLL_INTERVAL = float(os.environ.get("POLL_INTERVAL", "3.0"))

# Standardnahe BrowseNames (case-insensitive), gesucht ausschliesslich unterhalb des Maschinenknotens.
# Bewusst KEIN generisches "State": das wuerde z.B. Server/ServerStatus/State oder
# MachineryItemState/CurrentState faelschlich als Geraetestatus treffen.
TEMP_NODE_NAMES = ["Temperature", "Temp", "CNC_Temperature"]
HEALTH_NODE_NAMES = ["DeviceHealth"]  # OPC 10000-100 (DI), hat Vorrang
STATUS_FALLBACK_NAMES = ["MachineStatus", "Status"]  # nur fuer Maschinen ohne DeviceHealth
PARTS_NODE_NAMES = ["PartsProducedInLifetime", "PartCount", "ProducedParts"]
SPINDLE_ROTATING_NAMES = ["IsRotating"]
OPERATION_DURATION_NAMES = ["OperationDuration"]
POWER_ON_DURATION_NAMES = ["PowerOnDuration"]
# Zustandsmaschinen (OPC 40001-1): gesucht wird das OBJEKT, der Wert steht in dessen Kind "CurrentState".
# ("OperationMode" aus OPC 40501-1 ist etwas anderes: ein Enum-Wert, kein MachineryOperationMode.)
MACHINERY_ITEM_STATE_NAMES = ["MachineryItemState"]
MACHINERY_OPERATION_MODE_NAMES = ["MachineryOperationMode"]
MAX_SEARCH_DEPTH = 4


def bootstrap_configuration() -> tuple[str, str]:
    """
    Führt beim Start einen Zero-Touch-Handshake mit dem Gateway durch,
    um die zugewiesene Tenant-ID und Box-ID dynamisch zu ermitteln.
    """
    handshake_url = f"{BASE_GATEWAY_URL}/v1/connector-boxes/handshake"

    log.info(
        "Starting runtime bootstrap (Handshake) with gateway at %s for hardware_id=%s...",
        handshake_url,
        BOX_HARDWARE_ID,
    )

    while True:
        try:
            response = requests.post(handshake_url, json={"hardware_id": BOX_HARDWARE_ID}, timeout=3)
            if response.status_code == 200:
                data = response.json()
                tenant_id = data.get("tenant_id")
                box_id = data.get("box_id")
                log.info("Bootstrap successful! Assigned Tenant: %s, Box-ID: %s", tenant_id, box_id)
                return tenant_id, box_id
            log.warning(
                "Handshake pending or rejected (%s: %s). Retrying in 5s...",
                response.status_code,
                response.text,
            )
        except Exception as exc:
            log.warning("Gateway not reachable during bootstrap (%s). Retrying in 5s...", exc)

        time.sleep(5)


async def _browse_children(node) -> list[tuple[int, str, ua.NodeClass, object]]:
    """
    Liefert (ns_index, browse_name, node_class, child) fuer alle Kinder von `node`.
    Knoten mit NodeId-Namespace 0 (OPC-UA-Basis/Server, z.B. ServerStatus) werden konsequent ausgefiltert.
    """
    result = []
    for child in await node.get_children():
        if child.nodeid.NamespaceIndex == 0:
            continue
        try:
            browse_name = await child.read_browse_name()
            node_class = await child.read_node_class()
        except Exception:
            continue
        result.append((browse_name.NamespaceIndex, browse_name.Name or "", node_class, child))
    return result


async def find_deviceset(client):
    """Findet Objects/DeviceSet (OPC 10000-100) ohne auf einen Namespace-Index festgenagelt zu sein."""
    for _ns, name, node_class, child in await _browse_children(client.nodes.objects):
        if name == "DeviceSet" and node_class == ua.NodeClass.Object:
            return child
    return None


async def resolve_machine_node(client, machine_hint: str):
    """
    Loest den Maschinenknoten unter Objects/DeviceSet auf.
    Reihenfolge: 1) BrowseName == machine_hint (case-insensitive),
                 2) genau eine Maschine unter DeviceSet -> diese (mit Warnung),
                 3) sonst None (mehrdeutig oder nicht vorhanden).
    Rueckgabe: (machine_name, node) oder None.
    """
    deviceset = await find_deviceset(client)
    if deviceset is None:
        log.warning("Objects/DeviceSet nicht gefunden")
        return None

    candidates = [
        (name, node)
        for _ns, name, node_class, node in await _browse_children(deviceset)
        if node_class == ua.NodeClass.Object
    ]
    if not candidates:
        log.warning("DeviceSet enthaelt keine Maschinen")
        return None

    hint = (machine_hint or "").strip().lower()
    for name, node in candidates:
        if name.lower() == hint:
            return name, node

    if len(candidates) == 1:
        log.warning(
            "Maschine '%s' nicht unter DeviceSet gefunden, verwende die einzige vorhandene: '%s'",
            machine_hint,
            candidates[0][0],
        )
        return candidates[0]

    log.warning(
        "Maschine '%s' nicht eindeutig aufloesbar. Vorhanden: %s",
        machine_hint,
        [name for name, _ in candidates],
    )
    return None


async def find_variable_in_subtree(root, names: list[str], max_depth: int = MAX_SEARCH_DEPTH):
    """
    Breitensuche unterhalb von `root` nach einer Variable mit einem der BrowseNames.
    Prioritaet folgt der Reihenfolge in `names`; innerhalb eines Namens gewinnt der flachste Treffer.
    Rueckgabe: (node, relativer_pfad) oder None.
    """
    wanted = [n.lower() for n in names]
    found: dict[str, tuple[object, str]] = {}
    queue = deque([(root, 0, "")])

    while queue:
        node, depth, path = queue.popleft()
        if depth >= max_depth:
            continue
        try:
            children = await _browse_children(node)
        except Exception:
            continue
        for _ns, name, node_class, child in children:
            child_path = f"{path}/{name}"
            lname = name.lower()
            if node_class == ua.NodeClass.Variable:
                if lname in wanted and lname not in found:
                    found[lname] = (child, child_path)
            elif node_class == ua.NodeClass.Object:
                queue.append((child, depth + 1, child_path))

    for lname in wanted:
        if lname in found:
            return found[lname]
    return None


async def find_state_machine_value(root, object_names: list[str], max_depth: int = MAX_SEARCH_DEPTH):
    """
    Findet eine Zustandsmaschine (z. B. MachineryItemState, MachineryOperationMode) und liefert deren Wert.
    Das OBJEKT wird ueber seinen BrowseName gesucht, der Wert steht in seinem Kind `CurrentState`. So gibt es
    keine Verwechslung zwischen mehreren Zustandsmaschinen, die alle `CurrentState` heissen, und das Ergebnis
    haengt nicht von der Reihenfolge ab, in der ein Server seine Knoten liefert.
    Fallback fuer vereinfachte Server: eine Variable mit dem Namen der Zustandsmaschine.
    Prioritaet folgt `object_names`, innerhalb eines Namens gewinnt der flachste Treffer.
    Rueckgabe: (node, relativer_pfad) oder None.
    """
    wanted = [n.lower() for n in object_names]
    objects_found: dict[str, tuple[object, str]] = {}
    variables_found: dict[str, tuple[object, str]] = {}
    queue = deque([(root, 0, "")])

    while queue:
        node, depth, path = queue.popleft()
        if depth >= max_depth:
            continue
        try:
            children = await _browse_children(node)
        except Exception:
            continue
        for _ns, name, node_class, child in children:
            child_path = f"{path}/{name}"
            lname = name.lower()
            if node_class == ua.NodeClass.Object:
                if lname in wanted and lname not in objects_found:
                    objects_found[lname] = (child, child_path)
                queue.append((child, depth + 1, child_path))
            elif node_class == ua.NodeClass.Variable and lname in wanted and lname not in variables_found:
                variables_found[lname] = (child, child_path)

    for lname in wanted:
        if lname in objects_found:
            obj, path = objects_found[lname]
            try:
                for _ns, name, node_class, child in await _browse_children(obj):
                    if node_class == ua.NodeClass.Variable and name.lower() == "currentstate":
                        return child, f"{path}/{name}"
            except Exception:
                pass
        if lname in variables_found:
            return variables_found[lname]
    return None


# OPC 10000-100 (DI): DeviceHealthEnumeration -> (status, error_code)
DEVICE_HEALTH_MAP: dict[int, tuple[str, str | None]] = {
    0: ("ok", None),  # NORMAL
    1: ("error", "FAILURE"),
    2: ("warning", "CHECK_FUNCTION"),
    3: ("warning", "OFF_SPEC"),
    4: ("warning", "MAINTENANCE_REQUIRED"),
}
_DEVICE_HEALTH_BY_KEY = {
    "normal": 0,
    "failure": 1,
    "checkfunction": 2,
    "offspec": 3,
    "maintenancerequired": 4,
}


def _unwrap(raw_val):
    """LocalizedText -> str; alles andere unveraendert."""
    if isinstance(raw_val, ua.LocalizedText):
        return raw_val.Text
    return raw_val


def normalize_device_health(raw_val) -> tuple[str, str | None]:
    """
    Bildet einen DI-DeviceHealth-Wert exakt auf (status, error_code) ab.
    Akzeptiert Enum-Integer (0..4), Enum-Namen in gaengiger Schreibweise
    ('CHECK_FUNCTION', 'CheckFunction', ...) sowie LocalizedText.
    Unbekannte Werte -> ("warning", "UNKNOWN_DEVICE_HEALTH_<wert>").
    """
    raw = _unwrap(raw_val)
    if raw is None:
        return "ok", None

    code: int | None = None
    if isinstance(raw, bool):
        code = None
    elif isinstance(raw, int):  # inkl. IntEnum
        code = int(raw)
    else:
        text = str(raw).strip()
        if text.lstrip("-").isdigit():
            code = int(text)
        else:
            code = _DEVICE_HEALTH_BY_KEY.get(re.sub(r"[\s_\-]", "", text).lower())

    if code in DEVICE_HEALTH_MAP:
        return DEVICE_HEALTH_MAP[code]
    return "warning", f"UNKNOWN_DEVICE_HEALTH_{raw}"


def normalize_machine_status(raw_val, device_health: bool = False) -> tuple[str, str | None]:
    """
    Bildet Status-Werte auf (status, error_code) ab. status in {"ok", "warning", "error"}.

    device_health=True : Wert stammt von einem DI-DeviceHealth-Knoten (Enum 0..4, siehe oben).
    device_health=False: generischer Fallback fuer herstellerspezifische Status-Knoten (String-Heuristik;
                         Zahlen 0/1/2 = ok/warning/error ist hier nur eine Heuristik, KEIN DI-Enum).
    """
    if device_health:
        return normalize_device_health(raw_val)

    raw_val = _unwrap(raw_val)
    if raw_val is None:
        return "ok", None

    text = str(raw_val).strip()
    lower = text.lower()

    if lower in ("", "ok", "normal", "good", "0"):
        return "ok", None

    if lower in (
        "warning",
        "warn",
        "checkfunction",
        "check_function",
        "offspec",
        "off_spec",
        "maintenancerequired",
        "maintenance_required",
        "1",
    ):
        return "warning", text

    if lower in ("error", "failure", "fault", "alarm", "critical", "2"):
        return "error", text

    # Unbekannte nicht-leere Statuswerte konservativ als warning markieren
    return "warning", text


def send_telemetry(
    tenant_id: str,
    box_id: str,
    machine_id: str,
    temp_val: float,
    parts_val: int | None = None,
    spindle_rotating: bool | None = None,
    operation_hours: float | None = None,
    power_on_hours: float | None = None,
    machinery_item_state: str | None = None,
    machinery_operation_mode: str | None = None,
) -> None:
    telemetry_data: dict[str, object] = {
        "temperature": float(temp_val),
    }
    if parts_val is not None:
        telemetry_data["parts_produced"] = int(parts_val)
    if spindle_rotating is not None:
        telemetry_data["spindle_rotating"] = bool(spindle_rotating)
    if operation_hours is not None:
        telemetry_data["operation_hours"] = float(operation_hours)
    if power_on_hours is not None:
        telemetry_data["power_on_hours"] = float(power_on_hours)
    if machinery_item_state:
        telemetry_data["machinery_item_state"] = machinery_item_state
    if machinery_operation_mode:
        telemetry_data["machinery_operation_mode"] = machinery_operation_mode

    payload = {
        "tenant_id": tenant_id,
        "box_id": box_id,
        "machine_id": machine_id,
        "telemetry": telemetry_data,
    }
    response = requests.post(TELEMETRY_URL, json=payload, timeout=3)
    if response.status_code != 200:
        log.warning(
            "Gateway hat Telemetrie abgelehnt für %s: %s - %s",
            machine_id,
            response.status_code,
            response.text,
        )


def send_status_update(
    tenant_id: str,
    machine_id: str,
    status: str,
    error_code: str | None,
) -> bool:
    status_url = f"{BASE_GATEWAY_URL}/v1/machines/{machine_id}/status"
    payload = {
        "tenant_id": tenant_id,
        "status": status,
        "error_code": error_code,
    }
    response = requests.patch(status_url, json=payload, timeout=3)
    if response.status_code != 200:
        log.warning(
            "Gateway hat Status-Update abgelehnt für %s (%s): %s - %s",
            machine_id,
            status,
            response.status_code,
            response.text,
        )
        return False
    return True


async def poll_loop(tenant_id: str, box_id: str, machine_id: str, opc_endpoint: str):
    last_reported_status_key: tuple[str, str | None] | None = None

    while True:
        client = Client(url=opc_endpoint)
        try:
            async with client:
                log.info("Verbunden mit OPC-UA Server für Maschine %s bei %s", machine_id, opc_endpoint)

                machine = await resolve_machine_node(client, machine_id)
                if not machine:
                    log.warning("Maschinenknoten fuer %s nicht gefunden! Suche erneut in 5s...", machine_id)
                    await asyncio.sleep(5)
                    continue
                machine_name, machine_node = machine

                temp_hit = await find_variable_in_subtree(machine_node, TEMP_NODE_NAMES)
                status_hit = await find_variable_in_subtree(
                    machine_node, HEALTH_NODE_NAMES + STATUS_FALLBACK_NAMES
                )
                parts_hit = await find_variable_in_subtree(machine_node, PARTS_NODE_NAMES)
                spindle_hit = await find_variable_in_subtree(machine_node, SPINDLE_ROTATING_NAMES)
                op_dur_hit = await find_variable_in_subtree(machine_node, OPERATION_DURATION_NAMES)
                pwr_dur_hit = await find_variable_in_subtree(machine_node, POWER_ON_DURATION_NAMES)
                item_state_hit = await find_state_machine_value(machine_node, MACHINERY_ITEM_STATE_NAMES)
                op_mode_hit = await find_state_machine_value(machine_node, MACHINERY_OPERATION_MODE_NAMES)

                temp_node = temp_hit[0] if temp_hit else None
                status_node = status_hit[0] if status_hit else None
                parts_node = parts_hit[0] if parts_hit else None
                spindle_node = spindle_hit[0] if spindle_hit else None
                op_dur_node = op_dur_hit[0] if op_dur_hit else None
                pwr_dur_node = pwr_dur_hit[0] if pwr_dur_hit else None
                item_state_node = item_state_hit[0] if item_state_hit else None
                op_mode_node = op_mode_hit[0] if op_mode_hit else None
                is_device_health = bool(status_hit and status_hit[1].lower().endswith("/devicehealth"))

                if not temp_node:
                    log.warning(
                        "Temperatur-Knoten unter DeviceSet/%s nicht gefunden! Suche erneut in 5s...",
                        machine_name,
                    )
                    await asyncio.sleep(5)
                    continue

                log.info(
                    "Gebunden fuer %s an DeviceSet/%s (Temp: %s | Status/Health: %s | Teile: %s | Spindel: %s | ItemState: %s | OpMode: %s)",
                    machine_id,
                    machine_name,
                    temp_hit[1],
                    status_hit[1] if status_hit else "nein -> default ok",
                    parts_hit[1] if parts_hit else "nein",
                    spindle_hit[1] if spindle_hit else "nein",
                    item_state_hit[1] if item_state_hit else "nein",
                    op_mode_hit[1] if op_mode_hit else "nein",
                )

                while True:
                    try:
                        temp_val = float(await temp_node.read_value())
                        raw_status = await status_node.read_value() if status_node else "ok"
                        mapped_status, error_code = normalize_machine_status(
                            raw_status, device_health=is_device_health
                        )

                        parts_val = int(await parts_node.read_value()) if parts_node else None
                        spindle_rotating = bool(await spindle_node.read_value()) if spindle_node else None
                        op_hours = (
                            round(float(await op_dur_node.read_value()) / 3_600_000.0, 2)
                            if op_dur_node
                            else None
                        )
                        pwr_hours = (
                            round(float(await pwr_dur_node.read_value()) / 3_600_000.0, 2)
                            if pwr_dur_node
                            else None
                        )
                        raw_item_state = (
                            _unwrap(await item_state_node.read_value()) if item_state_node else None
                        )
                        raw_op_mode = _unwrap(await op_mode_node.read_value()) if op_mode_node else None
                        machinery_item_state = (
                            str(raw_item_state).strip() if raw_item_state is not None else None
                        )
                        machinery_operation_mode = (
                            str(raw_op_mode).strip() if raw_op_mode is not None else None
                        )

                        # 1. Messwerte an /v1/telemetry senden
                        send_telemetry(
                            tenant_id,
                            box_id,
                            machine_id,
                            temp_val,
                            parts_val=parts_val,
                            spindle_rotating=spindle_rotating,
                            operation_hours=op_hours,
                            power_on_hours=pwr_hours,
                            machinery_item_state=machinery_item_state or None,
                            machinery_operation_mode=machinery_operation_mode or None,
                        )

                        # 2. Statuswechsel nur bei Änderung an PATCH /v1/machines/<id>/status melden
                        status_key = (mapped_status, error_code)
                        if status_key != last_reported_status_key:
                            if send_status_update(tenant_id, machine_id, mapped_status, error_code):
                                last_reported_status_key = status_key
                                log.info(
                                    "Statuswechsel gesendet [%s] -> %s (code=%s)",
                                    machine_id,
                                    mapped_status,
                                    error_code,
                                )

                        log.info(
                            "Telemetrie gesendet [%s] -> Temp: %.1f °C | Status: %s | Teile: %s | Spindel: %s | State: %s | Mode: %s",
                            machine_id,
                            temp_val,
                            mapped_status,
                            parts_val if parts_val is not None else "-",
                            spindle_rotating if spindle_rotating is not None else "-",
                            machinery_item_state or "-",
                            machinery_operation_mode or "-",
                        )

                    except Exception as read_err:
                        log.error("Fehler beim Lesen/Senden für %s: %s", machine_id, read_err)
                        break

                    await asyncio.sleep(POLL_INTERVAL)

        except Exception as exc:
            log.warning("OPC-UA Verbindung verloren für %s (%s). Reconnect in 5s...", machine_id, exc)
            await asyncio.sleep(5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="uretOS Telemetry Poller")
    parser.add_argument("--machine", required=True, help="Machine ID / Name")
    parser.add_argument("--endpoint", required=True, help="OPC-UA Endpoint URL")
    args = parser.parse_args()

    log.info("Initialisiere uretOS Telemetrie-Poller für Maschine %s bei %s", args.machine, args.endpoint)
    tenant_id, box_id = bootstrap_configuration()
    asyncio.run(poll_loop(tenant_id, box_id, args.machine, args.endpoint))