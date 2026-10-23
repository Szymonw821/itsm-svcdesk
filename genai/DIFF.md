---
lab3_genai_diff:
  instrumentation: "opentelemetry-instrumentation-genai-openai 1.2b0 (with opentelemetry-util-genai 1.3b0), opentelemetry-sdk 1.45.0, opentelemetry-exporter-otlp-json-file 0.66b0, openai 3.19.2"
  spec_ref: "semantic-conventions@v1.41.1"
  attributes:
    - {name: gen_ai.operation.name, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.provider.name, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.request.model, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.request.temperature, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.request.max_tokens, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.response.finish_reasons, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.response.model, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.response.id, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.usage.input_tokens, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.usage.output_tokens, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.request.top_p, emitted: false, in_spec: true, stability: development}
    - {name: gen_ai.usage.reasoning.output_tokens, emitted: false, in_spec: true, stability: development}
    - {name: gen_ai.input.messages, emitted: false, in_spec: true, stability: development}
    - {name: gen_ai.system, emitted: false, in_spec: true, stability: deprecated}
    - {name: gen_ai.openai.response.system_fingerprint, emitted: false, in_spec: true, stability: deprecated}
---
<!-- ai-generated: 85% - Claude Code ran the call, diffed the spans against the v1.41.1 registry and wrote the prose, reviewed by the author -->

# What the library emits, against the spec

One chat completion (`genai/call_llm.py`) against a local Ollama serving `qwen3:1.7b` through its OpenAI-compatible
endpoint, instrumented with `OpenAIInstrumentor` from `opentelemetry.instrumentation.genai.openai` 1.2b0, exported
with `FileSpanExporter` to `genai/spans.json`. One span, `chat qwen3:1.7b`, with ten `gen_ai.*` attributes, compared
with the attribute registry of `semantic-conventions@v1.41.1` (`model/gen-ai/registry.yaml` and
`model/gen-ai/deprecated/registry-deprecated.yaml` at that tag).

**What agrees.** Every one of the ten emitted keys is defined in the spec, under the name the spec uses, and all
are `development` - nothing in the GenAI conventions is stable at this ref. The library already follows the newer
vocabulary: it writes `gen_ai.provider.name` (`openai`), not the deprecated `gen_ai.system`, and
`gen_ai.usage.input_tokens` / `output_tokens`, not the deprecated `prompt_tokens` / `completion_tokens`.

**What does not, or not quite.**

- `gen_ai.provider.name` says `openai` because the client library is OpenAI's; the model actually ran in Ollama.
  The attribute names the API flavour, not who served the request, so a dashboard grouped by provider would count
  this local call as OpenAI traffic. `server.address` (`localhost:11434`) is the only hint.
- The system fingerprint is emitted as `openai.response.system_fingerprint`, outside the `gen_ai.*` namespace; the
  spec's only name for it, `gen_ai.openai.response.system_fingerprint`, is deprecated at this ref, so there is no
  current spec attribute for it at all.
- `gen_ai.usage.reasoning.output_tokens` is in the spec but not emitted, although qwen3 is a reasoning model and
  spent its whole 200-token budget thinking (`finish_reasons: ["length"]`): the OpenAI-compatible answer does not
  break the usage down, so the instrumentation has nothing to report.
- `gen_ai.request.top_p` is not emitted because the call did not set it - the library reports what was requested,
  not the server's defaults.
- `gen_ai.input.messages` (the prompt itself) is opt-in content capture and is off by default, which is the right
  default for a service-desk text that may contain personal data.

**For a dashboard.** Token usage, model and finish reason are there and are enough for cost and truncation
panels (a rising share of `length` is a useful alert). Grouping by provider is misleading for self-hosted models,
and because everything is `development`, any of these names may still change: pin the instrumentation version and
expect to rename queries when it moves.
