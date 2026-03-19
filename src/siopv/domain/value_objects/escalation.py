"""Escalation configuration value object for HITL timeout levels."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EscalationConfig:
    """Escalation timeout configuration from settings.

    Attributes:
        level_thresholds: List of (hours, level) tuples, sorted descending
        review_deadline_hours: Hours until review deadline
    """

    level_thresholds: tuple[tuple[int, int], ...]
    review_deadline_hours: int


__all__ = [
    "EscalationConfig",
]
