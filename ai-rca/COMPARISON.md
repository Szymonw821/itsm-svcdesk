<!-- ai-generated: 70% - Claude Code (Opus 5.5) drafted the comparison from the two ledgers and their transcripts; the author checked every entry against the queries -->
# Two investigators on the same incident

Both investigators got the same question, in UTC with the date and nothing else: "Checkout errors paged at
06:39:19Z on 2026-10-12. Investigate 06:30Z to 06:50Z. What is the cause?", and both read the lab4-rec-4 snapshot
through the same read-only MCP server, `prom_mcp.py (mcp 2.2.0)`.

| | first (`ai-rca-eval.json`) | second (`ai-rca-eval-2.json`) |
|---|---|---|
| agent | the course agent loop `agent.py` (the recorded transcript) | Claude Code 2.1.310, headless, only the five MCP tools allowed |
| model | qwen3:4b-instruct (local, Ollama) | claude-sonnet-5-5 |
| tool calls, time | 17 calls in 8 model steps, about 19 minutes | 8 calls, 19 seconds |
| verdicts | 3 correct, 1 partially correct, 1 hallucinated | 3 correct, 1 hallucinated, 1 unfalsifiable |

The fault, as the data shows it, was three flags at once: `paymentFailure` (charges failing, orders failing),
`loadGeneratorFloodHomepage` (frontend traffic times fifteen) and `recommendationCacheFailure` (recommendation
calling the catalog for half its requests and growing its memory). Both agents found the first and missed the
other two.

## Where they agreed

- **Payment's charge is where the errors start.** First H1 and H3, second S1. Both are correct: payment's charge
  failed at 0.032/s at 06:42:00Z, checkout's PlaceOrder failed at exactly the same rate, and no other upstream of
  checkout had a failed server span. The second agent proved the "origin" part properly, by showing that the only
  non-load-generator error series at 06:39Z were payment's Charge and its callers; the first agent got there from
  one `query_range` of raw counters and then lost the thread.
- **Checkout fails because of payment.** First H3 and H4, second S1's description of the callers. Both correct. The
  first agent misquoted the span name (`PaymentService/Charge` without the `oteldemo.` prefix), so the series it
  cites as evidence does not exist, but the dependency it claims is true.
- **Neither went beyond errors.** Neither ever queried traffic volume, latency or memory. Both started from the alert
  names (the second called `alerts_at` first and read ShopCheckoutErrors and ShopServiceErrors for payment and
  checkout); the payment finding goes one step past the alerts, since no alert names payment's charge span.

## Where they parted

- **Time and mechanism.** The first agent (H2) said charge showed "increasing error counts over time, indicating a
  failure in the core transaction processing logic". The data proves it half right: the errors were real
  (partially correct), but the counter stopped at 8 at 06:41:10Z and never moved again, with no restart or deploy of
  payment, which is a switched-off flag and not a code failure. The second agent got the time right (S3, "about 4
  minutes": failures between the 06:37:10Z and 06:41:10Z pushes, correct) and the share right (S2, 31 % of payment's
  calls, correct), and said honestly that the metrics could not tell why Charge failed.
- **Flags.** The second agent looked for flag metrics and said "Feature flags don't clearly explain it" (S4). That is
  unfalsifiable on this snapshot: no metric names a flag of the injector's pool, so no query can confirm or refute
  it. It was a reasonable thing to say and it led nowhere.
- **The wrong turns.** The first agent's worst entry (H5, hallucinated) came from querying 2024-04-14T10:00:00Z, a
  date outside the snapshot, and reading the empty answer as "there might be no errors" for checkout, after it had
  already seen the errors in an earlier result. The second agent's wrong turn was a conclusion, not a query: "a
  single fault, not two" (S5, hallucinated), because frontend-proxy served 31.7 requests/s against about 2/s on the
  baseline and recommendation changed its call pattern at the same time.

## Which one the data proved right

Entry by entry the second investigator was right more often and wrong for a better reason: four of its five claims
survive their queries or are honestly uncheckable, and its one hallucination is an over-reach from too few queries.
The first was right about the component, wrong about the mechanism, and once contradicted data it had already seen.
On the question that matters for the postmortem, though, neither was right: the incident had three causes, and both
reported one. The two missed faults showed up only in series neither agent looked at (frontend request rate,
recommendation's ListProducts-to-request ratio, container memory), so a better prompt or a bigger model would not
have been enough; the agents need to be pushed to check traffic, latency and resources and not only errors, and
their answers need a ledger like this one before anyone acts on them.
