# Tasks: svcdesk — service desk ticketing API

<!-- ai-generated: 70% - Claude Code drafted from plan.md, reviewed and adjusted by the author -->

**Input**: `specs/001-svcdesk/plan.md`, `specs/001-svcdesk/spec.md`

**Note**: no file under `src/` is created until the `specs` receipt exists (course rule, L1-CORE-5).

## Phase 1: Setup (after the specs receipt)

- [ ] T001 `cp Dockerfile.example Dockerfile`; create `requirements.txt` at repo root with pinned `fastapi` and
      `uvicorn` versions
- [ ] T002 Create `src/svcdesk/__init__.py` and `src/svcdesk/main.py` with a bare FastAPI app and `GET /health`
      (FR-001)

## Phase 2: Foundational (blocks every story)

- [ ] T003 `src/svcdesk/models.py`: pydantic models for `Reporter`, `TicketCreate`, `Ticket`, `SlaStatus`, and the
      `{"error": {...}}` response shape (FR-002, FR-010)
- [ ] T004 `src/svcdesk/main.py`: exception handler overriding FastAPI's default validation error body to
      `{"error": {"code": "validation", "message": ...}}` (FR-002)
- [ ] T005 `src/svcdesk/clock.py`: resolve "now" per request from `X-Test-Clock` (when `SVCDESK_TEST_CLOCK` is
      `1`/`true`) or real UTC; reject a malformed instant (FR-009)
- [ ] T006 `src/svcdesk/storage.py`: in-memory ticket repository (dict keyed by uuid4), create/get/list/update
      (FR-010)

**Checkpoint**: app boots, `/health` responds, storage and clock primitives exist.

## Phase 3: User Story 1 — Log and prioritize a ticket (Priority: P1) 🎯 MVP

**Goal**: `POST /tickets`, `GET /tickets`, `GET /tickets/{id}` with correct validation, priority, and SLA due
instants at creation time.

**Independent Test**: create tickets covering all 9 impact/urgency combinations plus a VIP case; check computed
`priority` and `sla.ack_due_at`/`sla.resolve_due_at` against `docs/API.md` §3-4.

- [ ] T007 [P] `src/svcdesk/priority.py`: 3x3 matrix + the C3 (VIP) resolution recorded in `DECISIONS.md`
      (FR-003)
- [ ] T008 [P] `src/svcdesk/sla.py`: `SLA_TARGETS` table (P1..P4 -> ack/resolve durations) and the business-hours
      algorithm (Europe/Warsaw, Mon-Fri 08:00-16:00, tie-at-closing rule) plus the C1 resolution for P1 (FR-006)
- [ ] T009 [US1] `POST /tickets` handler in `main.py`: validate, compute priority (T007), compute
      `sla.ack_due_at`/`sla.resolve_due_at` at `created_at` (T008), store (T006), return 201
- [ ] T010 [US1] `GET /tickets` (state/priority filters, no pagination) and `GET /tickets/{id}` (404 on unknown
      id) handlers (FR-008)
- [ ] T011 [US1] Manually verify all 9 priority-matrix combinations plus VIP escalation and VIP-at-P1 against
      `docs/CHECKS.md` 2.07-2.15, 2.46-2.48 before running the checker

**Checkpoint**: User Story 1 fully functional — a ticket can be created, listed, and fetched with correct
priority and SLA due instants.

## Phase 4: User Story 2 — Work a ticket through its lifecycle (Priority: P2)

**Goal**: the five action endpoints and the reopen window, matching the C2 resolution.

**Independent Test**: drive one ticket through ack -> start -> resolve -> close; confirm each out-of-order call
returns 409; confirm reopen behavior at 6 days and 7 days + 1 second.

- [ ] T012 [US2] `src/svcdesk/state_machine.py`: transition table (`new->acknowledged->in_progress->resolved
      ->closed`), reopen from `resolved` always, reopen from `closed` per the C2 resolution, 7-day window checks
      (FR-004, FR-005)
- [ ] T013 [US2] `POST /tickets/{id}/{ack,start,resolve,close,reopen}` handlers in `main.py`: apply
      `state_machine.py`, stamp the relevant timestamp from `clock.py`, return 200 or 409/404 (FR-004)
- [ ] T014 [US2] Manually verify `docs/CHECKS.md` 2.24-2.35, 2.49 (full lifecycle, invalid transitions, reopen
      window, C2 case) before running the checker

**Checkpoint**: User Stories 1 and 2 both work independently.

## Phase 5: User Story 3 — Report SLA status (Priority: P3)

**Goal**: `GET /tickets/{id}/sla` with correct breach and pause semantics.

**Independent Test**: reproduce SLA vectors T1-T8 by hand; confirm breach/pause combinations from
`docs/CHECKS.md` 2.36-2.45.

- [ ] T015 [US3] `src/svcdesk/sla.py`: `ack_breached`, `resolve_breached`, `paused` computation at a given "now"
      (FR-007)
- [ ] T016 [US3] `GET /tickets/{id}/sla` handler in `main.py` (404 on unknown id) (FR-007)
- [ ] T017 [US3] Manually verify all 8 SLA vectors (T1-T8) and `docs/CHECKS.md` 2.36-2.45 before running the
      checker

**Checkpoint**: all three user stories independently functional.

## Phase 6: Polish and packaging

- [ ] T018 [P] Unknown-path handler returning 404 with a JSON `error` body (FR-011)
- [ ] T019 Add `ai-generated:` headers to every file under `src/` created above
- [ ] T020 Finalize `docker-compose.yml` / `Dockerfile` (confirm `build:`, port 8080, `SVCDESK_TEST_CLOCK`, no
      bind mounts) and run `./itsmlab.sh verify 1` until every Core spec passes
- [ ] T021 Fill in `DECISIONS.md` (C1=wallclock, C2=immutable, C3=vip, five labels per section) and confirm
      `report.json`'s `observations` match

## Dependencies & Execution Order

- Phase 1 and 2 block every user story.
- User Story 1 (T007-T011) has no dependency on Stories 2 or 3.
- User Story 2 (T012-T014) depends on Story 1's storage/model foundation (Phase 2), not on Story 1's handlers.
- User Story 3 (T015-T017) depends on Story 1 (priority/creation) and Story 2 (lifecycle timestamps) being
  correct, since breach/pause math reads `created_at`, `acknowledged_at`, `resolved_at`.
- Polish (Phase 6) runs last, once all three stories pass their manual vector checks.

## Notes

- [P] tasks touch different files and can be done in any order relative to each other.
- No `src/` file is committed before the specs receipt exists (course rule).
- Each manual verification task (T011, T014, T017) exists because the course checker charges real time per run
  (`docker compose build` + `up`); catching a mismatch by hand against the published vectors first is cheaper
  than discovering it through a full `./itsmlab.sh verify 1` cycle.
