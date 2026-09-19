# Implementation Plan: svcdesk — service desk ticketing API

<!-- ai-generated: 70% - Claude Code drafted from spec.md and docs/API.md, reviewed and adjusted by the author -->

**Branch**: `001-svcdesk` | **Date**: 2026-09-19 | **Spec**: `specs/001-svcdesk/spec.md`

**Input**: Feature specification from `specs/001-svcdesk/spec.md`

## Summary

Build `svcdesk`, a single-process JSON HTTP API (FastAPI on Uvicorn) that creates tickets, computes their
priority and SLA due instants, drives them through a fixed lifecycle, and reports SLA breach/pause status. Three
requirement conflicts from `docs/REQUIREMENTS.md` (SLA clock for P1, closed-ticket reopening, VIP priority
override) are each resolved one way and recorded in `DECISIONS.md`; the implementation encodes exactly that
resolution so the running service matches the declaration (checked by L1-CORE-4).

## Technical Context

**Language/Version**: Python 3.13

**Primary Dependencies**: FastAPI, Uvicorn, pydantic (ships with FastAPI); stdlib `zoneinfo` for `Europe/Warsaw`
business-hours math (no extra tzdata package needed on `python:3.13-slim`, a Debian base).

**Storage**: in-memory dict keyed by ticket id (uuid4); no database. Ticket survival across a container restart
(R-23) is out of scope for Lab 1 (not graded in Tier A).

**Testing**: manual verification against the published SLA test vectors (`docs/API.md` §4, T1-T8) plus
`./itsmlab.sh verify 1` (the course checker, `docs/CHECKS.md`) as the acceptance suite. No `tests/` project is
added for Lab 1 (Stretch S3 "own-tests" is out of scope per the chosen Core-only scope).

**Target Platform**: Linux container, `python:3.13-slim` base, listening on `0.0.0.0:8080`.

**Project Type**: single web service.

**Performance Goals**: none specific; the checker creates at most 100 tickets per run.

**Constraints**: no network access at runtime (deps installed at build time only); no host-path bind mounts; must
answer `GET /health` within 120 s of `docker compose up --wait`.

**Scale/Scope**: single service, ~10 endpoints, one resource type (Ticket).

## Constitution Check

*Against `.specify/memory/constitution.md`.*

- **I. API.md is the contract** — every endpoint/status code/schema decision in this plan traces back to
  `docs/API.md` section citations in `spec.md`'s functional requirements. Pass.
- **II. No network at runtime** — `requirements.txt` pins FastAPI/Uvicorn versions installed at Docker build
  time; storage is in-memory, no external service calls. Pass.
- **III. Contradictions are resolved, not hidden** — C1/C2/C3 resolutions are fixed values consumed by
  `priority.py`, `state_machine.py`, and `sla.py`, not runtime-configurable, and mirrored in `DECISIONS.md`. Pass.
- **IV. Simplicity for a 150-minute lab** — one module per concern, no ORM, no repository pattern beyond a plain
  dict. Pass.
- **V. Disclosure** — every file below carries an `ai-generated:` header. Pass (verified before commit).

No violations; Complexity Tracking is not needed.

## Project Structure

### Documentation (this feature)

```text
specs/001-svcdesk/
├── plan.md              # this file
├── spec.md              # feature specification
└── tasks.md             # task breakdown
```

### Source Code (repository root)

```text
requirements.txt          # repo root: fastapi, uvicorn (pinned)
src/
├── README.md              # unchanged (course placeholder)
└── svcdesk/
    ├── __init__.py
    ├── main.py             # FastAPI app, routing, exception handlers -> {"error": {...}}
    ├── models.py           # pydantic request/response schemas
    ├── priority.py         # impact x urgency matrix + C3 (VIP) rule
    ├── clock.py             # X-Test-Clock resolution, RFC 3339 parsing
    ├── sla.py               # SLA targets, business-hours algorithm, C1 rule, breach/pause
    ├── state_machine.py     # allowed transitions, reopen window, C2 rule
    └── storage.py            # in-memory ticket repository
```

**Structure Decision**: single project, no `tests/` directory for Lab 1 (Core-only scope; verification is manual
vector checks plus the course checker).

## Complexity Tracking

Not applicable — no constitution violations.
