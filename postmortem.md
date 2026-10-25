---
lab4_postmortem:
  ticket: "50ceffde-fa49-40b3-b4ca-957734d74bf7"
  detecting_alert: ShopCheckoutErrors
  onset: 2026-10-12T06:36:23Z
  detection: 2026-10-12T06:39:19Z
  acknowledgement: 2026-10-12T06:40:09Z
  recovery: 2026-10-12T06:44:19Z
  mttd_seconds: 176
  mtta_seconds: 50
  mttr_seconds: 476
  identified_flags: [paymentFailure, loadGeneratorFloodHomepage, recommendationCacheFailure]
---
<!-- ai-generated: 70% - Claude Code (Opus 5.5) ran the queries on the lab4-rec-4 recording and drafted the text; the author checked the numbers against itsmlab incident 4 and edited it -->

# Postmortem: one order in seven failed at checkout while a traffic flood and a recommendation cache fault ran unseen

All times are UTC. Every number below was measured on the snapshot of recording `lab4-rec-4`
(`incident/tsdb-snapshot.tar.gz`), served by Prometheus 3.15.0; the query that measured it is given with it.

## Date

The incident happened on Monday 12 October 2026, from 06:36:23Z to 06:44:19Z. This postmortem was written on
25 October 2026 from the recorded snapshot and ticket.

## Authors

Szymon Wiernik (GitHub szymonw821), working the recorded incident as the on-call engineer after the fact. The live
actions in the recording (the ticket, the acknowledgement, switching the flags off) were taken by the recording's
on-call; this document describes what they could see at each moment.

## Status

Complete for the incident: service was restored at 06:44:19Z and the incident ticket can close. The problem record
at the end stays open, and the action items are not started yet.

## Summary

For about eight minutes the shop's checkout failed part of the orders: 8 of the 53 orders placed between 06:36Z and
06:44Z were rejected, because payment's Charge call failed for about a quarter of its calls. At the same time the
storefront received about fifteen times its normal traffic and the recommendation service switched to a broken
cache path; neither of those was noticed during the incident. Three feature flags were switched on at the onset,
and service came back when all three were switched off.

## Impact

Buyers trying to pay were hit; buyers who were only browsing were not slowed down.

- **Failed orders.** 8 of 53 PlaceOrder calls failed between the 06:37:10Z and the 06:44:10Z pushes of the span
  metrics, 15 % of all orders in the incident, with a peak of 31 % over five minutes at 06:42Z. Counted from the
  counter `traces_span_metrics_calls_total{service_name="checkout", span_kind="SPAN_KIND_SERVER"}` by `status_code`
  (errors 0 → 8, successes 81 → 126), and the peak from
  `sum(rate(...{service_name="checkout", span_kind="SPAN_KIND_SERVER", status_code="STATUS_CODE_ERROR"}[5m])) /
  sum(rate(...{service_name="checkout", span_kind="SPAN_KIND_SERVER"}[5m]))` = 0.312 at 06:42:00Z. Each failed order
  was a buyer who got an error after filling the cart; whether they retried is not in the metrics.
- **Traffic flood.** The frontend served 63 requests/s at the peak (06:42Z) against 3.6/s before the onset, about
  20,000 extra requests in eight minutes: `sum(rate(traces_span_metrics_calls_total{service_name="frontend",
  span_kind="SPAN_KIND_SERVER"}[5m]))`. These were cheap homepage requests and the shop had headroom: the frontend's
  p95 latency went down, not up (4.4 ms at 06:42Z against 34 ms at 06:36Z), so buyers did not feel it. On a busier
  day the same flood would cost real capacity.
- **Recommendation cache path.** From the onset to about 06:43Z, recommendation answered about half of its requests
  from an internal list instead of asking the product catalog: the ratio of its ListProducts client calls to its
  ListRecommendations server calls fell from exactly 1.0 to 0.5 (`sum(increase(...{service_name="recommendation",
  span_kind="SPAN_KIND_CLIENT", span_name="oteldemo.ProductCatalogService/ListProducts"}[2m])) /
  sum(increase(...{service_name="recommendation", span_kind="SPAN_KIND_SERVER"}[2m]))`). Its memory grew from 57 MB
  to 63 MB (`container_memory_usage_total_bytes{container_name="recommendation"}`) and its mean latency doubled
  briefly to 8 ms at 06:44Z. No request failed; the risk is the memory growth, which does not stop on its own.
