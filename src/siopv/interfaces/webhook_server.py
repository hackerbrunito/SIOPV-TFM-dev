"""SIOPV Webhook Server — FastAPI entry point for CI/CD integration.

Mounts the Trivy webhook router and starts a uvicorn server.
The webhook receives Trivy JSON reports, validates HMAC-SHA256
signatures, and triggers pipeline execution as a background task.

Launch:
    uv run python -m siopv.interfaces.webhook_server
    # or via CLI:
    siopv webhook-server
"""

from __future__ import annotations

import structlog
import uvicorn
from fastapi import FastAPI

from siopv.adapters.inbound.webhook_adapter import (
    router as webhook_router,
)
from siopv.adapters.inbound.webhook_adapter import (
    set_webhook_receiver,
)
from siopv.infrastructure.config.settings import get_settings
from siopv.infrastructure.di.webhook import build_webhook_receiver

logger = structlog.get_logger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI webhook application."""
    settings = get_settings()

    app = FastAPI(
        title="SIOPV Webhook Server",
        description="Receives Trivy vulnerability reports from CI/CD pipelines",
        version="0.1.0",
    )

    # Wire DI — inject the configured webhook receiver
    receiver = build_webhook_receiver(settings)
    set_webhook_receiver(receiver)

    # Mount the webhook router
    app.include_router(webhook_router)

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        return {"status": "ok", "service": "siopv-webhook"}

    logger.info(
        "webhook_server_created",
        host=settings.webhook_host,
        port=settings.webhook_port,
    )

    return app


def main() -> None:
    """Start the webhook server."""
    settings = get_settings()
    app = create_app()

    logger.info(
        "webhook_server_starting",
        host=settings.webhook_host,
        port=settings.webhook_port,
    )

    uvicorn.run(
        app,
        host=settings.webhook_host,
        port=settings.webhook_port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
