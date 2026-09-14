"""
System-Postgres access for the connector-box registry - WRITE SIDE ONLY.

This service is the single writer for the `connector_boxes` table. Each box
is mandatorily linked to a tenant at creation time (no "unassigned" boxes -
boxes are only built after a customer order comes in).
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
import psycopg

SYSTEM_DB_URL = os.environ.get(
    "SYSTEM_DB_URL",
    "postgresql://uretos_system:uretos_system_dev_pass@system-postgres:5432/uretos_system",
)
JWT_SECRET = os.environ.get("CONNECTOR_BOX_JWT_SECRET", "uretos_dev_jwt_secret_change_me")
PAIRING_TOKEN_TTL_HOURS = 72

_SCHEMA = """
CREATE TABLE IF NOT EXISTS connector_boxes (
    box_id          UUID PRIMARY KEY,
    tenant_id       TEXT NOT NULL REFERENCES tenants(tenant_id),
    hardware_id     TEXT NOT NULL UNIQUE,
    mac_address     TEXT NOT NULL UNIQUE,
    pairing_token   TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending_pairing',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


class ConnectorBoxError(RuntimeError):
    pass


def ensure_schema() -> None:
    with psycopg.connect(SYSTEM_DB_URL) as conn:
        conn.execute(_SCHEMA)
        conn.commit()


def _build_pairing_token(box_id: str, tenant_id: str, hardware_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "box_id": box_id,
        "tenant_id": tenant_id,
        "hardware_id": hardware_id,
        "iat": now,
        "exp": now + timedelta(hours=PAIRING_TOKEN_TTL_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def insert_connector_box(tenant_id: str, hardware_id: str, mac_address: str) -> dict[str, Any]:
    box_id = str(uuid.uuid4())
    pairing_token = _build_pairing_token(box_id, tenant_id, hardware_id)

    try:
        with psycopg.connect(SYSTEM_DB_URL) as conn:
            conn.execute(
                """
                INSERT INTO connector_boxes
                    (box_id, tenant_id, hardware_id, mac_address, pairing_token)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (box_id, tenant_id, hardware_id, mac_address, pairing_token),
            )
            conn.commit()
    except psycopg.errors.ForeignKeyViolation as exc:
        raise ConnectorBoxError(f"Tenant '{tenant_id}' does not exist") from exc
    except psycopg.errors.UniqueViolation as exc:
        raise ConnectorBoxError(
            f"hardware_id '{hardware_id}' or mac_address '{mac_address}' "
            "already registered to another box"
        ) from exc

    return {
        "box_id": box_id,
        "tenant_id": tenant_id,
        "hardware_id": hardware_id,
        "mac_address": mac_address,
        "pairing_token": pairing_token,
        "status": "pending_pairing",
        "pairing_token_expires_in_hours": PAIRING_TOKEN_TTL_HOURS,
    }
# ergänzen in services/connector-box-command-service/app/db.py

def pair_connector_box(hardware_id: str) -> dict[str, Any]:
    """
    Looks up a box by hardware_id and transitions pending_pairing -> paired.
    Returns the box's pairing_token so the (simulated) device receives its
    identity for the first time. Raises ConnectorBoxError if the
    hardware_id is unknown or the box is not in pending_pairing state
    (pairing is a one-time transition, not idempotent).
    """
    with psycopg.connect(SYSTEM_DB_URL) as conn:
        row = conn.execute(
            """
            SELECT box_id, tenant_id, status, pairing_token
            FROM connector_boxes
            WHERE hardware_id = %s
            FOR UPDATE
            """,
            (hardware_id,),
        ).fetchone()

        if row is None:
            raise ConnectorBoxError(f"Unknown hardware_id '{hardware_id}'")

        box_id, tenant_id, status, pairing_token = row
        if status != "pending_pairing":
            raise ConnectorBoxError(
                f"Box '{hardware_id}' is not in pending_pairing state "
                f"(current status: '{status}')"
            )

        conn.execute(
            "UPDATE connector_boxes SET status = 'paired' WHERE hardware_id = %s",
            (hardware_id,),
        )
        conn.commit()

    return {
        "box_id": str(box_id),
        "tenant_id": tenant_id,
        "hardware_id": hardware_id,
        "pairing_token": pairing_token,
        "status": "paired",
    }