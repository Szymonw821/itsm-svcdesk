# ai-generated: 80% - Claude Code drafted the test suite against the finished implementation, reviewed by the author
"""Own test suite for svcdesk (Stretch S3): exercises the running service over HTTP via SVCDESK_URL.

Uses only the standard library so the tests image needs no dependency beyond what svcdesk itself already
installs at build time. Prints "ITSMLAB-TESTS: passed=<n> failed=0" as the last stdout line and exits 0 only
when every test passed.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE_URL = os.environ.get("SVCDESK_URL", "http://svcdesk:8080")

TESTS = []


def test(fn):
    TESTS.append(fn)
    return fn


def _request(method, path, body=None, headers=None):
    url = BASE_URL + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    for key, value in (headers or {}).items():
        req.add_header(key, value)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            status, payload = resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        status, payload = exc.code, exc.read()
    return status, (json.loads(payload) if payload else None)


def _wait_for_health(timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            status, _ = _request("GET", "/health")
            if status == 200:
                return
        except OSError:
            pass
        time.sleep(0.5)
    raise RuntimeError(f"{BASE_URL}/health did not respond within {timeout}s")


def _create_ticket(clock, impact, urgency, vip=False, title="test ticket"):
    body = {
        "title": title,
        "reporter": {"name": "tester", "vip": vip},
        "impact": impact,
        "urgency": urgency,
    }
    status, ticket = _request("POST", "/tickets", body, {"X-Test-Clock": clock})
    assert status == 201, f"expected 201, got {status}: {ticket}"
    return ticket


@test
def health_reports_ok():
    status, body = _request("GET", "/health")
    assert status == 200
    assert body == {"status": "ok", "service": "svcdesk"}


@test
def unknown_route_is_404_with_error_body():
    status, body = _request("GET", "/nope-9f3c")
    assert status == 404
    assert "error" in body


@test
def priority_matrix_p1():
    ticket = _create_ticket("2026-10-14T10:00:00Z", 1, 1)
    assert ticket["priority"] == "P1"


@test
def priority_matrix_p4():
    ticket = _create_ticket("2026-10-14T10:00:00Z", 3, 3)
    assert ticket["priority"] == "P4"


@test
def missing_title_is_rejected():
    status, body = _request(
        "POST",
        "/tickets",
        {"reporter": {"name": "tester"}, "impact": 1, "urgency": 1},
        {"X-Test-Clock": "2026-10-14T10:00:00Z"},
    )
    assert status in (400, 422)
    assert "error" in body


@test
def get_ticket_by_id_round_trips():
    ticket = _create_ticket("2026-10-14T10:00:00Z", 2, 2, title="round trip")
    status, fetched = _request("GET", f"/tickets/{ticket['id']}")
    assert status == 200
    assert fetched["id"] == ticket["id"]
    assert fetched["title"] == "round trip"


@test
def get_unknown_ticket_is_404():
    status, body = _request("GET", "/tickets/does-not-exist-9f3c")
    assert status == 404
    assert "error" in body


@test
def full_lifecycle_reaches_closed():
    ticket_id = _create_ticket("2026-10-14T10:00:00Z", 1, 1)["id"]
    status, ticket = _request(
        "POST", f"/tickets/{ticket_id}/ack", headers={"X-Test-Clock": "2026-10-14T10:05:00Z"}
    )
    assert status == 200 and ticket["state"] == "acknowledged"
    status, ticket = _request(
        "POST", f"/tickets/{ticket_id}/start", headers={"X-Test-Clock": "2026-10-14T10:10:00Z"}
    )
    assert status == 200 and ticket["state"] == "in_progress"
    status, ticket = _request(
        "POST", f"/tickets/{ticket_id}/resolve", headers={"X-Test-Clock": "2026-10-14T11:00:00Z"}
    )
    assert status == 200 and ticket["state"] == "resolved"
    status, ticket = _request(
        "POST", f"/tickets/{ticket_id}/close", headers={"X-Test-Clock": "2026-10-14T12:00:00Z"}
    )
    assert status == 200 and ticket["state"] == "closed"


@test
def resolve_before_start_is_409():
    ticket = _create_ticket("2026-10-14T10:00:00Z", 1, 1)
    status, body = _request(
        "POST", f"/tickets/{ticket['id']}/resolve", headers={"X-Test-Clock": "2026-10-14T10:05:00Z"}
    )
    assert status == 409
    assert "error" in body


@test
def vip_escalates_low_priority_ticket():
    ticket = _create_ticket("2026-10-14T10:00:00Z", 3, 3, vip=True)
    assert ticket["priority"] == "P2"


@test
def sla_vector_t1_p1_business_hours():
    ticket = _create_ticket("2026-10-14T10:00:00Z", 1, 1)
    assert ticket["sla"]["ack_due_at"] == "2026-10-14T10:15:00Z"
    assert ticket["sla"]["resolve_due_at"] == "2026-10-14T14:00:00Z"


@test
def reopen_new_ticket_is_409():
    ticket = _create_ticket("2026-10-14T10:00:00Z", 1, 1)
    status, body = _request(
        "POST", f"/tickets/{ticket['id']}/reopen", headers={"X-Test-Clock": "2026-10-14T10:05:00Z"}
    )
    assert status == 409
    assert "error" in body


@test
def list_filters_by_state():
    ticket = _create_ticket("2026-10-14T10:00:00Z", 1, 1, title="filter me")
    status, body = _request("GET", "/tickets?state=new")
    assert status == 200
    assert any(t["id"] == ticket["id"] for t in body)


def main() -> None:
    _wait_for_health()
    passed = failed = 0
    for fn in TESTS:
        try:
            fn()
            passed += 1
        except AssertionError as exc:
            failed += 1
            print(f"FAIL {fn.__name__}: {exc}", file=sys.stderr)
        except Exception as exc:  # noqa: BLE001 - report and keep going, still counts as a failure
            failed += 1
            print(f"ERROR {fn.__name__}: {exc}", file=sys.stderr)
    print(f"ITSMLAB-TESTS: passed={passed} failed={failed}")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
