"""
uretOS super_admin panel - throwaway internal tool.

Calls gateway-api's REST endpoints exclusively - no direct RabbitMQ access.
This makes the admin panel an ordinary external client, same as the
connector-box simulator, rather than a special case.

Run with:
    streamlit run app.py
"""
import os

import requests
import streamlit as st

GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://localhost:8080")
SUPER_ADMIN_USER = os.environ.get("SUPER_ADMIN_USER", "admin")
SUPER_ADMIN_PASSWORD = os.environ.get("SUPER_ADMIN_PASSWORD", "changeme")
TIMEOUT_SECONDS = 30


def login_screen():
    st.title("uretOS super_admin")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username == SUPER_ADMIN_USER and password == SUPER_ADMIN_PASSWORD:
            st.session_state["logged_in"] = True
            st.rerun()
        else:
            st.error("Invalid credentials")


def refresh_tenants():
    try:
        response = requests.get(GATEWAY_URL + "/v1/tenants", timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        st.session_state["tenants_cache"] = response.json()
    except requests.RequestException as exc:
        st.error("Could not reach gateway-api: " + str(exc))
        st.session_state["tenants_cache"] = []


def render_tenant_tab():
    st.subheader("Create tenant")
    tenant_id = st.text_input("Tenant ID (lowercase, alphanumeric, hyphens)", help="Beispiel: acme-gmbh")
    if st.button("Provision tenant") and tenant_id:
        with st.spinner("Provisioning " + tenant_id + " ..."):
            try:
                response = requests.post(
                    GATEWAY_URL + "/v1/tenants",
                    json={"tenant_id": tenant_id},
                    timeout=TIMEOUT_SECONDS,
                )
            except requests.RequestException as exc:
                st.error("Could not reach gateway-api: " + str(exc))
                return

        if response.status_code == 201:
            st.success("Tenant " + tenant_id + " provisioned")
            st.json(response.json())
            refresh_tenants()
        else:
            st.error("Provisioning failed: " + str(response.json().get("error")))

    st.divider()
    st.subheader("Existing tenants")
    if st.button("Refresh tenant list") or "tenants_cache" not in st.session_state:
        refresh_tenants()

    if st.session_state.get("tenants_cache"):
        st.table(st.session_state["tenants_cache"])
    else:
        st.caption("No tenants yet.")


def refresh_connector_boxes():
    try:
        response = requests.get(GATEWAY_URL + "/v1/connector-boxes", timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        st.session_state["boxes_cache"] = response.json()
    except requests.RequestException as exc:
        st.error("Could not reach gateway-api: " + str(exc))
        st.session_state["boxes_cache"] = []


def _generate_hardware_id():
    import random
    import string
    from datetime import datetime, timezone

    tenant_id = st.session_state.get("connector_box_tenant_select", "tenant")
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
    st.session_state["hardware_id_input"] = tenant_id + "-" + date_part + "-" + suffix


def render_connector_box_tab():
    st.subheader("Create connector box")

    if "tenants_cache" not in st.session_state:
        refresh_tenants()
    tenant_ids = [t["tenant_id"] for t in st.session_state.get("tenants_cache", [])]

    if not tenant_ids:
        st.caption("No tenants available yet - create a tenant in the Tenants tab first.")
    else:
        tenant_id = st.selectbox("Tenant", tenant_ids, key="connector_box_tenant_select")

        col1, col2 = st.columns([3, 1])
        with col1:
            hardware_id = st.text_input(
                "Hardware ID", help="Beispiel: HW-2026-000123", key="hardware_id_input"
            )
        with col2:
            st.write("")
            st.write("")
            st.button("Auto-generate", on_click=_generate_hardware_id)

        mac_address = st.text_input("MAC address", help="Beispiel: AA:BB:CC:DD:EE:FF")

        if st.button("Create connector box") and hardware_id and mac_address:
            with st.spinner("Creating connector box ..."):
                try:
                    response = requests.post(
                        GATEWAY_URL + "/v1/connector-boxes",
                        json={"tenant_id": tenant_id, "hardware_id": hardware_id, "mac_address": mac_address},
                        timeout=TIMEOUT_SECONDS,
                    )
                except requests.RequestException as exc:
                    st.error("Could not reach gateway-api: " + str(exc))
                    response = None

            if response is not None:
                if response.status_code == 201:
                    st.success("Connector box created for tenant " + tenant_id)
                    st.json(response.json())
                    st.caption("Pairing token is only shown once here - it is not returned by list queries.")
                    refresh_connector_boxes()
                else:
                    st.error("Creation failed: " + str(response.json().get("error")))

    st.divider()
    st.subheader("Existing connector boxes")
    if st.button("Refresh connector box list") or "boxes_cache" not in st.session_state:
        refresh_connector_boxes()

    if st.session_state.get("boxes_cache"):
        st.table(st.session_state["boxes_cache"])
    else:
        st.caption("No connector boxes yet.")


def admin_screen():
    st.title("uretOS - Admin Panel")
    st.caption("super_admin panel - throwaway internal tool")

    if st.button("Logout"):
        st.session_state["logged_in"] = False
        st.rerun()

    st.divider()
    tab_tenants, tab_boxes = st.tabs(["Tenants", "Connector Boxes"])
    with tab_tenants:
        render_tenant_tab()
    with tab_boxes:
        render_connector_box_tab()


def main():
    if not st.session_state.get("logged_in"):
        login_screen()
    else:
        admin_screen()


if __name__ == "__main__":
    main()