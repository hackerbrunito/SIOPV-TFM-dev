"""ML Feature Vector entity for risk classification.

Represents the 17-feature vector used by the XGBoost classifier.
Features: 9 CVSS metrics, 2 EPSS scores, 1 temporal, 3 binary
indicators (exploit ref, ExploitDB, Metasploit), 1 reference count,
1 CWE category (target encoded).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator


class MLFeatureVector(BaseModel):
    """Domain entity representing the feature vector for ML classification.

    Contains the 17 features used by the trained XGBoost model:
    - CVSS metrics (9 features)
    - EPSS data (2 features)
    - Temporal data (1 feature)
    - Binary indicators (3 features: exploit ref, ExploitDB, Metasploit)
    - Reference count (1 feature)
    - Categorical (1 feature, target encoded CWE)
    """

    model_config = ConfigDict(frozen=True)

    # Identifier
    cve_id: str = Field(..., description="CVE identifier")

    # === CVSS v3.1 Metrics (9 features) ===
    cvss_base_score: Annotated[
        float,
        Field(ge=0.0, le=10.0, description="CVSS v3 base score"),
    ]
    attack_vector: Annotated[
        int,
        Field(ge=0, le=3, description="AV: Network(3), Adjacent(2), Local(1), Physical(0)"),
    ]
    attack_complexity: Annotated[
        int,
        Field(ge=0, le=1, description="AC: Low(1), High(0)"),
    ]
    privileges_required: Annotated[
        int,
        Field(ge=0, le=2, description="PR: None(2), Low(1), High(0)"),
    ]
    user_interaction: Annotated[
        int,
        Field(ge=0, le=1, description="UI: None(1), Required(0)"),
    ]
    scope: Annotated[
        int,
        Field(ge=0, le=1, description="S: Changed(1), Unchanged(0)"),
    ]
    confidentiality_impact: Annotated[
        int,
        Field(ge=0, le=2, description="C: High(2), Low(1), None(0)"),
    ]
    integrity_impact: Annotated[
        int,
        Field(ge=0, le=2, description="I: High(2), Low(1), None(0)"),
    ]
    availability_impact: Annotated[
        int,
        Field(ge=0, le=2, description="A: High(2), Low(1), None(0)"),
    ]

    # === EPSS Data (2 features) ===
    epss_score: Annotated[
        float,
        Field(ge=0.0, le=1.0, description="EPSS probability of exploitation"),
    ]
    epss_percentile: Annotated[
        float,
        Field(ge=0.0, le=1.0, description="EPSS percentile ranking"),
    ]

    # === Temporal Data (1 feature) ===
    days_since_publication: Annotated[
        int,
        Field(ge=0, description="Days since CVE publication"),
    ]

    # === Binary Indicators (3 features) ===
    has_exploit_ref: Annotated[
        int,
        Field(ge=0, le=1, description="1 if exploit references exist, 0 otherwise"),
    ]
    has_public_exploit: Annotated[
        int,
        Field(ge=0, le=1, description="1 if ExploitDB reference exists, 0 otherwise"),
    ]
    has_metasploit: Annotated[
        int,
        Field(ge=0, le=1, description="1 if Metasploit module exists, 0 otherwise"),
    ]

    # === Reference count (1 feature) ===
    num_references: Annotated[
        int,
        Field(ge=0, description="Number of advisory/reference URLs"),
    ]

    # === Categorical (1 feature, target encoded) ===
    cwe_category: Annotated[
        float,
        Field(description="Target-encoded CWE category"),
    ]

    # Metadata
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when vector was created",
    )

    @field_validator("attack_vector", "attack_complexity", mode="before")
    @classmethod
    def coerce_int(cls, v: int | float) -> int:
        """Coerce numeric values to int."""
        if isinstance(v, float):
            return int(v)
        return v

    # Pydantic @computed_field + @property known mypy incompatibility
    @computed_field  # type: ignore[prop-decorator]
    @property
    def feature_names(self) -> list[str]:
        """Return ordered list of feature names for ML model."""
        return [
            "cvss_base_score",
            "attack_vector",
            "attack_complexity",
            "privileges_required",
            "user_interaction",
            "scope",
            "confidentiality_impact",
            "integrity_impact",
            "availability_impact",
            "epss_score",
            "epss_percentile",
            "days_since_publication",
            "has_exploit_ref",
            "has_public_exploit",
            "has_metasploit",
            "num_references",
            "cwe_category",
        ]

    def to_array(self) -> np.ndarray:
        """Convert to numpy array for model input.

        Returns:
            1D numpy array with 17 features in correct order
        """
        return np.array(
            [
                self.cvss_base_score,
                self.attack_vector,
                self.attack_complexity,
                self.privileges_required,
                self.user_interaction,
                self.scope,
                self.confidentiality_impact,
                self.integrity_impact,
                self.availability_impact,
                self.epss_score,
                self.epss_percentile,
                self.days_since_publication,
                self.has_exploit_ref,
                self.has_public_exploit,
                self.has_metasploit,
                self.num_references,
                self.cwe_category,
            ],
            dtype=np.float32,
        )

    def to_dict(self) -> dict[str, float]:
        """Convert to dictionary with feature names as keys.

        Returns:
            Dictionary mapping feature names to values
        """
        return dict(zip(self.feature_names, self.to_array().tolist(), strict=True))

    @classmethod
    def from_enrichment(
        cls,
        cve_id: str,
        *,
        cvss_base_score: float = 0.0,
        cvss_vector: dict[str, int] | None = None,
        epss_score: float = 0.0,
        epss_percentile: float = 0.0,
        days_since_publication: int = 0,
        has_exploit_ref: bool = False,
        has_public_exploit: bool = False,
        has_metasploit: bool = False,
        num_references: int = 0,
        cwe_category: float = 0.0,
    ) -> MLFeatureVector:
        """Create MLFeatureVector from enrichment data.

        Args:
            cve_id: CVE identifier
            cvss_base_score: CVSS v3 base score
            cvss_vector: Dictionary with CVSS vector components
            epss_score: EPSS probability
            epss_percentile: EPSS percentile
            days_since_publication: Days since CVE publication
            has_exploit_ref: Whether exploit references exist
            cwe_category: Target-encoded CWE category

        Returns:
            MLFeatureVector instance
        """
        # Default CVSS vector values
        vector = cvss_vector or {}

        return cls(
            cve_id=cve_id,
            cvss_base_score=cvss_base_score,
            attack_vector=vector.get("attack_vector", 0),
            attack_complexity=vector.get("attack_complexity", 0),
            privileges_required=vector.get("privileges_required", 0),
            user_interaction=vector.get("user_interaction", 0),
            scope=vector.get("scope", 0),
            confidentiality_impact=vector.get("confidentiality_impact", 0),
            integrity_impact=vector.get("integrity_impact", 0),
            availability_impact=vector.get("availability_impact", 0),
            epss_score=epss_score,
            epss_percentile=epss_percentile,
            days_since_publication=days_since_publication,
            has_exploit_ref=1 if has_exploit_ref else 0,
            has_public_exploit=1 if has_public_exploit else 0,
            has_metasploit=1 if has_metasploit else 0,
            num_references=num_references,
            cwe_category=cwe_category,
        )

    def __str__(self) -> str:
        return (
            f"MLFeatureVector({self.cve_id}: "
            f"CVSS={self.cvss_base_score:.1f}, "
            f"EPSS={self.epss_score:.4f}, "
            f"exploit={bool(self.has_exploit_ref)})"
        )


__all__ = ["MLFeatureVector"]
