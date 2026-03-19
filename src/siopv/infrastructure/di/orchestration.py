"""Dependency injection factory functions for orchestration components.

Factory functions for creating threshold configuration and escalation
settings from application settings, injected into orchestration utils
and graph nodes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from siopv.domain.value_objects.discrepancy import ThresholdConfig
from siopv.domain.value_objects.escalation import EscalationConfig

if TYPE_CHECKING:
    from siopv.infrastructure.config import Settings

logger = structlog.get_logger(__name__)


def build_threshold_config(settings: Settings) -> ThresholdConfig:
    """Create ThresholdConfig from application settings.

    Args:
        settings: Application settings with uncertainty threshold configuration

    Returns:
        ThresholdConfig with values from settings
    """
    config = ThresholdConfig(
        base_threshold=settings.uncertainty_threshold,
        confidence_floor=settings.confidence_floor,
        percentile=settings.adaptive_percentile,
        history_size=settings.discrepancy_history_size,
        default_confidence=settings.default_confidence,
    )
    logger.info(
        "threshold_config_created",
        base_threshold=config.base_threshold,
        confidence_floor=config.confidence_floor,
        percentile=config.percentile,
        history_size=config.history_size,
    )
    return config


def build_escalation_config(settings: Settings) -> EscalationConfig:
    """Create EscalationConfig from application settings.

    Args:
        settings: Application settings with HITL timeout configuration

    Returns:
        EscalationConfig with values from settings
    """
    config = EscalationConfig(
        level_thresholds=(
            (settings.hitl_timeout_level3_hours, 3),
            (settings.hitl_timeout_level2_hours, 2),
            (settings.hitl_timeout_level1_hours, 1),
        ),
        review_deadline_hours=settings.review_deadline_hours,
    )
    logger.info(
        "escalation_config_created",
        level_thresholds=config.level_thresholds,
        review_deadline_hours=config.review_deadline_hours,
    )
    return config


__all__ = [
    "EscalationConfig",
    "build_escalation_config",
    "build_threshold_config",
]
