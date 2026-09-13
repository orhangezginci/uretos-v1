"""
System-Postgres access for the tenant registry - WRITE SIDE ONLY.

This service is the single writer for the `tenants` table, per uretOS's
CQRS convention. Reading happens exclusively through a separate read-service
- never here.
"""
from __future__ import annotations

import os
from typing import Any

import psycopg

SYSTEM_DB_URL = os.environ.get(
    "SYSTEM_DB_URL",
    "postgresql://uretos_system:uretos_system_dev_pass@system-postgres:5432/uretos_system",
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS tenants (
    tenant_id       TEXT PRIMARY KEY,
    status          TEXT NOT NULL DEFAULT 'active',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    postgres_host   TEXT NOT NULL,
    postgres_port   INTEGER NOT NULL,
    postgres_user   TEXT NOT NULL,
    postgres_password TEXT NOT NULL,
    postgres_db     TEXT NOT NULL,
    redis_host      TEXT NOT NULL,
    redis_port      INTEGER NOT NULL
);
"""


def ensure_schema() -> None:
    with psycopg.connect(SYSTEM_DB_URL) as conn:
        conn.execute(_SCHEMA)
        conn.commit()


def insert_tenant(infra_info: dict[str, Any]) -> None:
    pg = infra_info["postgres"]
    redis = infra_info["redis"]
    with psycopg.connect(SYSTEM_DB_URL) as conn:
        conn.execute(
            """
            INSERT INTO tenants (
                tenant_id, postgres_host, postgres_port, postgres_user,
                postgres_password, postgres_db, redis_host, redis_port
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                infra_info["tenant_id"],
                pg["internal_host"],
                pg["port"],
                pg["user"],
                pg["password"],
                pg["database"],
                redis["internal_host"],
                redis["port"],
            ),
        )
        conn.commit()       