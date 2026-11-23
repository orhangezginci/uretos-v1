"""
Registration rules of the machine-command-service (pure Python, no database access, unit-testable).

  1. A machine belongs to at most ONE connector box          -> error_code "machine_taken"
  2. A box holds at most `limit` machines (license)          -> error_code "box_limit_reached"

db.py loads the facts (who owns what) inside one transaction that holds a per-tenant lock and asks
check_registration() whether the requested registration is allowed. Nothing is written if it is not.
"""
from __future__ import annotations


class RegistrationRejected(Exception):
    """A rule was violated. `code` is machine readable (travels to the gateway), `reason` is safe for external clients
    (it names machine ids, but never other boxes, hosts or credentials)."""

    def __init__(self, code: str, reason: str):
        super().__init__(reason)
        self.code = code
        self.reason = reason


def resolve_identities(machines: list[dict]) -> list[tuple[str, dict, bool]]:
    """-> [(machine_id, machine, stable)]. `stable` is False when the id had to be derived from the name."""
    out: list[tuple[str, dict, bool]] = []
    for m in machines:
        explicit = m.get("machine_id") or m.get("node_id")
        machine_id = explicit or m.get("name")
        if not machine_id:
            raise RegistrationRejected("invalid_machine", "Machine entry without machine_id, node_id or name.")
        out.append((str(machine_id), m, bool(explicit)))
    return out


def check_registration(ids: list[str], taken_elsewhere: set[str], owned_by_box: set[str], limit: int) -> list[str]:
    """Raises RegistrationRejected or returns the ids that are NEW for this box.
    Re-registering a machine the box already owns is an update and does not count against the limit."""
    if len(set(ids)) != len(ids):
        raise RegistrationRejected("duplicate_in_batch", "The same machine appears more than once in one registration.")
    taken = taken_elsewhere & set(ids)
    if taken:
        raise RegistrationRejected(
            "machine_taken", "Machine(s) already assigned to another connector box: " + ", ".join(sorted(taken)))
    new = [i for i in ids if i not in owned_by_box]
    if len(owned_by_box) + len(new) > limit:
        raise RegistrationRejected(
            "box_limit_reached",
            f"Box limit reached: {len(owned_by_box)} of {limit} machines already assigned, {len(new)} new requested.")
    return new
