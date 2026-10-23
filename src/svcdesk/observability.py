# ai-generated: 90% - Claude Code wrote the histogram and middleware from lab3 MONITORING-SPEC.md M-03 to M-07, reviewed by the author
"""The RED request histogram (lab3 MONITORING-SPEC.md M-03 to M-07) and GET /metrics.

One histogram, http_server_request_duration_seconds, in seconds, with exactly the three OpenTelemetry HTTP labels.
A pure ASGI middleware times every request from the moment it arrives until the last byte of its response is
sent, and observes it exactly once; /metrics itself is left out. http_route is the template of the matched
route (FastAPI puts the route in the scope while routing), or "unmatched" when no route matched, so raw paths,
ids and query strings never reach a label (M-05, M-07).
"""

import time

from prometheus_client import CollectorRegistry, Histogram, disable_created_metrics, generate_latest

# No *_created series: one less series per label set to count against the cardinality budget (M-07).
disable_created_metrics()

# The ladder (M-06, M-11, M-13): at most 30 finite boundaries. See slo.md, section "Buckets", for why these.
BUCKETS = (
    0.005, 0.01, 0.015, 0.02, 0.025, 0.03, 0.04, 0.05, 0.06,
    0.07, 0.075, 0.08, 0.085, 0.09, 0.095, 0.1, 0.105, 0.11, 0.115,
    0.13, 0.15, 0.2, 0.3, 0.5, 1.0, 2.5, 5.0,
)

UNMATCHED = "unmatched"
METRICS_PATH = "/metrics"
# Prometheus 3 scrapes only a text/plain answer (M-03); pinned here rather than taken from the library's
# CONTENT_TYPE_LATEST, whose version changes between releases.
METRICS_CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"

REGISTRY = CollectorRegistry(auto_describe=True)
REQUEST_DURATION = Histogram(
    "http_server_request_duration_seconds",
    "Duration of HTTP server requests, from arrival to the last byte of the response.",
    ["http_request_method", "http_route", "http_response_status_code"],
    buckets=BUCKETS,
    registry=REGISTRY,
)


def render_metrics() -> bytes:
    return generate_latest(REGISTRY)


class RequestDurationMiddleware:
    """Observe every HTTP request once, under the template of the route that answered it."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["path"] == METRICS_PATH:
            await self.app(scope, receive, send)
            return

        start = time.perf_counter()
        status = {"code": 500}

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status["code"] = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            route = scope.get("route")
            template = getattr(route, "path", None) or UNMATCHED
            REQUEST_DURATION.labels(
                http_request_method=scope["method"],
                http_route=template,
                http_response_status_code=str(status["code"]),
            ).observe(time.perf_counter() - start)
