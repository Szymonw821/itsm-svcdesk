# ai-generated: 90% - Claude Code wrote the script from lab3 HANDOUT.md Stretch 1, reviewed by the author
"""Stretch 1 (M-28): one instrumented LLM call, its spans written to genai/spans.json as OTLP JSON.

Runs outside svcdesk, against any OpenAI-compatible endpoint (here a local Ollama with qwen3:1.7b):
    pip install openai==3.19.2 opentelemetry-sdk==1.45.0 opentelemetry-instrumentation-genai-openai==1.2b0 \
        opentelemetry-exporter-otlp-json-file==0.66b0
    python genai/call_llm.py
"""

import os
from pathlib import Path

from openai import OpenAI
from opentelemetry import trace
from opentelemetry.exporter.otlp.json.file import FileSpanExporter
from opentelemetry.instrumentation.genai.openai import OpenAIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

SPANS = Path(__file__).with_name("spans.json")
BASE_URL = os.environ.get("OPENAI_BASE_URL", "http://localhost:11434/v1")
MODEL = os.environ.get("GENAI_MODEL", "qwen3:1.7b")

SPANS.unlink(missing_ok=True)
provider = TracerProvider(resource=Resource.create({"service.name": "svcdesk-genai-diff"}))
provider.add_span_processor(SimpleSpanProcessor(FileSpanExporter(path=str(SPANS))))
trace.set_tracer_provider(provider)
OpenAIInstrumentor().instrument(tracer_provider=provider)

client = OpenAI(base_url=BASE_URL, api_key=os.environ.get("OPENAI_API_KEY", "ollama"))
response = client.chat.completions.create(
    model=MODEL,
    messages=[{"role": "user", "content": "In one sentence: what is a known error in ITIL problem management? /no_think"}],
    max_tokens=200,
    temperature=0.2,
)
print(response.choices[0].message.content)
provider.shutdown()
