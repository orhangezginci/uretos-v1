"""
uretOS Connector Box Simulator - throwaway internal tool.

Simulates a physical uretOS Connector box booting and pairing with the
platform. Calls gateway-api's REST endpoint directly (POST request) -
this deliberately mirrors what the real hardware would do, unlike the
admin panel which talks to RabbitMQ directly as a documented exception.

Run with:
    streamlit run app.py
"""
import os
import time

import requests
import streamlit as st

GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://localhost:8080")

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
    return html


def main():
    st.title("uretOS Connector Box Simulator")
    st.caption("throwaway internal tool - simulates real device boot/pairing over REST")

    hardware_id = st.text_input("Hardware ID", help="Beispiel: firma-a-20260913-f1pp")
    boot_clicked = st.button("Boot")

    box_placeholder = st.empty()

    leds = {"POWER": LED_OFF, "NETWORK": LED_OFF, "URETOS": LED_OFF, "ERROR": LED_OFF}
    box_placeholder.markdown(render_box("URETOS CONNECTOR", "READY", leds), unsafe_allow_html=True)

    if boot_clicked and hardware_id:
        leds["POWER"] = LED_GREEN
        box_placeholder.markdown(render_box("BOOTING...", "", leds), unsafe_allow_html=True)
        time.sleep(0.6)

        leds["NETWORK"] = LED_GREEN
        box_placeholder.markdown(render_box("CONNECTING...", "TO URETOS CLOUD", leds), unsafe_allow_html=True)
        time.sleep(0.6)

        try:
            response = requests.post(
                GATEWAY_URL + "/v1/connector-boxes/pair",
                json={"hardware_id": hardware_id},
                timeout=25,
            )
        except requests.RequestException as exc:
            leds["ERROR"] = LED_RED
            box_placeholder.markdown(render_box("GATEWAY UNREACHABLE", str(exc)[:32], leds), unsafe_allow_html=True)
            st.error("Could not reach gateway-api: " + str(exc))
            return

        if response.status_code == 200:
            data = response.json()
            leds["URETOS"] = LED_GREEN
            box_placeholder.markdown(render_box(hardware_id[:20], "ONLINE", leds), unsafe_allow_html=True)
            st.success("Paired successfully")
            st.json(data)
        else:
            leds["ERROR"] = LED_RED
            reason = response.json().get("error", "Unknown error")
            box_placeholder.markdown(render_box("PAIRING FAILED", reason[:28], leds), unsafe_allow_html=True)
            st.error(reason)


if __name__ == "__main__":
    main()