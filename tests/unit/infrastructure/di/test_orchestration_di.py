"""Tests for orchestration DI factory functions.

Covers:
- build_threshold_config: creates ThresholdConfig from settings
- build_escalation_config: creates EscalationConfig from settings
- EscalationConfig dataclass
"""

from __future__ import annotations

from unittest.mock import MagicMock

from siopv.domain.value_objects.escalation import EscalationConfig
from siopv.infrastructure.di.orchestration import (
    build_escalation_config,
    build_threshold_config,
)


def _make_settings() -> MagicMock:
    settings = MagicMock()
    settings.uncertainty_threshold = 0.25
    settings.confidence_floor = 0.65
    settings.adaptive_percentile = 85
    settings.discrepancy_history_size = 300
    settings.hitl_timeout_level1_hours = 4
    settings.hitl_timeout_level2_hours = 8
    settings.hitl_timeout_level3_hours = 24
    settings.review_deadline_hours = 48
    return settings


class TestBuildThresholdConfig:
    def test_creates_config_from_settings(self) -> None:
        settings = _make_settings()
        config = build_threshold_config(settings)

        assert config.base_threshold == 0.25
        assert config.confidence_floor == 0.65
        assert config.percentile == 85
        assert config.history_size == 300

    def test_uses_settings_values_not_defaults(self) -> None:
        settings = _make_settings()
        settings.uncertainty_threshold = 0.5
        settings.confidence_floor = 0.9

        config = build_threshold_config(settings)

        assert config.base_threshold == 0.5
        assert config.confidence_floor == 0.9


class TestBuildEscalationConfig:
    def test_creates_config_from_settings(self) -> None:
        settings = _make_settings()
        config = build_escalation_config(settings)

        assert config.level_thresholds == ((24, 3), (8, 2), (4, 1))
        assert config.review_deadline_hours == 48

    def test_uses_settings_values_not_defaults(self) -> None:
        settings = _make_settings()
        settings.hitl_timeout_level1_hours = 2
        settings.hitl_timeout_level2_hours = 6
        settings.hitl_timeout_level3_hours = 12
        settings.review_deadline_hours = 72

        config = build_escalation_config(settings)

        assert config.level_thresholds == ((12, 3), (6, 2), (2, 1))
        assert config.review_deadline_hours == 72


class TestEscalationConfig:
    def test_is_frozen(self) -> None:
        config = EscalationConfig(
            level_thresholds=((24, 3), (8, 2), (4, 1)),
            review_deadline_hours=24,
        )
        # Frozen dataclass should raise on attribute assignment
        try:
            config.review_deadline_hours = 48  # type: ignore[misc]
            raise AssertionError("Expected FrozenInstanceError")
        except AttributeError:
            pass

    def test_fields_accessible(self) -> None:
        config = EscalationConfig(
            level_thresholds=((24, 3),),
            review_deadline_hours=12,
        )
        assert config.level_thresholds == ((24, 3),)
        assert config.review_deadline_hours == 12
