"""Domain value objects for SIOPV."""

from __future__ import annotations

import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from siopv.domain.value_objects.discrepancy import (
    DiscrepancyHistory,
    DiscrepancyResult,
    ThresholdConfig,
)
from siopv.domain.value_objects.enrichment import (
    CVSSVector,
    EnrichmentData,
    EPSSScore,
    GitHubAdvisory,
    NVDEnrichment,
    OSINTResult,
)
from siopv.domain.value_objects.escalation import EscalationConfig
from siopv.domain.value_objects.risk_score import (
    LIMEExplanation,
    RiskScore,
    SHAPValues,
)

# Severity levels as defined in the specification
SeverityLevel = Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN"]

# CVE ID pattern: CVE-YYYY-NNNNN (4+ digits for year, variable for ID)
CVE_PATTERN = re.compile(r"^CVE-\d{4}-\d+$")


class CVEId(BaseModel):
    """Value object representing a CVE identifier.

    Format: CVE-YYYY-NNNNN where YYYY is the year and NNNNN is a numeric ID.
    """

    model_config = ConfigDict(frozen=True)

    value: str = Field(..., description="CVE identifier in format CVE-YYYY-NNNNN")

    @field_validator("value")
    @classmethod
    def validate_cve_format(cls, v: str) -> str:
        """Validate CVE ID format."""
        if not CVE_PATTERN.match(v):
            msg = f"Invalid CVE ID format: {v}. Expected CVE-YYYY-NNNNN"
            raise ValueError(msg)
        return v

    def __str__(self) -> str:
        return self.value

    def __hash__(self) -> int:
        return hash(self.value)


def validate_cve_id(cve_id: str) -> str:
    """Validate CVE ID format and return the validated string.

    Args:
        cve_id: CVE identifier to validate

    Returns:
        The validated CVE ID string

    Raises:
        ValueError: If cve_id does not match CVE-YYYY-NNNNN format
    """
    if not CVE_PATTERN.match(cve_id):
        msg = f"Invalid CVE ID format: {cve_id}. Expected CVE-YYYY-NNNNN"
        raise ValueError(msg)
    return cve_id


class CVSSScore(BaseModel):
    """Value object representing a CVSS v3 score.

    Score must be between 0.0 and 10.0.
    """

    model_config = ConfigDict(frozen=True)

    value: Annotated[float, Field(ge=0.0, le=10.0, description="CVSS v3 score (0.0-10.0)")]

    @classmethod
    def from_float(cls, score: float | None) -> CVSSScore | None:
        """Create CVSSScore from float, returning None if input is None."""
        if score is None:
            return None
        return cls(value=score)

    def __str__(self) -> str:
        return f"{self.value:.1f}"

    def __float__(self) -> float:
        return self.value


class PackageVersion(BaseModel):
    """Value object representing a package version string."""

    model_config = ConfigDict(frozen=True)

    value: str = Field(..., min_length=1, description="Package version string")

    def __str__(self) -> str:
        return self.value


class LayerInfo(BaseModel):
    """Value object representing Docker layer information."""

    model_config = ConfigDict(frozen=True)

    digest: str | None = Field(default=None, description="Layer digest (sha256)")
    diff_id: str | None = Field(default=None, description="Layer diff ID")

    @classmethod
    def from_trivy(cls, layer_data: dict[str, str] | None) -> LayerInfo | None:
        """Create LayerInfo from Trivy layer data."""
        if not layer_data:
            return None
        return cls(
            digest=layer_data.get("Digest"),
            diff_id=layer_data.get("DiffID"),
        )


__all__ = [
    "CVEId",
    "CVSSScore",
    "CVSSVector",
    "DiscrepancyHistory",
    "DiscrepancyResult",
    "EPSSScore",
    "EnrichmentData",
    "EscalationConfig",
    "GitHubAdvisory",
    "LIMEExplanation",
    "LayerInfo",
    "NVDEnrichment",
    "OSINTResult",
    "PackageVersion",
    "RiskScore",
    "SHAPValues",
    "SeverityLevel",
    "ThresholdConfig",
    "validate_cve_id",
]
