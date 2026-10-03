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

        # 4. Smart Gateway Communication: Handshake First, Fallback to Pairing if unknown (404) or pending (403)
        # Pairing identifies the box only - machine persistence happens exclusively via /autoscan below.
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

            data = response.json()
            leds["URETOS"] = LED_GREEN
            box_placeholder.markdown(render_box(hardware_id[:20], "ONLINE & STREAMING", leds), unsafe_allow_html=True)
            st.success(f"{action_msg} Erkannte Maschinen: **{len(identities)}**")

            with st.expander(f"Discovery details ({len(identities)} Maschinen)", expanded=True):
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


if __name__ == "__main__":
    main()