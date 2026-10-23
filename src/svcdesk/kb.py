# ai-generated: 90% - Claude Code wrote the kb-index client from lab3 MONITORING-SPEC.md M-02, reviewed by the author
"""GET /kb/search's upstream: exactly one GET {KB_INDEX_URL}/search?q=<q> per request (lab3 MONITORING-SPEC.md M-02).

No cache and no retry: every valid request waits for kb-index, so svcdesk's histogram observes kb-index's
latency. Any non-200 answer, timeout or connection error becomes UpstreamUnavailable, which the HTTP layer
answers 502 upstream_unavailable.
"""

import os

import httpx

KB_INDEX_URL = os.environ.get("KB_INDEX_URL", "http://kb-index:8080").rstrip("/")
# M-02 asks for at least 2 s; kb-index's slowest answers are well under a second.
TIMEOUT_SECONDS = 5.0

Q_MAX_LENGTH = 200

_client: httpx.AsyncClient | None = None


class UpstreamUnavailable(Exception):
    pass


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        # The open-loop load keeps up to 64 requests in flight; let each have its own upstream connection.
        _client = httpx.AsyncClient(
            timeout=TIMEOUT_SECONDS,
            limits=httpx.Limits(max_connections=200, max_keepalive_connections=100),
        )
    return _client


async def close() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def search(q: str) -> list:
    """Return kb-index's hits for q, unchanged."""
    try:
        response = await _get_client().get(f"{KB_INDEX_URL}/search", params={"q": q})
    except httpx.HTTPError as exc:
        raise UpstreamUnavailable(f"kb-index unreachable: {type(exc).__name__}") from None
    if response.status_code != 200:
        raise UpstreamUnavailable(f"kb-index answered {response.status_code}")
    try:
        return response.json()["hits"]
    except (ValueError, KeyError, TypeError):
        raise UpstreamUnavailable("kb-index answered an unreadable body") from None
