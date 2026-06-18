"""Tests for configuration loading and URL construction."""

from __future__ import annotations

import pytest

from otel_prometheus.config import Settings, load_settings


def test_remote_write_url_format(settings: Settings) -> None:
    assert settings.remote_write_url == (
        "https://example-ws.eastus-1.metrics.ingest.monitor.azure.com"
        "/dataCollectionRules/dcr-1234567890abcdef1234567890abcdef"
        "/streams/Microsoft-PrometheusMetrics/api/v1/write?api-version=2023-04-24"
    )


def test_remote_write_url_strips_trailing_slash() -> None:
    settings = Settings(
        ingestion_endpoint="https://ws.eastus-1.metrics.ingest.monitor.azure.com/",
        dcr_immutable_id="dcr-abc",
        api_version="2023-04-24",
        service_name="s",
        job="j",
        instance="i",
        export_interval_seconds=15,
        metric_scope="m",
        run_seconds=0,
    )
    assert "azure.com/dataCollectionRules" in settings.remote_write_url
    assert "azure.com//dataCollectionRules" not in settings.remote_write_url


def test_load_settings_requires_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AZURE_MONITOR_INGESTION_ENDPOINT", raising=False)
    monkeypatch.setenv("AZURE_MONITOR_DCR_IMMUTABLE_ID", "dcr-abc")
    with pytest.raises(KeyError):
        load_settings()


def test_load_settings_reads_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AZURE_MONITOR_INGESTION_ENDPOINT", "https://ws.metrics.ingest.monitor.azure.com")
    monkeypatch.setenv("AZURE_MONITOR_DCR_IMMUTABLE_ID", "dcr-xyz")
    monkeypatch.setenv("OTEL_JOB", "custom-job")
    monkeypatch.setenv("OTEL_INSTANCE_ID", "host-7")
    monkeypatch.setenv("EXPORT_INTERVAL_SECONDS", "5")
    loaded = load_settings()
    assert loaded.job == "custom-job"
    assert loaded.instance == "host-7"
    assert loaded.export_interval_seconds == 5
