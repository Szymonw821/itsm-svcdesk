# ai-generated: 85% - Claude Code drafted the whole package from docs/REQUIREMENTS.md and docs/API.md, reviewed by the author
"""SLA targets, the business-hours clock, and decision C1 (which clock applies to P1), see docs/API.md section 4-5."""

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

WARSAW = ZoneInfo("Europe/Warsaw")
BUSINESS_START = time(8, 0)
BUSINESS_END = time(16, 0)

SLA_TARGETS: dict[str, tuple[timedelta, timedelta]] = {
    "P1": (timedelta(minutes=15), timedelta(hours=4)),
    "P2": (timedelta(hours=1), timedelta(hours=8)),
    "P3": (timedelta(hours=4), timedelta(hours=24)),
    "P4": (timedelta(hours=8), timedelta(hours=72)),
}

# C1 = wallclock (DECISIONS.md): both P1 targets are wall-clock; every other priority is business-hours.
WALLCLOCK_PRIORITIES = {"P1"}


def _is_business_day(day: date) -> bool:
    return day.weekday() < 5  # Monday .. Friday


def _next_business_open(day: date) -> datetime:
    next_day = day + timedelta(days=1)
    while not _is_business_day(next_day):
        next_day += timedelta(days=1)
    return datetime.combine(next_day, BUSINESS_START, tzinfo=WARSAW)


def _advance_to_business_open(local: datetime) -> datetime:
    day = local.date()
    if not _is_business_day(day):
        return _next_business_open(day)
    open_dt = datetime.combine(day, BUSINESS_START, tzinfo=WARSAW)
    close_dt = datetime.combine(day, BUSINESS_END, tzinfo=WARSAW)
    if local < open_dt:
        return open_dt
    if local < close_dt:
        return local
    return _next_business_open(day)


def add_business_time(start_utc: datetime, duration: timedelta) -> datetime:
    """Consume `duration` from consecutive Mon-Fri 08:00-16:00 Europe/Warsaw windows.

    A duration that ends exactly at closing time is due at that closing instant, not at the next
    business day's opening (docs/API.md section 4, vector T4).
    """
    local = _advance_to_business_open(start_utc.astimezone(WARSAW))
    remaining = duration
    while remaining > timedelta(0):
        close_dt = datetime.combine(local.date(), BUSINESS_END, tzinfo=WARSAW)
        available = close_dt - local
        if remaining <= available:
            local = local + remaining
            remaining = timedelta(0)
        else:
            remaining -= available
            local = _next_business_open(local.date())
    return local.astimezone(timezone.utc)


def is_within_business_hours(instant_utc: datetime) -> bool:
    local = instant_utc.astimezone(WARSAW)
    if not _is_business_day(local.date()):
        return False
    return BUSINESS_START <= local.time() < BUSINESS_END


def resolve_clock_is_business(priority: str) -> bool:
    return priority not in WALLCLOCK_PRIORITIES


def compute_sla_due(priority: str, created_at: datetime) -> tuple[datetime, datetime]:
    ack_target, resolve_target = SLA_TARGETS[priority]
    if priority in WALLCLOCK_PRIORITIES:
        return created_at + ack_target, created_at + resolve_target
    return add_business_time(created_at, ack_target), add_business_time(created_at, resolve_target)


def compute_breach_and_pause(record: dict, now: datetime) -> dict:
    """Breach/pause semantics from docs/API.md section 5.

    Reaching a due instant exactly is not a breach. A reopened ticket has `resolved_at` cleared, so
    it is "not resolved" again against its original `resolve_due_at` without any special-casing here.
    """
    ack_due = record["ack_due_at"]
    resolve_due = record["resolve_due_at"]
    acknowledged_at = record["acknowledged_at"]
    resolved_at = record["resolved_at"]

    if acknowledged_at is not None:
        ack_breached = acknowledged_at > ack_due
    else:
        ack_breached = now > ack_due

    if resolved_at is not None:
        resolve_breached = resolved_at > resolve_due
    else:
        resolve_breached = now > resolve_due

    is_open = record["state"] not in ("resolved", "closed")
    paused = is_open and resolve_clock_is_business(record["priority"]) and not is_within_business_hours(now)

    return {
        "ack_breached": ack_breached,
        "resolve_breached": resolve_breached,
        "paused": paused,
    }
