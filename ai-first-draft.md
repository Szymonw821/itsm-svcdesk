---
lab3_first_draft:
  source: ai
  tool: "Claude Opus 5.5 (claude-opus-5-5) in Claude Code, the same session that then did the lab, 23 October 2026"
  ladder: [0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.15, 0.2, 0.3, 0.5, 0.75, 1.0, 2.5, 5.0]
  verdict: refuted
  evidence: {p99_seconds: 0.0958, bucket: [0.075, 0.1], relative_width: 0.261}
lab3_flawed_ladder:
  verdict: refuted
  evidence: {p99_seconds: 0.0958, bucket: [0.04, 0.5], relative_width: 4.802}
---
<!-- ai-generated: 90% - the answer is the assistant's by construction; Claude Code also wrote the verdicts from the two itsmlab load 3 runs, reviewed by the author -->

# The assistant's first draft, and two verdicts

The exchange below happened before anything was measured: the prompt was put to Claude Code at the start of the
lab, its answer was saved as it stands, and only then did `./itsmlab.sh load 3` run. The answer is quoted line by
line so that it stays inside its section.

## Prompt

I am adding GET /kb/search to a FastAPI service (svcdesk). Each request calls an upstream knowledge-base index (kb-index) over HTTP and waits for its answer. I want a Prometheus histogram http_server_request_duration_seconds (in seconds, labels http_request_method, http_route, http_response_status_code) for it. Give me the histogram bucket boundaries you recommend, and one Prometheus alerting rule for this endpoint's availability. I have not measured the latency yet.

## Answer

> For a request that waits on one HTTP call to a search index, I would start with a ladder that is fine in the tens of milliseconds, where a healthy index answers, and still has a few buckets out to the client timeout:
>
> buckets (seconds): [0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.15, 0.2, 0.3, 0.5, 0.75, 1.0, 2.5, 5.0]
>
> That is 14 finite boundaries, so 15 series per label set including +Inf. It keeps the Prometheus client's default resolution below 100 ms, adds 0.15, 0.2 and 0.3 between 100 and 500 ms where a slow search usually lands, and stops at 5 s, above a 2 s upstream timeout. In prometheus_client:
>
>     REQUEST_DURATION = Histogram(
>         "http_server_request_duration_seconds",
>         "Duration of HTTP server requests.",
>         ["http_request_method", "http_route", "http_response_status_code"],
>         buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.15, 0.2, 0.3, 0.5, 0.75, 1.0, 2.5, 5.0),
>     )
>
> Once you have real traffic, look at where your p99 falls and add boundaries around it.
>
> Alert rule, availability of /kb/search against a 99.9 % objective, the SRE Workbook's fast-burn page (burn rate 14.4: 2 % of a 30-day budget in one hour), with a 5-minute short window so that it stops soon after the errors stop:
>
>     groups:
>       - name: svcdesk-kb-search
>         rules:
>           - alert: KbSearchHighErrorBudgetBurn
>             expr: |
>               (
>                 sum(rate(http_server_request_duration_seconds_count{http_route="/kb/search", http_response_status_code=~"5.."}[1h]))
>                   /
>                 sum(rate(http_server_request_duration_seconds_count{http_route="/kb/search"}[1h]))
>               ) > (14.4 * 0.001)
>               and
>               (
>                 sum(rate(http_server_request_duration_seconds_count{http_route="/kb/search", http_response_status_code=~"5.."}[5m]))
>                   /
>                 sum(rate(http_server_request_duration_seconds_count{http_route="/kb/search"}[5m]))
>               ) > (14.4 * 0.001)
>             for: 2m
>             labels:
>               severity: page
>             annotations:
>               summary: "/kb/search is burning its error budget 14.4x too fast"
>
> Pair it with a slower ticket alert (burn rate 6 over 6h and 30m) so that a slow leak is noticed too.

## Verdict on the draft ladder

Two runs of `./itsmlab.sh load 3` against my profile (login `szymonw821`, 23 October 2026) measured q = 89.2 ms and
q = 95.8 ms; the evidence uses the second, 0.0958 s, the run with my final ladder in the service. The draft ladder
has 0.075 and 0.1 around it, so the p99 sits in the bucket (0.075, 0.1], which is 0.025 s wide: 0.025 / 0.0958 =
26.1 % of the p99, above the 20 % that M-11 allows. `histogram_quantile` assumes the requests in that bucket are
spread evenly over it, so from this ladder it could report any p99 between 75 and 100 ms - the whole slow mode of
`kb-index` (roughly 70 to 120 ms in oha's histogram) looks like one flat bucket. The first run tells the same
story: 89.2 ms is in the same bucket, 28.0 % wide. And the bucket next to it does not help if the grader's q comes
out above 100 ms: (0.1, 0.15] is at least a third of any q inside it. **Verdict: refuted.** The draft added 0.15,
0.2 and 0.3 between 100 and 500 ms, guessing that a slow search lands there; my p99 is just under 100 ms, where
the draft kept the library's coarse 25 ms step. Its own advice - "look at where your p99 falls and add boundaries
around it" - is the right one, and is what the final ladder does.

## The draft alert rule

The draft rule is the SRE Workbook's fast-burn page: burn rate 14.4 over 1h and 5m, `for: 2m`, with a 99.9 %
objective. I kept its shape - multiwindow, burn rate 14.4 on the long 1h and short 5m windows, `for: 2m` - for
`KbSearchErrorsBurnFast`, and its suggestion of a second, slower 6x alert over 6h and 30m became
`KbSearchErrorsBurnSlow`. I changed three things. The objective: at 99.9 % the budget is 0.1 %, and `kb-index`
alone fails 0.29 to 0.38 % of my searches, so the SLO would be broken on an ordinary day and the slow alert would
fire all the time; slo.md explains the 99 % I chose, and the threshold became `14.4 * (1 - 0.99)`. The labels:
`severity: page` became `severity: P1` (P2 for the slow alert) with `service: svcdesk` and `slo: availability`,
which Lab 4 routes on. And the selectors: the draft selected no `job`; I added `job="svcdesk"` so that the rule
never mixes in another scrape job's series.

## Verdict on the instructor's flawed ladder

The flawed ladder spends twelve of its fourteen boundaries below 40 ms, where my p50 (22 ms) and p95 (38 ms) live,
and then jumps from 0.04 to 0.5. My p99 of 0.0958 s falls in that gap, the bucket (0.04, 0.5], which is 0.46 s
wide: 0.46 / 0.0958 = 480.2 % of the p99. From that bucket `histogram_quantile` could report anything from 40 ms
to half a second, and a p99 that doubled tomorrow would not move the number it reports by any reliable amount.
**Verdict: refuted.** It describes the median beautifully and the tail not at all, which is exactly what an SLO on
the slow mode cannot afford.
