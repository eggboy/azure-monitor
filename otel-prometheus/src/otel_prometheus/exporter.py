"""Azure Monitor managed Prometheus remote-write exporter.

Wraps the OpenTelemetry Prometheus remote-write exporter and injects a fresh
Microsoft Entra ID bearer token on every export. Azure Monitor managed
Prometheus authenticates remote-write requests with an Entra token whose
audience is ``https://monitor.azure.com``; the caller identity needs the
``Monitoring Metrics Publisher`` role on the workspace's data collection rule.
"""

from __future__ import annotations

import logging

from azure.core.credentials import TokenCredential
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from opentelemetry.exporter.prometheus_remote_write import (
    PrometheusRemoteWriteMetricsExporter,
)

logger = logging.getLogger(__name__)

MONITOR_INGESTION_SCOPE = "https://monitor.azure.com/.default"


class AzureMonitorRemoteWriteExporter(PrometheusRemoteWriteMetricsExporter):
    """Remote-write exporter that authenticates with Microsoft Entra ID.

    The bearer token is obtained through :func:`get_bearer_token_provider`,
    which caches the token and refreshes it automatically before expiry, so a
    long-running process keeps exporting without manual token management.
    """

    def __init__(
        self,
        endpoint: str,
        *,
        credential: TokenCredential | None = None,
        **kwargs,
    ) -> None:
        """Initialize the exporter with the remote-write URL and an Entra credential."""
        super().__init__(endpoint=endpoint, **kwargs)
        self._token_provider = get_bearer_token_provider(
            credential or DefaultAzureCredential(),
            MONITOR_INGESTION_SCOPE,
        )

    def _build_headers(self) -> dict:
        headers = super()._build_headers()
        headers["Authorization"] = f"Bearer {self._token_provider()}"
        return headers
