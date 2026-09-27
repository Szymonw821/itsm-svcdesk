# ai-generated: 90% - Claude Code wrote the metric computation from lab2 METRIC-SPEC.md, reviewed by the author
"""DORA delivery metrics over a JSONL event log (Lab 2 METRIC-SPEC.md, rules R-01 to R-17).

Pure standard library and a pure function of its input: compute(body) either returns the metric object or
raises LogError, which the HTTP layer maps to 422.
"""

from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction
from itertools import combinations

SPEC_VERSION = "1.0.0"
_MICRO = 1_000_000


class LogError(ValueError):
    """The request body or the event log is malformed (METRIC-SPEC.md sections 1 and 6)."""


# --- parsing and validation -----------------------------------------------------------------------------------


def _instant(value, where: str) -> datetime:
    if not isinstance(value, str) or "T" not in value.upper():
        raise LogError(f"{where}: not an RFC 3339 instant")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise LogError(f"{where}: not an RFC 3339 instant") from None
    if parsed.tzinfo is None:
        raise LogError(f"{where}: RFC 3339 instant needs an offset")
    return parsed.astimezone(timezone.utc)


def _str(event: dict, key: str, where: str, nullable: bool = False):
    value = event.get(key)
    if value is None and nullable and key in event:
        return None
    if not isinstance(value, str) or not value:
        raise LogError(f"{where}: {key} must be a non-empty string{' or null' if nullable else ''}")
    return value


def _str_list(event: dict, key: str, where: str) -> list[str]:
    value = event.get(key)
    if not isinstance(value, list) or not all(isinstance(v, str) and v for v in value):
        raise LogError(f"{where}: {key} must be an array of strings")
    return value


def _parse_window(body) -> tuple[datetime, datetime]:
    if not isinstance(body, dict):
        raise LogError("body must be a JSON object")
    window = body.get("window")
    if not isinstance(window, dict):
        raise LogError("window is missing or not an object")
    start = _instant(window.get("from"), "window.from")
    end = _instant(window.get("to"), "window.to")
    if end <= start:
        raise LogError("window.to must be after window.from")
    return start, end


def _parse_events(raw) -> tuple[dict, dict, dict]:
    """Returns (commits by sha, deployments in log order, incidents by id), deduplicated per R-05."""
    if not isinstance(raw, list):
        raise LogError("events is missing or not an array")
    seen: set[str] = set()
    commits: dict[str, dict] = {}
    deployments: list[dict] = []
    incidents: dict[str, dict] = {}
    for index, event in enumerate(raw):
        where = f"events[{index}]"
        if not isinstance(event, dict):
            raise LogError(f"{where}: not an object")
        event_id = event.get("event_id")
        if not isinstance(event_id, str) or not 1 <= len(event_id) <= 64:
            raise LogError(f"{where}: event_id must be a string of 1..64 characters")
        if event_id in seen:
            continue  # R-05: the first occurrence wins, later ones are ignored
        seen.add(event_id)
        kind = event.get("type")
        at = _instant(event.get("at"), f"{where}.at")
        if kind == "commit":
            sha = _str(event, "sha", where)
            if sha in commits:
                raise LogError(f"{where}: duplicate sha {sha}")
            _str(event, "branch", where)
            change_id = _str(event, "change_id", where, nullable=True)
            reverts = _str(event, "reverts", where, nullable=True)
            if (change_id is None) == (reverts is None):
                raise LogError(f"{where}: a commit carries change_id exactly when reverts is null")
            commits[sha] = {"at": at, "sha": sha, "branch": event["branch"],
                            "change_id": change_id, "reverts": reverts}
        elif kind == "deployment":
            outcome = event.get("outcome")
            if outcome not in ("success", "failure"):
                raise LogError(f"{where}: outcome must be success or failure")
            if not isinstance(event.get("unplanned"), bool):
                raise LogError(f"{where}: unplanned must be a boolean")
            deployments.append({
                "at": at,
                "deployment_id": _str(event, "deployment_id", where),
                "environment": _str(event, "environment", where),
                "outcome": outcome,
                "commits": _str_list(event, "commits", where),
                "unplanned": event["unplanned"],
                "caused_by": _str(event, "caused_by", where, nullable=True),
            })
        elif kind == "incident":
            incident_id = _str(event, "incident_id", where)
            phase = event.get("phase")
            if phase not in ("opened", "resolved"):
                raise LogError(f"{where}: phase must be opened or resolved")
            record = incidents.setdefault(incident_id, {"incident_id": incident_id, "opened": None,
                                                        "resolved": None, "deployments": set()})
            if record[phase] is not None:
                raise LogError(f"{where}: incident {incident_id} already has a {phase} event")
            record[phase] = at
            record["deployments"].update(_str_list(event, "deployments", where))
        else:
            raise LogError(f"{where}: type must be commit, deployment or incident")
    _check_references(commits, deployments, incidents)
    return commits, deployments, incidents


