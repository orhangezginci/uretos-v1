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
"""
from __future__ import annotations

import logging
import os
import time

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from models import MachineModel

log = logging.getLogger("machine-command-service.db")

SYSTEM_DB_URL = os.environ.get(
    "SYSTEM_DB_URL",
    "postgresql+psycopg://uretos_system:uretos_system_dev_pass@system-postgres:5432/uretos_system",
)

# A freshly provisioned tenant-postgres container may not accept connections yet.
SCHEMA_RETRY_ATTEMPTS = int(os.environ.get("TENANT_DB_RETRY_ATTEMPTS", "6"))
SCHEMA_RETRY_DELAY_SECONDS = float(os.environ.get("TENANT_DB_RETRY_DELAY_SECONDS", "2"))

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
            return
        except OperationalError:
            if attempt == SCHEMA_RETRY_ATTEMPTS:
                raise
            log.warning(
                "Tenant DB of '%s' not ready (attempt %d/%d), retrying...",
                tenant_id, attempt, SCHEMA_RETRY_ATTEMPTS,
            )
            time.sleep(SCHEMA_RETRY_DELAY_SECONDS)


def _get_tenant_engine(tenant_id: str) -> Engine:
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
    _ensure_tenant_schema(engine, tenant_id)

    _tenant_engines[tenant_id] = engine
    log.info("Tenant engine for '%s' ready", tenant_id)
    return engine


def register_machines_for_box(hardware_id: str, machines: list[dict]) -> tuple[list[dict], str | None, str | None]:
    try:
        with _system_engine.connect() as conn:
            box_row = conn.execute(
                text("SELECT box_id, tenant_id FROM connector_boxes WHERE hardware_id = :hw_id"),
                {"hw_id": hardware_id},
            ).fetchone()

        if not box_row:
            return [], f"Connector box with hardware_id '{hardware_id}' not found.", None

        box_id = str(box_row.box_id)
        tenant_id = str(box_row.tenant_id)

        engine = _get_tenant_engine(tenant_id)

        persisted = []
        with Session(engine) as db:
            for m in machines:
                machine_id = m.get("machine_id") or m.get("node_id") or m.get("name")
                if not machine_id:
                    db.rollback()
                    return [], "Machine entry without machine_id, node_id or name.", tenant_id

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

        return persisted, None, tenant_id

    except Exception as e:
        log.exception("Machine registration failed for hardware_id=%s", hardware_id)
        return [], str(e), None