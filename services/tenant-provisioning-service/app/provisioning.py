"""
Per-tenant infrastructure provisioning.

Talks to the Docker Engine API *through* docker-socket-proxy (never the raw
socket) to create one isolated Postgres container (with TimescaleDB enabled
via post-start exec_run, after a real readiness check on the target database)
and one isolated Redis container per tenant. Also creates an isolated RabbitMQ
vhost + user per tenant via the RabbitMQ Management HTTP API.

Naming:
- Container / volume / RabbitMQ vhost names keep the tenant_id as-is (hyphens ok).
- Postgres database + role names are Postgres-conformant identifiers
  (hyphens -> underscores), so they never need quoting in SQL/psql.

Failure handling:
- Everything created by provision_tenant_infrastructure() is rolled back if a
  later step fails, so a failed attempt never leaves a half-provisioned tenant.
"""
from __future__ import annotations

import os
import re
import secrets
import logging
import time

import docker
import requests

logger = logging.getLogger("tenant-provisioning")

DOCKER_HOST = "tcp://uretos-docker-proxy:2375"
NETWORK_NAME = "uretos-tenant-net"

RABBITMQ_MGMT_URL = os.environ.get("RABBITMQ_MGMT_URL", "http://rabbitmq:15672")
RABBITMQ_ADMIN_USER = os.environ.get("RABBITMQ_ADMIN_USER", "uretos")
RABBITMQ_ADMIN_PASSWORD = os.environ.get("RABBITMQ_ADMIN_PASSWORD", "uretos_dev_pass")

_TENANT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,30}[a-z0-9]$")

POSTGRES_READY_TIMEOUT_SECONDS = 90


class ProvisioningError(RuntimeError):
    pass


def _validate_tenant_id(tenant_id: str) -> None:
    if not isinstance(tenant_id, str) or not _TENANT_ID_RE.match(tenant_id):
        raise ProvisioningError(
            f"tenant_id '{tenant_id}' invalid - must be lowercase "
            "alphanumeric/hyphen, 3-32 chars, used directly in container "
            "and volume names."
        )


def _pg_ident(tenant_id: str) -> str:
    """
    Postgres-conformant identifier used for BOTH database and role name.
    Hyphens become underscores. The mapping is injective because tenant_id
    can never contain an underscore (see _TENANT_ID_RE).
    """
    return f"tenant_{tenant_id.replace('-', '_')}"


def _client() -> docker.DockerClient:
    return docker.DockerClient(base_url=DOCKER_HOST)


def _ensure_network(client: docker.DockerClient) -> None:
    try:
        client.networks.get(NETWORK_NAME)
    except docker.errors.NotFound:
        client.networks.create(NETWORK_NAME, driver="bridge")


def _remove_resources(client: docker.DockerClient, container_names, volume_names) -> None:
    """Best-effort removal; never raises (used in error paths)."""
    for name in container_names:
        try:
            client.containers.get(name).remove(force=True, v=True)
        except docker.errors.NotFound:
            pass
        except Exception:
            logger.exception("Cleanup: could not remove container %s", name)
    for name in volume_names:
        try:
            client.volumes.get(name).remove(force=True)
        except docker.errors.NotFound:
            pass
        except Exception:
            logger.exception("Cleanup: could not remove volume %s", name)


def _wait_for_postgres(container, user: str, db: str, password: str) -> None:
    """
    Waits until the FINAL Postgres server is up and the target database is
    actually reachable.

    The official image's entrypoint first starts a temporary server that only
    listens on the Unix socket and creates the database there. A plain
    `pg_isready` over the socket reports "ready" during that phase, i.e. before
    the target DB exists. Connecting via TCP (127.0.0.1) with a real login on
    the target DB only succeeds once the final server is running.
    """
    deadline = time.monotonic() + POSTGRES_READY_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        container.reload()
        if container.status != "running":
            raise ProvisioningError(
                f"Postgres container stopped unexpectedly (status={container.status})."
            )
        res = container.exec_run(
            ["psql", "-h", "127.0.0.1", "-U", user, "-d", db, "-tAc", "SELECT 1"],
            environment={"PGPASSWORD": password},
        )
        if res.exit_code == 0 and res.output.strip() == b"1":
            return
        time.sleep(1)
    raise ProvisioningError("Timed out waiting for tenant Postgres to accept connections.")


