# ai-generated: 100% - Claude Code wrote these tests from slaclock.py's docstrings, aiming at every documented boundary
"""Behaviour tests for slaclock (Lab 5, Stretch 1): each docstring boundary on both of its sides."""

from datetime import datetime

import pytest

import slaclock
from slaclock import (
    add_business_minutes,
    business_minutes_between,
    escalation_tier,
    is_business_time,
    parse_duration,
    priority_of,
    sla_state,
    targets,
)

# 16 November 2026 is a Monday; 20 November a Friday; 21 and 22 November the weekend.
MON = (2026, 11, 16)
FRI = (2026, 11, 20)
SAT = (2026, 11, 21)
SUN = (2026, 11, 22)
NEXT_MON = (2026, 11, 23)


def at(day, hour, minute=0, second=0, micro=0):
    return datetime(*day, hour, minute, second, micro)


# --- priority_of -----------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "impact, urgency, expected",
    [
        (1, 1, "P1"),
        (1, 2, "P2"),
        (2, 1, "P2"),
        (1, 3, "P3"),
        (2, 2, "P3"),
        (3, 1, "P3"),
        (2, 3, "P4"),
        (3, 2, "P4"),
        (3, 3, "P4"),
    ],
)
def test_priority_matrix(impact, urgency, expected):
    assert priority_of(impact, urgency) == expected
    assert priority_of(impact, urgency, False) == expected
    assert priority_of(impact, urgency, vip=False) == expected


@pytest.mark.parametrize(
    "impact, urgency, expected",
    [
        (1, 1, "P1"),
        (1, 2, "P2"),
        (2, 1, "P2"),
        (1, 3, "P2"),
        (2, 2, "P2"),
        (3, 1, "P2"),
        (2, 3, "P2"),
        (3, 2, "P2"),
        (3, 3, "P2"),
    ],
)
def test_priority_vip(impact, urgency, expected):
    assert priority_of(impact, urgency, vip=True) == expected
    assert priority_of(impact, urgency, True) == expected


@pytest.mark.parametrize("bad", [0, 4, -1, 2.0, 1.0, True, False, "1", None, 100])
def test_priority_rejects_impact(bad):
    with pytest.raises(ValueError):
        priority_of(bad, 1)


@pytest.mark.parametrize("bad", [0, 4, -1, 2.0, 1.0, True, False, "1", None, 100])
def test_priority_rejects_urgency(bad):
    with pytest.raises(ValueError):
        priority_of(1, bad)


def test_priority_rejects_even_for_vip():
    with pytest.raises(ValueError):
        priority_of(4, 1, vip=True)
    with pytest.raises(ValueError):
        priority_of(1, 0, vip=True)


def test_priority_returns_string():
    result = priority_of(3, 3)
    assert isinstance(result, str) and result == "P4"


# --- targets ---------------------------------------------------------------------------------------------------


def test_targets_values():
    assert targets("P1") == (15, 240)
    assert targets("P2") == (60, 480)
    assert targets("P3") == (240, 1440)
    assert targets("P4") == (480, 4320)


@pytest.mark.parametrize("bad", ["p1", " P1", "P1 ", "P5", "P0", "", "P", "1"])
def test_targets_rejects(bad):
    with pytest.raises(ValueError):
        targets(bad)


# --- sla_state -------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "elapsed, target, expected",
    [
        (0, 15, "ok"),
        (11, 15, "ok"),
        (12, 15, "warning"),
        (14, 15, "warning"),
        (15, 15, "warning"),
        (16, 15, "breached"),
        (74, 100, "ok"),
        (75, 100, "warning"),
        (76, 100, "warning"),
        (99, 100, "warning"),
        (100, 100, "warning"),
        (101, 100, "breached"),
        (2, 4, "ok"),
        (3, 4, "warning"),
        (4, 4, "warning"),
        (5, 4, "breached"),
        (0, 1, "ok"),
        (1, 1, "warning"),
        (2, 1, "breached"),
        (1000, 240, "breached"),
        (179, 240, "ok"),
        (180, 240, "warning"),
    ],
)
def test_sla_state(elapsed, target, expected):
    assert sla_state(elapsed, target) == expected


