"""JSON-formatted logs with trace correlation.

The OpenTelemetry logging instrumentation injects the active trace_id and
span_id into each log record, so logs in Loki/CloudWatch can be linked
back to Jaeger spans.
"""

from __future__ import annotations

import logging
import sys

from opentelemetry.instrumentation.logging import LoggingInstrumentor
from pythonjsonlogger import jsonlogger


def setup_logging(level: str = "INFO") -> None:
    LoggingInstrumentor().instrument(set_logging_format=False)

    root = logging.getLogger()
    # Clear default handlers so we don't double-log.
    for h in list(root.handlers):
        root.removeHandler(h)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        jsonlogger.JsonFormatter(
            fmt=(
                "%(asctime)s %(levelname)s %(name)s %(message)s "
                "%(otelTraceID)s %(otelSpanID)s %(otelServiceName)s"
            ),
            rename_fields={
                "asctime": "ts",
                "levelname": "level",
                "name": "logger",
                "otelTraceID": "trace_id",
                "otelSpanID": "span_id",
                "otelServiceName": "service",
            },
        )
    )
    root.addHandler(handler)
    root.setLevel(level.upper())
