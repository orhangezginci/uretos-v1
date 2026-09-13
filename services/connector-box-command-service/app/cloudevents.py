"""
Minimal CloudEvent v1.0 (uretOS dialect) envelope helper.

This module is intentionally duplicated per-service rather than shared as a
library, per uretOS's hyper-decoupled architecture principle. Any service
needing this logic should copy this file, not import it from elsewhere.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import jsonschema

_SCHEMA_PATH = Path(__file__).parent.parent / "contracts" / "cloudevent-v1.0.json"
_SCHEMA = json.loads(_SCHEMA_PATH.read_text())


def build_envelope(
    *,
    event_type: str,
    source: str,
    data: dict[str, Any],
    tenant_id: str,
    messagetype: str = "event",
    correlation_id: Optional[str] = None,
    subject: Optional[str] = None,
) -> dict[str, Any]:
    """Build a CloudEvent envelope dict ready to be published to RabbitMQ."""
    envelope = {
        "specversion": "1.0",
        "id": str(uuid.uuid4()),
        "source": source,
        "type": event_type,
        "datacontenttype": "application/json",
        "time": datetime.now(timezone.utc).isoformat(),
        "correlationid": correlation_id or str(uuid.uuid4()),
        "messagetype": messagetype,
        "tenantid": tenant_id,
        "data": data,
    }
    if subject:
        envelope["subject"] = subject
    validate_envelope(envelope)
    return envelope


def validate_envelope(envelope: dict[str, Any]) -> None:
    """Raises jsonschema.ValidationError if the envelope is malformed."""
    jsonschema.validate(instance=envelope, schema=_SCHEMA)


def loads(raw_body: bytes) -> dict[str, Any]:
    """Parse and validate a raw RabbitMQ message body into an envelope."""
    envelope = json.loads(raw_body)
    validate_envelope(envelope)
    return envelope