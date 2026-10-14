from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
import jsonschema

_SCHEMA_PATH = Path(__file__).resolve().parent.parent.parent / "contracts" / "cloudevent-v1.0.json"
if not _SCHEMA_PATH.exists():
    _SCHEMA_PATH = Path("/app/contracts/cloudevent-v1.0.json")

_SCHEMA = json.loads(_SCHEMA_PATH.read_text()) if _SCHEMA_PATH.exists() else {}

def build_envelope(
    event_type: str,
    source: str,
    data: dict[str, Any],
    tenant_id: str,
    messagetype: str = "query",
    correlation_id: Optional[str] = None,
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
    if _SCHEMA:
        jsonschema.validate(instance=envelope, schema=_SCHEMA)
    return envelope