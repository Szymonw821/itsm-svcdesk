# ai-generated: 85% - Claude Code drafted the whole package from docs/REQUIREMENTS.md and docs/API.md, reviewed by the author
"""In-memory ticket repository (Lab 1 scope; R-23 persistence is not graded in Tier A this lab)."""

import uuid

_tickets: dict[str, dict] = {}


def create(fields: dict) -> dict:
    ticket_id = str(uuid.uuid4())
    record = {"id": ticket_id, **fields}
    _tickets[ticket_id] = record
    return record


def get(ticket_id: str) -> dict | None:
    return _tickets.get(ticket_id)


def list_all(state: str | None = None, priority: str | None = None) -> list[dict]:
    values = list(_tickets.values())
    if state is not None:
        values = [t for t in values if t["state"] == state]
    if priority is not None:
        values = [t for t in values if t["priority"] == priority]
    return values
