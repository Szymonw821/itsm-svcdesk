# ai-generated: 85% - Claude Code drafted the whole package from docs/REQUIREMENTS.md and docs/API.md, reviewed by the author
"""Ticket lifecycle and decision C2 (reopening a closed ticket), see docs/API.md section 6."""

from datetime import datetime, timedelta

REOPEN_WINDOW = timedelta(days=7)

# C2 = immutable (DECISIONS.md): a closed ticket can never be reopened; only a resolved one can.
ALLOW_REOPEN_FROM_CLOSED = False

_TRANSITIONS = {
    "ack": ("new", "acknowledged"),
    "start": ("acknowledged", "in_progress"),
    "resolve": ("in_progress", "resolved"),
    "close": ("resolved", "closed"),
}


class InvalidTransition(Exception):
    """The requested action is not allowed from the ticket's current state."""


def apply_action(record: dict, action: str, now: datetime) -> None:
    if action == "reopen":
        _reopen(record, now)
        return
    if action not in _TRANSITIONS:
        raise InvalidTransition(action)
    src, dst = _TRANSITIONS[action]
    if record["state"] != src:
        raise InvalidTransition(action)
    record["state"] = dst
    if action == "ack":
        record["acknowledged_at"] = now
    elif action == "resolve":
        record["resolved_at"] = now
    elif action == "close":
        record["closed_at"] = now


def _reopen(record: dict, now: datetime) -> None:
    state = record["state"]
    if state == "resolved" and now <= record["resolved_at"] + REOPEN_WINDOW:
        _reset_to_in_progress(record)
        return
    if (
        state == "closed"
        and ALLOW_REOPEN_FROM_CLOSED
        and now <= record["closed_at"] + REOPEN_WINDOW
    ):
        _reset_to_in_progress(record)
        return
    raise InvalidTransition("reopen")


def _reset_to_in_progress(record: dict) -> None:
    # Reopening does not restart or extend the resolution target: resolve_due_at is untouched.
    record["state"] = "in_progress"
    record["resolved_at"] = None
    record["closed_at"] = None
