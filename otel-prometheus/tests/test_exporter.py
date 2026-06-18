"""Tests for the Entra-authenticated remote-write exporter."""

from __future__ import annotations

from otel_prometheus.exporter import AzureMonitorRemoteWriteExporter


def test_build_headers_injects_bearer_token(fake_credential, settings) -> None:
    exporter = AzureMonitorRemoteWriteExporter(
        endpoint=settings.remote_write_url,
        credential=fake_credential,
    )
    headers = exporter._build_headers()
    assert headers["Authorization"] == "Bearer faketoken"
    assert headers["Content-Type"] == "application/x-protobuf"
    assert headers["Content-Encoding"] == "snappy"


def test_endpoint_is_remote_write_url(fake_credential, settings) -> None:
    exporter = AzureMonitorRemoteWriteExporter(
        endpoint=settings.remote_write_url,
        credential=fake_credential,
    )
    assert exporter.endpoint == settings.remote_write_url
