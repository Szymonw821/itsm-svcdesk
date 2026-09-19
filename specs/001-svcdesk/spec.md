# Feature Specification: svcdesk — service desk ticketing API

<!-- ai-generated: 70% - Claude Code drafted from docs/REQUIREMENTS.md and docs/API.md, reviewed and adjusted by the author -->

**Feature Branch**: `001-svcdesk`

**Created**: 2026-09-19

**Status**: Draft

**Input**: `docs/REQUIREMENTS.md` (R-01..R-25) and `docs/API.md` (the enforced HTTP contract), course Lab 1.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Log and prioritize a ticket (Priority: P1)

A desk agent or an automated integration reports an issue (title, description, reporter, impact, urgency). The
service assigns a unique id, computes a priority from impact and urgency (raising it further if the reporter is
VIP), and returns SLA due instants so the agent knows the acknowledgement and resolution deadlines immediately.

**Why this priority**: without ticket creation and priority computation, nothing else in the service has meaning;
this is the entry point for every other story.

**Independent Test**: `POST /tickets` with a valid body returns 201 with `state: "new"`, a computed `priority`,
and an `sla` block; can be tested in isolation with no other endpoint.

**Acceptance Scenarios**:

1. **Given** a ticket with impact=1, urgency=1, **When** it is created, **Then** its priority is `P1`.
2. **Given** a ticket with impact=3, urgency=3 and `reporter.vip=true`, **When** it is created, **Then** its
   priority reflects the VIP-escalation resolution recorded in `DECISIONS.md` (C3).
3. **Given** a request missing `title`, **When** it is submitted, **Then** the service answers 400 or 422 with a
   JSON body carrying a top-level `error` object.

---

### User Story 2 - Work a ticket through its lifecycle (Priority: P2)

An agent acknowledges a new ticket, starts work, resolves it, and closes it once the reporter confirms the fix,
one explicit action at a time. A reporter can reopen a resolved ticket (and, depending on the C2 decision, a
recently closed one) if the fix did not hold.

**Why this priority**: the state machine is what makes the desk's reports trustworthy — it must be impossible to
skip a step or to silently resurrect stale work.

**Independent Test**: drive one ticket through `ack` → `start` → `resolve` → `close` via their dedicated
endpoints and confirm each returns 200 with the updated state and timestamp; confirm an out-of-order call (e.g.
`resolve` before `start`) returns 409.

**Acceptance Scenarios**:

1. **Given** a new ticket, **When** `POST /tickets/{id}/resolve` is called before `start`, **Then** the service
   answers 409 with a JSON `error` body.
2. **Given** a ticket resolved 6 days ago, **When** it is reopened, **Then** it returns to `in_progress`.
3. **Given** a ticket resolved 7 days and 1 second ago, **When** it is reopened, **Then** the service answers 409.
4. **Given** a closed ticket, **When** it is reopened, **Then** the outcome (200 or 409) matches the C2 decision
   recorded in `DECISIONS.md`.

---

### User Story 3 - Report SLA status for the Monday review (Priority: P3)

Monitoring or a weekly report calls `GET /tickets/{id}/sla` for each open ticket to learn its due instants,
whether either target has been breached, and whether its clock is currently paused outside business hours.

**Why this priority**: this is the reporting value the whole service exists to deliver, but it depends on
stories 1 and 2 already working correctly (priority and lifecycle timestamps feed directly into the SLA
calculation).

**Independent Test**: create a ticket with a known `X-Test-Clock`, advance the clock past its ack-due instant
without acknowledging it, and confirm `GET /tickets/{id}/sla` reports `ack_breached: true`.

**Acceptance Scenarios**:

1. **Given** a P3 ticket created on a Friday afternoon, **When** its SLA is queried, **Then** the due instants
   match the business-hours calculation (skipping the weekend).
2. **Given** an open ticket whose resolution target runs on the business-hours clock, **When** queried outside
   business hours, **Then** `paused` is `true`.
3. **Given** a P1 ticket, **When** its SLA is queried at any hour, **Then** its clock behavior (paused or not)
   matches the C1 decision recorded in `DECISIONS.md`.

---

### Edge Cases

- A ticket action (`ack`, `start`, `resolve`, `close`, `reopen`) targeting an id that does not exist returns 404
  with a JSON `error` body, not 409.
- `impact` or `urgency` sent as a string (e.g. `"high"`) or outside 1..3 is a validation error (400/422), not a
  silently-clamped value.
- A client-supplied `priority`, `state`, `id`, or any timestamp field in a create request is ignored, never
  rejected and never honored — the service always computes these itself.
- `X-Test-Clock` is honored per-request only, and only when `SVCDESK_TEST_CLOCK` is `1`/`true`; a malformed
  instant is a validation error; without the header the service uses real UTC time.
