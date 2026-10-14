"""
connector-box-poller

Polls OPC-UA machines periodically using the local discovery module
and reports status changes to the uretOS gateway-api (Variant A).
"""
from __future__ import annotations

import logging
import os
import time
import requests

from discovery import discover_machines

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("connector-box-poller")

GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://gateway-api:8080")
OPC_UA_HOST = os.environ.get("OPC_UA_HOST", "opcua-server")
OPC_UA_PORT = int(os.environ.get("OPC_UA_PORT", "4840"))
POLL_INTERVAL_SECONDS = float(os.environ.get("POLL_INTERVAL_SECONDS", "5.0"))
TENANT_ID = os.environ.get("TENANT_ID", "test-tenant-e2e")

_last_known_statuses: dict[str, str] = {}


def poll_loop() -> None:
    log.info("Starting OPC-UA poller loop targeting %s:%d...", OPC_UA_HOST, OPC_UA_PORT)
    while True:
        try:
            machines = discover_machines(OPC_UA_HOST, OPC_UA_PORT, max_machines=5)
            for m in machines:
                machine_id = m.name or "BasicMachineTool"
                current_status = getattr(m, "status", "ok")
                error_code = getattr(m, "error_code", None)

                if _last_known_statuses.get(machine_id) != current_status:
                    log.info("Status change detected for machine %s: %s", machine_id, current_status)
                    
                    response = requests.patch(
                        f"{GATEWAY_URL}/v1/machines/{machine_id}/status",
                        json={
                            "tenant_id": TENANT_ID,
                            "status": current_status,
                            "error_code": error_code,
                        },
                        timeout=5,
                    )
                    
                    if response.status_code == 200:
                        _last_known_statuses[machine_id] = current_status
                    else:
                        log.warning("Failed to report status: HTTP %d", response.status_code)

        except Exception as exc:
            log.warning("Error during OPC-UA polling cycle: %s", exc)

        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    poll_loop()