- **Who was not affected.** No other service had failed server spans in the window (product-catalog, shipping,
  email, cart, currency, quote, ad), apart from a few flagd EventStream resets that also occur before and after the
  fault, and checkout's p95 stayed at 48 ms throughout.

## Root Causes

Three independent faults were switched on at once, one of each class the injector draws from:

1. `paymentFailure` (errors): payment's `charge` deliberately failed a share of the calls, about 25 % judging by the
   measured 31 % peak on a small number of orders. Checkout calls Charge synchronously during PlaceOrder and has no
   retry or fallback for it, so every failed charge became a failed order, and the frontend and frontend-proxy
   passed the error to the buyer. The error rates of payment's Charge, checkout's PlaceOrder and the frontend's
   `/api/checkout` are identical at every minute, which is what a single failing dependency looks like.
2. `loadGeneratorFloodHomepage` (load): the load generator flooded the homepage. Only frontend and frontend-proxy
   saw it; nothing failed.
3. `recommendationCacheFailure` (resources): recommendation took its "cache" code path, which skips the product
   catalog call on about half of the requests and appends to an in-memory list that keeps growing. It produced the
   memory and latency growth above and no errors.

What made the first fault an outage rather than a warning is the design underneath: one payment dependency on the
critical path of every order, with no retry, no queue and no circuit breaker. What made the other two invisible is
that no alert watches traffic volume or the shape of a service's calls, only checkout's errors.

## Trigger

At 06:36:23Z, 4 minutes 20 seconds after the fault injector was armed (at about 06:32Z), the three flags switched on
together: that is the first sample of `seeded_fault_active`. Nothing was deployed and no service restarted
(`container_uptime_seconds` grows without a reset for every container through the snapshot). The first failed
orders reached Prometheus with the 06:38:10Z push of the span metrics.

## Resolution

The workaround was to switch the three flags off through the injector, one at a time. From the metrics, the order
was: `paymentFailure` first, between the 06:40:10Z and 06:42:10Z pushes, most likely around 06:41 (the failed-order
counter stopped at 8 at 06:41:10Z and never moved again); then `loadGeneratorFloodHomepage`, about 06:42:20Z (the frontend counter grew by about 3,000 requests a
minute until 06:42:20Z and by about 230 after); and `recommendationCacheFailure` last, just before 06:43:18Z, when
`seeded_fault_active` fell to 0 and recommendation went back to one catalog call per request. Payment came first
because it was the only fault that hurt buyers. ShopCheckoutErrors resolved at 06:44:19Z, when its five-minute
window no longer held any failed order; that is the recovery. Nothing was rolled back or restarted, and the
recommendation container still holds the memory its list grew to.

## Detection

