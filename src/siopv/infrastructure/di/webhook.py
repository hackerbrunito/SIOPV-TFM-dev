"""Dependency injection factory functions for webhook components."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from siopv.adapters.inbound.webhook_adapter import TrivyWebhookReceiver
from siopv.application.ports.webhook_receiver import WebhookReceiverPort

if TYPE_CHECKING:
    from siopv.infrastructure.config import Settings

logger = structlog.get_logger(__name__)


def build_webhook_receiver(settings: Settings) -> WebhookReceiverPort:
    """Create a configured TrivyWebhookReceiver from application settings.

    Args:
        settings: Application settings with webhook configuration

    Returns:
        WebhookReceiverPort implementation backed by TrivyWebhookReceiver
    """
    adapter = TrivyWebhookReceiver(
        secret=settings.webhook_secret,
        output_dir=settings.output_dir,
    )
    logger.info(
        "webhook_receiver_created",
        enabled=settings.webhook_enabled,
        host=settings.webhook_host,
        port=settings.webhook_port,
    )
    return adapter


__all__ = [
    "build_webhook_receiver",
]
