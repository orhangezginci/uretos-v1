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

def discover_machines(host: str, port: int, max_machines: int = 5, timeout: float = 3.0) -> list[MachineIdentity]:
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
    results = discover_machines(host, port, max_machines=1, timeout=timeout)
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