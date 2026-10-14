from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import jsonschema

# Versuche den Pfad flexibel zu finden (entweder relativ zu src oder im gemounteten Kontext)
_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "contracts" / "cloudevent-v1.0.json"
if not _SCHEMA_PATH.exists():
    # Fallback für andere Ordnerstrukturen im Container
    _SCHEMA_PATH = Path("/app/contracts/cloudevent-v1.0.json")

_SCHEMA = json.loads(_SCHEMA_PATH.read_text()) if _SCHEMA_PATH.exists() else {}


def build_envelope(
    event_type: str,
    source: str,
    data: dict[str, Any],
    tenant_id: str,
    messagetype: str = "event",
    correlation_id: Optional[str] = None,
    subject: Optional[str] = None,
) -> dict[str, Any]:
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
    if _SCHEMA:
        jsonschema.validate(instance=envelope, schema=_SCHEMA)


def loads(raw_body: bytes) -> dict[str, Any]:
    envelope = json.loads(raw_body)
    validate_envelope(envelope)
    return envelope