"""OpenTelemetry metrics — small set of business counters/histograms
that surface in Prometheus + Grafana via the collector."""

from __future__ import annotations

import os
import time
from contextlib import contextmanager

from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource

_initialized = False
_meter = None
_deployment_triggered = None
_deployment_succeeded = None
_deployment_failed = None
_queue_publish_duration = None
_worker_job_duration = None


def setup_metrics(service_name: str) -> None:
    global _initialized, _meter
    global _deployment_triggered, _deployment_succeeded, _deployment_failed
    global _queue_publish_duration, _worker_job_duration

    if _initialized:
        return

    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317")
    resource = Resource.create({"service.name": service_name})
    reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=endpoint, insecure=True),
        export_interval_millis=10_000,
    )
    metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[reader]))

    _meter = metrics.get_meter("deployflow")
    _deployment_triggered = _meter.create_counter(
        "deployflow.deployments.triggered", description="Deployments triggered by users"
    )
    _deployment_succeeded = _meter.create_counter(
        "deployflow.deployments.succeeded", description="Deployments that reached SUCCEEDED"
    )
    _deployment_failed = _meter.create_counter(
        "deployflow.deployments.failed", description="Deployments that reached FAILED"
    )
    _queue_publish_duration = _meter.create_histogram(
        "deployflow.queue.publish.duration_ms",
        description="Time spent publishing a job to the queue",
        unit="ms",
    )
    _worker_job_duration = _meter.create_histogram(
        "deployflow.worker.job.duration_ms",
        description="End-to-end worker processing time per deployment",
        unit="ms",
    )

    _initialized = True


def inc_triggered() -> None:
    if _deployment_triggered:
        _deployment_triggered.add(1)


def inc_succeeded() -> None:
    if _deployment_succeeded:
        _deployment_succeeded.add(1)


def inc_failed() -> None:
    if _deployment_failed:
        _deployment_failed.add(1)


@contextmanager
def timed_publish():
    t0 = time.perf_counter()
    try:
        yield
    finally:
        if _queue_publish_duration:
            _queue_publish_duration.record((time.perf_counter() - t0) * 1000)


@contextmanager
def timed_worker_job():
    t0 = time.perf_counter()
    try:
        yield
    finally:
        if _worker_job_duration:
            _worker_job_duration.record((time.perf_counter() - t0) * 1000)
