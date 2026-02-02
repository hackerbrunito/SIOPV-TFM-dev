"""Domain entities for SIOPV."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from siopv.domain.value_objects import (
    CVEId,
    CVSSScore,
    LayerInfo,
    PackageVersion,
    SeverityLevel,
)


class VulnerabilityRecord(BaseModel):
    """Domain entity representing a vulnerability record from Trivy scan.

    This is the core domain model for CVE processing in the SIOPV pipeline.
    Each record represents a unique vulnerability found in a scanned artifact.
    """

    model_config = ConfigDict(frozen=True)

    # Required fields from specification
    cve_id: CVEId = Field(..., description="CVE identifier")
    package_name: str = Field(..., min_length=1, description="Name of the affected package")
    installed_version: PackageVersion = Field(..., description="Currently installed version")
    fixed_version: PackageVersion | None = Field(
        default=None, description="Version that fixes the vulnerability"
    )
    severity: SeverityLevel = Field(..., description="Severity level of the vulnerability")
    cvss_v3_score: CVSSScore | None = Field(default=None, description="CVSS v3 score (0.0-10.0)")

    # Additional context fields from Trivy
    title: str | None = Field(default=None, description="Short vulnerability title")
    description: str | None = Field(default=None, description="Full vulnerability description")
    primary_url: str | None = Field(default=None, description="Primary reference URL")
    target: str | None = Field(default=None, description="Scan target (image, filesystem, etc.)")
    layer: LayerInfo | None = Field(default=None, description="Docker layer information")

    # Metadata for deduplication tracking
    locations: Annotated[
        list[str], Field(default_factory=list, description="All locations where this CVE was found")
    ]
    first_seen: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="First detection timestamp"
    )

    @field_validator("severity", mode="before")
    @classmethod
    def normalize_severity(cls, v: str) -> str:
        """Normalize severity to uppercase."""
        if isinstance(v, str):
            normalized = v.upper()
            if normalized not in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN"):
                return "UNKNOWN"
            return normalized
        return v

    @classmethod
    def from_trivy(cls, vuln_data: dict, target: str | None = None) -> VulnerabilityRecord:
        """Create VulnerabilityRecord from Trivy vulnerability data.

        Args:
            vuln_data: Dictionary from Trivy Results[].Vulnerabilities[] item
            target: The scan target name

        Returns:
            VulnerabilityRecord instance
        """
        # Extract CVSS v3 score from nested structure
        cvss_score = None
        cvss_data = vuln_data.get("CVSS", {})
        for source in ("nvd", "ghsa", "redhat", "debian"):
            if source in cvss_data and "V3Score" in cvss_data[source]:
                cvss_score = cvss_data[source]["V3Score"]
                break

        # Extract layer info
        layer_info = LayerInfo.from_trivy(vuln_data.get("Layer"))

        # Build package path for location tracking
        pkg_path = vuln_data.get("PkgPath", "")
        location = (
            pkg_path
            if pkg_path
            else f"{vuln_data.get('PkgName', '')}@{vuln_data.get('InstalledVersion', '')}"
        )

        return cls(
            cve_id=CVEId(value=vuln_data["VulnerabilityID"]),
            package_name=vuln_data.get("PkgName", ""),
            installed_version=PackageVersion(value=vuln_data.get("InstalledVersion", "")),
            fixed_version=(
                PackageVersion(value=vuln_data["FixedVersion"])
                if vuln_data.get("FixedVersion")
                else None
            ),
            severity=vuln_data.get("Severity", "UNKNOWN"),
            cvss_v3_score=CVSSScore(value=cvss_score) if cvss_score is not None else None,
            title=vuln_data.get("Title"),
            description=vuln_data.get("Description"),
            primary_url=vuln_data.get("PrimaryURL"),
            target=target,
            layer=layer_info,
            locations=[location] if location else [],
        )

    @property
    def dedup_key(self) -> tuple[str, str, str]:
        """Return the deduplication key tuple (cve_id, package_name, installed_version)."""
        return (
            self.cve_id.value,
            self.package_name,
            self.installed_version.value,
        )

    def merge_location(self, other_location: str) -> VulnerabilityRecord:
        """Create a new record with an additional location merged.

        Since the model is frozen, this returns a new instance.
        """
        if other_location and other_location not in self.locations:
            new_locations = [*self.locations, other_location]
            return self.model_copy(update={"locations": new_locations})
        return self


# Phase 3 - ML Classification
from siopv.domain.entities.ml_feature_vector import MLFeatureVector

__all__ = [
    # Phase 1 - Ingestion
    "VulnerabilityRecord",
    # Phase 3 - ML Classification
    "MLFeatureVector",
]
