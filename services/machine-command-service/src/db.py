"""
Database operations for machine-command-service.

Two databases are involved:

- system-postgres (READ ONLY usage here): resolves hardware_id -> box_id/tenant_id
  via `connector_boxes`, and tenant_id -> connection info via `tenants`.
- tenant-postgres (one instance per tenant): the `machines` table lives here.
  Engines are created lazily per tenant and cached.

The tenant is always derived from the connector box row in system-postgres,
never from the message payload, so a manipulated payload can not point a
write at another tenant's database.

Engine cache:
  The cached engine holds the credentials it was built with. If a tenant is
  re-provisioned (new container, new password), the cached engine is stale.
  Any OperationalError while talking to the tenant DB therefore drops the
  cached engine, re-reads the credentials from system-postgres and retries
  exactly once.

Registration rules (see registration_rules.py), enforced HERE because only the server can guarantee them:
  - a machine belongs to at most one connector box of the tenant,
  - a box holds at most MAX_MACHINES_PER_BOX machines.
Both are checked inside one transaction that holds a per-tenant advisory lock, so two boxes registering at the same
time cannot overtake each other. A unique index on machines.machine_id is created as a database-level backstop.
"""
from __future__ import annotations

import logging
import os
import time

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, Engine
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from models import MachineModel
from registration_rules import RegistrationRejected, check_registration, resolve_identities

log = logging.getLogger("machine-command-service.db")

SYSTEM_DB_URL = os.environ.get(
    "SYSTEM_DB_URL",
    "postgresql+psycopg://uretos_system:uretos_system_dev_pass@system-postgres:5432/uretos_system",
)

# A freshly provisioned tenant-postgres container may not accept connections yet.
SCHEMA_RETRY_ATTEMPTS = int(os.environ.get("TENANT_DB_RETRY_ATTEMPTS", "6"))
SCHEMA_RETRY_DELAY_SECONDS = float(os.environ.get("TENANT_DB_RETRY_DELAY_SECONDS", "2"))

# License: maximum number of machines per connector box.
# TODO: read this from the tenant's license instead of the environment.
MAX_MACHINES_PER_BOX = int(os.environ.get("MAX_MACHINES_PER_BOX", "5"))
# Constant is enough: every tenant has its own database, so the lock is effectively per tenant.
_REGISTRATION_LOCK_KEY = 724_001

_system_engine = create_engine(SYSTEM_DB_URL, pool_pre_ping=True)
_tenant_engines: dict[str, Engine] = {}


class TenantNotFound(RuntimeError):
    pass


def init_db() -> None:
    """
    No schema creation here anymore: system-postgres is not ours to write to,
    and the machines table is created per tenant on first use.
    Only verifies that the system registry is reachable.
    """
    with _system_engine.connect() as conn:
        conn.execute(text("SELECT 1"))


def _ensure_tenant_schema(engine: Engine, tenant_id: str) -> None:
    for attempt in range(1, SCHEMA_RETRY_ATTEMPTS + 1):
        try:
            MachineModel.__table__.create(bind=engine, checkfirst=True)
            _ensure_unique_identity(engine, tenant_id)
            return
        except OperationalError:
            if attempt == SCHEMA_RETRY_ATTEMPTS:
                raise
            log.warning(
                "Tenant DB of '%s' not ready (attempt %d/%d), retrying...",
                tenant_id, attempt, SCHEMA_RETRY_ATTEMPTS,
            )
            time.sleep(SCHEMA_RETRY_DELAY_SECONDS)


def _ensure_unique_identity(engine: Engine, tenant_id: str) -> None:
    """Database-level backstop: a machine exists once per tenant. Idempotent, also retrofits existing tenants.
    Legacy duplicates make the index impossible; that is logged and the application-level check still applies."""
    try:
        with engine.begin() as conn:
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_machines_machine_id ON machines (machine_id)"))
    except IntegrityError:
        log.warning("Tenant '%s' has duplicate machine_ids - unique index not created, clean up the legacy data", tenant_id)


def _invalidate_tenant_engine(tenant_id: str) -> None:
    """Drops the cached engine of a tenant and closes its connection pool."""
    engine = _tenant_engines.pop(tenant_id, None)
    if engine is not None:
        engine.dispose()


