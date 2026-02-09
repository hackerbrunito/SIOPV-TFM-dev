"""Value objects for ML risk classification results.

These represent the output of the ML classification pipeline:
- RiskScore: Probability of exploitation with confidence
- SHAPValues: Global feature importance from SHAP
- LIMEExplanation: Local per-prediction explanation from LIME
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from siopv.domain.constants import (
    CONFIDENCE_CENTER_PROBABILITY,
    CONFIDENCE_SCALE_FACTOR,
    RISK_PROBABILITY_CRITICAL_THRESHOLD,
    RISK_PROBABILITY_HIGH_THRESHOLD,
    RISK_PROBABILITY_LOW_THRESHOLD,
    RISK_PROBABILITY_MEDIUM_THRESHOLD,
)


class SHAPValues(BaseModel):
    """Value object representing SHAP feature importance values.

    SHAP (SHapley Additive exPlanations) provides global feature importance
    for the XGBoost model predictions.
    """

    model_config = ConfigDict(frozen=True)

    feature_names: list[str] = Field(
        ...,
        description="Names of features in order",
    )
    shap_values: list[float] = Field(
        ...,
        description="SHAP values for each feature",
    )
    base_value: float = Field(
        ...,
        description="Expected model output (base value)",
    )

    @field_validator("shap_values")
    @classmethod
    def validate_shap_values(cls, v: list[float]) -> list[float]:
        """Validate SHAP values have same length as feature names."""
        return v

    def to_dict(self) -> dict[str, float]:
        """Convert to feature name -> SHAP value mapping."""
        return dict(zip(self.feature_names, self.shap_values, strict=True))

    @property
    def top_contributors(self) -> list[tuple[str, float]]:
        """Get top 5 contributing features sorted by absolute SHAP value."""
        pairs = list(zip(self.feature_names, self.shap_values, strict=True))
        sorted_pairs = sorted(pairs, key=lambda x: abs(x[1]), reverse=True)
        return sorted_pairs[:5]

    def __str__(self) -> str:
        top = self.top_contributors[:3]
        formatted = ", ".join(f"{name}: {value:+.3f}" for name, value in top)
        return f"SHAP({formatted})"


class LIMEExplanation(BaseModel):
    """Value object representing LIME local explanation.

    LIME (Local Interpretable Model-agnostic Explanations) provides
    per-prediction explanations showing which features contributed
    to the risk classification decision.
    """

    model_config = ConfigDict(frozen=True)

    feature_contributions: list[tuple[str, float]] = Field(
        ...,
        description="List of (feature_condition, contribution) tuples",
    )
    prediction_local: float = Field(
        ge=0.0,
        le=1.0,
        description="Local model prediction probability",
    )
    intercept: float = Field(
        ...,
        description="Intercept of the local linear model",
    )
    model_score: float = Field(
        ge=0.0,
        le=1.0,
        default=0.0,
        description="R-squared score of local model fidelity",
    )

    @property
    def positive_contributors(self) -> list[tuple[str, float]]:
        """Get features that increased risk probability."""
        return [(f, c) for f, c in self.feature_contributions if c > 0]

    @property
    def negative_contributors(self) -> list[tuple[str, float]]:
        """Get features that decreased risk probability."""
        return [(f, c) for f, c in self.feature_contributions if c < 0]

    def explain_top_factors(self, n: int = 3) -> str:
        """Generate human-readable explanation of top factors.

        Args:
            n: Number of top factors to include

        Returns:
            Human-readable explanation string
        """
        sorted_contrib = sorted(
            self.feature_contributions,
            key=lambda x: abs(x[1]),
            reverse=True,
        )[:n]

        explanations = []
        for feature, contrib in sorted_contrib:
            direction = "increased" if contrib > 0 else "decreased"
            explanations.append(f"'{feature}' {direction} risk by {abs(contrib):.3f}")

        return "; ".join(explanations)

    def __str__(self) -> str:
        return f"LIME(local_pred={self.prediction_local:.3f}, fidelity={self.model_score:.3f})"


class RiskScore(BaseModel):
    """Value object representing the ML risk classification result.

    Contains the probability of exploitation, SHAP global explanation,
    and LIME local explanation. This is the output tuple from Phase 3
    that propagates to the LangGraph state.
    """

    model_config = ConfigDict(frozen=True)

    cve_id: str = Field(
        ...,
        description="CVE identifier for this classification",
    )
    risk_probability: Annotated[
        float,
        Field(ge=0.0, le=1.0, description="Probability of exploitation (0-1)"),
    ]
    risk_label: str = Field(
        ...,
        description="Risk classification label",
    )
    shap_values: SHAPValues | None = Field(
        default=None,
        description="SHAP feature importance values",
    )
    lime_explanation: LIMEExplanation | None = Field(
        default=None,
        description="LIME local explanation",
    )
    model_version: str = Field(
        default="1.0.0",
        description="Version of the ML model used",
    )
    classified_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp of classification",
    )
    confidence: Annotated[
        float,
        Field(ge=0.0, le=1.0, default=1.0, description="Model confidence in prediction"),
    ]

    @classmethod
    def from_prediction(
        cls,
        cve_id: str,
        probability: float,
        *,
        shap_values: SHAPValues | None = None,
        lime_explanation: LIMEExplanation | None = None,
        model_version: str = "1.0.0",
    ) -> RiskScore:
        """Create RiskScore from model prediction.

        Args:
            cve_id: CVE identifier
            probability: Predicted exploitation probability
            shap_values: Optional SHAP explanation
            lime_explanation: Optional LIME explanation
            model_version: Model version string

        Returns:
            RiskScore instance with appropriate label
        """
        # Determine risk label based on probability thresholds
        if probability >= RISK_PROBABILITY_CRITICAL_THRESHOLD:
            label = "CRITICAL"
        elif probability >= RISK_PROBABILITY_HIGH_THRESHOLD:
            label = "HIGH"
        elif probability >= RISK_PROBABILITY_MEDIUM_THRESHOLD:
            label = "MEDIUM"
        elif probability >= RISK_PROBABILITY_LOW_THRESHOLD:
            label = "LOW"
        else:
            label = "MINIMAL"

        # Calculate confidence based on how far from 0.5 the prediction is
        confidence = abs(probability - CONFIDENCE_CENTER_PROBABILITY) * CONFIDENCE_SCALE_FACTOR

        return cls(
            cve_id=cve_id,
            risk_probability=probability,
            risk_label=label,
            shap_values=shap_values,
            lime_explanation=lime_explanation,
            model_version=model_version,
            confidence=confidence,
        )

    @property
    def is_high_risk(self) -> bool:
        """Check if classified as high risk (>= 0.6)."""
        return self.risk_probability >= RISK_PROBABILITY_HIGH_THRESHOLD

    @property
    def requires_immediate_action(self) -> bool:
        """Check if requires immediate action (>= 0.8)."""
        return self.risk_probability >= RISK_PROBABILITY_CRITICAL_THRESHOLD

    def to_output_tuple(self) -> tuple[float, SHAPValues | None, LIMEExplanation | None]:
        """Return the output tuple for LangGraph state propagation.

        This is the format specified in the Phase 3 requirements:
        (risk_probability, shap_values, lime_explanation)
        """
        return (self.risk_probability, self.shap_values, self.lime_explanation)

    def __str__(self) -> str:
        return (
            f"RiskScore({self.cve_id}: {self.risk_label} "
            f"[{self.risk_probability:.3f}], confidence={self.confidence:.2f})"
        )


__all__ = [
    "LIMEExplanation",
    "RiskScore",
    "SHAPValues",
]
