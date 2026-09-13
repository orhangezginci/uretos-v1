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


def create_tenant(tenant_id):
    correlation_id = str(uuid.uuid4())
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()
    channel.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)

    result = channel.queue_declare(queue="", exclusive=True)
    listen_queue = result.method.queue
    for routing_key in ["uretos.tenant.event.provisioned", "uretos.tenant.event.provisioning_failed"]:
        channel.queue_bind(queue=listen_queue, exchange=EXCHANGE, routing_key=routing_key)

    envelope_out = {
        "specversion": "1.0",
        "id": str(uuid.uuid4()),
        "source": "tools/admin-panel",
        "type": "uretos.tenant.command.create",
        "datacontenttype": "application/json",
        "time": datetime.now(timezone.utc).isoformat(),
        "correlationid": correlation_id,
        "messagetype": "command",
        "tenantid": "system",
        "data": {"tenant_id": tenant_id},
    }
    channel.basic_publish(
        exchange=EXCHANGE,
        routing_key="uretos.tenant.command.create",
        body=json.dumps(envelope_out).encode("utf-8"),
        properties=pika.BasicProperties(content_type="application/json"),
    )

    deadline = time.monotonic() + TIMEOUT_SECONDS
    envelope_in = wait_for_response(channel, listen_queue, correlation_id, deadline)
    connection.close()

    if envelope_in is None:
        raise TimeoutError("No response from tenant-provisioning-service within " + str(TIMEOUT_SECONDS) + "s")
    return envelope_in


def create_connector_box(tenant_id, hardware_id, mac_address):
    correlation_id = str(uuid.uuid4())
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()
    channel.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)

    result = channel.queue_declare(queue="", exclusive=True)
    listen_queue = result.method.queue
    for routing_key in ["uretos.connectorbox.event.created", "uretos.connectorbox.event.creation_failed"]:
        channel.queue_bind(queue=listen_queue, exchange=EXCHANGE, routing_key=routing_key)

    envelope_out = {
        "specversion": "1.0",
        "id": str(uuid.uuid4()),
        "source": "tools/admin-panel",
        "type": "uretos.connectorbox.command.create",
        "datacontenttype": "application/json",
        "time": datetime.now(timezone.utc).isoformat(),
        "correlationid": correlation_id,
        "messagetype": "command",
        "tenantid": "system",
        "data": {
            "tenant_id": tenant_id,
            "hardware_id": hardware_id,
            "mac_address": mac_address,
        },
    }
    channel.basic_publish(
        exchange=EXCHANGE,
        routing_key="uretos.connectorbox.command.create",
        body=json.dumps(envelope_out).encode("utf-8"),
        properties=pika.BasicProperties(content_type="application/json"),
    )

    deadline = time.monotonic() + TIMEOUT_SECONDS
    envelope_in = wait_for_response(channel, listen_queue, correlation_id, deadline)
    connection.close()

    if envelope_in is None:
        raise TimeoutError("No response from connector-box-command-service within " + str(TIMEOUT_SECONDS) + "s")
    return envelope_in


def list_tenants_rpc():
    correlation_id = str(uuid.uuid4())
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()
    channel.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)

    envelope = {
        "specversion": "1.0",
        "id": str(uuid.uuid4()),
        "source": "tools/admin-panel",
        "type": "uretos.tenant.query.list",
        "datacontenttype": "application/json",
        "time": datetime.now(timezone.utc).isoformat(),
        "correlationid": correlation_id,
        "messagetype": "query",
        "tenantid": "system",
        "data": {},
    }

    result_holder = {}

    def on_response(ch, method, properties, body):
        if properties.correlation_id == correlation_id:
            result_holder["envelope"] = json.loads(body)
            ch.stop_consuming()

    channel.basic_consume(queue="amq.rabbitmq.reply-to", on_message_callback=on_response, auto_ack=True)
    channel.basic_publish(
        exchange=EXCHANGE,
        routing_key="uretos.tenant.query.list",
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
        raise TimeoutError("No response from tenant-query-service within " + str(TIMEOUT_SECONDS) + "s")
    return result_holder["envelope"]["data"]["tenants"]


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


def render_tenant_section():
    st.subheader("Create tenant")
    tenant_id = st.text_input("Tenant ID (lowercase, alphanumeric, hyphens)", help="Beispiel: acme-gmbh")
    if st.button("Provision tenant") and tenant_id:
        with st.spinner("Provisioning " + tenant_id + " ..."):
            try:
                envelope = create_tenant(tenant_id)
            except TimeoutError as exc:
                st.error(str(exc))
                return

        if envelope["type"] == "uretos.tenant.event.provisioned":
            st.success("Tenant " + tenant_id + " provisioned")
            st.json(envelope["data"])
        else:
            st.error("Provisioning failed: " + str(envelope["data"].get("reason")))

    st.divider()
    st.subheader("Existing tenants")
    if st.button("Refresh tenant list") or "tenants_cache" not in st.session_state:
        try:
            st.session_state["tenants_cache"] = list_tenants_rpc()
        except TimeoutError as exc:
            st.error(str(exc))
            st.session_state["tenants_cache"] = []

    if st.session_state.get("tenants_cache"):
        st.table(st.session_state["tenants_cache"])
    else:
        st.caption("No tenants yet.")


def render_connector_box_section():
    st.subheader("Create connector box")

    tenant_ids = [t["tenant_id"] for t in st.session_state.get("tenants_cache", [])]
    if not tenant_ids:
        st.caption("No tenants available yet - create a tenant first, then refresh the tenant list above.")
        return

    tenant_id = st.selectbox("Tenant", tenant_ids)
    hardware_id = st.text_input("Hardware ID", help="Beispiel: HW-2026-000123")
    mac_address = st.text_input("MAC address", help="Beispiel: AA:BB:CC:DD:EE:FF")
    
    if st.button("Create connector box") and hardware_id and mac_address:
        with st.spinner("Creating connector box ..."):
            try:
                envelope = create_connector_box(tenant_id, hardware_id, mac_address)
            except TimeoutError as exc:
                st.error(str(exc))
                return

        if envelope["type"] == "uretos.connectorbox.event.created":
            st.success("Connector box created for tenant " + tenant_id)
            st.json(envelope["data"])
            st.caption("Pairing token is only shown once here - it is not returned by list queries.")
        else:
            st.error("Creation failed: " + str(envelope["data"].get("reason")))


def admin_screen():
    st.title("uretOS - Admin Panel")
    st.caption("super_admin panel - throwaway internal tool")

    if st.button("Logout"):
        st.session_state["logged_in"] = False
        st.rerun()

    st.divider()
    render_tenant_section()
    st.divider()
    render_connector_box_section()


def main():
    if not st.session_state.get("logged_in"):
        login_screen()
    else:
        admin_screen()


if __name__ == "__main__":
    main()