def _get_tenant_engine(tenant_id: str, force_reconnect: bool = False) -> Engine:
    if force_reconnect:
        _invalidate_tenant_engine(tenant_id)
    else:
        engine = _tenant_engines.get(tenant_id)
        if engine is not None:
            return engine

    with _system_engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT postgres_host, postgres_port, postgres_user, "
                "postgres_password, postgres_db FROM tenants WHERE tenant_id = :t"
            ),
            {"t": tenant_id},
        ).fetchone()

    if row is None:
        raise TenantNotFound(f"Tenant '{tenant_id}' not found in registry.")

    url = URL.create(
        "postgresql+psycopg",
        username=row.postgres_user,
        password=row.postgres_password,
        host=row.postgres_host,
        port=row.postgres_port,
        database=row.postgres_db,
    )
    engine = create_engine(url, pool_pre_ping=True)
    try:
        _ensure_tenant_schema(engine, tenant_id)
    except Exception:
        engine.dispose()
        raise

    _tenant_engines[tenant_id] = engine
    log.info("Tenant engine for '%s' ready", tenant_id)
    return engine


def _persist_machines(engine: Engine, box_id: str, tenant_id: str, machines: list[dict]) -> list[dict]:
    """Registers the machines for a box. Raises RegistrationRejected (and writes nothing) if a rule is violated.
    Facts are read and the machines written in ONE transaction that holds a per-tenant lock."""
    persisted: list[dict] = []
    with Session(engine) as db:
        if engine.dialect.name == "postgresql":
            db.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": _REGISTRATION_LOCK_KEY})

        entries = resolve_identities(machines)
        for machine_id, _, stable in entries:
            if not stable:
                log.warning("Machine '%s' has no machine_id/node_id - its name is used as identity (not stable)", machine_id)
        ids = [machine_id for machine_id, _, _ in entries]

        taken = {r[0] for r in db.query(MachineModel.machine_id).filter(
            MachineModel.machine_id.in_(ids), MachineModel.box_id != box_id)}
        owned = {r[0] for r in db.query(MachineModel.machine_id).filter(MachineModel.box_id == box_id)}
        check_registration(ids, taken, owned, MAX_MACHINES_PER_BOX)

        for machine_id, m, _ in entries:
            name = m.get("name", "Unknown Machine")
            endpoint_url = m.get("endpoint_url", "")

            existing = db.query(MachineModel).filter_by(machine_id=machine_id, box_id=box_id).first()

            if existing:
                existing.name = name
                existing.endpoint_url = endpoint_url
                existing.metadata_json = m
            else:
                db.add(
                    MachineModel(
                        machine_id=machine_id,
                        box_id=box_id,
                        tenant_id=tenant_id,
                        name=name,
                        endpoint_url=endpoint_url,
                        metadata_json=m,
                    )
                )

            persisted.append({"machine_id": machine_id, "name": name})

        db.commit()

    return persisted


def register_machines_for_box(
    hardware_id: str, machines: list[dict]
) -> tuple[list[dict], str | None, str | None, str | None]:
    """-> (persisted, error_reason, tenant_id, error_code). error_code is machine readable, e.g. machine_taken,
    box_limit_reached, invalid_machine, box_not_found, tenant_not_found, tenant_db_unreachable, internal_error."""
    tenant_id: str | None = None
    try:
        with _system_engine.connect() as conn:
            box_row = conn.execute(
                text("SELECT box_id, tenant_id FROM connector_boxes WHERE hardware_id = :hw_id"),
                {"hw_id": hardware_id},
            ).fetchone()

        if not box_row:
            return [], f"Connector box with hardware_id '{hardware_id}' not found.", None, "box_not_found"

        box_id = str(box_row.box_id)
        tenant_id = str(box_row.tenant_id)

        try:
            persisted = _persist_machines(_get_tenant_engine(tenant_id), box_id, tenant_id, machines)
        except OperationalError:
            # Cached engine may hold outdated credentials (tenant re-provisioned),
            # or the tenant DB was not reachable. Rebuild from the registry, retry once.
            log.warning(
                "Tenant DB access failed for '%s' - dropping cached engine and retrying once",
                tenant_id,
            )
            persisted = _persist_machines(
                _get_tenant_engine(tenant_id, force_reconnect=True), box_id, tenant_id, machines
            )

        return persisted, None, tenant_id, None

    except RegistrationRejected as e:
        log.info("Registration rejected for hardware_id=%s: [%s] %s", hardware_id, e.code, e.reason)
        return [], e.reason, tenant_id, e.code

    except IntegrityError:
        # Database-level backstop (unique machine identity) caught a writer that bypassed the lock.
        log.warning("Integrity error while registering machines for hardware_id=%s", hardware_id, exc_info=True)
        return [], "Machine already assigned to another connector box.", tenant_id, "machine_taken"

    except TenantNotFound as e:
        return [], str(e), None, "tenant_not_found"

    except OperationalError:
        # Full details only in the log: the reason travels to external clients
        # and must not contain internal hosts, ports or database users.
        log.exception("Tenant database not reachable for hardware_id=%s", hardware_id)
        return [], "Tenant database not reachable.", None, "tenant_db_unreachable"

    except Exception as e:
        log.exception("Machine registration failed for hardware_id=%s", hardware_id)
        return [], str(e), None, "internal_error"