The P1 alert ShopCheckoutErrors (checkout's server error ratio, five-minute window) went pending at 06:38:19Z, the
first evaluation after the 06:38:10Z push carried failed orders, and fired at 06:39:19Z after its one-minute `for`:
MTTD 176 s. 116 s of that is the time until the first failed orders happened at about 0.1 orders/s and reached
Prometheus with the next one-minute push of the span metrics; 60 s is the alert's `for`. The pager received the page by 06:39:34Z
(`itsm_pager_notifications_total{receiver="pager", status="firing"}` appears then), the ticket was opened at
06:39:44Z and acknowledged at 06:40:09Z: MTTA 50 s. MTTR was 476 s (onset to the alert's end at 06:44:19Z).

The P2 alert ShopServiceErrors fired for checkout and payment at 06:40:19Z, but the inhibit rule muted it while the
P1 fired, so chat only got it at 06:44:34Z, after the page had resolved. The flood and the recommendation fault were
detected by no alert at all; without an investigation of traffic and call ratios they would only have been noticed
in a capacity review or when recommendation ran out of memory. A buyer would have noticed the payment fault
immediately; nobody outside would have noticed the other two.

## Action Items

| Action Item | Type | Owner | Bug |
|---|---|---|---|
| Add a P3 chat alert on frontend-proxy traffic above five times its normal rate (ShopTrafficSurge in prometheus/demo-alerts.yml) | prevent | on-call team (Szymon Wiernik) | ITSM-41 |
| Add a P3 alert on recommendation memory growth and on its ListProducts-to-request ratio leaving 1.0 for 5 minutes | prevent | recommendation owners | ITSM-42 |
| Make checkout retry a failed Charge once with an idempotency key, and return a clear "try again" to the buyer instead of a generic error | mitigate | checkout owners | ITSM-43 |
| Require a change record and an expiry for every production feature flag switch, and post flag changes to the incident channel automatically | process | platform team | ITSM-44 |
| Restart recommendation in a quiet hour to release the memory the cache list grew to, then verify its memory is back at about 56 MB | mitigate | recommendation owners | ITSM-45 |
| Review the inhibit rule: let P2 alerts of a different service than the paging one reach chat during a page, so that a second fault is not hidden | process | on-call team (Szymon Wiernik) | ITSM-46 |

## Lessons Learned

### What went well

The page was on a symptom buyers feel, checkout errors, and it fired within three minutes of the onset, of which one
minute is the alert's `for`. The ticket was opened 25 s after the alert fired and acknowledged 25 s later,
and the payment fault was switched off first, which was the right priority.

### What went wrong

Two of the three faults were never alerted on and appear in no notification; the investigation found them only by
looking at traffic and call ratios after the fact. The inhibit rule that keeps the page quiet also hid the P2 view of
the incident until it was over. Both AI investigators stopped at the payment errors: the recorded one queried a 2024
date and concluded checkout had no errors (ledger H5), and the second called it "a single fault, not two" (ledger S5
of `ai-rca-eval-2.json`), which the traffic data contradicts.

### Where we got lucky

The flood hit cheap homepage requests on a shop with plenty of headroom, so it slowed nothing. The recommendation
fault was switched off after about seven minutes, before its growing list could exhaust the container's 524 MB
limit. And the payment variant failed about a quarter of the charges, not all of them.

## Timeline

All times UTC, 12 October 2026.

- 06:22:13 - The fault injector starts its run (`seeded_injector_info` first sample); the baseline begins.
- 06:32:03 - The injector is armed (`seeded_fault_armed` = 1). No alert fires on the healthy shop before the onset.
- 06:35:20 - Last quiet push: about 3.6 frontend requests/s, no failed order, no alert pending or firing.
- 06:36:23 - Onset: `paymentFailure`, `loadGeneratorFloodHomepage` and `recommendationCacheFailure` switch on
  together (first sample of `seeded_fault_active`).
- 06:37:20 - The frontend's request counter jumps by 1,700 in a minute instead of about 270: the flood has started.
- 06:38:10 - The first two failed orders arrive with the span-metrics push; recommendation now calls ListProducts for
  only about half of its requests.
- 06:38:19 - ShopCheckoutErrors (P1) and ShopServiceErrors (P2, checkout and payment) go pending.
- 06:39:19 - Detection: ShopCheckoutErrors fires (MTTD 176 s).
- 06:39:34 - The page reaches the pager.
- 06:39:44 - P1 ticket 50ceffde-fa49-40b3-b4ca-957734d74bf7 opened in svcdesk ("Shop checkout failing, paged by
  ShopCheckoutErrors").
- 06:40:09 - Acknowledgement of the ticket (MTTA 50 s).
- 06:40:19 - ShopServiceErrors fires for checkout and payment; inhibited by the P1, so chat is not notified.
- 06:40:10 to 06:42:10 - `paymentFailure` switched off, most likely around 06:41; the failed-order counter stops at 8.
- 06:42:20 - `loadGeneratorFloodHomepage` switched off; frontend traffic falls back toward its normal rate.
- 06:43:18 - `recommendationCacheFailure` switched off; `seeded_fault_active` = 0, the last flag is off.
- 06:44:19 - Recovery: ShopCheckoutErrors resolves (MTTR 476 s); the pager gets the resolved notification at 06:44:34.
- 06:44:34 - Chat receives ShopServiceErrors for the first time, now that the P1 no longer inhibits it; it resolves
  at 06:45:34 (its last firing sample is 06:45:09).

The AI hypotheses that shaped the investigation, each with its ledger entry, query and result (evaluated after the
incident on the snapshot; no AI ran during it):

- H1 of `ai-rca-eval.json`, payment's charge span failing: `sum(rate(traces_span_metrics_calls_total{service_name="payment",
  span_name="charge", status_code="STATUS_CODE_ERROR"}[5m])) > 0.01` returned 0.032 at 06:42:00Z and nothing at
  06:31:23Z (correct). It pointed at payment as the origin of the failed orders.
- S5 of `ai-rca-eval-2.json`, "a single fault, not two": `sum(rate(...{service_name="payment", span_kind="SPAN_KIND_SERVER",
  status_code="STATUS_CODE_ERROR"}[5m])) > 0.01 unless on() sum(rate(...{service_name="frontend-proxy",
  span_kind="SPAN_KIND_SERVER"}[5m])) > 10` returned nothing at 06:42:00Z because frontend-proxy served 31.7
  requests/s (hallucinated). Disproving it is what led to the second and third faults.

## Supporting information

- `itsmlab incident 4` on `incident/tsdb-snapshot.tar.gz` and `incident/ticket.json`: run c1daa7d0f4acf990, onset
  06:36:23Z, detection 06:39:19Z by ShopCheckoutErrors, acknowledgement 06:40:09Z, recovery 06:44:19Z, MTTD 176 s,
  MTTA 50 s, MTTR 476 s.
- The AI scorecards: `ai-rca-eval.json` (the recorded investigator, qwen3:4b-instruct through the course agent loop,
  transcript `ai-rca/transcript.md`) and `ai-rca-eval-2.json` (Claude Code with claude-sonnet-5-5, transcript
  `ai-rca/second/transcript.md`), compared in `ai-rca/COMPARISON.md`.
- The regulators' clocks for this incident are in `comms-log.md`.
- The three flags were identified from the metrics alone, against INCIDENT-SPEC.md section 2.2: payment errors only
  in Charge (`paymentFailure`; no product-catalog GetProduct errors, so not `productCatalogFailure`; no ad errors, so
  not `adFailure`); frontend traffic times fifteen with no latency change elsewhere (`loadGeneratorFloodHomepage`;
  shipping, product-catalog and ad latency flat, so not the other latency flags); recommendation's catalog-call
  ratio at 0.5 and its memory growth (`recommendationCacheFailure`; email's memory flat at about 61 MB and its
  uptime never reset, so not `emailMemoryLeak`).
- The alerting that would watch the next incident: `prometheus/demo-alerts.yml`, `alertmanager/alertmanager.yml`,
  `alertmanager/routing-tests.yml`. Evaluated on this recording, its ShopCheckoutErrorRate would have fired as the
  recording's page did, and its ShopTrafficSurge would have shown the flood in chat.

## Problem record

- Incident record: ticket 50ceffde-fa49-40b3-b4ca-957734d74bf7 (P1, acknowledged 06:40:09Z); service restored at 06:44:19Z, so the incident can close.
- Root cause: checkout depends synchronously on payment's Charge with no retry or fallback, so a payment fault fails orders directly; and feature flags can be switched in production with no record and no alert on their effects (the flood and the recommendation cache path went unseen).
- Known error: when payment's Charge fails a share of calls, the same share of orders fails at checkout with a generic error; recommendation's cache path grows its memory without bound while it is enabled.
- Workaround: switch the failing flags off (paymentFailure first), then restart recommendation to free the memory its cache list holds; no code change is needed to restore service.