@pytest.mark.parametrize("elapsed, target", [(-1, 15), (-100, 15), (0, 0), (5, 0), (0, -1), (5, -15)])
def test_sla_state_rejects(elapsed, target):
    with pytest.raises(ValueError):
        sla_state(elapsed, target)


def test_warning_percent_constant():
    assert slaclock.WARNING_PERCENT == 75


# --- is_business_time ------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "moment, expected",
    [
        (at(MON, 7, 59), False),
        (at(MON, 8, 0), True),
        (at(MON, 8, 1), True),
        (at(MON, 12, 0), True),
        (at(MON, 15, 59), True),
        (at(MON, 16, 0), False),
        (at(MON, 16, 1), False),
        (at(MON, 0, 0), False),
        (at(MON, 23, 59), False),
        (at(FRI, 8, 0), True),
        (at(FRI, 15, 59), True),
        (at(FRI, 16, 0), False),
        (at(SAT, 8, 0), False),
        (at(SAT, 12, 0), False),
        (at(SUN, 12, 0), False),
        (at(SUN, 15, 59), False),
        (at((2026, 11, 17), 9, 0), True),
        (at((2026, 11, 18), 10, 0), True),
        (at((2026, 11, 19), 11, 0), True),
        (at(MON, 15, 59, 59), True),
        (at(MON, 7, 59, 59), False),
    ],
)
def test_is_business_time(moment, expected):
    assert is_business_time(moment) is expected


# --- add_business_minutes --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "start, minutes, expected",
    [
        (at(MON, 9, 0), 0, at(MON, 9, 0)),
        (at(MON, 8, 0), 0, at(MON, 8, 0)),
        (at(MON, 9, 0), 1, at(MON, 9, 1)),
        (at(MON, 9, 0), 60, at(MON, 10, 0)),
        (at(MON, 8, 0), 480, at(MON, 16, 0)),
        (at(MON, 8, 0), 479, at(MON, 15, 59)),
        (at(MON, 8, 0), 481, at((2026, 11, 17), 8, 1)),
        (at(MON, 15, 0), 60, at(MON, 16, 0)),
        (at(MON, 15, 0), 61, at((2026, 11, 17), 8, 1)),
        (at(MON, 15, 59), 1, at(MON, 16, 0)),
        (at(MON, 15, 59), 2, at((2026, 11, 17), 8, 1)),
        (at(MON, 7, 0), 0, at(MON, 8, 0)),
        (at(MON, 7, 59), 0, at(MON, 8, 0)),
        (at(MON, 7, 0), 30, at(MON, 8, 30)),
        (at(MON, 0, 0), 15, at(MON, 8, 15)),
        (at(MON, 16, 0), 0, at((2026, 11, 17), 8, 0)),
        (at(MON, 16, 0), 15, at((2026, 11, 17), 8, 15)),
        (at(MON, 18, 30), 15, at((2026, 11, 17), 8, 15)),
        (at(FRI, 15, 0), 60, at(FRI, 16, 0)),
        (at(FRI, 15, 0), 120, at(NEXT_MON, 9, 0)),
        (at(FRI, 16, 0), 0, at(NEXT_MON, 8, 0)),
        (at(FRI, 17, 0), 10, at(NEXT_MON, 8, 10)),
        (at(SAT, 10, 0), 0, at(NEXT_MON, 8, 0)),
        (at(SAT, 10, 0), 240, at(NEXT_MON, 12, 0)),
        (at(SUN, 7, 0), 480, at(NEXT_MON, 16, 0)),
        (at(SUN, 23, 59), 1, at(NEXT_MON, 8, 1)),
        (at(MON, 8, 0), 2400, at(FRI, 16, 0)),
        (at(MON, 8, 0), 2401, at(NEXT_MON, 8, 1)),
        (at(MON, 12, 0), 4320, at((2026, 11, 27), 12, 0)),
        (at(MON, 9, 0, 45, 123), 30, at(MON, 9, 30)),
        (at(MON, 15, 59, 59), 1, at(MON, 16, 0)),
        (at(MON, 7, 59, 59), 0, at(MON, 8, 0)),
    ],
)
def test_add_business_minutes(start, minutes, expected):
    assert add_business_minutes(start, minutes) == expected


