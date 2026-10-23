<!-- ai-generated: 85% - Claude Code ran the measurement through Toxiproxy and wrote the explanation, reviewed by the author -->
# The client-server latency gap (Stretch 2, M-30)

**Setup.** Toxiproxy 2.12.0 (`ghcr.io/shopify/toxiproxy:2.12.0`, compose profile `gap`) listens on 8666 in front
of `svcdesk:8080`, with one toxic: `latency`, stream `downstream`, toxicity 1.0, latency 100 ms, jitter 10 ms.
Measured on 23 October 2026 with `./itsmlab.sh load 3 --base-url http://host.docker.internal:8666` (the M-08 load:
60 s open-loop at 40 requests per second, latency-corrected, 64 connections), login `szymonw821`:

| | p50 | p95 | p99 |
|---|---|---|---|
| client (oha, through the proxy) | 125.3 ms | 142.9 ms | **194.1 ms** |
| server (`histogram_quantile(0.99)` over the run's increments of `/kb/search`) | | | **92.5 ms** |

Gap: 194.1 - 92.5 = 101.6 ms.

**Why the gap is about 100 ms.** The server's histogram starts its timer when the request reaches svcdesk's ASGI
stack and stops it when the last byte of the response has been handed to the socket. Everything that happens
outside that interval is invisible to it - and Toxiproxy's downstream latency toxic delays exactly the bytes
travelling from svcdesk back to the client, after svcdesk has finished. So every response arrives at the client
about 100 ms (± the 10 ms jitter) later than the server believes it was done, and the client's whole distribution
is shifted right by the toxic: p50 22 ms on the server becomes 125 ms at the client, and the p99 moves from the
server's 92.5 ms to 194 ms. The shift is almost a constant added to every request, so the gap at p99 is close to
the toxic's mean latency; the few milliseconds above 100 come from the jitter (the p99 of a value that adds ±10 ms
to every request lands near its top), from the extra hop through the proxy, and from the two p99s being computed
from different instruments - oha's exact latencies against the histogram's linear interpolation inside a 5 ms
bucket.

**What it means.** A server-side SLO measures what the service controls, not what users experience. A slow
network, a load balancer, a proxy or a client's own queue all add latency that the server's histogram never sees:
here a dashboard built on `http_server_request_duration_seconds` would show a healthy 92 ms p99 while every user
waits almost 200 ms. The server's histogram is the right instrument to debug svcdesk, but a user-facing latency SLO
needs a measurement from the client side as well - synthetic probes or client telemetry - or at least an explicit
statement of what the server-side number leaves out. My latency SLI's threshold of 0.15 s is a server-side
threshold: through this proxy, nearly every request would be over it as the user sees it, while the SLI would
still report almost 100 % good.
