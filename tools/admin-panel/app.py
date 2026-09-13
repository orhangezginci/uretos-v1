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


def build_command_envelope(tenant_id, correlation_id):
    return {
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


def create_tenant(tenant_id):
    correlation_id = str(uuid.uuid4())
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()
    channel.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)

    result = channel.queue_declare(queue="", exclusive=True)
    listen_queue = result.method.queue
    routing_keys = ["uretos.tenant.event.provisioned", "uretos.tenant.event.provisioning_failed"]
    for routing_key in routing_keys:
        channel.queue_bind(queue=listen_queue, exchange=EXCHANGE, routing_key=routing_key)

    body = json.dumps(build_command_envelope(tenant_id, correlation_id)).encode("utf-8")
    channel.basic_publish(
        exchange=EXCHANGE,
        routing_key="uretos.tenant.command.create",
        body=body,
        properties=pika.BasicProperties(content_type="application/json"),
    )

    deadline = time.monotonic() + TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        method, properties, body = channel.basic_get(queue=listen_queue, auto_ack=True)
        if body is None:
            time.sleep(0.5)
            continue
        envelope = json.loads(body)
        if envelope.get("correlationid") != correlation_id:
            continue
        connection.close()
        return envelope

    connection.close()
    raise TimeoutError("No response from tenant-provisioning-service within " + str(TIMEOUT_SECONDS) + "s")


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


def admin_screen():
    st.title("uretOS - Tenant Management")
    st.caption("super_admin panel - throwaway internal tool")

    if st.button("Logout"):
        st.session_state["logged_in"] = False
        st.rerun()

    st.divider()
    st.subheader("Create tenant")
    tenant_id = st.text_input("Tenant ID (lowercase, alphanumeric, hyphens)", placeholder="acme-gmbh")
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
    if st.button("Refresh list") or "tenants_cache" not in st.session_state:
        try:
            st.session_state["tenants_cache"] = list_tenants_rpc()
        except TimeoutError as exc:
            st.error(str(exc))
            st.session_state["tenants_cache"] = []

    if st.session_state.get("tenants_cache"):
        st.table(st.session_state["tenants_cache"])
    else:
        st.caption("No tenants yet.")


def main():
    if not st.session_state.get("logged_in"):
        login_screen()
    else:
        admin_screen()


if __name__ == "__main__":
    main()