"""
uretOS Connector Box Simulator - throwaway internal tool.

Simulates a physical uretOS Connector box booting, discovering OPC-UA machines
(up to the licensed limit), trying a handshake first, falling back to pairing
if unknown (404) or pending (403), and persisting discovered machines via the
autoscan endpoint.

Runtime operational status is pushed separately via
POST /v1/connector-boxes/machine-status (not only at boot).
"""
import logging
import os
import time

import requests
import streamlit as st

from discovery import discover_machines

logging.basicConfig(level=logging.INFO)

GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://localhost:8080")
OPC_UA_HOST = os.environ.get("OPC_UA_HOST", "localhost")
OPC_UA_PORT = int(os.environ.get("OPC_UA_PORT", "4840"))
MAX_LICENSED_MACHINES = 5  # Lizenz-Limit für Maschinen pro Connector Box

LED_OFF = "#333"
LED_GREEN = "#3ddc84"
LED_RED = "#e5484d"

STATUS_OPTIONS = ["ok", "warning", "error"]

BOX_CSS = """
<style>
.uretos-box {
    background: linear-gradient(180deg, #2b2b2e, #1a1a1c);
    border-radius: 14px;
    padding: 28px 32px;
    width: 480px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.4);
    font-family: 'Courier New', monospace;
    color: #ddd;
}
.uretos-title {
    font-size: 15px;
    letter-spacing: 3px;
    color: #aaa;
    margin-bottom: 16px;
}
.uretos-title b { color: #fff; }
.uretos-display {
    background: #0a0f0a;
    border: 2px solid #111;
    border-radius: 4px;
    padding: 14px 18px;
    font-size: 18px;
    line-height: 1.6;
    color: #3ddc84;
    white-space: pre;
    min-height: 56px;
    margin-bottom: 18px;
    text-shadow: 0 0 4px rgba(61,220,132,0.6);
}
.uretos-leds {
    display: flex;
    gap: 24px;
}
.uretos-led-row {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    color: #bbb;
}
.uretos-led-dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    display: inline-block;
}
</style>
"""


def render_box(display_line1, display_line2, leds):
    dots = "".join(
        '<div class="uretos-led-row"><span class="uretos-led-dot" '
        'style="background:' + leds[name] + '"></span>' + name + '</div>'
        for name in ["POWER", "NETWORK", "URETOS", "ERROR"]
    )
    html = (
        BOX_CSS
        + '<div class="uretos-box">'
        + '<div class="uretos-title"><b>URETOS</b> CONNECTOR</div>'
        + '<div class="uretos-display">' + display_line1 + "\n" + display_line2 + "</div>"
        + '<div class="uretos-leds">' + dots + "</div>"
        + "</div>"
    )
    html = str(html) if html is not None else ""
    return html


def push_machine_status(hardware_id: str, machines: list[dict]) -> requests.Response:
    """
    Push operational status to the gateway.

    Only send entries whose status actually changed (caller filters).
    Gateway → machine.command.update_status → status_changed → shopfloor SSE.
    """
    return requests.post(
        GATEWAY_URL + "/v1/connector-boxes/machine-status",
        json={"hardware_id": hardware_id, "machines": machines},
        timeout=25,
    )


def build_status_payload(tracked: list[dict]) -> list[dict]:
    """Build gateway payload; prefer machine_id, fall back to serial/name."""
    payload = []
    for m in tracked:
        entry = {"status": m["status"]}
        if m.get("machine_id"):
            entry["machine_id"] = m["machine_id"]
        if m.get("serial"):
            entry["serial"] = m["serial"]
        if m.get("name"):
            entry["name"] = m["name"]
        payload.append(entry)
    return payload


