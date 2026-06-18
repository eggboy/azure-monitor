"""OpenTelemetry metrics setup and the demo instrument workload."""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass

from opentelemetry.metrics import Counter, Histogram, Meter, UpDownCounter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource

from otel_prometheus.config import Settings
from otel_prometheus.exporter import AzureMonitorRemoteWriteExporter

logger = logging.getLogger(__name__)

_HTTP_METHODS = ("GET", "POST", "PUT", "DELETE")
_ROUTES = ("/orders", "/users", "/checkout", "/health")


def build_meter_provider(settings: Settings) -> MeterProvider:
    """Create a :class:`MeterProvider` wired to Azure managed Prometheus.

    The resource attributes ``job`` and ``instance`` become Prometheus labels
    on every exported series, matching standard Prometheus conventions. A
    minimal resource is used so the SDK's ``telemetry_sdk_*`` attributes do not
    leak in as labels.
    """
    resource = Resource(
        attributes={
            "service.name": settings.service_name,
            "job": settings.job,
            "instance": settings.instance,
        }
    )
    exporter = AzureMonitorRemoteWriteExporter(endpoint=settings.remote_write_url)
    reader = PeriodicExportingMetricReader(
        exporter,
        export_interval_millis=settings.export_interval_seconds * 1000,
    )
    return MeterProvider(metric_readers=[reader], resource=resource)


@dataclass(slots=True)
class DemoInstruments:
    """A small set of custom instruments exercised by the demo workload."""

    requests_total: Counter
    request_duration_seconds: Histogram
    active_connections: UpDownCounter

    @classmethod
    def create(cls, meter: Meter) -> DemoInstruments:
        """Register the demo instruments on ``meter``."""
        return cls(
            requests_total=meter.create_counter(
                "demo_requests_total",
                description="Total number of demo HTTP requests handled.",
            ),
            request_duration_seconds=meter.create_histogram(
                "demo_request_duration_seconds",
                description="Latency of demo HTTP requests in seconds.",
            ),
            active_connections=meter.create_up_down_counter(
                "demo_active_connections",
                description="Currently active demo connections.",
            ),
        )

    def record_iteration(self) -> None:
        """Emit one synthetic measurement on each instrument."""
        attributes = {
            "http_method": random.choice(_HTTP_METHODS),
            "route": random.choice(_ROUTES),
            "status_code": random.choice((200, 200, 200, 404, 500)),
        }
        self.requests_total.add(random.randint(1, 5), attributes)
        self.request_duration_seconds.record(random.uniform(0.005, 1.5), attributes)
        self.active_connections.add(random.randint(-3, 3), {"pool": "default"})