def test_add_business_minutes_zero_has_no_seconds():
    result = add_business_minutes(at(MON, 10, 30, 15, 999), 0)
    assert result == at(MON, 10, 30)
    assert result.second == 0 and result.microsecond == 0


@pytest.mark.parametrize("minutes", [-1, -480])
def test_add_business_minutes_rejects_negative(minutes):
    with pytest.raises(ValueError):
        add_business_minutes(at(MON, 9, 0), minutes)


def test_add_business_minutes_max_days():
    # 366 calendar days from Monday 16 Nov 2026 is Tuesday 17 Nov 2027. Business days in between: count them.
    start = at(MON, 8, 0)
    last_ok = add_business_minutes(start, 261 * 480)
    assert (last_ok.date() - start.date()).days <= slaclock.MAX_DAYS
    with pytest.raises(ValueError):
        add_business_minutes(start, 600 * 480)


def test_add_business_minutes_exactly_at_max_days():
    start = at(MON, 8, 0)
    # The due date 17 Nov 2027 16:00 is exactly 366 days after the start's date: allowed.
    due = datetime(2027, 11, 17, 16, 0)
    minutes = business_minutes_between(start, due)
    assert add_business_minutes(start, minutes) == due
    # one more minute moves the due date to 18 Nov 2027 08:01, 367 days away: rejected.
    with pytest.raises(ValueError):
        add_business_minutes(start, minutes + 1)


# --- business_minutes_between ----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "start, end, expected",
    [
        (at(MON, 9, 0), at(MON, 9, 0), 0),
        (at(MON, 9, 0), at(MON, 9, 1), 1),
        (at(MON, 9, 0), at(MON, 10, 0), 60),
        (at(MON, 8, 0), at(MON, 16, 0), 480),
        (at(MON, 0, 0), at(MON, 23, 59), 480),
        (at(MON, 7, 0), at(MON, 8, 30), 30),
        (at(MON, 15, 30), at(MON, 17, 0), 30),
        (at(MON, 16, 0), at(MON, 18, 0), 0),
        (at(MON, 6, 0), at(MON, 8, 0), 0),
        (at(MON, 15, 0), at((2026, 11, 17), 9, 0), 120),
        (at(FRI, 15, 0), at(NEXT_MON, 9, 0), 120),
        (at(SAT, 9, 0), at(SUN, 15, 0), 0),
        (at(SAT, 9, 0), at(NEXT_MON, 8, 10), 10),
        (at(MON, 8, 0), at(NEXT_MON, 8, 0), 2400),
        (at(MON, 12, 0), at((2026, 11, 27), 12, 0), 4320),
        (at(MON, 9, 0, 59), at(MON, 9, 1, 1), 1),
        (at(MON, 9, 0, 30), at(MON, 9, 0, 45), 0),
        (at(FRI, 8, 0), at(FRI, 16, 0), 480),
        (at(SUN, 15, 59), at(NEXT_MON, 8, 1), 1),
    ],
)
def test_business_minutes_between(start, end, expected):
    assert business_minutes_between(start, end) == expected


def test_business_minutes_between_rejects_reverse():
    with pytest.raises(ValueError):
        business_minutes_between(at(MON, 10, 0), at(MON, 9, 59))


def test_business_minutes_between_same_minute_reverse_seconds():
    # seconds are ignored: 09:00:30 to 09:00:10 is the same minute, so 0, not an error
    assert business_minutes_between(at(MON, 9, 0, 30), at(MON, 9, 0, 10)) == 0


def test_business_minutes_between_max_days():
    start = at(MON, 9, 0)
    assert business_minutes_between(start, datetime(2027, 11, 17, 9, 0)) > 0  # exactly 366 days: allowed
    with pytest.raises(ValueError):
        business_minutes_between(start, datetime(2027, 11, 18, 9, 0))  # 367 days


