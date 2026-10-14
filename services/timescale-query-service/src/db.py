from __future__ import annotations

import logging
import os

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import URL, Engine
from sqlalchemy.orm import Session

from models import MachineStateModel

log = logging.getLogger("timescale-query-service.db")

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


def get_machine_history(tenant_id: str, machine_id: str, limit: int = 50) -> list[dict]:
    engine = _get_tenant_engine(tenant_id)

    if not inspect(engine).has_table("machine_states"):
        return []

    with Session(engine) as db:
        rows = (
            db.query(MachineStateModel)
            .filter_by(machine_id=machine_id)
            .order_by(MachineStateModel.time.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "time": r.time.isoformat() if r.time else None,
                "status": r.status,
                "error_code": r.error_code,
            }
            for r in rows
        ]