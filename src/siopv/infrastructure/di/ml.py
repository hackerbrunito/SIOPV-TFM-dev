"""Dependency injection factory functions for ML components.

Factory functions for creating ML classification adapters that implement
MLClassifierPort. Supports graceful degradation when model files are missing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from siopv.adapters.ml.xgboost_classifier import XGBoostClassifier
from siopv.application.ports.ml_classifier import MLClassifierPort

if TYPE_CHECKING:
    from siopv.infrastructure.config import Settings

logger = structlog.get_logger(__name__)


def build_classifier(settings: Settings) -> MLClassifierPort | None:
    """Create a configured XGBoost classifier from application settings.

    Args:
        settings: Application settings with model path configuration

    Returns:
        MLClassifierPort implementation, or None if model file does not exist
    """
    model_path = settings.model_path

    if not model_path.exists():
        logger.warning(
            "classifier_skipped",
            reason="model file not found",
            model_path=str(model_path),
        )
        return None

    adapter = XGBoostClassifier(model_path=model_path)
    logger.info("classifier_created", model_path=str(model_path))
    return adapter


__all__ = [
    "build_classifier",
]
