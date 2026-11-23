"""
Standard-Compliant Single-Machine OPC-UA Server Simulator for uretOS Virtual Shopfloor.
Located in tools/ as a companion utility for trial periods and testing.

Address space (Schritt 1):

Objects
├── Machines                                   (ns=Machinery)   OPC 40001-1: Einstiegspunkt aller Maschinen
│   └── <MACHINE_NAME>  --Organizes-->  (dieselbe Maschine wie unter DeviceSet, kein zweiter Knoten)
└── DeviceSet                                  (ns=DI)          DI-Sicht, vorerst beibehalten
    └── <MACHINE_NAME>                         (ns=custom)
        ├── Identification                     (ns=DI)
        │   ├── Manufacturer / Model / SerialNumber / ProductInstanceUri   (ns=DI)
        ├── DeviceHealth                       (ns=DI)       Int32, DI DeviceHealthEnumeration
        ├── MachineryItemState                 (ns=Machinery)
        │   └── CurrentState                                 LocalizedText
        ├── MachineryOperationMode             (ns=Machinery)
        │   └── CurrentState                                 LocalizedText
        ├── Monitoring                         (ns=MachineTool)
        │   ├── MachineTool                    (ns=MachineTool)
        │       └── OperationCounters          (ns=DI, per HasAddIn)
        │           ├── PowerOnDuration        (ns=DI, Property)  Duration (Double, ms), monoton wachsend
        │           ├── OperationDuration      (ns=DI, Property)  Duration (Double, ms), waechst nur waehrend der Produktion
        │           └── PartsProducedInLifetime (ns=MachineTool)  UInt64, zaehlt nur waehrend der Produktion
        │   └── MainSpindle                    (ns=custom)  <MonitoredElement>, SpindleMonitoringType
        │       ├── Name                       (ns=MachineTool, Property)  String
        │       └── IsRotating                 (ns=MachineTool)  Boolean, dreht im Bearbeitungsabschnitt jedes Teilezyklus
        └── ParameterSet                       (ns=DI)
            └── Temperature                    (ns=custom)  Double, °C
"""
from __future__ import annotations

import json
import logging
import os
import random
import socket
import threading
import time
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from opcua import Server, ua
from zeroconf import ServiceInfo, Zeroconf

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("opc-machine-sim")

MACHINE_NAME = os.environ.get("MACHINE_NAME", "VirtualCNC-01")
MANUFACTURER = os.environ.get("MANUFACTURER", "uretOS Robotics")
MODEL = os.environ.get("MODEL", "V-Mill 500")
SERIAL = os.environ.get("SERIAL", "UR-2026-001")
PORT = int(os.environ.get("PORT", "4840"))
CONTROL_PORT = int(os.environ.get("CONTROL_PORT", str(PORT + 4000)))
AUTO_TEMP_PAUSE_SEC = float(os.environ.get("AUTO_TEMP_PAUSE_SEC", "15.0"))
# Optional: Startwert der Betriebsstunden explizit setzen (Default: aus der Seriennummer abgeleitet)
POWER_ON_HOURS_START = os.environ.get("POWER_ON_HOURS_START")
# Teilezaehler: Zykluszeit/Startwert/Werkzeugwechsel-Wahrscheinlichkeit/Zufalls-Seed fuer Tests ueberschreibbar
CYCLE_TIME_SEC = os.environ.get("CYCLE_TIME_SEC")
PARTS_START = os.environ.get("PARTS_START")
TOOL_CHANGE_PROB = float(os.environ.get("TOOL_CHANGE_PROB", "0.04"))
SIM_SEED = os.environ.get("SIM_SEED")

# OPC 10000-100 (DI): DeviceHealthEnumeration
HEALTH_NAMES = {
    0: "NORMAL",
    1: "FAILURE",
    2: "CHECK_FUNCTION",
    3: "OFF_SPEC",
    4: "MAINTENANCE_REQUIRED",
}
HEALTH_BY_NAME = {name: value for value, name in HEALTH_NAMES.items()}

