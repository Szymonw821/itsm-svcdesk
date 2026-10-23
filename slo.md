---
lab3_slo:
  service: svcdesk
  route: /kb/search
  window: 30d
  slis:
    availability:
      objective: 0.99
      good: 'sum(rate(http_server_request_duration_seconds_count{job="svcdesk", http_route="/kb/search", http_response_status_code!~"5.."}[5m]))'
      valid: 'sum(rate(http_server_request_duration_seconds_count{job="svcdesk", http_route="/kb/search"}[5m]))'
      error_budget: {fraction: 0.01, minutes: 432}
    latency:
      objective: 0.99
      threshold_seconds: 0.15
      good: 'sum(rate(http_server_request_duration_seconds_bucket{job="svcdesk", http_route="/kb/search", le="0.15"}[5m]))'
      valid: 'sum(rate(http_server_request_duration_seconds_count{job="svcdesk", http_route="/kb/search"}[5m]))'
      error_budget: {fraction: 0.01, minutes: 432}
  alerts:
    - {alert: KbSearchErrorsBurnFast, sli: availability, burn_rate: 14.4, long_window: 1h, short_window: 5m}
    - {alert: KbSearchErrorsBurnSlow, sli: availability, burn_rate: 6, long_window: 6h, short_window: 30m}
---
<!-- ai-generated: 75% - Claude Code drafted the prose and the arithmetic from the two itsmlab load 3 runs, the author reviewed and chose the objectives -->

# SLO for `GET /kb/search`

Every number below comes from two runs of `./itsmlab.sh load 3` against my own `kb-index` profile (login
`szymonw821`, 23 October 2026), each 60 s open-loop at 40 requests per second, latency-corrected:

| run | p50 | p95 | p99 (q) | p99.9 | p99.99 | 502s / responses |
|---|---|---|---|---|---|---|
| 1 | 21.8 ms | 37.5 ms | 89.2 ms | 104.7 ms | 106.7 ms | 7 / 2,399 (0.29 %) |
| 2 | 22.0 ms | 37.7 ms | 95.8 ms | 114.6 ms | 121.1 ms | 9 / 2,399 (0.38 %) |

The shape is two modes: about 97 % of searches answer between 10 and 50 ms, and a small slow mode of about 2 % sits
between roughly 70 and 120 ms. The p99 falls inside that slow mode, which is why it moves by 7 % between two runs
of the same profile while the p95 moves by half a per cent. `kb-index` measured directly has the same p99 (90.2
and 96.6 ms), so `svcdesk` adds nothing measurable: the latency and the failures are the dependency's.

## Availability

