"""
CloudEvent envelope builder helper for uretOS services.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone


def build_envelope(
    event_type: str,
    source: str,
    data: dict,
    tenant_id: str,
    messagetype: str = "event",
    correlation_id: str | None = None,
) -> dict:
    return {
        "specversion": "1.0",
        "type": event_type,
        "source": source,
        "id": str(uuid.uuid4()),
        "time": datetime.now(timezone.utc).isoformat(),
        "tenantid": tenant_id,
        "messagetype": messagetype,
        "correlationid": correlation_id or str(uuid.uuid4()),
        "data": data,
    }