# Komfort-Mapping für E2E-Tests: POST /opc/set {"status": "ok|warning|error"}
STATUS_TO_HEALTH = {"ok": 0, "warning": 2, "error": 1}
HEALTH_TO_STATUS = {0: "ok", 1: "error", 2: "warning", 3: "warning", 4: "warning"}

# OPC 40001-1 (Machinery)
ITEM_STATES = ("Executing", "NotExecuting", "OutOfService")
OPERATION_MODES = ("None", "Processing", "Setup")


def parse_health(value) -> int:
    """Akzeptiert Enum-Name ('CHECK_FUNCTION'), Zahl (2) oder ok/warning/error."""
    if isinstance(value, bool):
        raise ValueError("health must not be bool")
    if isinstance(value, int):
        if value in HEALTH_NAMES:
            return value
        raise ValueError(f"unknown DeviceHealth value {value}")
    text = str(value).strip()
    if text.lower() in STATUS_TO_HEALTH:
        return STATUS_TO_HEALTH[text.lower()]
    if text.upper() in HEALTH_BY_NAME:
        return HEALTH_BY_NAME[text.upper()]
    if text.isdigit() and int(text) in HEALTH_NAMES:
        return int(text)
    raise ValueError(f"unknown DeviceHealth value '{value}'")


def parse_choice(value, allowed: tuple[str, ...], label: str) -> str:
    for candidate in allowed:
        if str(value).strip().lower() == candidate.lower():
            return candidate
    raise ValueError(f"unknown {label} '{value}', allowed: {list(allowed)}")


def read_text(var) -> str:
    val = var.get_value()
    return val.Text if isinstance(val, ua.LocalizedText) else str(val)


def initial_power_on_hours(serial: str) -> float:
    """Plausibler, pro Seriennummer reproduzierbarer Startwert der Betriebsstunden (2000.0 .. 24999.9 h)."""
    if POWER_ON_HOURS_START:
        return float(POWER_ON_HOURS_START)
    return 2000.0 + (zlib.crc32(serial.encode("utf-8")) % 230000) / 10.0


def machine_profile(serial: str) -> tuple[float, float]:
    """Pro Seriennummer reproduzierbar: (mittlere Zykluszeit je Teil in s: 36..54, Auslastung: 0.45..0.65)."""
    cycle = 36.0 + (zlib.crc32((serial + ":cycle").encode("utf-8")) % 1801) / 100.0
    util = 0.45 + (zlib.crc32((serial + ":util").encode("utf-8")) % 2001) / 10000.0
    if CYCLE_TIME_SEC:
        cycle = float(CYCLE_TIME_SEC)
    return cycle, util


class PartCounter:
    """Teilezaehler: pro Teil eine schwankende Zykluszeit; zaehlt nur, solange produziert wird."""

    def __init__(self, start: int, cycle_mean_sec: float, rng: random.Random, tool_change_prob: float = 0.04):
        self.count = int(start)
        self.mean = float(cycle_mean_sec)
        self.rng = rng
        self.tool_change_prob = tool_change_prob
        self.progress = 0.0
        self.cycle = self._next_cycle()

    def _next_cycle(self) -> float:
        # Streuung von Teil zu Teil (ca. 4 %), gelegentlich ein laengerer Zyklus (Werkzeug-/Teilewechsel)
        base = self.mean * min(1.2, max(0.85, self.rng.gauss(1.0, 0.04)))
        # Die Spindel dreht nur im Bearbeitungsabschnitt (75..85 % des Grundzyklus); der Rest sowie ein
        # eventueller Werkzeugwechsel ist Stillstand (Teile laden/entladen).
        cut = base * self.rng.uniform(0.75, 0.85)
        extra = self.rng.uniform(25.0, 90.0) if self.rng.random() < self.tool_change_prob else 0.0
        cycle = base + extra
        self.stand = cycle - cut
        return cycle

    def rotating(self, producing: bool) -> bool:
        """Spindel dreht, wenn produziert wird und der Stillstandsanteil des aktuellen Zyklus vorbei ist."""
        return producing and self.progress >= self.stand

    def advance(self, dt: float, producing: bool) -> int:
        """Schreibt dt Sekunden fort, liefert die Zahl neu fertiggestellter Teile."""
        if not producing:
            return 0
        self.progress += dt
        made = 0
        while self.progress >= self.cycle:
            self.progress -= self.cycle
            self.count += 1
            made += 1
            self.cycle = self._next_cycle()
        return made