def main():
    st.title("uretOS Connector Box Simulator")
    st.caption(
        "Boot · OPC-UA Discovery · Handshake/Pair · Autoscan · "
        "Live Status-Push (machine-status)"
    )

    hardware_id = st.text_input("Hardware ID", help="Beispiel: tennant-c-20260928-u31c")
    boot_clicked = st.button("Boot & Connect")

    box_placeholder = st.empty()

    leds = {"POWER": LED_OFF, "NETWORK": LED_OFF, "URETOS": LED_OFF, "ERROR": LED_OFF}
    box_placeholder.markdown(render_box("URETOS CONNECTOR", "READY", leds), unsafe_allow_html=True)

    if boot_clicked and hardware_id:
        # 1. Power On
        leds["POWER"] = LED_GREEN
        box_placeholder.markdown(render_box("BOOTING...", "HARDWARE INIT", leds), unsafe_allow_html=True)
        time.sleep(0.4)

        # 2. Network Connection
        leds["NETWORK"] = LED_GREEN
        box_placeholder.markdown(render_box("NETWORKING...", "DHCP / LINK UP", leds), unsafe_allow_html=True)
        time.sleep(0.4)

        # 3. OPC UA Discovery & Metadata Read (Multi-Machine)
        box_placeholder.markdown(render_box("DISCOVERING...", f"SCANNING :{OPC_UA_PORT}", leds), unsafe_allow_html=True)
        time.sleep(0.6)

        identities = discover_machines(OPC_UA_HOST, OPC_UA_PORT, max_machines=MAX_LICENSED_MACHINES)

        if identities:
            primary_name = str(identities[0].name)[:18].upper()
            count_str = f"FOUND: {len(identities)} MACHINES"
            box_placeholder.markdown(render_box(count_str, primary_name, leds), unsafe_allow_html=True)
        else:
            box_placeholder.markdown(render_box("DISCOVERY WARN", "NO OPC-UA SERVER", leds), unsafe_allow_html=True)
        time.sleep(0.8)

        # 4. Handshake first, fallback to pairing
        try:
            box_placeholder.markdown(render_box("HANDSHAKE...", "VERIFYING TOKEN", leds), unsafe_allow_html=True)
            response = requests.post(
                GATEWAY_URL + "/v1/connector-boxes/handshake",
                json={"hardware_id": hardware_id},
                timeout=25,
            )

            if response.status_code in (404, 403):
                box_placeholder.markdown(render_box("PAIRING...", "INITIAL REGISTRATION", leds), unsafe_allow_html=True)
                response = requests.post(
                    GATEWAY_URL + "/v1/connector-boxes/pair",
                    json={"hardware_id": hardware_id},
                    timeout=25,
                )
                action_msg = "Box erfolgreich gepaired & online!"
            else:
                action_msg = "Handshake erfolgreich durchgeführt!"

        except requests.RequestException as exc:
            leds["ERROR"] = LED_RED
            box_placeholder.markdown(render_box("GATEWAY UNREACHABLE", str(exc)[:32], leds), unsafe_allow_html=True)
            st.error("Could not reach gateway-api: " + str(exc))
            return

        if response.status_code == 200:
            # 5. Autoscan (identity only — once at boot)
            registered_machines = []
            try:
                scan_response = requests.post(
                    GATEWAY_URL + "/v1/connector-boxes/autoscan",
                    json={
                        "hardware_id": hardware_id,
                        "machines": [m.to_dict() for m in identities],
                    },
                    timeout=25,
                )
                if scan_response.status_code == 200:
                    st.toast("Erkannte Maschinen erfolgreich mit Box-Kontext persistiert!", icon="💾")
                    scan_data = scan_response.json()
                    registered_machines = scan_data.get("machines") or []
                else:
                    st.warning("Maschinen-Persistenz ergab Status: " + str(scan_response.status_code))
            except requests.RequestException as exc:
                st.warning(f"Konnte Maschinen-Autoscan nicht senden: {exc}")

            # Track machines for live status UI (merge discovery + registration ids)
            tracked = []
            for idx, ident in enumerate(identities):
                d = ident.to_dict()
                reg = registered_machines[idx] if idx < len(registered_machines) else {}
                if isinstance(reg, dict):
                    machine_id = reg.get("machine_id") or reg.get("id")
                else:
                    machine_id = None
                tracked.append({
                    "machine_id": machine_id,
                    "name": d.get("name"),
                    "serial": d.get("serial"),
                    "status": d.get("status") or "ok",
                    "last_pushed_status": None,  # force initial push
                })

            # 6. Initial status push (after registration)
            box_placeholder.markdown(render_box("STATUS PUSH...", "INITIAL ONLINE", leds), unsafe_allow_html=True)
            try:
                status_resp = push_machine_status(hardware_id, build_status_payload(tracked))
                if status_resp.status_code == 200:
                    for m in tracked:
                        m["last_pushed_status"] = m["status"]
                    st.toast("Initialer Status (ok) an Gateway gemeldet", icon="📡")
                else:
                    st.warning(
                        f"Status-Push fehlgeschlagen: HTTP {status_resp.status_code} — "
                        f"{status_resp.text[:120]}"
                    )
            except requests.RequestException as exc:
                st.warning(f"Status-Push nicht erreichbar: {exc}")

            data = response.json()
            leds["URETOS"] = LED_GREEN
            box_placeholder.markdown(render_box(hardware_id[:20], "ONLINE & STREAMING", leds), unsafe_allow_html=True)
            st.success(f"{action_msg} Erkannte Maschinen: **{len(identities)}**")

            # Persist in session for live status controls below
            st.session_state["box_online"] = True
            st.session_state["hardware_id"] = hardware_id
            st.session_state["tracked_machines"] = tracked
            st.session_state["leds"] = leds

            with st.expander(f"Discovery details ({len(identities)} Maschinen)", expanded=False):
                for idx, m in enumerate(identities):
                    st.markdown(f"**Maschine {idx + 1}: {m.name}**")
                    st.json(m.to_dict())

            st.json(data)
        else:
            leds["ERROR"] = LED_RED
            try:
                reason = response.json().get("error", "Unknown error")
            except ValueError:
                reason = f"HTTP {response.status_code}"
            box_placeholder.markdown(render_box("FAILED", reason[:28], leds), unsafe_allow_html=True)
            st.error(reason)
            st.session_state["box_online"] = False

    # -------------------------------------------------------------------------
    # Live status panel (after successful boot, survives reruns via session_state)
    # -------------------------------------------------------------------------
    if st.session_state.get("box_online") and st.session_state.get("tracked_machines"):
        st.divider()
        st.subheader("Live Maschinen-Status")
        st.caption(
            "Simuliert OPC-UA-Statusänderungen. Nur bei Änderung wird "
            "`POST /v1/connector-boxes/machine-status` aufgerufen."
        )

        hid = st.session_state["hardware_id"]
        tracked = st.session_state["tracked_machines"]
        changed = []

        for i, m in enumerate(tracked):
            label = m.get("name") or m.get("serial") or m.get("machine_id") or f"Machine {i+1}"
            cols = st.columns([3, 2])
            with cols[0]:
                st.write(f"**{label}**")
                if m.get("machine_id"):
                    st.caption(f"id: `{m['machine_id']}`")
            with cols[1]:
                new_status = st.selectbox(
                    "Status",
                    STATUS_OPTIONS,
                    index=STATUS_OPTIONS.index(m["status"]) if m["status"] in STATUS_OPTIONS else 0,
                    key=f"status_select_{i}",
                )
                if new_status != m["status"]:
                    m["status"] = new_status
                if m["status"] != m.get("last_pushed_status"):
                    changed.append(m)

        st.session_state["tracked_machines"] = tracked

        if st.button("Status-Änderungen pushen", type="primary", disabled=len(changed) == 0):
            box_placeholder.markdown(
                render_box("STATUS PUSH...", f"{len(changed)} UPDATE(S)", st.session_state.get("leds", leds)),
                unsafe_allow_html=True,
            )
            try:
                resp = push_machine_status(hid, build_status_payload(changed))
                if resp.status_code == 200:
                    for m in changed:
                        m["last_pushed_status"] = m["status"]
                    st.session_state["tracked_machines"] = tracked
                    st.success(f"{len(changed)} Status-Update(s) gesendet")
                    box_placeholder.markdown(
                        render_box(hid[:20], "ONLINE & STREAMING", st.session_state.get("leds", leds)),
                        unsafe_allow_html=True,
                    )
                else:
                    st.error(f"HTTP {resp.status_code}: {resp.text[:200]}")
            except requests.RequestException as exc:
                st.error(f"Gateway nicht erreichbar: {exc}")

        if changed:
            st.info(f"{len(changed)} Maschine(n) mit unpushtem Status — Button drücken zum Senden.")
        else:
            st.caption("Alle Status-Werte sind bereits an den Gateway gepusht.")


if __name__ == "__main__":
    main()