@pytest.mark.parametrize(
    "start",
    [at(MON, 9, 0), at(MON, 7, 0), at(MON, 16, 0), at(FRI, 15, 30), at(SAT, 12, 0), at(MON, 15, 59)],
)
@pytest.mark.parametrize("minutes", [0, 1, 59, 60, 479, 480, 481, 1000, 2400, 5000])
def test_roundtrip(start, minutes):
    assert business_minutes_between(start, add_business_minutes(start, minutes)) == minutes


# --- escalation_tier -------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "priority, breached, reopens, expected",
    [
        ("P1", False, 0, 1),
        ("P2", False, 0, 1),
        ("P3", False, 0, 0),
        ("P4", False, 0, 0),
        ("P1", True, 0, 3),
        ("P2", True, 0, 2),
        ("P3", True, 0, 1),
        ("P4", True, 0, 1),
        ("P1", False, 1, 1),
        ("P1", False, 2, 2),
        ("P2", False, 2, 2),
        ("P3", False, 1, 0),
        ("P3", False, 2, 1),
        ("P4", False, 3, 1),
        ("P1", True, 2, 3),
        ("P2", True, 2, 3),
        ("P2", True, 1, 2),
        ("P3", True, 2, 2),
        ("P4", True, 5, 2),
        ("P1", True, 10, 3),
    ],
)
def test_escalation_tier(priority, breached, reopens, expected):
    assert escalation_tier(priority, breached, reopens) == expected


@pytest.mark.parametrize("priority", ["P5", "p1", " P1", "", "P0"])
def test_escalation_rejects_priority(priority):
    with pytest.raises(ValueError):
        escalation_tier(priority, False, 0)


def test_escalation_rejects_negative_reopens():
    with pytest.raises(ValueError):
        escalation_tier("P3", False, -1)
    with pytest.raises(ValueError):
        escalation_tier("P1", True, -5)


# --- parse_duration --------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text, expected",
    [
        ("90m", 90),
        ("1m", 1),
        ("4h", 240),
        ("1h", 60),
        ("1h30m", 90),
        ("2d", 2880),
        ("1d", 1440),
        ("1d4h", 1680),
        ("1d0h5m", 1445),
        ("1h59m", 119),
        ("60m", 60),
        ("0h60m", 60),
        ("0d60m", 60),
        ("0d0h1m", 1),
        ("1d59m", 1499),
        ("2d3h4m", 2880 + 180 + 4),
        ("  90m  ", 90),
        ("\t1h\n", 60),
        ("120m", 120),
        ("0h1m", 1),
        ("0d1h", 60),
        ("25h", 1500),
    ],
)
def test_parse_duration(text, expected):
    assert parse_duration(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "",
        "   ",
        "0m",
        "0h",
        "0d",
        "0d0h0m",
        "1.5h",
        "30m1h",
        "1h1d",
        "-5m",
        "1 h",
        "1h 30m",
        "1H",
        "1M",
        "90",
        "m",
        "1h60m",
        "1d60m",
        "1d0h60m",
        "1h99m",
        "1x",
        "1h1h",
        "abc",
    ],
)
def test_parse_duration_rejects(text):
    with pytest.raises(ValueError):
        parse_duration(text)


# --- whole minutes are ints (module docstring: "Durations and targets are whole minutes (int)") -------------------


@pytest.mark.parametrize(
    "start, end",
    [(at(MON, 9, 0), at(MON, 9, 30)), (at(FRI, 15, 0), at(NEXT_MON, 9, 0)), (at(SAT, 9, 0), at(SUN, 9, 0))],
)
def test_business_minutes_between_is_int(start, end):
    assert type(business_minutes_between(start, end)) is int


def test_add_business_minutes_lands_on_whole_minutes():
    for minutes in (1, 480, 481, 1000):
        due = add_business_minutes(at(MON, 9, 0), minutes)
        assert due.second == 0 and due.microsecond == 0
        assert type(business_minutes_between(at(MON, 9, 0), due)) is int


def test_parse_duration_and_targets_are_int():
    assert type(parse_duration("1h30m")) is int
    assert all(type(value) is int for value in targets("P3"))
    assert type(escalation_tier("P1", True, 2)) is int
