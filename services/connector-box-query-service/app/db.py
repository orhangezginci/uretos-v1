"""
System-Postgres access for the connector-box registry - READ SIDE ONLY.

This service never writes to the `connector_boxes` table -
connector-box-command-service is the single writer, per uretOS's CQRS
convention.
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


def list_connector_boxes() -> list[dict[str, Any]]:
    """
    Returns connector-box registry entries WITHOUT the pairing_token -
    the token is a credential, and a query response should never carry
    secrets, same reasoning as leaving passwords out of the tenant list.
    """
    with psycopg.connect(SYSTEM_DB_URL, row_factory=dict_row) as conn:
        rows = conn.execute(
            """
            SELECT box_id, tenant_id, hardware_id, mac_address, status, created_at
            FROM connector_boxes
            ORDER BY created_at DESC
            """
        ).fetchall()
    for row in rows:
        row["box_id"] = str(row["box_id"])
        row["created_at"] = row["created_at"].isoformat()
    return rows