def _check_references(commits: dict, deployments: list, incidents: dict) -> None:
    deployment_ids = {d["deployment_id"] for d in deployments}
    for commit in commits.values():
        if commit["reverts"] is not None and commit["reverts"] not in commits:
            raise LogError(f"commit {commit['sha']} reverts unknown sha {commit['reverts']}")
    for dep in deployments:
        for sha in dep["commits"]:
            if sha not in commits:
                raise LogError(f"deployment {dep['deployment_id']} names unknown sha {sha}")
        if dep["caused_by"] is not None and dep["caused_by"] not in incidents:
            raise LogError(f"deployment {dep['deployment_id']} caused_by unknown incident {dep['caused_by']}")
    for incident in incidents.values():
        if incident["opened"] is None:
            raise LogError(f"incident {incident['incident_id']} resolved but never opened")
        for dep_id in incident["deployments"]:
            if dep_id not in deployment_ids:
                raise LogError(f"incident {incident['incident_id']} names unknown deployment {dep_id}")


# --- arithmetic (R-03, R-04) ----------------------------------------------------------------------------------


def _micros(later: datetime, earlier: datetime) -> int:
    delta = later - earlier
    return (delta.days * 86400 + delta.seconds) * _MICRO + delta.microseconds


def _half_up(value: Fraction, places: int = 0) -> Decimal:
    exact = Decimal(value.numerator) / Decimal(value.denominator)
    return exact.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)


def _median_seconds(micros: list[int]):
    if not micros:
        return None
    ordered = sorted(micros)
    mid = len(ordered) // 2
    value = Fraction(ordered[mid]) if len(ordered) % 2 else Fraction(ordered[mid - 1] + ordered[mid], 2)
    return int(_half_up(value / _MICRO))


def _ratio(numerator: int, denominator: int):
    if denominator == 0:
        return None
    return float(_half_up(Fraction(numerator, denominator), 6))


def _iso(instant: datetime) -> str:
    text = instant.astimezone(timezone.utc).isoformat()
    return text.replace("+00:00", "Z")


# --- change identity (R-06, R-07) -----------------------------------------------------------------------------


def _resolve_changes(commits: dict) -> dict[str, str]:
    """Maps every sha to its change_id, following reverts transitively (R-06)."""
    resolved: dict[str, str] = {}
    for sha in commits:
        chain = []
        cursor = sha
        while cursor not in resolved and commits[cursor]["change_id"] is None:
            if cursor in chain:
                raise LogError(f"revert cycle through sha {cursor}")
            chain.append(cursor)
            cursor = commits[cursor]["reverts"]
        change = resolved.get(cursor, commits[cursor]["change_id"])
        for link in chain + [cursor]:
            resolved[link] = change
    return resolved


# --- the metric object ----------------------------------------------------------------------------------------


