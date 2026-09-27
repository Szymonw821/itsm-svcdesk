---
feature: "POST /dora/metrics/weekly - the five DORA metrics split into consecutive 7-day buckets of the window"
predicted_minutes: 45
predicted_at: "2026-09-27T09:06:27Z"
feature_path: metrics/weekly.py
---
<!-- ai-generated: 50% - Claude Code proposed the feature, the estimate is the author's -->

# Prediction

I predict that adding `POST /dora/metrics/weekly` will take 45 minutes, from this prediction's receipt to a
passing `./itsmlab.sh verify 2` on the committed tree. The feature takes the same request body as
`POST /dora/metrics` and returns the metric object for each consecutive 7-day bucket `[from + 7k days,
from + 7(k+1) days)` of the window, the last bucket cut at `to`. It lives in `metrics/weekly.py`, reuses
`metrics/dora.py` unchanged, and gets at least one test in the compose `tests` suite.
