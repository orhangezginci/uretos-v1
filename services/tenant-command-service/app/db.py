"""
System-Postgres access for the tenant registry - WRITE SIDE ONLY.

This service is the single writer for the `tenants` table, per uretOS's
CQRS convention. Reading happens exclusively through tenant-query-service.

Uses SQLAlchemy ORM instead of hand-written SQL. No migration framework
(Alembic) - schema changes during this early stage are handled by
resetting the database (docker compose down -v), not by altering
existing tables in place.
"""
from __future__ import annotations

import os
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from models import Base, Tenant

SYSTEM_DB_URL = os.environ.get(
    "SYSTEM_DB_URL",
    "postgresql+psycopg://uretos_system:uretos_system_dev_pass@system-postgres:5432/uretos_system",
)

_engine = create_engine(SYSTEM_DB_URL)


def ensure_schema() -> None:
    Base.metadata.create_all(_engine)


def insert_tenant(infra_info: dict[str, Any]) -> None:
    pg = infra_info["postgres"]
    redis = infra_info["redis"]
    rabbitmq = infra_info["rabbitmq"]

    tenant = Tenant(
        tenant_id=infra_info["tenant_id"],
        postgres_host=pg["internal_host"],
        postgres_port=pg["port"],
        postgres_user=pg["user"],
        postgres_password=pg["password"],
        postgres_db=pg["database"],
        redis_host=redis["internal_host"],
        redis_port=redis["port"],
        rabbitmq_vhost=rabbitmq["vhost"],
        rabbitmq_user=rabbitmq["user"],
        rabbitmq_password=rabbitmq["password"],
    )

    with Session(_engine) as session:
        session.add(tenant)
        session.commit()