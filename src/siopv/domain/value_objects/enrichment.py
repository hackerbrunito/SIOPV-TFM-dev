"""Value objects for vulnerability enrichment data.

These represent enriched context from external sources:
- NVD (National Vulnerability Database)
- GitHub Security Advisories
- FIRST EPSS (Exploit Prediction Scoring System)
- OSINT search results
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from siopv.domain.constants import (
    EPSS_HIGH_RISK_THRESHOLD,
    RELEVANCE_SCORE_OSINT_FALLBACK_THRESHOLD,
)


class EPSSScore(BaseModel):
    """Value object representing EPSS (Exploit Prediction Scoring System) data.

    EPSS provides probability of exploitation in the next 30 days.
    Updated daily by FIRST.org.
    """

    model_config = ConfigDict(frozen=True)

    score: Annotated[
        float,
        Field(ge=0.0, le=1.0, description="Probability of exploitation (0-1)"),
    ]
    percentile: Annotated[
        float,
        Field(ge=0.0, le=1.0, description="Percentile ranking relative to all CVEs"),
    ]
    date: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Date when EPSS score was retrieved",
    )

    @classmethod
    def from_api_response(cls, data: dict[str, str]) -> EPSSScore:
        """Create EPSSScore from FIRST EPSS API response.

        Args:
            data: Dictionary with 'epss' and 'percentile' keys

        Returns:
            EPSSScore instance
        """
        return cls(
            score=float(data["epss"]),
            percentile=float(data["percentile"]),
        )

    @property
    def is_high_risk(self) -> bool:
        """Check if EPSS score indicates high exploitation risk (>0.1)."""
        return self.score > EPSS_HIGH_RISK_THRESHOLD

    def __str__(self) -> str:
        return f"EPSS: {self.score:.4f} (percentile: {self.percentile:.2%})"


class CVSSVector(BaseModel):
    """Value object representing CVSS v3.1 vector components.

    Used for ML feature extraction in Phase 3.
    """

    model_config = ConfigDict(frozen=True)

    # Base metrics
    attack_vector: Annotated[
        str,
        Field(description="AV: Network(N), Adjacent(A), Local(L), Physical(P)"),
    ]
    attack_complexity: Annotated[
        str,
        Field(description="AC: Low(L), High(H)"),
    ]
    privileges_required: Annotated[
        str,
        Field(description="PR: None(N), Low(L), High(H)"),
    ]
    user_interaction: Annotated[
        str,
        Field(description="UI: None(N), Required(R)"),
    ]
    scope: Annotated[
        str,
        Field(description="S: Unchanged(U), Changed(C)"),
    ]
    confidentiality_impact: Annotated[
        str,
        Field(description="C: None(N), Low(L), High(H)"),
    ]
    integrity_impact: Annotated[
        str,
        Field(description="I: None(N), Low(L), High(H)"),
    ]
    availability_impact: Annotated[
        str,
        Field(description="A: None(N), Low(L), High(H)"),
    ]

    @field_validator(
        "attack_vector",
        "attack_complexity",
        "privileges_required",
        "user_interaction",
        "scope",
        "confidentiality_impact",
        "integrity_impact",
        "availability_impact",
        mode="before",
    )
    @classmethod
    def normalize_to_uppercase(cls, v: str) -> str:
        """Normalize CVSS metric values to uppercase."""
        return v.upper() if isinstance(v, str) else v

    @classmethod
    def from_vector_string(cls, vector: str) -> CVSSVector | None:
        """Parse CVSS v3.1 vector string.

        Args:
            vector: CVSS vector string, e.g., "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"

        Returns:
            CVSSVector instance or None if parsing fails
        """
        if not vector or "CVSS:3" not in vector:
            return None

        metrics: dict[str, str] = {}
        parts = vector.split("/")

        for part in parts:
            if ":" in part and part.startswith(
                ("AV:", "AC:", "PR:", "UI:", "S:", "C:", "I:", "A:")
            ):
                key, value = part.split(":", 1)
                metrics[key] = value

        required_keys = {"AV", "AC", "PR", "UI", "S", "C", "I", "A"}
        if not required_keys.issubset(metrics.keys()):
            return None

        return cls(
            attack_vector=metrics["AV"],
            attack_complexity=metrics["AC"],
            privileges_required=metrics["PR"],
            user_interaction=metrics["UI"],
            scope=metrics["S"],
            confidentiality_impact=metrics["C"],
            integrity_impact=metrics["I"],
            availability_impact=metrics["A"],
        )

    def to_feature_dict(self) -> dict[str, int]:
        """Convert to numeric features for ML model.

        Returns:
            Dictionary with encoded feature values
        """
        av_map = {"N": 3, "A": 2, "L": 1, "P": 0}
        ac_map = {"L": 1, "H": 0}
        pr_map = {"N": 2, "L": 1, "H": 0}
        ui_map = {"N": 1, "R": 0}
        scope_map = {"C": 1, "U": 0}
        impact_map = {"H": 2, "L": 1, "N": 0}

        return {
            "attack_vector": av_map.get(self.attack_vector, 0),
            "attack_complexity": ac_map.get(self.attack_complexity, 0),
            "privileges_required": pr_map.get(self.privileges_required, 0),
            "user_interaction": ui_map.get(self.user_interaction, 0),
            "scope": scope_map.get(self.scope, 0),
            "confidentiality_impact": impact_map.get(self.confidentiality_impact, 0),
            "integrity_impact": impact_map.get(self.integrity_impact, 0),
            "availability_impact": impact_map.get(self.availability_impact, 0),
        }


class NVDEnrichment(BaseModel):
    """Value object representing enrichment data from NVD API.

    Contains detailed CVE information from the National Vulnerability Database.
    """

    model_config = ConfigDict(frozen=True)

    cve_id: str = Field(..., description="CVE identifier")
    description: str | None = Field(default=None, description="Full CVE description")
    cvss_v3_score: float | None = Field(default=None, ge=0.0, le=10.0)
    cvss_v3_vector: CVSSVector | None = Field(default=None)
    published_date: datetime | None = Field(default=None)
    last_modified_date: datetime | None = Field(default=None)
    references: list[str] = Field(default_factory=list, description="Reference URLs")
    cwe_ids: list[str] = Field(default_factory=list, description="CWE identifiers")
    has_exploit_ref: bool = Field(
        default=False,
        description="Whether any reference indicates exploit availability",
    )

    @classmethod
    def from_nvd_response(cls, data: dict[str, Any]) -> NVDEnrichment:
        """Create NVDEnrichment from NVD API 2.0 response.

        Args:
            data: CVE item from NVD API response

        Returns:
            NVDEnrichment instance
        """
        cve_data = data.get("cve", data)
        cve_id = cve_data.get("id", "")

        # Extract description (prefer English)
        description = None
        descriptions = cve_data.get("descriptions", [])
        for desc in descriptions:
            if desc.get("lang") == "en":
                description = desc.get("value")
                break

        # Extract CVSS v3 metrics
        cvss_score = None
        cvss_vector = None
        metrics = cve_data.get("metrics", {})
        cvss_v31 = metrics.get("cvssMetricV31", [])
        if cvss_v31:
            primary = cvss_v31[0].get("cvssData", {})
            cvss_score = primary.get("baseScore")
            vector_string = primary.get("vectorString")
            if vector_string:
                cvss_vector = CVSSVector.from_vector_string(vector_string)

        # Extract dates
        published = cve_data.get("published")
        modified = cve_data.get("lastModified")

        # Extract references and check for exploit tags
        references = []
        has_exploit = False
        for ref in cve_data.get("references", []):
            url = ref.get("url", "")
            if url:
                references.append(url)
            tags = ref.get("tags", [])
            if "Exploit" in tags or "Third Party Advisory" in tags:
                has_exploit = True

        # Extract CWE IDs
        cwe_ids = []
        weaknesses = cve_data.get("weaknesses", [])
        for weakness in weaknesses:
            for desc in weakness.get("description", []):
                cwe_value = desc.get("value", "")
                if cwe_value.startswith("CWE-"):
                    cwe_ids.append(cwe_value)

        return cls(
            cve_id=cve_id,
            description=description,
            cvss_v3_score=cvss_score,
            cvss_v3_vector=cvss_vector,
            published_date=datetime.fromisoformat(published.replace("Z", "+00:00"))
            if published
            else None,
            last_modified_date=datetime.fromisoformat(modified.replace("Z", "+00:00"))
            if modified
            else None,
            references=references,
            cwe_ids=cwe_ids,
            has_exploit_ref=has_exploit,
        )

    @property
    def days_since_publication(self) -> int | None:
        """Calculate days since CVE was published."""
        if not self.published_date:
            return None
        delta = datetime.now(UTC) - self.published_date
        return delta.days


class GitHubAdvisory(BaseModel):
    """Value object representing GitHub Security Advisory data."""

    model_config = ConfigDict(frozen=True)

    ghsa_id: str = Field(..., description="GitHub Security Advisory ID")
    cve_id: str | None = Field(default=None, description="Associated CVE ID")
    summary: str | None = Field(default=None, description="Advisory summary")
    severity: str | None = Field(default=None, description="Severity level")
    published_at: datetime | None = Field(default=None)
    updated_at: datetime | None = Field(default=None)
    vulnerable_version_range: str | None = Field(default=None, description="Affected version range")
    patched_versions: list[str] = Field(default_factory=list, description="Versions with fix")
    package_ecosystem: str | None = Field(
        default=None, description="Package ecosystem (npm, pip, etc.)"
    )
    package_name: str | None = Field(default=None, description="Affected package name")

    @classmethod
    def from_graphql_response(cls, data: dict[str, Any]) -> GitHubAdvisory:
        """Create GitHubAdvisory from GitHub GraphQL API response.

        Args:
            data: SecurityAdvisory node from GraphQL response

        Returns:
            GitHubAdvisory instance
        """
        # Extract identifiers
        ghsa_id = data.get("ghsaId", "")
        identifiers = data.get("identifiers", [])
        cve_id = None
        for ident in identifiers:
            if ident.get("type") == "CVE":
                cve_id = ident.get("value")
                break

        # Extract package info from vulnerabilities
        vulnerable_range = None
        patched = []
        ecosystem = None
        pkg_name = None

        vulnerabilities = data.get("vulnerabilities", {}).get("nodes", [])
        if vulnerabilities:
            vuln = vulnerabilities[0]
            pkg = vuln.get("package", {})
            ecosystem = pkg.get("ecosystem")
            pkg_name = pkg.get("name")
            vulnerable_range = vuln.get("vulnerableVersionRange")

            first_patched = vuln.get("firstPatchedVersion", {})
            if first_patched and first_patched.get("identifier"):
                patched.append(first_patched["identifier"])

        # Parse dates
        published = data.get("publishedAt")
        updated = data.get("updatedAt")

        return cls(
            ghsa_id=ghsa_id,
            cve_id=cve_id,
            summary=data.get("summary"),
            severity=data.get("severity"),
            published_at=datetime.fromisoformat(published.replace("Z", "+00:00"))
            if published
            else None,
            updated_at=datetime.fromisoformat(updated.replace("Z", "+00:00")) if updated else None,
            vulnerable_version_range=vulnerable_range,
            patched_versions=patched,
            package_ecosystem=ecosystem,
            package_name=pkg_name,
        )


class OSINTResult(BaseModel):
    """Value object representing OSINT search result from Tavily."""

    model_config = ConfigDict(frozen=True)

    title: str = Field(..., description="Result title")
    url: str = Field(..., description="Result URL")
    content: str = Field(..., description="Result snippet/content")
    score: float = Field(ge=0.0, le=1.0, description="Relevance score")
    published_date: str | None = Field(default=None)

    @classmethod
    def from_tavily_result(cls, data: dict[str, Any]) -> OSINTResult:
        """Create OSINTResult from Tavily API response item."""
        return cls(
            title=data.get("title", ""),
            url=data.get("url", ""),
            content=data.get("content", ""),
            score=data.get("score", 0.0),
            published_date=data.get("published_date"),
        )


class EnrichmentData(BaseModel):
    """Aggregated enrichment data for a vulnerability.

    Combines data from all enrichment sources for pipeline processing.
    """

    model_config = ConfigDict(frozen=True)

    cve_id: str = Field(..., description="CVE identifier")
    nvd: NVDEnrichment | None = Field(default=None, description="NVD enrichment data")
    epss: EPSSScore | None = Field(default=None, description="EPSS score data")
    github_advisory: GitHubAdvisory | None = Field(
        default=None, description="GitHub Security Advisory"
    )
    osint_results: list[OSINTResult] = Field(
        default_factory=list, description="OSINT search results"
    )
    enriched_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp of enrichment",
    )
    relevance_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="CRAG relevance score for retrieved documents",
    )

    @property
    def is_enriched(self) -> bool:
        """Check if any enrichment data is available."""
        return self.nvd is not None or self.epss is not None

    @property
    def needs_osint_fallback(self) -> bool:
        """Check if OSINT fallback should be triggered (relevance < 0.6)."""
        return self.relevance_score < RELEVANCE_SCORE_OSINT_FALLBACK_THRESHOLD

    def to_embedding_text(self) -> str:
        """Generate text representation for embedding.

        Used for ChromaDB vector storage.
        """
        parts = [f"CVE: {self.cve_id}"]

        if self.nvd:
            if self.nvd.description:
                parts.append(f"Description: {self.nvd.description}")
            if self.nvd.cwe_ids:
                parts.append(f"CWE: {', '.join(self.nvd.cwe_ids)}")

        if self.epss:
            parts.append(f"EPSS Score: {self.epss.score:.4f}")

        if self.github_advisory and self.github_advisory.summary:
            parts.append(f"Advisory: {self.github_advisory.summary}")

        return "\n".join(parts)


__all__ = [
    "CVSSVector",
    "EPSSScore",
    "EnrichmentData",
    "GitHubAdvisory",
    "NVDEnrichment",
    "OSINTResult",
]
