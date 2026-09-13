"""
uretOS super_admin panel - throwaway internal tool.

Deliberately NOT following uretOS's normal architecture rules: talks to
RabbitMQ directly via pika instead of going through a Gateway REST API,
since this tool is only ever used locally by the super_admin. A real
customer-facing client MUST go through a Gateway service instead - see
project notes.

Run with:
    streamlit run app.py
"""
import json
import os
import random
import string
import time
import uuid
from datetime import datetime, timezone

import pika
import streamlit as st

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://uretos:uretos_dev_pass@localhost:5672/")
EXCHANGE = "uretos.events"
SUPER_ADMIN_USER = os.environ.get("SUPER_ADMIN_USER", "admin")
SUPER_ADMIN_PASSWORD = os.environ.get("SUPER_ADMIN_PASSWORD", "changeme")
TIMEOUT_SECONDS = 45


def wait_for_response(channel, listen_queue, correlation_id, deadline):
    while time.monotonic() < deadline:
        method, properties, body = channel.basic_get(queue=listen_queue, auto_ack=True)
        if body is None:
            time.sleep(0.5)
            continue
        envelope = json.loads(body)
        if envelope.get("correlationid") != correlation_id:
            continue
        return envelope
    return None


def publish_command_and_wait(command_type, data, success_type, failure_type):
    correlation_id = str(uuid.uuid4())
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()
    channel.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)

    result = channel.queue_declare(queue="", exclusive=True)
    listen_queue = result.method.queue
    for routing_key in [success_type, failure_type]:
        channel.queue_bind(queue=listen_queue, exchange=EXCHANGE, routing_key=routing_key)

    envelope_out = {
        "specversion": "1.0",
        "id": str(uuid.uuid4()),
        "source": "tools/admin-panel",
        "type": command_type,
        "datacontenttype": "application/json",
        "time": datetime.now(timezone.utc).isoformat(),
        "correlationid": correlation_id,
        "messagetype": "command",
        "tenantid": "system",
        "data": data,
    }
    channel.basic_publish(
        exchange=EXCHANGE,
        routing_key=command_type,
        body=json.dumps(envelope_out).encode("utf-8"),
        properties=pika.BasicProperties(content_type="application/json"),
    )

    deadline = time.monotonic() + TIMEOUT_SECONDS
    envelope_in = wait_for_response(channel, listen_queue, correlation_id, deadline)
    connection.close()

    if envelope_in is None:
        raise TimeoutError("No response received within " + str(TIMEOUT_SECONDS) + "s")
    return envelope_in


def query_rpc(query_type, data):
    correlation_id = str(uuid.uuid4())
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()
    channel.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)

    envelope = {
        "specversion": "1.0",
        "id": str(uuid.uuid4()),
        "source": "tools/admin-panel",
        "type": query_type,
        "datacontenttype": "application/json",
        "time": datetime.now(timezone.utc).isoformat(),
        "correlationid": correlation_id,
        "messagetype": "query",
        "tenantid": "system",
        "data": data,
    }

    result_holder = {}

    def on_response(ch, method, properties, body):
        if properties.correlation_id == correlation_id:
            result_holder["envelope"] = json.loads(body)
            ch.stop_consuming()

    channel.basic_consume(queue="amq.rabbitmq.reply-to", on_message_callback=on_response, auto_ack=True)
    channel.basic_publish(
        exchange=EXCHANGE,
        routing_key=query_type,
        properties=pika.BasicProperties(
            reply_to="amq.rabbitmq.reply-to",
            correlation_id=correlation_id,
            content_type="application/json",
        ),
        body=json.dumps(envelope).encode("utf-8"),
    )

    connection.process_data_events(time_limit=TIMEOUT_SECONDS)
    connection.close()

    if "envelope" not in result_holder:
        raise TimeoutError("No response received within " + str(TIMEOUT_SECONDS) + "s")
    return result_holder["envelope"]


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
        envelope = query_rpc("uretos.tenant.query.list", {})
        st.session_state["tenants_cache"] = envelope["data"]["tenants"]
    except TimeoutError as exc:
        st.error(str(exc))
        st.session_state["tenants_cache"] = []


def render_tenant_tab():
    st.subheader("Create tenant")
    tenant_id = st.text_input("Tenant ID (lowercase, alphanumeric, hyphens)", help="Beispiel: acme-gmbh")
    if st.button("Provision tenant") and tenant_id:
        with st.spinner("Provisioning " + tenant_id + " ..."):
            try:
                envelope = publish_command_and_wait(
                    "uretos.tenant.command.create",
                    {"tenant_id": tenant_id},
                    "uretos.tenant.event.provisioned",
                    "uretos.tenant.event.provisioning_failed",
                )
            except TimeoutError as exc:
                st.error(str(exc))
                return

        if envelope["type"] == "uretos.tenant.event.provisioned":
            st.success("Tenant " + tenant_id + " provisioned")
            st.json(envelope["data"])
            refresh_tenants()
        else:
            st.error("Provisioning failed: " + str(envelope["data"].get("reason")))

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
        envelope = query_rpc("uretos.connectorbox.query.list", {})
        st.session_state["boxes_cache"] = envelope["data"]["connector_boxes"]
    except TimeoutError as exc:
        st.error(str(exc))
        st.session_state["boxes_cache"] = []


def _generate_hardware_id():
    """
    Callback for the 'Auto-generate' button. Runs BEFORE the next script
    rerun renders the hardware_id_input widget, so writing to
    session_state here is safe (unlike doing it in the main script body
    after the widget has already been instantiated in the current run).
    """
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
                    envelope = publish_command_and_wait(
                        "uretos.connectorbox.command.create",
                        {"tenant_id": tenant_id, "hardware_id": hardware_id, "mac_address": mac_address},
                        "uretos.connectorbox.event.created",
                        "uretos.connectorbox.event.creation_failed",
                    )
                except TimeoutError as exc:
                    st.error(str(exc))
                    envelope = None

            if envelope is not None:
                if envelope["type"] == "uretos.connectorbox.event.created":
                    st.success("Connector box created for tenant " + tenant_id)
                    st.json(envelope["data"])
                    st.caption("Pairing token is only shown once here - it is not returned by list queries.")
                    refresh_connector_boxes()
                else:
                    st.error("Creation failed: " + str(envelope["data"].get("reason")))

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