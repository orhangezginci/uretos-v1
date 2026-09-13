"""
System-Postgres access for the tenant registry - READ SIDE ONLY.

This service never writes to the `tenants` table - tenant-command-service
is the single writer, per uretOS's CQRS convention.
"""
from __future__ import annotations

import os
from typing import Any

import psycopg
from psycopg.rows import dict_row

SYSTEM_DB_URL = os.environ.get(
    "SYSTEM_DB_URL",
    "postgresql://uretos_system:uretos_system_dev_pass@system-postgres:5432/uretos_system",
)


def list_tenants() -> list[dict[str, Any]]:
    """
    Returns tenant registry entries WITHOUT credentials - postgres_password
    is deliberately excluded here, even though this is currently only ever
    read by the super_admin. No query response should ever carry secrets.
    """
    with psycopg.connect(SYSTEM_DB_URL, row_factory=dict_row) as conn:
        rows = conn.execute(
            """
            SELECT tenant_id, status, created_at, postgres_host, postgres_db,
                   redis_host
            FROM tenants
            ORDER BY created_at DESC
            """
        ).fetchall()
    for row in rows:
        row["created_at"] = row["created_at"].isoformat()
    return rows