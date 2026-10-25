# Investigation transcript (Claude Code, headless, course MCP server prom_mcp.py)

claude-code 2.1.310, model: claude-sonnet-5-5, MCP servers: prom (connected)

## Question

Checkout errors paged at 06:39:19Z on 2026-10-12. Investigate 06:30Z to 06:50Z. What is the cause?

### Tool `mcp__prom__alerts_at`

```
{"time": "2026-10-12T06:39:30Z"}
```

```
{"result":"{\"resultType\": \"vector\", \"result\": [{\"labels\": {\"__name__\": \"ALERTS\", \"alertname\": \"ShopCheckoutErrors\", \"alertstate\": \"firing\", \"service\": \"checkout\", \"severity\": \"P1\", \"system\": \"shop\"}, \"value\": \"1\"}, {\"labels\": {\"__name__\": \"ALERTS\", \"alertname\": \"ShopServiceErrors\", \"alertstate\": \"pending\", \"service\": \"shop\", \"service_name\": \"checkout\", \"severity\": \"P2\", \"system\": \"shop\"}, \"value\": \"1\"}, {\"labels\": {\"__name__\": \"ALERTS\", \"alertname\": \"ShopServiceErrors\", \"alertstate\": \"pending\", \"service\": \"shop\", \"service_name\": \"payment\", \"severity\": \"P2\", \"system\": \"shop\"}, \"value\": \"1\"}]}"}
```

### Tool `mcp__prom__query`

```
{"expr": "sum by (service_name, span_name) (rate(traces_span_metrics_calls_total{status_code=\"STATUS_CODE_ERROR\"}[2m]))", "time": "2026-10-12T06:39:00Z"}
```

```
{"result":"{\"resultType\": \"vector\", \"result\": [{\"labels\": {\"service_name\": \"ad\", \"span_name\": \"flagd.evaluation.v2.Service/EventStream\"}, \"value\": \"0\"}, {\"labels\": {\"service_name\": \"payment\", \"span_name\": \"flagd.evaluation.v2.Service/EventStream\"}, \"value\": \"0\"}, {\"labels\": {\"service_name\": \"payment\", \"span_name\": \"charge\"}, \"value\": \"0.030283611111111112\"}, {\"labels\": {\"service_name\": \"payment\", \"span_name\": \"oteldemo.PaymentService/Charge\"}, \"value\": \"0.030283611111111112\"}, {\"labels\": {\"service_name\": \"recommendation\", \"span_name\": \"flagd.evaluation.v2.Service/EventStream\"}, \"value\": \"0\"}, {\"labels\": {\"service_name\": \"checkout\", \"span_name\": \"oteldemo.PaymentService/Charge\"}, \"value\": \"0.030283611111111112\"}, {\"labels\": {\"service_name\": \"checkout\", \"span_name\": \"oteldemo.CheckoutService/PlaceOrder\"}, \"value\": \"0.030283611111111112\"}, {\"labels\": {\"service_name\": \"flagd\", \"span_name\": \"flagd.evaluation.v2.Service/EventStream\"}, \"value\": \"0\"}, {\"labels\": {\"service_name\": \"frontend\", \"span_name\": \"oteldemo.CheckoutService/PlaceOrder\"}, \"value\": \"0.030283611111111112\"}, {\"labels\": {\"service_name\": \"frontend\", \"span_name\": \"executing api route (pages) /api/checkout\"}, \"value\": \"0.030283611111111112\"}, {\"labels\": {\"service_name\": \"frontend-proxy\", \"span_name\": \"router frontend egress\"}, \"value\": \"0.030283611111111112\"}, {\"labels\": {\"service_name\": \"load-generator\", \"span_name\": \"POST\"}, \"value\": \"0.2\"}]}"}
```

### Tool `mcp__prom__query`

```
{"expr": "sum by (service_name, span_name) (rate(traces_span_metrics_calls_total{status_code=\"STATUS_CODE_ERROR\"}[2m]))", "time": "2026-10-12T06:33:00Z"}
```

```
{"result":"{\"resultType\": \"vector\", \"result\": [{\"labels\": {\"service_name\": \"load-generator\", \"span_name\": \"POST\"}, \"value\": \"0.16666666666666666\"}]}"}
```

### Tool `mcp__prom__query_range`

```
{"expr": "sum by (service_name, span_name) (rate(traces_span_metrics_calls_total{status_code=\"STATUS_CODE_ERROR\", service_name=\"payment\"}[1m]))", "start": "2026-10-12T06:30:00Z", "end": "2026-10-12T06:50:00Z", "step": "60s"}
```

```
{"result":"{\"resultType\": \"matrix\", \"result\": []}"}
```

### Tool `mcp__prom__query`

```
{"expr": "sum by (span_name, span_kind, status_code) (rate(traces_span_metrics_calls_total{service_name=\"payment\"}[2m]))", "time": "2026-10-12T06:39:00Z"}
```

