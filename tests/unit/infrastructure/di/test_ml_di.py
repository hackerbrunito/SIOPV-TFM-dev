"""Unit tests for ML DI factory functions.

Tests factory functions for creating ML classification adapters:
- build_classifier: Returns XGBoostClassifier or None based on model file existence
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from siopv.application.ports.ml_classifier import MLClassifierPort
from siopv.infrastructure.config.settings import Settings
from siopv.infrastructure.di.ml import build_classifier

# === Fixtures ===


@pytest.fixture
def settings_with_model(tmp_path: Path) -> Settings:
    """Settings with a model file that exists."""
    model_file = tmp_path / "xgboost_risk_model.json"
    model_file.write_text("{}")
    return Settings(model_path=model_file)


@pytest.fixture
def settings_no_model(tmp_path: Path) -> Settings:
    """Settings with a model path that does not exist."""
    return Settings(model_path=tmp_path / "nonexistent_model.json")


# === Test build_classifier ===


class TestBuildClassifier:
    """Tests for build_classifier factory."""

    def test_returns_none_when_model_missing(self, settings_no_model: Settings) -> None:
        classifier = build_classifier(settings_no_model)
        assert classifier is None

    @patch("siopv.infrastructure.di.ml.XGBoostClassifier")
    def test_returns_classifier_when_model_exists(
        self,
        mock_cls: object,
        settings_with_model: Settings,
    ) -> None:
        classifier = build_classifier(settings_with_model)
        assert classifier is not None
        assert mock_cls is not None

    @patch("siopv.infrastructure.di.ml.XGBoostClassifier")
    def test_passes_model_path(self, mock_cls: object, settings_with_model: Settings) -> None:
        from unittest.mock import MagicMock

        mock_instance = MagicMock(spec=MLClassifierPort)
        mock_cls_typed = mock_cls  # type: ignore[assignment]
        mock_cls_typed.return_value = mock_instance

        build_classifier(settings_with_model)
        mock_cls_typed.assert_called_once_with(
            model_path=settings_with_model.model_path,
            environment=settings_with_model.environment,
        )


# === Test exports ===


class TestMlDiExports:
    """Tests for ML DI module exports via __init__.py."""

    def test_importable_from_di_package(self) -> None:
        from siopv.infrastructure.di import build_classifier

        assert callable(build_classifier)
