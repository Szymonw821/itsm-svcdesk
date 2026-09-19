# ai-generated: 85% - Claude Code drafted the whole package from docs/REQUIREMENTS.md and docs/API.md, reviewed by the author
"""svcdesk HTTP API - see docs/API.md for the full contract this module implements."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import storage
from .clock import ClockError, resolve_now
from .models import TicketCreate
from .priority import compute_priority
from .sla import compute_breach_and_pause, compute_sla_due
from .state_machine import InvalidTransition, apply_action

app = FastAPI()

_ERROR_CODES = {400: "validation", 404: "not_found", 409: "invalid_transition", 422: "validation"}


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    message = exc.detail if isinstance(exc.detail, str) else "request failed"
    code = _ERROR_CODES.get(exc.status_code, "error")
    return JSONResponse(status_code=exc.status_code, content={"error": {"code": code, "message": message}})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    message = "; ".join(f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in errors) or "invalid request"
    return JSONResponse(status_code=422, content={"error": {"code": "validation", "message": message}})


@app.exception_handler(ClockError)
async def clock_error_handler(request: Request, exc: ClockError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"error": {"code": "validation", "message": str(exc)}})


def _now(request: Request) -> datetime:
    return resolve_now(request.headers.get("x-test-clock"))


def _iso(instant: Optional[datetime]) -> Optional[str]:
    if instant is None:
        return None
    return instant.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _to_out(record: dict) -> dict:
    return {
        "id": record["id"],
        "title": record["title"],
        "description": record["description"],
        "reporter": record["reporter"],
        "impact": record["impact"],
        "urgency": record["urgency"],
        "priority": record["priority"],
        "state": record["state"],
        "created_at": _iso(record["created_at"]),
        "acknowledged_at": _iso(record["acknowledged_at"]),
        "resolved_at": _iso(record["resolved_at"]),
        "closed_at": _iso(record["closed_at"]),
        "related_to": record["related_to"],
        "sla": {
            "ack_due_at": _iso(record["ack_due_at"]),
            "resolve_due_at": _iso(record["resolve_due_at"]),
        },
    }


def _get_or_404(ticket_id: str) -> dict:
    record = storage.get(ticket_id)
    if record is None:
        raise HTTPException(status_code=404, detail="ticket not found")
    return record


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "svcdesk"}


@app.post("/tickets", status_code=201)
def create_ticket(body: TicketCreate, request: Request) -> dict:
    now = _now(request)
    priority = compute_priority(body.impact, body.urgency, body.reporter.vip)
    ack_due_at, resolve_due_at = compute_sla_due(priority, now)
    record = storage.create(
        {
            "title": body.title,
            "description": body.description,
            "reporter": body.reporter.model_dump(),
            "impact": body.impact,
            "urgency": body.urgency,
            "priority": priority,
            "state": "new",
            "created_at": now,
            "acknowledged_at": None,
            "resolved_at": None,
            "closed_at": None,
            "related_to": body.related_to,
            "ack_due_at": ack_due_at,
            "resolve_due_at": resolve_due_at,
        }
    )
    return _to_out(record)


@app.get("/tickets")
def list_tickets(state: Optional[str] = None, priority: Optional[str] = None) -> list[dict]:
    return [_to_out(t) for t in storage.list_all(state, priority)]


@app.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: str) -> dict:
    return _to_out(_get_or_404(ticket_id))


@app.get("/tickets/{ticket_id}/sla")
def get_sla(ticket_id: str, request: Request) -> dict:
    record = _get_or_404(ticket_id)
    now = _now(request)
    status = compute_breach_and_pause(record, now)
    return {
        "priority": record["priority"],
        "ack_due_at": _iso(record["ack_due_at"]),
        "resolve_due_at": _iso(record["resolve_due_at"]),
        "ack_breached": status["ack_breached"],
        "resolve_breached": status["resolve_breached"],
        "paused": status["paused"],
    }


def _perform_action(ticket_id: str, action: str, request: Request) -> dict:
    record = _get_or_404(ticket_id)
    now = _now(request)
    try:
        apply_action(record, action, now)
    except InvalidTransition:
        raise HTTPException(status_code=409, detail="invalid transition") from None
    return _to_out(record)


@app.post("/tickets/{ticket_id}/ack")
def ack_ticket(ticket_id: str, request: Request) -> dict:
    return _perform_action(ticket_id, "ack", request)


@app.post("/tickets/{ticket_id}/start")
def start_ticket(ticket_id: str, request: Request) -> dict:
    return _perform_action(ticket_id, "start", request)


@app.post("/tickets/{ticket_id}/resolve")
def resolve_ticket(ticket_id: str, request: Request) -> dict:
    return _perform_action(ticket_id, "resolve", request)


@app.post("/tickets/{ticket_id}/close")
def close_ticket(ticket_id: str, request: Request) -> dict:
    return _perform_action(ticket_id, "close", request)


@app.post("/tickets/{ticket_id}/reopen")
def reopen_ticket(ticket_id: str, request: Request) -> dict:
    return _perform_action(ticket_id, "reopen", request)
