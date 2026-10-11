"""
uretOS Connector Box Simulator - throwaway internal tool.

Simulates a physical uretOS Connector box booting, discovering OPC-UA machines
(up to the licensed limit), trying a handshake first, falling back to pairing
if unknown (404) or pending (403), and persisting discovered machines via the
autoscan endpoint.
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


def main():
    st.title("uretOS Connector Box Simulator")
    st.caption("Simuliert Geräte-Boot, OPC-UA Multi-Maschinen-Discovery, Smart Handshake, Auto-Pairing und Maschinen-Persistenz")

    # Session State initialisieren, damit Daten bei Reruns erhalten bleiben
    if "is_online" not in st.session_state:
        st.session_state.is_online = False
    if "identities" not in st.session_state:
        st.session_state.identities = []
    if "box_data" not in st.session_state:
        st.session_state.box_data = {}
    if "leds" not in st.session_state:
        st.session_state.leds = {"POWER": LED_OFF, "NETWORK": LED_OFF, "URETOS": LED_OFF, "ERROR": LED_OFF}

    hardware_id = st.text_input("Hardware ID", value="edc701f0-bf8c-4024-b23e-d90499caafca", help="Beispiel: tennant-c-20260928-u31c")
    boot_clicked = st.button("Boot & Connect")

    box_placeholder = st.empty()

    if boot_clicked and hardware_id:
        st.session_state.leds = {"POWER": LED_OFF, "NETWORK": LED_OFF, "URETOS": LED_OFF, "ERROR": LED_OFF}
        
        # 1. Power On
        st.session_state.leds["POWER"] = LED_GREEN
        box_placeholder.markdown(render_box("BOOTING...", "HARDWARE INIT", st.session_state.leds), unsafe_allow_html=True)
        time.sleep(0.4)

        # 2. Network Connection
        st.session_state.leds["NETWORK"] = LED_GREEN
        box_placeholder.markdown(render_box("NETWORKING...", "DHCP / LINK UP", st.session_state.leds), unsafe_allow_html=True)
        time.sleep(0.4)

        # 3. OPC UA Discovery & Metadata Read (Multi-Machine)
        box_placeholder.markdown(render_box("DISCOVERING...", f"SCANNING :{OPC_UA_PORT}", st.session_state.leds), unsafe_allow_html=True)
        time.sleep(0.6)

        identities = discover_machines(OPC_UA_HOST, OPC_UA_PORT, max_machines=MAX_LICENSED_MACHINES)
        st.session_state.identities = identities

        if identities:
            primary_name = str(identities[0].name)[:18].upper()
            count_str = f"FOUND: {len(identities)} MACHINES"
            box_placeholder.markdown(render_box(count_str, primary_name, st.session_state.leds), unsafe_allow_html=True)
        else:
            box_placeholder.markdown(render_box("DISCOVERY WARN", "NO OPC-UA SERVER", st.session_state.leds), unsafe_allow_html=True)
        time.sleep(0.8)

        # 4. Smart Gateway Communication
        try:
            box_placeholder.markdown(render_box("HANDSHAKE...", "VERIFYING TOKEN", st.session_state.leds), unsafe_allow_html=True)
            response = requests.post(
                GATEWAY_URL + "/v1/connector-boxes/handshake",
                json={"hardware_id": hardware_id},
                timeout=25,
            )

            if response.status_code in (404, 403):
                box_placeholder.markdown(render_box("PAIRING...", "INITIAL REGISTRATION", st.session_state.leds), unsafe_allow_html=True)
                response = requests.post(
                    GATEWAY_URL + "/v1/connector-boxes/pair",
                    json={"hardware_id": hardware_id},
                    timeout=25,
                )
                action_msg = "Box erfolgreich gepaired & online!"
            else:
                action_msg = "Handshake erfolgreich durchgeführt!"

        except requests.RequestException as exc:
            st.session_state.leds["ERROR"] = LED_RED
            box_placeholder.markdown(render_box("GATEWAY UNREACHABLE", str(exc)[:32], st.session_state.leds), unsafe_allow_html=True)
            st.error("Could not reach gateway-api: " + str(exc))
            st.session_state.is_online = False
            return

        if response.status_code == 200:
            # 5. Autoscan / Maschinen an Gateway zur Persistenz übergeben
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
                else:
                    st.warning("Maschinen-Persistenz ergab Status: " + str(scan_response.status_code))
            except requests.RequestException as exc:
                st.warning(f"Konnte Maschinen-Autoscan nicht senden: {exc}")

            st.session_state.box_data = response.json()
            st.session_state.leds["URETOS"] = LED_GREEN
            st.session_state.is_online = True
        else:
            st.session_state.leds["ERROR"] = LED_RED
            try:
                reason = response.json().get("error", "Unknown error")
            except ValueError:
                reason = f"HTTP {response.status_code}"
            box_placeholder.markdown(render_box("FAILED", reason[:28], st.session_state.leds), unsafe_allow_html=True)
            st.error(reason)
            st.session_state.is_online = False

    # UI-Darstellung basierend auf dem Session State (bleibt bei Widget-Interaktionen stabil)
    if st.session_state.is_online:
        box_placeholder.markdown(render_box(hardware_id[:20], "ONLINE & STREAMING", st.session_state.leds), unsafe_allow_html=True)
        st.success(f"Box online! Erkannte Maschinen: **{len(st.session_state.identities)}**")

        with st.expander(f"Discovery details ({len(st.session_state.identities)} Maschinen)", expanded=False):
            for idx, m in enumerate(st.session_state.identities):
                st.markdown(f"**Maschine {idx + 1}: {m.name}**")
                st.json(m.to_dict())

        # --- Live Status Control Panel ---
        st.divider()
        st.subheader("🛠️ Live Status Control Panel")

        identities = st.session_state.identities
        if identities:
            machine_options = { (m.name or f"Machine-{i}"): m for i, m in enumerate(identities) }
            selected_machine_name = st.selectbox("Maschine auswählen", options=list(machine_options.keys()))
            selected_machine = machine_options[selected_machine_name]

            status_options = {"OK (Grün)": "ok", "WARNING (Gelb)": "warning", "ERROR (Rot)": "error"}
            selected_status_label = st.selectbox("Neuer Status", options=list(status_options.keys()))
            new_status = status_options[selected_status_label]

            error_code = st.text_input("Fehlercode (optional)", value="" if new_status == "ok" else "E-500: Beispiel-Fehler")

            if st.button("Status an Gateway senden"):
                machine_id_to_send = selected_machine.name or "BasicMachineTool"
                tenant_id = st.session_state.box_data.get("tenant_id", "test-tenant-e2e")

                try:
                    status_resp = requests.patch(
                        f"{GATEWAY_URL}/v1/machines/{machine_id_to_send}/status",
                        json={
                            "tenant_id": tenant_id,
                            "status": new_status,
                            "error_code": error_code if new_status != "ok" else None
                        },
                        timeout=10
                    )
                    if status_resp.status_code == 200:
                        st.toast(f"Status für {machine_id_to_send} erfolgreich auf '{new_status}' aktualisiert!", icon="⚡")
                    else:
                        st.warning(f"Fehler beim Update: {status_resp.status_code} - {status_resp.text}")
                except requests.RequestException as exc:
                    st.error(f"Konnte Gateway nicht erreichen: {exc}")
    else:
        box_placeholder.markdown(render_box("URETOS CONNECTOR", "READY", st.session_state.leds), unsafe_allow_html=True)


if __name__ == "__main__":
    main()