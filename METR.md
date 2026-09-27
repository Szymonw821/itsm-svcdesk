---
actual_minutes: 6.6
---
<!-- ai-generated: 80% - Claude Code drafted the write-up from the recorded timestamps, reviewed by the author -->

# METR n=1 self-replication - outcome

| | |
|---|---|
| feature | `POST /dora/metrics/weekly` (the five metrics per 7-day bucket), `feature_path: metrics/weekly.py` |
| predicted | 45 minutes (`PREDICTION.md`, receipt issue 190 in the submissions repository) |
| clock start | 2026-09-27T09:10:06Z, the `received_at` of the prediction receipt |
| clock stop | 2026-09-27T09:16:42Z, `./itsmlab.sh verify 2` passing Core on the committed feature (eff0bbb) |
| actual | 6.6 minutes |
| ratio actual/predicted | **0.15** |

The feature took 0.15 of the predicted time, a large speed-up against my own estimate. The main reason is
that the work was done by Claude Code and was mostly composition: `metrics/dora.py` already computed the full
metric object for any window, so the feature reduced to splitting the window into 7-day buckets, calling the
existing function once per bucket, one route and one test. My 45 minutes was a human estimate that assumed I
would write and debug the bucketing, the edge of the last partial week and the test by hand, and it included
a margin for a failing checker run that never happened.

Two things make this single number weaker than it looks. First, the clock ran from the receipt, so it includes
the few minutes between the bot's comment and the moment the assistant started, but it excludes the time I
spent reading and reviewing the change afterwards and writing this file; the "verification tax" of AI-written
code is exactly the part a stop-at-green clock leaves out. Second, n=1 on a feature that reused a module
built an hour earlier says little about AI speed-ups in general: METR's own study found experienced developers
predicting a speed-up and measuring a slow-down on mature codebases they knew well, and a small greenfield
feature on top of fresh code is the opposite situation. What this replication does show is how badly an
estimate made in "human minutes" transfers when the work is delegated to an assistant, in either direction.
