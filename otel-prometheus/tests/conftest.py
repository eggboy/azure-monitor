"""Shared pytest fixtures."""

from __future__ import annotations

import time

import pytest
from azure.core.credentials import AccessToken

from otel_prometheus.config import Settings


class FakeCredential:
    """Token credential stub that returns a static, non-expiring token."""

    def __init__(self, token: str = "faketoken") -> None:
        self._token = token

    def get_token(self, *_scopes: str, **_kwargs) -> AccessToken:
        return AccessToken(self._token, int(time.time()) + 3600)


@pytest.fixture
def fake_credential() -> FakeCredential:
    return FakeCredential()


@pytest.fixture
def settings() -> Settings:
    return Settings(
        ingestion_endpoint="https://example-ws.eastus-1.metrics.ingest.monitor.azure.com",
        dcr_immutable_id="dcr-1234567890abcdef1234567890abcdef",
        api_version="2023-04-24",
        service_name="otel-prometheus-demo",
        job="otel-prometheus-demo",
        instance="test-host",
        export_interval_seconds=15,
        metric_scope="otel_prometheus.demo",
        run_seconds=0,
    )
