# svcdesk Constitution
<!-- ai-generated: 70% - Claude Code drafted from docs/REQUIREMENTS.md and docs/API.md, reviewed and adjusted by the author -->

## Core Principles

### I. API.md is the contract
`docs/REQUIREMENTS.md` states intent; `docs/API.md` is the enforced technical contract (exact paths, field
names, status codes, the test clock). Where the two differ in precision, API.md wins. The published checks in
`docs/CHECKS.md` are the acceptance test for every principle below.

### II. No network at runtime
All dependencies (Python packages, timezone data) are installed at Docker build time. The service starts and
serves every request with zero outbound or inbound network access beyond the port it listens on. A dependency
fetched at process start is a defect, not a convenience.

### III. Contradictions are resolved, not hidden
Three pairs of requirements in REQUIREMENTS.md cannot both hold (SLA clock for P1, closed-ticket reopening, VIP
priority override). Each is resolved deliberately, the resolution is declared in `DECISIONS.md`, and the running
service's behavior must match that declaration exactly (checked by L1-CORE-4). Ambiguity here is a defect.

### IV. Simplicity for a 150-minute lab
This is a single HTTP service built in one lab session. No persistence layer beyond in-memory storage (ticket
survival across restarts is not graded in Lab 1), no speculative abstractions, no framework beyond FastAPI +
Uvicorn. Prefer a straightforward module per concern (priority, state machine, SLA clock, storage) over generic
layering.

### V. Disclosure
Every source and specification file under `src/` and `specs/`, plus `DECISIONS.md`, carries an `ai-generated:`
header in its first ten lines, stating how much of the file an AI drafted and how.

## Technology constraints

Python 3.13, FastAPI + Uvicorn, pydantic for request/response validation. Storage: an in-memory dictionary keyed
by ticket id (uuid4); no database. Business-hours SLA math uses the standard library `zoneinfo` against
`Europe/Warsaw` (available without extra packages on `python:3.13-slim`, a Debian base). JSON is the only
representation on the wire.

## Development workflow

Specs (this repository's `specs/`) are written and pushed before any file under `src/` (other than
`src/README.md`) is committed — the course's `specs` receipt gates this. Implementation follows
`docs/API.md` section by section; conformance is verified locally and repeatedly with `./itsmlab.sh verify 1`
before tagging an attempt.

## Governance

This constitution applies to Lab 1 of the svcdesk course project. It may be amended in later labs as the
service grows; amendments are recorded in this file's version line.

**Version**: 1.0.0 | **Ratified**: 2026-09-19 | **Last Amended**: 2026-09-19
