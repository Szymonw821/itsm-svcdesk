---
svcdesk_decisions:
  C1: wallclock      # wallclock | business
  C2: immutable      # reopen | immutable
  C3: vip            # matrix | vip
---
<!-- ai-generated: 60% - Claude Code drafted the reasoning from REQUIREMENTS.md/API.md and the running service's behavior; the author reviewed and adjusted the wording -->

# Decisions

## C1 - SLA clock for P1

**Decision:** Both P1 targets (acknowledge in 15 minutes, resolve in 4 hours) run on the wall clock, around the
clock, seven days a week. They never pause outside business hours.

**Rejected alternative:** Running P1 on the same business-hours clock as every other priority, so a P1 raised
on Friday evening would not start counting again until Monday 08:00.

**Reason:** R-13 says every SLA clock pauses outside business hours; R-14 says a P1 raised Friday evening is
late at 15 minutes past, not Monday morning. Both cannot hold for P1 at once. P1 means the whole organisation is
affected and work has stopped — that is exactly the class of incident an on-call desk is expected to answer at
2 a.m., not on Monday. Pausing P1's clock over a weekend would let the most severe outages sit unacknowledged
for up to 60 hours while the dashboard still reports "on track", which defeats the purpose of having an SLA at
all for the incidents that matter most.

**Service owner:** The on-call incident manager, because they are paged against these two numbers (15 minutes to
acknowledge, 4 hours to resolve) and are the one held accountable when a P1 breach reaches the weekly report.

**Customer outcome:** Whoever reports an organisation-wide outage gets a response commitment that holds
regardless of when they raise it — the desk does not get to explain away a missed P1 by pointing at the clock.

## C2 - Closed tickets and reopening

**Decision:** A closed ticket is immutable. Reopen only works from `resolved`, within 7 days of `resolved_at`.
Once a ticket is `closed`, the only way to continue the same issue is a new ticket with `related_to` pointing at
it.

**Rejected alternative:** Allowing reopen from `closed` as well as from `resolved`, within 7 days of
`closed_at`, so a reporter could resurrect a ticket after it had already gone through the confirmation step.

**Reason:** R-09 says a closed ticket is immutable and any further work needs a new ticket; R-10 says a reporter
may reopen a resolved *or* closed ticket within 7 days. Both cannot hold for a closed ticket. "Closed" already
means the reporter confirmed the fix worked (that confirmation is what moves a ticket from `resolved` to
`closed` in the first place); reopening a case that was explicitly confirmed fixed would let a single ticket's
history and its SLA timestamps be silently rewritten weeks after the fact, and every downstream report (SLA
compliance, ticket counts per period) would need to account for a `closed` state that does not actually mean
closed.

**Service owner:** The service desk manager, because they sign off on the weekly SLA and volume reports that
read `closed` as final, and a movable `closed` state would make those reports unreliable.

**Customer outcome:** A reporter whose fix does not hold within a week of resolution can still get it reopened
without losing history; after that, they raise a linked follow-up ticket, which keeps the record of what was
fixed when, separate from what broke again later.

## C3 - VIP reporters and the priority matrix

**Decision:** After the impact/urgency matrix decides a priority, a VIP reporter's ticket is raised to `P2` if
the matrix gave it `P3` or `P4`. `P1` and `P2` tickets are unaffected by the VIP flag.

**Rejected alternative:** Letting the matrix decide alone and storing `reporter.vip` purely as metadata, so a
VIP reporter's cosmetic issue (impact 3, urgency 3) would stay `P4`, queued behind every other `P4` ticket.

**Reason:** R-05 says priority comes from the matrix and nothing else; R-06 says a VIP ticket is never lower
than `P2`. Both cannot hold whenever the matrix alone would produce `P3` or `P4` for a VIP reporter. VIP
escalation is a deliberate, named feature of the desk (R-06 exists on purpose), not an accident of the matrix,
so it has to actually change the outcome for it to mean anything.

**Service owner:** The service desk manager, because they are the one who has to explain to an executive
sponsor why their ticket sat at `P4` if the escalation were not honoured — and who benefits when it is.

**Customer outcome:** A VIP reporter's ticket is never buried in the backlog behind cosmetic issues, even when
its raw impact/urgency looks minor; the organisation gets visible handling of issues that carry outsized
political or business weight, at the cost of the matrix's raw impact/urgency signal being overridden for that
one group of reporters.
