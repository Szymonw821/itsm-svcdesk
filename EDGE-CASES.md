---
lab2_edge_cases:
  E1: {rule: R-08, count: 3}
  E2: {rule: R-06, count: 2}
  E3: {rule: R-09, count: 4}
  E4: {rule: R-10, count: 4}
  E5: {rule: R-12, count: 1}
  E6: {rule: R-13, count: 11}
---
<!-- ai-generated: 90% - Claude Code drafted the text from METRIC-SPEC.md and the practice log, reviewed by the author -->

# Edge cases in the practice event log

The six counts above are what `POST /dora/metrics` returns for `fixtures/events-practice.jsonl` over the
published window (they are also in `metrics.json`).

## E1 - clock skew produces a negative lead time

- What the log contains: three successful production deployments shipped a commit that is timestamped after
  the deployment itself: DEP-0012 carries sha-0040 (committed about 14 minutes after it was deployed), DEP-0024
  carries sha-0094 (51 seconds after) and DEP-0031 carries sha-0123 (13 minutes after). A commit cannot really
  reach production before it exists, so these are clocks on two machines disagreeing.
- What a default definition would have done: `deployment.at - commit.at` averaged or taken as a median over
  every pair, which either feeds negative durations into the median (dragging it down and, with a mean,
  possibly below zero) or silently drops the three pairs, so `lead_time_pairs` shrinks without anyone noticing.
- Why the rule is defensible: clamping to zero keeps the pair in the population, because the commit really was
  delivered, and states the least wrong duration we can know. Counting the clamps in
  `negative_lead_time_pairs` tells the reader of the dashboard that the input has a skew problem worth fixing
  at the source, instead of hiding it inside a slightly-too-good median.

## E2 - a revert of a revert

- What the log contains: sha-0069 belongs to CHG-0033; sha-0070 reverts sha-0069, and sha-0071 reverts
  sha-0070 - putting the original change back. The two revert commits carry `change_id: null`, which is why
  `revert_chains_collapsed` is 2.
- What a default definition would have done: treat every commit (or every distinct non-null `change_id`
  plus one per revert) as its own unit of work, reporting three changes where the team did one piece of work
  and fought with it twice. Changes per day go up precisely when delivery went badly.
- Why the rule is defensible: a revert has no intent of its own; it is part of the history of the change it
  undoes. Resolving transitively to CHG-0033 means churn on one change shows up as a longer lead time for that
  change (its first commit instant stays the earliest one), not as extra throughput.

## E3 - a hotfix that never touched `main`

- What the log contains: four commits on hotfix branches (sha-0019 on `hotfix/2609`, sha-0077 on
  `hotfix/4347`, sha-0108 on `hotfix/6085`, sha-0127 on `hotfix/1544`) went straight to production on
  DEP-0006, DEP-0019, DEP-0028 and DEP-0033, all successful.
- What a default definition would have done: most assistant-written definitions start with "commits on
  `main`", so these four pairs vanish from the lead time. Hotfixes are the fastest path to production, so
  dropping them biases the median upward and hides exactly the urgent work.
- Why the rule is defensible: DORA measures commit to running in production, and production does not care
  which branch the code came from. Ignoring `branch` for the metric, while still counting off-main commits in
  `commits_never_on_main`, measures what users actually got and still flags the process shortcut to reviewers.

## E4 - a deployment with zero linked commits

- What the log contains: four in-window production deployments with an empty `commits` list: DEP-0026 and
  DEP-0032 succeeded, DEP-0043 and DEP-0044 failed (both of the failures opened incidents, INC-0010 and
  INC-0011). These look like configuration or infrastructure redeploys.
- What a default definition would have done: either drop the deployment entirely because it "has no change",
  losing two real production failures from the change fail rate, or try to compute a per-deployment lead time
  and divide by an empty list.
- Why the rule is defensible: a deployment with no commits still changed production and can still break it,
  as DEP-0043 and DEP-0044 did. It counts in frequency and in both instability denominators; it only has no
  lead-time pair because there is no commit to measure from. The flip side is that it is cheap to fake, which
  is what the gaming section below uses.

## E5 - a deployment that failed and never recovered

- What the log contains: DEP-0015 failed on 2026-09-07 at 06:12; its covering incident INC-0004 was opened
  at 06:35 and has no `resolved` event anywhere in the log. It is the one open failure; the other seven
  failures recovered.
- What a default definition would have done: close the open failure at the end of the window (inventing a
  recovery time of about two weeks, which is not a measurement) or drop the deployment, which removes it from
  the change fail rate and makes the team look more stable exactly where it is least stable.
- Why the rule is defensible: the recovery time median should only contain durations that were observed;
  an invented one is fiction. But the failure itself was observed, so it stays in the change fail rate and is
  reported separately as `open_failures`, where a reader sees an unresolved outage instead of a number that
  pretends it ended.

## E6 - overlapping incidents

- What the log contains: eleven incidents, several running at the same time. On 2026-09-07 DEP-0015,
  DEP-0043, DEP-0044 and DEP-0016 failed within hours of each other, and their incidents INC-0004, INC-0010,
  INC-0011 and INC-0005 overlap pairwise. INC-0004 never resolves, so its interval runs to the window's end
  and it also overlaps INC-0006 to INC-0009; on 2026-09-19 INC-0007 and INC-0008 overlap as well. Together
  that makes 11 unordered overlapping pairs, 7 of them through INC-0004.
- What a default definition would have done: merge overlapping incidents into one outage (so several failed
  deployments get one recovery) or sum the incidents' wall-clock durations, counting the same hour of outage
  two or three times and inflating the recovery time.
- Why the rule is defensible: the question the metric answers is "when a deployment fails, how long until it
  is fixed", so it is computed per failed deployment from its own covering incident. Overlap is a real signal
  (a bad day, possibly one root cause) and is reported as `overlapping_incident_pairs`, but it must not change
  the arithmetic of each individual recovery.

## Gaming demonstration

I improved `deployment_frequency_per_day` (from 2.0 to 2.619048, +31 %) by exploiting R-10: a production
deployment with no linked commits still counts fully in deployment frequency. `gaming/after.jsonl` adds 18
successful production deployments with empty `commits`, one every eight hours - the equivalent of a pipeline
that redeploys the same build on a timer. As a side effect the change fail rate and the rework rate also look
better, because both share the inflated denominator. At the same time the last five real releases in the
window (DEP-0037, DEP-0039, DEP-0040, DEP-0041, DEP-0042) were moved to 2026-09-24, after the window closes,
as if the team had spent the last week feeding the dashboard and batching real work into one big release.
Measured on the base work alone, changes delivered in the window fell from 65 to 58 (89 %), so users got less,
later, while every chart went green. No commit was re-timed, no outcome flipped and nothing deleted, as R-19
requires.

The incentive that produces this is a target or a bonus tied to "deploys per day", for example a quarterly
OKR to reach elite deployment frequency, with nobody asking what each deployment contained. The people
rewarded are the team lead and the platform team who own the number in the quarterly review, and whoever
wrote the redeploy cron job; the cost lands on users waiting for the delayed features and on the next team
that trusts the dashboard. It is Goodhart's law in its cheapest form: the metric counts events, and an event
costs nothing to produce.