def is_producing(item_state_var, health_var) -> bool:
    """Produziert wird, solange MachineryItemState = Executing und DeviceHealth nicht FAILURE ist."""
    return read_text(item_state_var) == "Executing" and int(health_var.get_value()) != HEALTH_BY_NAME["FAILURE"]


def add_machinery_state(parent, idx: int, name: str, initial: str):
    """Vereinfachte Zustandsmaschine: Objekt <name> mit Variable CurrentState (LocalizedText)."""
    obj = parent.add_object(idx, name)
    current = obj.add_variable(idx, "CurrentState", ua.LocalizedText(initial))
    current.set_writable()
    return current


def make_control_handler(
    nodes: dict,
    state_lock: threading.Lock,
    manual_state: dict,
):
    health_var = nodes["health"]
    item_state_var = nodes["item_state"]
    op_mode_var = nodes["op_mode"]
    temp_var = nodes["temperature"]
    power_on_var = nodes["power_on"]
    operation_var = nodes["operation"]
    spindle_var = nodes["spindle"]
    parts_var = nodes["parts"]

    class ControlHandler(BaseHTTPRequestHandler):
        def _send_json(self, code: int, payload: dict) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            if self.path != "/opc/state":
                self._send_json(404, {"error": "not found"})
                return
            with state_lock:
                paused_remaining = max(0.0, manual_state["temp_pause_until"] - time.monotonic())
                health = int(health_var.get_value())
                self._send_json(
                    200,
                    {
                        "machine_name": MACHINE_NAME,
                        "opc_port": PORT,
                        "control_port": CONTROL_PORT,
                        # abgeleitet aus DeviceHealth (Abwärtskompatibilität zu bisherigen E2E-Tests)
                        "status": HEALTH_TO_STATUS.get(health, "warning"),
                        "device_health": health,
                        "device_health_name": HEALTH_NAMES.get(health, "UNKNOWN"),
                        "machinery_item_state": read_text(item_state_var),
                        "machinery_operation_mode": read_text(op_mode_var),
                        "temperature": temp_var.get_value(),
                        "power_on_hours": round(power_on_var.get_value() / 3_600_000.0, 2),
                        "operation_hours": round(operation_var.get_value() / 3_600_000.0, 2),
                        "parts_produced": int(parts_var.get_value()),
                        "cycle_time_mean_sec": round(nodes["cycle_mean_sec"], 2),
                        "producing": is_producing(item_state_var, health_var),
                        "spindle_rotating": bool(spindle_var.get_value()),
                        "auto_temp_paused": paused_remaining > 0,
                        "auto_temp_pause_remaining_sec": round(paused_remaining, 2),
                    },
                )

        def do_POST(self) -> None:
            if self.path != "/opc/set":
                self._send_json(404, {"error": "not found"})
                return

            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length > 0 else b"{}"
            try:
                data = json.loads(raw.decode("utf-8"))
            except Exception as exc:
                self._send_json(400, {"error": f"invalid json: {exc}"})
                return

            updated = {}
            try:
                with state_lock:
                    # "status" (ok|warning|error) ist ein Alias für "device_health"
                    health_in = data.get("device_health", data.get("status"))
                    if health_in is not None:
                        health = parse_health(health_in)
                        health_var.set_value(ua.Variant(health, ua.VariantType.Int32))
                        updated["device_health"] = health
                        updated["device_health_name"] = HEALTH_NAMES[health]
                        updated["status"] = HEALTH_TO_STATUS[health]
                        log.info(
                            "OPC DeviceHealth gesetzt [%s] -> %s (%d)",
                            MACHINE_NAME, HEALTH_NAMES[health], health,
                        )

                    if data.get("machinery_item_state") is not None:
                        value = parse_choice(data["machinery_item_state"], ITEM_STATES, "machinery_item_state")
                        item_state_var.set_value(ua.LocalizedText(value))
                        updated["machinery_item_state"] = value
                        log.info("OPC MachineryItemState gesetzt [%s] -> %s", MACHINE_NAME, value)

                    if data.get("machinery_operation_mode") is not None:
                        value = parse_choice(
                            data["machinery_operation_mode"], OPERATION_MODES, "machinery_operation_mode"
                        )
                        op_mode_var.set_value(ua.LocalizedText(value))
                        updated["machinery_operation_mode"] = value
                        log.info("OPC MachineryOperationMode gesetzt [%s] -> %s", MACHINE_NAME, value)

                    if "temperature" in data and data["temperature"] is not None:
                        new_temp = round(float(data["temperature"]), 1)
                        temp_var.set_value(ua.Variant(new_temp, ua.VariantType.Double))
                        manual_state["current_temp"] = new_temp
                        manual_state["temp_pause_until"] = time.monotonic() + AUTO_TEMP_PAUSE_SEC
                        updated["temperature"] = new_temp
                        updated["auto_temp_paused_for_sec"] = AUTO_TEMP_PAUSE_SEC
                        log.info(
                            "OPC Temperatur gesetzt [%s] -> %.1f °C (Auto-Drift pausiert für %.1fs)",
                            MACHINE_NAME,
                            new_temp,
                            AUTO_TEMP_PAUSE_SEC,
                        )

                    if data.get("resume_auto_temp") is True:
                        manual_state["temp_pause_until"] = 0.0
                        updated["auto_temp_paused"] = False
                        log.info("OPC Auto-Temperatur freigegeben [%s]", MACHINE_NAME)
            except (ValueError, TypeError) as exc:
                self._send_json(400, {"error": str(exc)})
                return

            self._send_json(200, {"ok": True, "machine_name": MACHINE_NAME, "updated": updated})

        def log_message(self, fmt: str, *args) -> None:
            return

    return ControlHandler


