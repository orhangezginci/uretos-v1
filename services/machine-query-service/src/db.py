"""
Read-side database access for machine-query-service (multi-tenant).

Machines live in the per-tenant Postgres instance, not in system-postgres.
system-postgres is only used (read only) to look up a tenant's connection
info in the `tenants` table. Engines are created lazily per tenant and cached.

This service never creates or alters tables - the schema is owned by
machine-command-service. If a tenant has no `machines` table yet (nothing was
registered so far), the result is simply an empty list.

The tenant_id is supplied by the gateway (resolved from the connector box or,
until authentication exists, from the request). This service does not decide
which tenant a caller belongs to.
"""
from __future__ import annotations

import logging
import os

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import URL, Engine
from sqlalchemy.orm import Session

from models import MachineModel

log = logging.getLogger("machine-query-service.db")

SYSTEM_DB_URL = os.environ.get(
    "SYSTEM_DB_URL",
    "postgresql+psycopg://uretos_system:uretos_system_dev_pass@system-postgres:5432/uretos_system",
)

_system_engine = create_engine(SYSTEM_DB_URL, pool_pre_ping=True)
_tenant_engines: dict[str, Engine] = {}


class TenantNotFound(RuntimeError):
    pass


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
    _tenant_engines[tenant_id] = engine
    log.info("Tenant engine for '%s' ready", tenant_id)
    return engine


def _serialize(m: MachineModel) -> dict:
    return {
        "machine_id": m.machine_id,
        "box_id": m.box_id,
        "tenant_id": m.tenant_id,
        "name": m.name,
        "endpoint_url": m.endpoint_url,
        "metadata": m.metadata_json,
        "updated_at": m.updated_at.isoformat() if m.updated_at else None,
    }


def _fetch(tenant_id: str, box_id: str | None = None) -> list[dict]:
    engine = _get_tenant_engine(tenant_id)

    if not inspect(engine).has_table("machines"):
        return []

    with Session(engine) as db:
        query = db.query(MachineModel)
        if box_id is not None:
            # str(): box_id is a String(255) column - never bind a uuid.UUID here
            query = query.filter_by(box_id=str(box_id))
        return [_serialize(m) for m in query.order_by(MachineModel.machine_id).all()]


def get_all_machines(tenant_id: str) -> list[dict]:
    return _fetch(tenant_id)


def get_machines_by_box(tenant_id: str, box_id: str) -> list[dict]:
    return _fetch(tenant_id, box_id)
