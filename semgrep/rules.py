# ai-generated: 100% - Claude Code wrote these test cases for semgrep/rules.yml (CI-SPEC.md P-31)
import time
from datetime import datetime, timezone

from fastapi.responses import JSONResponse

from svcdesk.clock import resolve_now


class LogError(ValueError):
    pass


def resolve_now_like(header_value):
    if not header_value:
        # ruleid: svcdesk-wall-clock-read
        return datetime.now(timezone.utc)
    return datetime.fromisoformat(header_value)


def created_at_wrong():
    # ruleid: svcdesk-wall-clock-read
    return datetime.utcnow()


def elapsed_wrong():
    # ruleid: svcdesk-wall-clock-read
    return time.time()


def created_at_right(request):
    # ok: svcdesk-wall-clock-read
    return resolve_now(request.headers.get("x-test-clock"))


def parse_right(text):
    # ok: svcdesk-wall-clock-read
    return datetime.fromisoformat(text).astimezone(timezone.utc)


def metrics(body, compute):
    try:
        return JSONResponse(content=compute(body))
    except LogError as exc:
        # ruleid: svcdesk-exception-text-in-response
        return JSONResponse(status_code=422, content={"error": {"code": "validation", "message": str(exc)}})


async def clock_error_handler(request, exc: LogError):
    # ruleid: svcdesk-exception-text-in-response
    return JSONResponse(status_code=400, content={"error": {"code": "validation", "message": str(exc)}})


def body_not_json(request):
    try:
        return request.json()
    except ValueError:
        # ok: svcdesk-exception-text-in-response
        return JSONResponse(status_code=400, content={"error": {"code": "validation", "message": "body is not JSON"}})


def logged_not_sent(logger, compute, body):
    try:
        return compute(body)
    except LogError as exc:
        # ok: svcdesk-exception-text-in-response
        logger.warning("rejected: %s", str(exc))
        return JSONResponse(status_code=422, content={"error": {"code": "validation", "message": "rejected"}})


def query_echo(q):
    # ok: svcdesk-exception-text-in-response
    return JSONResponse(content={"query": str(q), "hits": []})
