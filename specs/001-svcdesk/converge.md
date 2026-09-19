# Converge: svcdesk spec vs. implementation

<!-- ai-generated: 70% - Claude Code drafted the comparison against the running service, reviewed by the author -->

This compares `specs/001-svcdesk/spec.md` against what `src/svcdesk/` actually does, requirement by requirement,
after `./itsmlab.sh verify 1` reported every Core spec passing.

**R-03 / R-04 / R-05 (ticket shape and priority matrix)**: the spec's User Story 1 required a fixed 3x3
impact/urgency matrix with no client override. `src/svcdesk/models.py` validates impact/urgency as
`Literal[1, 2, 3]` integers (rejecting `"high"` or `5` with 422), and `src/svcdesk/priority.py` implements the
matrix exactly as tabulated in `docs/API.md` §3. A `priority` field sent in the request body is accepted by
pydantic's `extra="ignore"` config and silently dropped, matching R-05's "neither the reporter nor the agent can
request a priority." Verified against all nine impact/urgency combinations (checks 2.07-2.15) and the
priority-in-body-is-ignored case (check 2.48).

**R-06 (VIP escalation, decision C3)**: the spec's edge cases called for the C3 resolution to be encoded, not
left ambiguous. `priority.py`'s `VIP_ESCALATED_FROM = {"P3", "P4"}` raises a VIP ticket to `P2` exactly when the
matrix alone would have produced `P3` or `P4`, leaving `P1`/`P2` untouched — matching the `vip` value declared in
`DECISIONS.md` and observed by the checker at check 2.46.

**R-07 / R-08 / R-09 / R-10 / R-11 (lifecycle and reopening, decision C2)**: User Story 2 required the five
explicit action endpoints and a 409 on any shortcut. `src/svcdesk/state_machine.py`'s `_TRANSITIONS` table
allows only `new->acknowledged->in_progress->resolved->closed`; `ALLOW_REOPEN_FROM_CLOSED = False` encodes the
`immutable` resolution of C2, so a closed ticket can never be reopened regardless of age, while a resolved
ticket can be reopened within exactly 7 days of `resolved_at`. Manually verified at the 6-day and
7-day-plus-one-second boundaries before relying on the checker (which confirmed at checks 2.32-2.35).

**R-12 / R-13 / R-14 (SLA targets and the two clocks, decision C1)**: the plan's Phase 3/5 called for
`src/svcdesk/sla.py` to reproduce the published target table and the business-hours algorithm exactly.
`WALLCLOCK_PRIORITIES = {"P1"}` encodes the `wallclock` resolution of C1: P1's ack/resolve targets are
`created_at + target` with no business-hours pausing, while every other priority (and P1 under the rejected
`business` alternative) goes through `add_business_time`. All eight published test vectors (T1-T8 in
`docs/API.md` §4) were reproduced by hand against this implementation before the first checker run and matched
to the second.

**R-15 / R-16 (breach and pause)**: `compute_breach_and_pause` in `sla.py` follows the exact wording of
`docs/API.md` §5 — a target is breached only when the relevant event or "now" is strictly after the due instant,
and `paused` only applies to an open ticket whose resolution clock is business-hours. This is what makes a
reopened ticket "not resolved again" automatically: `_reset_to_in_progress` clears `resolved_at`, so the breach
check falls back to comparing `now` against the unchanged `resolve_due_at`, with no special-casing needed.

**Gaps knowingly left for later labs**: R-23 (ticket survival across a container restart) is implemented with
an in-memory dictionary (`storage.py`), not a database, per the plan's simplicity principle and because Tier A
of Lab 1 does not grade it. This is the one place the spec's assumptions section and the implementation
deliberately diverge from what a production desk would need, and it is expected to change in Lab 2.
