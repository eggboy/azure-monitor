"""Tests for instrument registration and the demo workload."""

from __future__ import annotations

from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader

from otel_prometheus.metrics import DemoInstruments


def _collect_metric_names(reader: InMemoryMetricReader) -> set[str]:
    data = reader.get_metrics_data()
    names: set[str] = set()
    for resource_metric in data.resource_metrics:
        for scope_metric in resource_metric.scope_metrics:
            names.update(metric.name for metric in scope_metric.metrics)
    return names


def test_demo_instruments_emit_expected_metrics() -> None:
    reader = InMemoryMetricReader()
    provider = MeterProvider(metric_readers=[reader])
    meter = provider.get_meter("test")
    instruments = DemoInstruments.create(meter)

    for _ in range(10):
        instruments.record_iteration()

    names = _collect_metric_names(reader)
    assert names == {
        "demo_requests_total",
        "demo_request_duration_seconds",
        "demo_active_connections",
    }
    provider.shutdown()
