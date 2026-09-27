# ai-generated: 90% - Claude Code wrote the weekly split on top of metrics/dora.py, reviewed by the author
"""POST /dora/metrics/weekly: the metric object of metrics/dora.py for each 7-day bucket of the window.

Bucket k is [from + 7k days, from + 7(k+1) days), the last one cut at `to`. Every bucket is scored over the
whole event log, exactly as POST /dora/metrics would score that bucket as its own window, so commits and
incidents outside a bucket still count through the deployments that reference them (R-02).
"""

from datetime import timedelta

from .dora import SPEC_VERSION, _iso, _parse_window, compute

BUCKET = timedelta(days=7)


def compute_weekly(body) -> dict:
    start, end = _parse_window(body)
    weeks = []
    bucket_start = start
    while bucket_start < end:
        bucket_end = min(bucket_start + BUCKET, end)
        weeks.append(compute({"window": {"from": _iso(bucket_start), "to": _iso(bucket_end)},
                              "events": body.get("events")}))
        bucket_start = bucket_end
    return {"spec_version": SPEC_VERSION, "window": {"from": _iso(start), "to": _iso(end)}, "weeks": weeks}