Good: a `/kb/search` request answered with anything but a 5xx. Valid: every `/kb/search` request, the 400s for a
bad `q` included (they are answered correctly and fast, and they are the client's mistake, not ours). Objective
**99 %** over 30 days: an error budget of 1 %, or 432 minutes of total outage.

Why 99 % and not 99.9 %: `kb-index` fails 0.29 to 0.38 % of ordinary searches on its own, and `svcdesk` has no
cache and no retry to hide that (the contract forbids both). At 99.9 % the budget would be 0.1 %, and the
dependency alone would spend three to four times the whole budget every month - the SLO would be red on a normal
day, the slow-burn alert would never stop, and nobody would trust either. At 99 % the dependency's normal failures
use about a third of the budget (a burn rate of about 0.3 to 0.4), which leaves two thirds for what we can
actually change: deploys, svcdesk's own bugs, and kb-index's bad days. 99.5 % would leave only a quarter of the
budget once the second run's 0.38 % is counted; a canary gate in Lab 6 that reads this objective must not roll back
an honest release because kb-index had an ordinary hour.

## Latency

Good: a `/kb/search` request that completed within **0.15 s**, counted directly from the `le="0.15"` bucket (0.15
is a boundary of the ladder, so nothing is interpolated). Valid: every `/kb/search` request. Objective **99 %** over
30 days: an error budget of 1 %, 432 minutes.

Why 0.15 s: it sits just above the slow mode, not inside it. Every search of both runs - p99.99 at 107 and 121 ms -
finished under it, so kb-index's normal slow answers are good requests, as they should be: they are how the
dependency behaves and users get their answer in well under a fifth of a second. A threshold of 0.1 s would cut
straight through the slow mode, where a 7 % run-to-run shift of the p99 already moves the share of bad requests by
a factor of two; the SLI would measure noise. What 0.15 s does catch is a real degradation: kb-index slowing down as
a whole (its admin `latency_factor` of 2 moves the slow mode to 140-240 ms and most of it out of the good bucket),
or svcdesk queueing requests behind its own event loop. The 0.15 s threshold is also far below Lab 6's 1 s cap.

Why 99 %: measured, it is met with a wide margin (no search over 0.15 s in 4,800), so the objective is not a hope;
and 99 % rather than 99.9 % because the slow mode's tail grew by 14 ms between two runs, and I do not know yet how
far it reaches over a month: a tighter objective would be a guess about the tail I have not measured.

## Alerts

| alert | SLI | burn rate | long / short window | budget spent when it fires | severity: page or chat |
|---|---|---|---|---|---|
| KbSearchErrorsBurnFast | availability | 14.4 | 1h / 5m (for 2m) | 2 % of the 30-day budget (14.4 x 1h / 720h) | P1, pages |
| KbSearchErrorsBurnSlow | availability | 6 | 6h / 30m (for 5m) | 5 % of the 30-day budget (6 x 6h / 720h) | P2, chat |

A burn rate of 14.4 means more than 14.4 % of searches fail - about forty times kb-index's normal failure rate.
That is not noise; it is kb-index down or svcdesk broken, and at that rate the whole month's budget is gone in two
days (720h / 14.4 = 50h). It pages: waking a person costs a night's sleep, but by morning (eight hours) the users
would have lost 16 % of the month's budget and seen one search in seven fail all night, and kb-index failures do
not fix themselves by waiting. The 5-minute short window means the page stops within minutes once the errors stop,
so a person is not woken for an incident that has already ended.

A burn rate of 6 (more than 6 % of searches failing for six hours) spends the budget in five days. It goes to chat:
it is serious enough to look at today, not serious enough to wake anyone - waiting until morning costs at most
another 8 x 6 / 720 = 7 % of the budget, and a person looking at it rested will fix it better. Both alerts are on
availability because that is where kb-index can hurt us without warning; the latency SLI has no alert of its own
yet, since nothing in either run came near its threshold, and it is on the dashboard.

## Buckets

The ladder (27 finite boundaries, in seconds):

    0.005, 0.01, 0.015, 0.02, 0.025, 0.03, 0.04, 0.05, 0.06,
    0.07, 0.075, 0.08, 0.085, 0.09, 0.095, 0.1, 0.105, 0.11, 0.115,
    0.13, 0.15, 0.2, 0.3, 0.5, 1.0, 2.5, 5.0

My q was 89.2 ms in the first run and 95.8 ms in the second. With this ladder the first lands in (0.085, 0.09],
5.6 % of q wide, and the second in (0.095, 0.1], 5.2 % of q wide; the histogram's own p99 over the second run was
95.0 ms against oha's 95.8 ms.

The band: 5 ms steps from 70 to 115 ms. That is roughly -25 % / +25 % around the middle of my two measurements
(92.5 ms), much wider than the ±10 % the handout asks for, because the p99 sits inside the slow mode and the slow
mode is what moves: two runs of my own already differed by 7 %, and the grader's machine and draws will differ
again. Inside the band every bucket is 5 ms, which is at most 7.1 % of any q in it (5 / 70), far below the 20 % rule;
even just outside it the ladder still resolves: (0.06, 0.07] is at most 16.7 % of a q of 60 ms, and (0.115, 0.13]
at most 13 % of a q of 115 ms.

The rest of the boundaries: nine below 70 ms, 5 ms apart up to 30 ms where the median and p95 live, so that the
dashboard's p50 and p95 are honest too; then 0.13 and 0.15 to close the slow mode's tail, 0.15 being the latency
SLI's threshold; and 0.2, 0.3, 0.5, 1.0, 2.5 and 5.0 for a degraded kb-index, up to the 5 s upstream timeout,
coarse because there I only need to know that something is badly wrong, not by how many milliseconds. Three of
the 30 allowed boundaries are left unused.