def main() -> None:
    server = Server()
    server.set_endpoint(f"opc.tcp://0.0.0.0:{PORT}")

    uri_di = "http://opcfoundation.org/UA/DI/"
    uri_machinery = "http://opcfoundation.org/UA/Machinery/"

    idx_di = server.register_namespace(uri_di)
    idx_mach = server.register_namespace(uri_machinery)
    idx_custom = server.register_namespace("http://uretos.io/opcua/machine")
    # MachineTool-Namespace: dort liegen Monitoring/MachineTool (OPC 40501-1). Eine echte Werkzeugmaschine
    # registriert ihn immer; Clients erkennen daran den Maschinentyp.
    idx_mt = server.register_namespace("http://opcfoundation.org/UA/MachineTool/")

    objects = server.get_objects_node()

    deviceset = objects.add_object(idx_di, "DeviceSet")
    machine_node = deviceset.add_object(idx_custom, MACHINE_NAME)

    # Machinery (OPC 40001-1): Alle Maschinen muessen unter Objects/Machines auffindbar sein.
    # Dieselbe Maschine wird per Organizes-Referenz eingehaengt (kein zweiter Knoten, keine doppelten Werte).
    machines_folder = objects.add_folder(idx_mach, "Machines")
    machines_folder.add_reference(machine_node, ua.ObjectIds.Organizes)

    # --- Identification (DI) ---
    ident_node = machine_node.add_object(idx_di, "Identification")
    ident_node.add_variable(idx_di, "Manufacturer", MANUFACTURER)
    ident_node.add_variable(idx_di, "Model", MODEL)
    ident_node.add_variable(idx_di, "SerialNumber", SERIAL)
    ident_node.add_variable(idx_di, "ProductInstanceUri", f"urn:uretos:machine:{MACHINE_NAME}")

    # --- Health (DI): DeviceHealth, Default NORMAL ---
    health_var = machine_node.add_variable(
        idx_di, "DeviceHealth", ua.Variant(HEALTH_BY_NAME["NORMAL"], ua.VariantType.Int32)
    )
    health_var.set_writable()

    # --- Zustand / Betriebsmodus (Machinery) ---
    item_state_var = add_machinery_state(machine_node, idx_mach, "MachineryItemState", "Executing")
    op_mode_var = add_machinery_state(machine_node, idx_mach, "MachineryOperationMode", "Processing")

    # --- Monitoring (Machine Tools): MachineTool/OperationCounters/... ---
    # Betriebsdauer seit Inbetriebnahme: Duration = Double in Millisekunden, zaehlt nie zurueck.
    power_on_hours0 = initial_power_on_hours(SERIAL)
    power_on_base_ms = power_on_hours0 * 3_600_000.0
    power_on_t0 = time.monotonic()
    monitoring_node = machine_node.add_object(idx_mt, "Monitoring")
    mt_monitoring_node = monitoring_node.add_object(idx_mt, "MachineTool")
    # OPC 40501-1 / 40001-1: 2:OperationCounters (DI-Namespace) haengt per HasAddIn (nicht HasComponent) an MachineTool.
    counters_node = mt_monitoring_node.add_object(idx_di, "OperationCounters")
    mt_monitoring_node.delete_reference(counters_node, ua.ObjectIds.HasComponent)
    # Achtung: python-opcua wandelt eine blanke Zahl >255 faelschlich in eine 1-Byte-NodeId um und bricht dann beim
    # Senden der Browse-Antwort ab. Deshalb hier ein vollstaendiges NodeId-Objekt uebergeben.
    mt_monitoring_node.add_reference(counters_node, ua.NodeId(ua.ObjectIds.HasAddIn))
    # 2:PowerOnDuration ist eine Property (HasProperty) im DI-Namespace.
    power_on_var = counters_node.add_property(
        idx_di,
        "PowerOnDuration",
        ua.Variant(power_on_base_ms, ua.VariantType.Double),
        datatype=ua.NodeId(ua.ObjectIds.Duration),
    )

    # Stueckzahl seit Inbetriebnahme (UInt64, ohne Qualitaetsinformation). Startwert passend zur Betriebsdauer:
    # Betriebsstunden x Auslastung x Teile pro Stunde (aus der mittleren Zykluszeit).
    cycle_mean_sec, utilization = machine_profile(SERIAL)
    parts_start = int(PARTS_START) if PARTS_START else int(power_on_hours0 * utilization * 3600.0 / cycle_mean_sec)
    part_counter = PartCounter(
        parts_start, cycle_mean_sec, random.Random(SIM_SEED if SIM_SEED else None), TOOL_CHANGE_PROB
    )
    parts_var = counters_node.add_variable(
        idx_mt, "PartsProducedInLifetime", ua.Variant(parts_start, ua.VariantType.UInt64)
    )

    # 2:OperationDuration (DI, Property): Dauer, in der die Maschine eingeschaltet ist UND eine Taetigkeit ausfuehrt
    # (hier: produziert). Startwert = Betriebsstunden x Auslastung, passt damit zum Teilezaehler
    # (OperationDuration / Teile = mittlere Zykluszeit). Zaehlt nie zurueck.
    operation_ms = power_on_hours0 * utilization * 3_600_000.0
    operation_var = counters_node.add_property(
        idx_di,
        "OperationDuration",
        ua.Variant(operation_ms, ua.VariantType.Double),
        datatype=ua.NodeId(ua.ObjectIds.Duration),
    )

    # Spindel als <MonitoredElement> (SpindleMonitoringType) unter Monitoring: Name (Property) und IsRotating
    # liegen im MachineTool-Namespace; DisplayName = Wert von Name (Empfehlung der Spec).
    spindle_node = monitoring_node.add_object(idx_custom, "MainSpindle")
    spindle_node.set_attribute(
        ua.AttributeIds.DisplayName,
        ua.DataValue(ua.Variant(ua.LocalizedText("Main Spindle"), ua.VariantType.LocalizedText)),
    )
    spindle_node.add_property(idx_mt, "Name", "Main Spindle")
    spindle_var = spindle_node.add_variable(idx_mt, "IsRotating", ua.Variant(False, ua.VariantType.Boolean))

    # --- Prozesswerte (DI ParameterSet) ---
    param_set = machine_node.add_object(idx_di, "ParameterSet")
    temp_var = param_set.add_variable(idx_custom, "Temperature", ua.Variant(38.5, ua.VariantType.Double))
    temp_var.set_writable()

    nodes = {
        "health": health_var,
        "item_state": item_state_var,
        "op_mode": op_mode_var,
        "temperature": temp_var,
        "power_on": power_on_var,
        "parts": parts_var,
        "operation": operation_var,
        "spindle": spindle_var,
        "cycle_mean_sec": cycle_mean_sec,
    }

    state_lock = threading.Lock()
    manual_state = {
        "current_temp": 38.5,
        "temp_pause_until": 0.0,
    }

    server.start()
    log.info("Standard-compliant OPC-UA Server for '%s' running on port %d", MACHINE_NAME, PORT)

    control_server = ThreadingHTTPServer(
        ("0.0.0.0", CONTROL_PORT),
        make_control_handler(nodes, state_lock, manual_state),
    )
    control_thread = threading.Thread(
        target=control_server.serve_forever,
        name=f"opc-control-{MACHINE_NAME}",
        daemon=True,
    )
    control_thread.start()
    log.info("OPC Control HTTP endpoint for '%s' listening on port %d", MACHINE_NAME, CONTROL_PORT)

    zeroconf = None
    info = None
    try:
        service_type = "_opcua-tcp._tcp.local."
        service_name = f"{MACHINE_NAME}._opcua-tcp._tcp.local."

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
        last_tick = time.monotonic()
        while True:
            time.sleep(1)
            now = time.monotonic()
            dt, last_tick = min(now - last_tick, 5.0), now
            power_on_var.set_value(
                ua.Variant(power_on_base_ms + (now - power_on_t0) * 1000.0, ua.VariantType.Double)
            )
            with state_lock:
                producing = is_producing(item_state_var, health_var)
                if part_counter.advance(dt, producing):
                    parts_var.set_value(ua.Variant(part_counter.count, ua.VariantType.UInt64))
                if producing:
                    operation_ms += dt * 1000.0
                    operation_var.set_value(ua.Variant(operation_ms, ua.VariantType.Double))
                spindle_var.set_value(ua.Variant(part_counter.rotating(producing), ua.VariantType.Boolean))
            with state_lock:
                if now < manual_state["temp_pause_until"]:
                    continue
                current_temp = round(38.0 + (time.time() % 10) * 0.15 + (os.getpid() % 3), 1)
                manual_state["current_temp"] = current_temp
                temp_var.set_value(ua.Variant(current_temp, ua.VariantType.Double))
    finally:
        control_server.shutdown()
        control_server.server_close()
        if zeroconf and info:
            zeroconf.unregister_service(info)
            zeroconf.close()
        server.stop()
        log.info("OPC-UA server stopped.")


if __name__ == "__main__":
    main()