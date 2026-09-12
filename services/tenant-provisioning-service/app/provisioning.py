"""
Per-tenant infrastructure provisioning.

Talks to the Docker Engine API *through* docker-socket-proxy (never the raw
socket) to create one isolated Postgres container and one isolated Redis
container per tenant. This is the technical backbone of the "each tenant has
their own DB server container" guarantee.

NOTE on scope: this is a pragmatic, right-sized implementation for the
"technically impossible to leak data between tenants" trust story - not a
hardened, audited production security design. Secrets are generated
per-tenant but stored in plain env vars here as a starting point; a real
secrets manager should replace that before this touches real customer data.
"""
from __future__ import annotations

import re
import secrets
import docker

DOCKER_HOST = "tcp://docker-socket-proxy:2375"
NETWORK_NAME = "uretos-tenant-net"

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
    Creates an isolated Postgres + Redis container pair for one tenant.
    Returns connection info that the provisioning-event's data payload
    can carry onward (e.g. to a tenant registry / config store).

    Idempotent-ish: if containers with this tenant's names already exist,
    it raises rather than silently reusing them, since silently reusing
    infra for a "create tenant" command is a dangerous default.
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

    db_password = secrets.token_urlsafe(24)
    pg_container = client.containers.run(
        image="postgres:16-alpine",
        name=pg_name,
        detach=True,
        network=NETWORK_NAME,
        environment={
            "POSTGRES_USER": f"tenant_{tenant_id}",
            "POSTGRES_PASSWORD": db_password,
            "POSTGRES_DB": f"tenant_{tenant_id}",
        },
        volumes={f"{pg_name}-data": {"bind": "/var/lib/postgresql/data", "mode": "rw"}},
        restart_policy={"Name": "unless-stopped"},
    )

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