def compute(body) -> dict:
    start, end = _parse_window(body)
    commits, deployments, incidents = _parse_events(body.get("events"))
    change_of = _resolve_changes(commits)

    # R-01, R-02: production deployments inside [from, to); stable order by instant, then id.
    in_window = sorted(
        (d for d in deployments if d["environment"] == "production" and start <= d["at"] < end),
        key=lambda d: (d["at"], d["deployment_id"]),
    )
    successes = [d for d in in_window if d["outcome"] == "success"]
    failures = [d for d in in_window if d["outcome"] == "failure"]

    # R-08: one pair per sha, at its first successful production deployment in the window; E1 clamps to zero.
    first_success_of_sha: dict[str, datetime] = {}
    for dep in successes:
        for sha in dep["commits"]:
            first_success_of_sha.setdefault(sha, dep["at"])
    lead_times = []
    negative_pairs = 0
    for sha, deployed_at in first_success_of_sha.items():
        micros = _micros(deployed_at, commits[sha]["at"])
        if micros < 0:
            negative_pairs += 1
            micros = 0
        lead_times.append(micros)

    # R-09 (E3): distinct shas off main on any in-window production deployment, any outcome.
    off_main = {sha for d in in_window for sha in d["commits"] if commits[sha]["branch"] != "main"}

    # R-10 (E4)
    without_commits = sum(1 for d in in_window if not d["commits"])

    # R-12, R-13 (E5, E6): recovery per failed deployment via its covering incident.
    recoveries = []
    open_failures = 0
    for dep in failures:
        covering = [i for i in incidents.values() if dep["deployment_id"] in i["deployments"]]
        covering.sort(key=lambda i: (i["opened"], i["incident_id"].encode()))
        if not covering or covering[0]["resolved"] is None:
            open_failures += 1
            continue
        recoveries.append(max(0, _micros(covering[0]["resolved"], dep["at"])))

    intervals = [(i["opened"], i["resolved"] if i["resolved"] is not None else end) for i in incidents.values()]
    overlapping = sum(1 for a, b in combinations(intervals, 2) if a[0] < b[1] and b[0] < a[1])

    # R-15
    rework = sum(1 for d in in_window if d["unplanned"] and d["caused_by"] is not None)

    # R-16, R-17: ground truth per change, from the change's earliest commit anywhere in the log.
    first_commit_of_change: dict[str, datetime] = {}
    for sha, commit in commits.items():
        change = change_of[sha]
        if change not in first_commit_of_change or commit["at"] < first_commit_of_change[change]:
            first_commit_of_change[change] = commit["at"]
    first_success_of_change: dict[str, datetime] = {}
    for dep in successes:
        for sha in dep["commits"]:
            first_success_of_change.setdefault(change_of[sha], dep["at"])
    true_lead_times = [
        max(0, _micros(deployed_at, first_commit_of_change[change]))
        for change, deployed_at in first_success_of_change.items()
    ]

    days = Fraction(_micros(end, start), _MICRO * 86400)
    return {
        "spec_version": SPEC_VERSION,
        "window": {"from": _iso(start), "to": _iso(end)},
        "deployment_frequency_per_day": float(_half_up(len(in_window) / days, 6)),
        "change_lead_time_seconds_p50": _median_seconds(lead_times),
        "failed_deployment_recovery_time_seconds_p50": _median_seconds(recoveries),
        "change_fail_rate": _ratio(len(failures), len(in_window)),
        "deployment_rework_rate": _ratio(rework, len(in_window)),
        "counts": {
            "deployments": len(in_window),
            "successful_deployments": len(successes),
            "failed_deployments": len(failures),
            "recovered_failures": len(recoveries),
            "open_failures": open_failures,
            "rework_deployments": rework,
            "lead_time_pairs": len(lead_times),
            "changes": len(set(change_of.values())),
        },
        "anomalies": {
            "negative_lead_time_pairs": negative_pairs,
            "deployments_without_commits": without_commits,
            "commits_never_on_main": len(off_main),
            "revert_chains_collapsed": sum(1 for c in commits.values() if c["reverts"] is not None),
            "overlapping_incident_pairs": overlapping,
        },
        "ground_truth": {
            "changes_delivered": len(first_success_of_change),
            "true_change_lead_time_seconds_p50": _median_seconds(true_lead_times),
        },
    }
