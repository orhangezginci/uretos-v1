"""
Per-tenant infrastructure provisioning.

Talks to the Docker Engine API *through* docker-socket-proxy (never the raw
socket) to create one isolated Postgres container (with TimescaleDB enabled 
via /docker-entrypoint-initdb.d/init-extension.sql) and one isolated Redis 
container per tenant. Also creates an isolated RabbitMQ vhost + user per 
tenant via the RabbitMQ Management HTTP API.
"""
from __future__ import annotations

import os
import re
import secrets
import logging

import docker
import requests

logger = logging.getLogger("tenant-provisioning")

DOCKER_HOST = "tcp://docker-socket-proxy:2375"
NETWORK_NAME = "uretos-tenant-net"

RABBITMQ_MGMT_URL = os.environ.get("RABBITMQ_MGMT_URL", "http://rabbitmq:15672")
RABBITMQ_ADMIN_USER = os.environ.get("RABBITMQ_ADMIN_USER", "uretos")
RABBITMQ_ADMIN_PASSWORD = os.environ.get("RABBITMQ_ADMIN_PASSWORD", "uretos_dev_pass")

_TENANT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,30}[a-z0-9]$")


class ProvisioningError(RuntimeError):
    pass


def _validate_tenant_id(tenant_id: str) -> None:
    if not _TENANT_ID_RE.match(tenant_id):
        raise ProvisioningError(
            f"tenant_id '{tenant_id}' invalid - must be lowercase "
            "alphanumeric/hyphen, 3-32 chars, used directly in container "
            "and volume names."
        )


def _client() -> docker.DockerClient:
    return docker.DockerClient(base_url=DOCKER_HOST)


def provision_tenant_infrastructure(tenant_id: str) -> dict:
    """
    Creates an isolated Postgres (TimescaleDB) + Redis container pair for one tenant.
    Returns connection info for the provisioning-event's data payload.
    """
    _validate_tenant_id(tenant_id)
    client = _client()

    pg_name = f"tenant-{tenant_id}-postgres"
    redis_name = f"tenant-{tenant_id}-redis"

    for name in (pg_name, redis_name):
        try:
            client.containers.get(name)
            raise ProvisioningError(
                f"Container '{name}' already exists - refusing to "
                "re-provision an existing tenant."
            )
        except docker.errors.NotFound:
            pass

    _ensure_network(client)

    # Absoluten Pfad zum im app-Verzeichnis liegenden init-extension.sql ermitteln
    init_sql_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "init-extension.sql"))

    db_password = secrets.token_urlsafe(24)
    pg_container = client.containers.run(
        image="timescale/timescaledb:latest-pg16",
        name=pg_name,
        detach=True,
        network=NETWORK_NAME,
        environment={
            "POSTGRES_USER": f"tenant_{tenant_id}",
            "POSTGRES_PASSWORD": db_password,
            "POSTGRES_DB": f"tenant_{tenant_id}",
        },
        volumes={
            f"{pg_name}-data": {"bind": "/var/lib/postgresql/data", "mode": "rw"},
            init_sql_path: {"bind": "/docker-entrypoint-initdb.d/init-extension.sql", "mode": "ro"},
        },
        restart_policy={"Name": "unless-stopped"},
    )

    # Die TimescaleDB-Extension wird nun nativ beim ersten Postgres-Start 
    # durch das gemountete Init-Skript im Container ausgeführt.

    redis_container = client.containers.run(
        image="redis:7-alpine",
        name=redis_name,
        detach=True,
        network=NETWORK_NAME,
        volumes={f"{redis_name}-data": {"bind": "/data", "mode": "rw"}},
        restart_policy={"Name": "unless-stopped"},
        command="redis-server --appendonly yes",
    )

    return {
        "tenant_id": tenant_id,
        "postgres": {
            "container_name": pg_name,
            "container_id": pg_container.id,
            "internal_host": pg_name,
            "port": 5432,
            "user": f"tenant_{tenant_id}",
            "password": db_password,
            "database": f"tenant_{tenant_id}",
        },
        "redis": {
            "container_name": redis_name,
            "container_id": redis_container.id,
            "internal_host": redis_name,
            "port": 6379,
        },
    }


def _ensure_network(client: docker.DockerClient) -> None:
    try:
        client.networks.get(NETWORK_NAME)
    except docker.errors.NotFound:
        client.networks.create(NETWORK_NAME, driver="bridge")


def provision_tenant_rabbitmq(tenant_id: str) -> dict:
    """
    Creates an isolated RabbitMQ vhost + a user scoped exclusively to it,
    via the Management HTTP API.
    """
    auth = (RABBITMQ_ADMIN_USER, RABBITMQ_ADMIN_PASSWORD)
    vhost_name = f"tenant-{tenant_id}"
    rabbitmq_user = f"tenant_{tenant_id}"
    rabbitmq_password = secrets.token_urlsafe(24)

    vhost_response = requests.put(
        f"{RABBITMQ_MGMT_URL}/api/vhosts/{vhost_name}", auth=auth, timeout=10
    )
    if vhost_response.status_code not in (201, 204):
        raise ProvisioningError(f"Failed to create RabbitMQ vhost: {vhost_response.text}")

    user_response = requests.put(
        f"{RABBITMQ_MGMT_URL}/api/users/{rabbitmq_user}",
        auth=auth,
        json={"password": rabbitmq_password, "tags": ""},
        timeout=10,
    )
    if user_response.status_code not in (201, 204):
        raise ProvisioningError(f"Failed to create RabbitMQ user: {user_response.text}")

    permission_response = requests.put(
        f"{RABBITMQ_MGMT_URL}/api/permissions/{vhost_name}/{rabbitmq_user}",
        auth=auth,
        json={"configure": ".*", "write": ".*", "read": ".*"},
        timeout=10,
    )
    if permission_response.status_code not in (201, 204):
        raise ProvisioningError(f"Failed to set RabbitMQ permissions: {permission_response.text}")

    return {
        "vhost": vhost_name,
        "user": rabbitmq_user,
        "password": rabbitmq_password,
    }