```
{"result":"{\"resultType\": \"vector\", \"result\": [{\"labels\": {\"span_kind\": \"SPAN_KIND_CLIENT\", \"span_name\": \"dns.lookup\", \"status_code\": \"STATUS_CODE_UNSET\"}, \"value\": \"0\"}, {\"labels\": {\"span_kind\": \"SPAN_KIND_CLIENT\", \"span_name\": \"flagd.evaluation.v2.Service/EventStream\", \"status_code\": \"STATUS_CODE_ERROR\"}, \"value\": \"0\"}, {\"labels\": {\"span_kind\": \"SPAN_KIND_CLIENT\", \"span_name\": \"flagd.evaluation.v2.Service/ResolveBoolean\", \"status_code\": \"STATUS_CODE_UNSET\"}, \"value\": \"0\"}, {\"labels\": {\"span_kind\": \"SPAN_KIND_CLIENT\", \"span_name\": \"flagd.evaluation.v2.Service/ResolveFloat\", \"status_code\": \"STATUS_CODE_UNSET\"}, \"value\": \"0\"}, {\"labels\": {\"span_kind\": \"SPAN_KIND_INTERNAL\", \"span_name\": \"charge\", \"status_code\": \"STATUS_CODE_ERROR\"}, \"value\": \"0.030283611111111112\"}, {\"labels\": {\"span_kind\": \"SPAN_KIND_INTERNAL\", \"span_name\": \"charge\", \"status_code\": \"STATUS_CODE_UNSET\"}, \"value\": \"0.06666666666666667\"}, {\"labels\": {\"span_kind\": \"SPAN_KIND_INTERNAL\", \"span_name\": \"tcp.connect\", \"status_code\": \"STATUS_CODE_UNSET\"}, \"value\": \"0\"}, {\"labels\": {\"span_kind\": \"SPAN_KIND_SERVER\", \"span_name\": \"oteldemo.PaymentService/Charge\", \"status_code\": \"STATUS_CODE_ERROR\"}, \"value\": \"0.030283611111111112\"}, {\"labels\": {\"span_kind\": \"SPAN_KIND_SERVER\", \"span_name\": \"oteldemo.PaymentService/Charge\", \"status_code\": \"STATUS_CODE_UNSET\"}, \"value\": \"0.06666666666666667\"}]}"}
```

### Tool `mcp__prom__list_metrics`

```
{"contains": "flag"}
```

```
{"result":"{\"count\": 3, \"names\": [\"feature_flag_evaluation_active_count\", \"feature_flag_evaluation_requests_total\", \"feature_flag_evaluation_success_total\"]}"}
```

### Tool `mcp__prom__query`

```
{"expr": "sum by (feature_flag_key, feature_flag_variant) (rate(feature_flag_evaluation_success_total[2m]))", "time": "2026-10-12T06:39:00Z"}
```

```
{"result":"{\"resultType\": \"vector\", \"result\": [{\"labels\": {\"feature_flag_key\": \"cartFailure\"}, \"value\": \"0.05\"}, {\"labels\": {\"feature_flag_key\": \"failedReadinessProbe\"}, \"value\": \"0.03333333333333333\"}]}"}
```

### Tool `mcp__prom__query_range`

```
{"expr": "sum(rate(traces_span_metrics_calls_total{service_name=\"payment\", span_name=\"oteldemo.PaymentService/Charge\", status_code=\"STATUS_CODE_ERROR\"}[2m]))", "start": "2026-10-12T06:30:00Z", "end": "2026-10-12T06:50:00Z", "step": "60s"}
```

```
{"result":"{\"resultType\": \"matrix\", \"result\": [{\"labels\": {}, \"values\": [[1791787140, \"0.030283611111111112\"], [1791787200, \"0.016666666666666666\"], [1791787260, \"0.06666666666666667\"], [1791787320, \"0.016666666666666666\"], [1791787380, \"0\"], [1791787440, \"0\"], [1791787500, \"0\"], [1791787560, \"0\"], [1791787620, \"0\"]]}]}"}
```

## The model

**Cause: the failures start in the payment service's `Charge` call and propagate up to checkout. I can't tell from these metrics why `Charge` failed.**

Each hypothesis below is a separate sentence with the query that supports it.

1. **Payment `Charge` is the origin of the errors.** At 06:39:00Z the only non-load-generator error series were `payment` `charge`, `payment` `oteldemo.PaymentService/Charge`, and the callers of that RPC. The callers were `checkout` `Charge`, `checkout` `PlaceOrder`, `frontend` `PlaceOrder`, `/api/checkout`, and `frontend-proxy`. All showed the same rate, about 0.030/s. Query: `sum by (service_name, span_name) (rate(traces_span_metrics_calls_total{status_code="STATUS_CODE_ERROR"}[2m]))` at 06:39:00Z. At 06:33:00Z the same query showed only load-generator `POST` errors.

2. **Only part of the payment traffic failed, and the failures were brief.** At 06:39:00Z, `Charge` server spans were erroring at about 0.030/s and succeeding at about 0.067/s, so roughly 30% failed. Query: `sum by (span_name, span_kind, status_code) (rate(traces_span_metrics_calls_total{service_name="payment"}[2m]))`.

3. **The failures lasted about 4 minutes.** The error rate was non-zero from 06:39 to 06:42 (0.030, 0.017, 0.067, 0.017 per second). It was 0 from 06:43 onward, so the alert fired near the start of the burst. Query: `sum(rate(traces_span_metrics_calls_total{service_name="payment", span_name="oteldemo.PaymentService/Charge", status_code="STATUS_CODE_ERROR"}[2m]))`, ranged over 06:30Z–06:50Z.

4. **Feature flags don't clearly explain it.** The flag metrics at 06:39Z showed evaluations only for `cartFailure` and `failedReadinessProbe`. There was no payment-related flag, and the series have no variant label. Query: `sum by (feature_flag_key, feature_flag_variant) (rate(feature_flag_evaluation_success_total[2m]))`. I can't rule out a flag-injected fault from this.

**Not established:** the actual error reason, such as a card validation failure, an upstream dependency, or an injected fault. Span metrics only carry status codes. Next I'd check payment service logs and sample error traces for `charge` between 06:39 and 06:43. I'd also check for a deploy or flag change around 06:38–06:39.

**Side note:** a `ShopServiceErrors` P2 alert was also pending for `payment` and `checkout` at 06:39:30Z. That is consistent with this being a single fault, not two.

(end: 9 turns, 19 s)

