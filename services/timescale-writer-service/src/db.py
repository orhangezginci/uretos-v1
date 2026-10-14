"""
Database operations for timescale-writer-service using SQLAlchemy ORM.
"""
from __future__ import annotations

import logging
import os
import time

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from models import MachineStateModel

logger = logging.getLogger("timescale-writer.db")

SYSTEM_DB_URL = os.environ.get(
    "SYSTEM_DB_URL",
    "postgresql+psycopg://uretos_system:uretos_system_dev_pass@system-postgres:5432/uretos_system",
)

SCHEMA_RETRY_ATTEMPTS = int(os.environ.get("TENANT_DB_RETRY_ATTEMPTS", "6"))
SCHEMA_RETRY_DELAY_SECONDS = float(os.environ.get("TENANT_DB_RETRY_DELAY_SECONDS", "2"))

_system_engine = create_engine(SYSTEM_DB_URL, pool_pre_ping=True)
_tenant_engines: dict[str, Engine] = {}


class TenantNotFound(RuntimeError):
    pass


def init_db() -> None:
    """Verifiziert die Erreichbarkeit der System-DB."""
    with _system_engine.connect() as conn:
        conn.execute(text("SELECT 1"))


def _ensure_tenant_schema(engine: Engine, tenant_id: str) -> None:
    """Erstellt die Tabelle deklarativ über SQLAlchemy und konfiguriert sie als Hypertable."""
    for attempt in range(1, SCHEMA_RETRY_ATTEMPTS + 1):
        try:
            # SQLAlchemy-Modell erzeugt die Tabelle konform zu Postgres-Standards
            MachineStateModel.__table__.create(bind=engine, checkfirst=True)

            # TimescaleDB Hypertable & Indizes über raw connection initialisieren
            with engine.begin() as conn:
                conn.execute(text("SELECT create_hypertable('machine_states', 'time', if_not_exists => TRUE);"))
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_machine_states_latest 
                    ON machine_states (tenant_id, machine_id, time DESC);
                """))
            return
        except OperationalError:
            if attempt == SCHEMA_RETRY_ATTEMPTS:
                raise
            logger.warning(
                "Tenant DB of '%s' not ready (attempt %d/%d), retrying...",
                tenant_id, attempt, SCHEMA_RETRY_ATTEMPTS,
            )
            time.sleep(SCHEMA_RETRY_DELAY_SECONDS)
        except Exception as e:
            # Falls TimescaleDB in der Tenant-Instanz evtl. zickt oder schon Hypertable ist
            logger.warning(f"Hinweis bei Hypertable-Initialisierung für Tenant {tenant_id}: {e}")
            return


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
    logger.info("Tenant engine for '%s' ready via SQLAlchemy ORM", tenant_id)
    return engine


def insert_machine_state(tenant_id: str, machine_id: str, status: str, error_code: str | None) -> None:
    """Schreibt Maschinenzustände typsicher über eine SQLAlchemy Session."""
    engine = _get_tenant_engine(tenant_id)
    with Session(engine) as session:
        state = MachineStateModel(
            tenant_id=tenant_id,
            machine_id=machine_id,
            status=status,
            error_code=error_code,
        )
        session.add(state)
        session.commit()