"""
System-Postgres access for the tenant registry - READ SIDE ONLY.

This service never writes to the `tenants` table - tenant-command-service
is the single writer, per uretOS's CQRS convention.

Uses SQLAlchemy ORM. No secrets (postgres_password, rabbitmq_password) are
ever included in query responses - same reasoning as never returning
credentials from a read endpoint, regardless of who's currently asking.
"""
from __future__ import annotations

import os
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from models import Tenant

SYSTEM_DB_URL = os.environ.get(
    "SYSTEM_DB_URL",
    "postgresql+psycopg://uretos_system:uretos_system_dev_pass@system-postgres:5432/uretos_system",
)

_engine = create_engine(SYSTEM_DB_URL)


def list_tenants() -> list[dict[str, Any]]:
    with Session(_engine) as session:
        tenants = session.scalars(select(Tenant).order_by(Tenant.created_at.desc())).all()
        return [
            {
                "tenant_id": t.tenant_id,
                "status": t.status,
                "created_at": t.created_at.isoformat(),
                "postgres_host": t.postgres_host,
                "postgres_db": t.postgres_db,
                "redis_host": t.redis_host,
                "rabbitmq_vhost": t.rabbitmq_vhost,
                "rabbitmq_user": t.rabbitmq_user,
            }
            for t in tenants
        ]