def provision_tenant_infrastructure(tenant_id: str) -> dict:
    """
    Creates an isolated Postgres (TimescaleDB) + Redis container pair for one tenant.
    Returns connection info for the provisioning-event's data payload.

    On any failure after resources were created, those resources are removed
    again before the error is raised.
    """
    _validate_tenant_id(tenant_id)
    client = _client()

    pg_name = f"tenant-{tenant_id}-postgres"
    redis_name = f"tenant-{tenant_id}-redis"
    pg_volume = f"{pg_name}-data"
    redis_volume = f"{redis_name}-data"
    pg_ident = _pg_ident(tenant_id)

    # Existence checks happen BEFORE anything is created, so nothing is rolled
    # back here (an existing tenant must never be touched by a failed attempt).
    for name in (pg_name, redis_name):
        try:
            client.containers.get(name)
            raise ProvisioningError(
                f"Container '{name}' already exists - refusing to "
                "re-provision an existing tenant."
            )
        except docker.errors.NotFound:
            pass
    for name in (pg_volume, redis_volume):
        try:
            client.volumes.get(name)
            raise ProvisioningError(
                f"Volume '{name}' already exists (leftover?) - refusing to "
                "reuse stale data."
            )
        except docker.errors.NotFound:
            pass

    _ensure_network(client)

    db_password = secrets.token_urlsafe(24)
    try:
        pg_container = client.containers.run(
            image="timescale/timescaledb:latest-pg16",
            name=pg_name,
            detach=True,
            network=NETWORK_NAME,
            environment={
                "POSTGRES_USER": pg_ident,
                "POSTGRES_PASSWORD": db_password,
                "POSTGRES_DB": pg_ident,
            },
            volumes={
                pg_volume: {"bind": "/var/lib/postgresql/data", "mode": "rw"},
            },
            restart_policy={"Name": "unless-stopped"},
        )

        _wait_for_postgres(pg_container, pg_ident, pg_ident, db_password)

        # Passwort-Sync explizit erzwingen (verhindert Drift bei bereits existierenden Volumes)
        passwd_res = pg_container.exec_run(
            [
                "psql", "-h", "127.0.0.1",
                "-U", pg_ident, "-d", pg_ident,
                "-v", "ON_ERROR_STOP=1",
                "-c", f"ALTER USER {pg_ident} WITH PASSWORD '{db_password}';",
            ],
            environment={"PGPASSWORD": db_password},
        )
        if passwd_res.exit_code != 0:
            raise ProvisioningError(
                f"Failed to synchronize tenant database password: {passwd_res.output.decode()}"
            )

        ext_res = pg_container.exec_run(
            [
                "psql", "-h", "127.0.0.1",
                "-U", pg_ident, "-d", pg_ident,
                "-v", "ON_ERROR_STOP=1",
                "-c", "CREATE EXTENSION IF NOT EXISTS timescaledb;",
            ],
            environment={"PGPASSWORD": db_password},
        )
        if ext_res.exit_code != 0:
            raise ProvisioningError(
                f"Failed to create TimescaleDB extension: {ext_res.output.decode()}"
            )

        redis_container = client.containers.run(
            image="redis:7-alpine",
            name=redis_name,
            detach=True,
            network=NETWORK_NAME,
            volumes={redis_volume: {"bind": "/data", "mode": "rw"}},
            restart_policy={"Name": "unless-stopped"},
            command="redis-server --appendonly yes",
        )
    except Exception as exc:
        logger.exception("Provisioning of tenant '%s' failed - rolling back", tenant_id)
        _remove_resources(client, (redis_name, pg_name), (redis_volume, pg_volume))
        if isinstance(exc, ProvisioningError):
            raise
        raise ProvisioningError(f"Unexpected provisioning error: {exc}") from exc

    return {
        "tenant_id": tenant_id,
        "postgres": {
            "container_name": pg_name,
            "container_id": pg_container.id,
            "internal_host": pg_name,
            "port": 5432,
            "user": pg_ident,
            "password": db_password,
            "database": pg_ident,
        },
        "redis": {
            "container_name": redis_name,
            "container_id": redis_container.id,
            "internal_host": redis_name,
            "port": 6379,
        },
    }


def rollback_tenant_infrastructure(tenant_id: str) -> None:
    """
    Removes the Postgres/Redis containers + volumes and the RabbitMQ vhost/user
    of a tenant (best effort, never raises).

    ONLY call this when provision_tenant_infrastructure() succeeded in the SAME
    command and a later step (RabbitMQ) failed. Never call it for a tenant that
    already existed before - it would delete that tenant's data.
    """
    _validate_tenant_id(tenant_id)
    client = _client()

    pg_name = f"tenant-{tenant_id}-postgres"
    redis_name = f"tenant-{tenant_id}-redis"
    _remove_resources(
        client,
        (redis_name, pg_name),
        (f"{redis_name}-data", f"{pg_name}-data"),
    )

    auth = (RABBITMQ_ADMIN_USER, RABBITMQ_ADMIN_PASSWORD)
    for path in (f"vhosts/tenant-{tenant_id}", f"users/tenant_{tenant_id}"):
        try:
            requests.delete(f"{RABBITMQ_MGMT_URL}/api/{path}", auth=auth, timeout=10)
        except requests.RequestException:
            logger.exception("Cleanup: could not delete RabbitMQ %s", path)


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