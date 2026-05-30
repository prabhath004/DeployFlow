"""OpenTelemetry tracing setup.

Reads OTEL_EXPORTER_OTLP_ENDPOINT + OTEL_SERVICE_NAME from env (already set
in docker-compose). `setup_tracing("deployflow-api")` is called once at
startup from main.py / worker main(). `instrument_app(app)` wires
auto-instrumentation for FastAPI; everything else (SQLAlchemy, Redis,
botocore) is instrumented globally.
"""

from __future__ import annotations

import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor
from opentelemetry.instrumentation.botocore import BotocoreInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

_initialized = False


def setup_tracing(service_name: str) -> None:
    """Idempotent — calling twice is safe."""
    global _initialized
    if _initialized:
        return

    endpoint = os.environ.get(
        "OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317"
    )

    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": "0.10.0",
            "deployment.environment": os.environ.get("ENVIRONMENT", "local"),
        }
    )
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, insecure=True))
    )
    trace.set_tracer_provider(provider)

    # Instrument client libraries globally. FastAPI is instrumented per-app
    # by instrument_app() because it needs the app instance.
    AsyncPGInstrumentor().instrument()
    RedisInstrumentor().instrument()
    BotocoreInstrumentor().instrument()

    _initialized = True


def instrument_app(app, engine=None) -> None:
    """FastAPI-specific instrumentation; engine is optional."""
    FastAPIInstrumentor.instrument_app(app)
    if engine is not None:
        # SQLAlchemy instrumentation needs the sync engine handle; for async
        # engines we pass engine.sync_engine.
        SQLAlchemyInstrumentor().instrument(
            engine=engine.sync_engine,
            enable_commenter=True,  # adds /* traceparent */ comments to SQL
        )


tracer = trace.get_tracer("deployflow")
