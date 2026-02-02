"""Feature engineering for ML classification.

Extracts the 14-feature vector from enrichment data for XGBoost model.
Based on specification section 3.3.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import structlog

from siopv.domain.entities.ml_feature_vector import MLFeatureVector

if TYPE_CHECKING:
    from siopv.domain.entities import VulnerabilityRecord
    from siopv.domain.value_objects import EnrichmentData

logger = structlog.get_logger(__name__)


# CWE category target encoding values (pre-computed from training data)
# Common CWE categories and their average exploitation rates
CWE_TARGET_ENCODING: dict[str, float] = {
    # High risk CWEs (commonly exploited)
    "CWE-78": 0.85,  # OS Command Injection
    "CWE-79": 0.65,  # Cross-site Scripting
    "CWE-89": 0.80,  # SQL Injection
    "CWE-94": 0.82,  # Code Injection
    "CWE-119": 0.75,  # Buffer Overflow
    "CWE-120": 0.72,  # Buffer Copy without Size Check
    "CWE-125": 0.68,  # Out-of-bounds Read
    "CWE-190": 0.55,  # Integer Overflow
    "CWE-200": 0.45,  # Information Exposure
    "CWE-22": 0.70,  # Path Traversal
    "CWE-269": 0.78,  # Improper Privilege Management
    "CWE-287": 0.72,  # Authentication Bypass
    "CWE-306": 0.70,  # Missing Authentication
    "CWE-352": 0.55,  # Cross-Site Request Forgery
    "CWE-400": 0.40,  # Resource Exhaustion
    "CWE-416": 0.75,  # Use After Free
    "CWE-434": 0.80,  # Unrestricted File Upload
    "CWE-502": 0.78,  # Deserialization of Untrusted Data
    "CWE-611": 0.60,  # XXE
    "CWE-787": 0.72,  # Out-of-bounds Write
    "CWE-798": 0.65,  # Hard-coded Credentials
    "CWE-862": 0.68,  # Missing Authorization
    "CWE-863": 0.65,  # Incorrect Authorization
    "CWE-918": 0.70,  # SSRF
    # Default for unknown CWEs
    "DEFAULT": 0.35,
}


class FeatureEngineer:
    """Extracts ML features from vulnerability and enrichment data.

    Produces the 14-feature vector specified in the technical proposal:
    1. cvss_base_score (float 0-10)
    2. attack_vector (int 0-3)
    3. attack_complexity (int 0-1)
    4. privileges_required (int 0-2)
    5. user_interaction (int 0-1)
    6. scope (int 0-1)
    7. confidentiality_impact (int 0-2)
    8. integrity_impact (int 0-2)
    9. availability_impact (int 0-2)
    10. epss_score (float 0-1)
    11. epss_percentile (float 0-1)
    12. days_since_publication (int)
    13. has_exploit_ref (int 0-1)
    14. cwe_category (float, target encoded)
    """

    def __init__(
        self,
        cwe_encoding: dict[str, float] | None = None,
    ) -> None:
        """Initialize feature engineer.

        Args:
            cwe_encoding: Custom CWE target encoding mapping.
                         Uses defaults if not provided.
        """
        self._cwe_encoding = cwe_encoding or CWE_TARGET_ENCODING

    def extract_features(
        self,
        vulnerability: VulnerabilityRecord,
        enrichment: EnrichmentData,
    ) -> MLFeatureVector:
        """Extract feature vector from vulnerability and enrichment data.

        Args:
            vulnerability: VulnerabilityRecord from Phase 1
            enrichment: EnrichmentData from Phase 2

        Returns:
            MLFeatureVector ready for ML model
        """
        cve_id = vulnerability.cve_id.value

        logger.debug("extracting_features", cve_id=cve_id)

        # Extract CVSS base score
        cvss_base_score = self._extract_cvss_score(vulnerability, enrichment)

        # Extract CVSS vector components
        cvss_vector = self._extract_cvss_vector(enrichment)

        # Extract EPSS data
        epss_score, epss_percentile = self._extract_epss(enrichment)

        # Calculate days since publication
        days_since_publication = self._calculate_days_since_publication(enrichment)

        # Check for exploit references
        has_exploit_ref = self._check_exploit_references(enrichment)

        # Encode CWE category
        cwe_category = self._encode_cwe(enrichment)

        feature_vector = MLFeatureVector(
            cve_id=cve_id,
            cvss_base_score=cvss_base_score,
            attack_vector=cvss_vector.get("attack_vector", 0),
            attack_complexity=cvss_vector.get("attack_complexity", 0),
            privileges_required=cvss_vector.get("privileges_required", 0),
            user_interaction=cvss_vector.get("user_interaction", 0),
            scope=cvss_vector.get("scope", 0),
            confidentiality_impact=cvss_vector.get("confidentiality_impact", 0),
            integrity_impact=cvss_vector.get("integrity_impact", 0),
            availability_impact=cvss_vector.get("availability_impact", 0),
            epss_score=epss_score,
            epss_percentile=epss_percentile,
            days_since_publication=days_since_publication,
            has_exploit_ref=1 if has_exploit_ref else 0,
            cwe_category=cwe_category,
        )

        logger.info(
            "features_extracted",
            cve_id=cve_id,
            cvss=cvss_base_score,
            epss=epss_score,
            has_exploit=has_exploit_ref,
        )

        return feature_vector

    def extract_features_batch(
        self,
        vulnerabilities: list[VulnerabilityRecord],
        enrichments: dict[str, EnrichmentData],
    ) -> list[MLFeatureVector]:
        """Extract features for multiple vulnerabilities.

        Args:
            vulnerabilities: List of VulnerabilityRecord
            enrichments: Dictionary mapping CVE ID to EnrichmentData

        Returns:
            List of MLFeatureVector instances
        """
        feature_vectors = []

        for vuln in vulnerabilities:
            cve_id = vuln.cve_id.value
            enrichment = enrichments.get(cve_id)

            if enrichment is None:
                logger.warning("missing_enrichment", cve_id=cve_id)
                # Create minimal enrichment for missing data
                from siopv.domain.value_objects import EnrichmentData

                enrichment = EnrichmentData(cve_id=cve_id)

            feature_vector = self.extract_features(vuln, enrichment)
            feature_vectors.append(feature_vector)

        return feature_vectors

    def _extract_cvss_score(
        self,
        vulnerability: VulnerabilityRecord,
        enrichment: EnrichmentData,
    ) -> float:
        """Extract CVSS base score from available sources.

        Priority: NVD enrichment > Vulnerability record
        """
        # Try NVD enrichment first
        if enrichment.nvd and enrichment.nvd.cvss_v3_score is not None:
            return enrichment.nvd.cvss_v3_score

        # Fall back to vulnerability record
        if vulnerability.cvss_v3_score is not None:
            return float(vulnerability.cvss_v3_score.value)

        # Default to 0 if no score available
        logger.debug("no_cvss_score", cve_id=vulnerability.cve_id.value)
        return 0.0

    def _extract_cvss_vector(self, enrichment: EnrichmentData) -> dict[str, int]:
        """Extract CVSS vector components from enrichment."""
        if enrichment.nvd and enrichment.nvd.cvss_v3_vector:
            return enrichment.nvd.cvss_v3_vector.to_feature_dict()

        # Return default values if no vector available
        return {
            "attack_vector": 0,
            "attack_complexity": 0,
            "privileges_required": 0,
            "user_interaction": 0,
            "scope": 0,
            "confidentiality_impact": 0,
            "integrity_impact": 0,
            "availability_impact": 0,
        }

    def _extract_epss(self, enrichment: EnrichmentData) -> tuple[float, float]:
        """Extract EPSS score and percentile."""
        if enrichment.epss:
            return enrichment.epss.score, enrichment.epss.percentile

        return 0.0, 0.0

    def _calculate_days_since_publication(self, enrichment: EnrichmentData) -> int:
        """Calculate days since CVE publication."""
        if enrichment.nvd and enrichment.nvd.published_date:
            delta = datetime.now(UTC) - enrichment.nvd.published_date
            return max(0, delta.days)

        # Default to 0 if unknown
        return 0

    def _check_exploit_references(self, enrichment: EnrichmentData) -> bool:
        """Check if exploit references exist in enrichment data."""
        # Check NVD references
        if enrichment.nvd and enrichment.nvd.has_exploit_ref:
            return True

        # Check OSINT results for exploit keywords
        exploit_keywords = {"exploit", "poc", "proof of concept", "rce", "shell"}
        for osint in enrichment.osint_results:
            content_lower = osint.content.lower()
            if any(keyword in content_lower for keyword in exploit_keywords):
                return True

        return False

    def _encode_cwe(self, enrichment: EnrichmentData) -> float:
        """Target encode CWE category.

        Uses pre-computed target encoding based on historical exploitation rates.
        """
        if not enrichment.nvd or not enrichment.nvd.cwe_ids:
            return self._cwe_encoding.get("DEFAULT", 0.35)

        # Use the first CWE ID
        primary_cwe = enrichment.nvd.cwe_ids[0]

        # Return encoded value or default
        return self._cwe_encoding.get(primary_cwe, self._cwe_encoding.get("DEFAULT", 0.35))


__all__ = ["FeatureEngineer"]
