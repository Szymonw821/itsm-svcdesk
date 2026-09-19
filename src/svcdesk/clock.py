# ai-generated: 85% - Claude Code drafted the whole package from docs/REQUIREMENTS.md and docs/API.md, reviewed by the author
"""Per-request "now": the real clock, or X-Test-Clock when SVCDESK_TEST_CLOCK is enabled (API.md section 8)."""

import os
from datetime import datetime, timezone


class ClockError(ValueError):
    """Raised when X-Test-Clock is present but does not parse as an RFC 3339 instant with an offset."""


def _test_clock_enabled() -> bool:
    return os.environ.get("SVCDESK_TEST_CLOCK", "").strip().lower() in ("1", "true")


def resolve_now(header_value: str | None) -> datetime:
    if not _test_clock_enabled() or not header_value:
        return datetime.now(timezone.utc)

    value = header_value.strip()
    if value.endswith("Z") or value.endswith("z"):
        value = value[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ClockError(f"X-Test-Clock is not a valid RFC 3339 instant: {header_value!r}") from exc

    if parsed.tzinfo is None:
        raise ClockError(f"X-Test-Clock is missing a UTC offset: {header_value!r}")

    return parsed.astimezone(timezone.utc)