- A target that is consumed exactly to the business-hours closing instant is due at that closing instant, not at
  the next business day's opening (the tie rule — see `docs/API.md` §4, vector T4).
- Reaching a due instant exactly is not a breach; only strictly later is.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The service MUST expose `GET /health` returning 200 with `{"status": "ok", "service": "svcdesk"}`.
- **FR-002**: The service MUST accept ticket creation (`POST /tickets`) with title (1-200 chars, required),
  optional description (0-4000 chars), a reporter (name required 1-100 chars, optional email, optional
  `vip` flag defaulting to false), required integer impact and urgency (each 1-3), and an optional `related_to`
  id, rejecting anything outside those bounds with 400/422 and a JSON `error` body.
- **FR-003**: The service MUST compute `priority` from impact and urgency using the fixed matrix in
  `docs/REQUIREMENTS.md` R-04, adjusted by the VIP rule this project resolves as decision C3; a client-supplied
  `priority` value MUST be ignored.
- **FR-004**: The service MUST drive tickets through the states `new → acknowledged → in_progress → resolved →
  closed` via five distinct action endpoints, rejecting any other transition with 409 and a JSON `error` body,
  and answering 404 for actions on an unknown ticket id.
- **FR-005**: The service MUST allow reopening a resolved ticket within 7 days of `resolved_at`, returning it to
  `in_progress` and clearing `resolved_at`/`closed_at`; reopening a closed ticket MUST follow the C2 decision
  recorded in `DECISIONS.md` (either allowed within 7 days of `closed_at`, or always refused with 409).
  Reopening never changes `resolve_due_at`.
- **FR-006**: The service MUST compute `ack_due_at` and `resolve_due_at` for every ticket from its priority and
  `created_at`, using the target table in `docs/API.md` §4, applying the business-hours clock
  (Mon-Fri 08:00-16:00 Europe/Warsaw) to every priority except P1, whose clock follows the C1 decision recorded
  in `DECISIONS.md`.
- **FR-007**: `GET /tickets/{id}/sla` MUST report priority, both due instants, `ack_breached`, `resolve_breached`
  (each true only when the relevant instant/event is strictly after the due instant), and `paused` (true only for
  an open ticket whose resolution clock is business-hours and the current instant is outside business hours).
- **FR-008**: `GET /tickets` MUST list every ticket in one unpaginated response, filterable by exact-match
  `state` and `priority` query parameters.
- **FR-009**: The service MUST accept an `X-Test-Clock` header (RFC 3339 instant) as "now" for a single request
  when `SVCDESK_TEST_CLOCK` is `1`/`true`; otherwise it MUST use real UTC time and ignore the header.
- **FR-010**: Every id the service assigns MUST be opaque, unique, and never client-chosen; every response
  timestamp MUST be an RFC 3339 instant.
- **FR-011**: An unknown path MUST answer 404 with a JSON body carrying a top-level `error` object.

### Key Entities

- **Ticket**: id, title, description, reporter, impact, urgency, computed priority, state, four lifecycle
  timestamps (`created_at`, `acknowledged_at`, `resolved_at`, `closed_at`), optional `related_to` (another
  ticket's id), and a computed `sla` block (`ack_due_at`, `resolve_due_at`).
- **Reporter**: name, optional email, optional VIP flag — embedded in a ticket, not a standalone resource.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every one of the 49 conformance checks in `docs/CHECKS.md` (L1-CORE-2) passes against the running
  service.
- **SC-002**: The compose contract check (L1-CORE-1) passes: the service starts from `docker compose up --wait`
  and answers `GET /health` within 120 seconds, with no bind mounts and no runtime network dependency.
- **SC-003**: `DECISIONS.md`'s declared C1/C2/C3 values match exactly what the running service exhibits
  (L1-CORE-4), verified by comparing `report.json`'s `observations` block after each `./itsmlab.sh verify 1` run.
- **SC-004**: The eight SLA test vectors (T1-T8 in `docs/API.md` §4) produce exactly the published due instants
  when reproduced by hand against the implementation before relying on the checker to catch a mismatch.

## Assumptions

- Single-process, single-instance deployment for Lab 1; no concurrency or multi-replica concerns.
- In-memory storage is acceptable for Lab 1 (ticket survival across a container restart, R-23, is not graded in
  Tier A this lab and is deferred to Lab 2).
- The checker creates at most 100 tickets per run (per `docs/API.md` §1), so no pagination is required.
- `related_to` is stored but not validated against existing ticket ids in Lab 1 (per `docs/API.md` §2).
- Error response `code`/`message` field contents are advisory only; only the HTTP status and the presence of a
  top-level `error` object are graded in Lab 1 (per `docs/API.md` §7).
