"""Runtime configuration loaded from environment variables."""

from __future__ import annotations

import os
import socket
from dataclasses import dataclass

REMOTE_WRITE_PATH_TEMPLATE = (
    "{endpoint}/dataCollectionRules/{dcr}/streams/Microsoft-PrometheusMetrics/api/v1/write?api-version={api_version}"
)


@dataclass(frozen=True, slots=True)
class Settings:
    """Application settings sourced from the environment.

    Required environment variables:
        AZURE_MONITOR_INGESTION_ENDPOINT: Metrics ingestion endpoint of the
            Azure Monitor workspace (the ``*.metrics.ingest.monitor.azure.com``
            host, without a trailing path).
        AZURE_MONITOR_DCR_IMMUTABLE_ID: Immutable ID of the workspace's default
            data collection rule (for example ``dcr-xxxxxxxx``).
    """

    ingestion_endpoint: str
    dcr_immutable_id: str
    api_version: str
    service_name: str
    job: str
    instance: str
    export_interval_seconds: float
    metric_scope: str
    run_seconds: float

    @property
    def remote_write_url(self) -> str:
        """Full Prometheus remote-write URL for the Azure Monitor workspace."""
        return REMOTE_WRITE_PATH_TEMPLATE.format(
            endpoint=self.ingestion_endpoint.rstrip("/"),
            dcr=self.dcr_immutable_id,
            api_version=self.api_version,
        )


def load_settings() -> Settings:
    """Build :class:`Settings` from environment variables.

    Raises:
        KeyError: If a required environment variable is missing.

    """
    instance = os.environ.get("OTEL_INSTANCE_ID") or socket.gethostname()
    return Settings(
        ingestion_endpoint=os.environ["AZURE_MONITOR_INGESTION_ENDPOINT"],
        dcr_immutable_id=os.environ["AZURE_MONITOR_DCR_IMMUTABLE_ID"],
        api_version=os.environ.get("AZURE_MONITOR_API_VERSION", "2023-04-24"),
        service_name=os.environ.get("OTEL_SERVICE_NAME", "otel-prometheus-demo"),
        job=os.environ.get("OTEL_JOB", "otel-prometheus-demo"),
        instance=instance,
        export_interval_seconds=float(os.environ.get("EXPORT_INTERVAL_SECONDS", "15")),
        metric_scope=os.environ.get("OTEL_METER_NAME", "otel_prometheus.demo"),
        run_seconds=float(os.environ.get("RUN_SECONDS", "0")),
    )
