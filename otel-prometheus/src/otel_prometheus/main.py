"""Entry point: emit custom OTEL metrics to Azure managed Prometheus."""

from __future__ import annotations

import logging
import signal
import time
from types import FrameType

from dotenv import load_dotenv

from otel_prometheus.config import Settings, load_settings
from otel_prometheus.metrics import DemoInstruments, build_meter_provider

logger = logging.getLogger(__name__)

_running = True


def _handle_stop(signum: int, _frame: FrameType | None) -> None:
    global _running
    logger.info("Received signal %s, shutting down...", signal.Signals(signum).name)
    _running = False


def run(settings: Settings) -> None:
    """Run the export loop until interrupted or ``run_seconds`` elapses."""
    provider = build_meter_provider(settings)
    meter = provider.get_meter(settings.metric_scope)
    instruments = DemoInstruments.create(meter)

    logger.info("Exporting metrics to %s", settings.remote_write_url)
    logger.info(
        "service.name=%s job=%s instance=%s interval=%ss",
        settings.service_name,
        settings.job,
        settings.instance,
        settings.export_interval_seconds,
    )

    signal.signal(signal.SIGINT, _handle_stop)
    signal.signal(signal.SIGTERM, _handle_stop)

    deadline = time.monotonic() + settings.run_seconds if settings.run_seconds > 0 else None
    try:
        while _running:
            instruments.record_iteration()
            if deadline is not None and time.monotonic() >= deadline:
                logger.info("Reached run_seconds=%s, stopping.", settings.run_seconds)
                break
            time.sleep(1)
    finally:
        logger.info("Flushing pending metrics...")
        provider.force_flush()
        provider.shutdown()
        logger.info("Shutdown complete.")


def main() -> None:
    """CLI entry point."""
    load_dotenv()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    run(load_settings())


if __name__ == "__main__":
    main()
