"""Unit tests for FeatureEngineer.

Tests the feature extraction logic for ML classification including:
- Single feature extraction from vulnerability and enrichment data
- Batch feature extraction for multiple vulnerabilities
- CVSS vector parsing and encoding
- EPSS score extraction
- CWE target encoding
- Exploit reference detection
- Edge cases with missing data
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import pytest

from siopv.adapters.ml.feature_engineer import (
    CWE_TARGET_ENCODING,
    FeatureEngineer,
)
from siopv.domain.entities import VulnerabilityRecord
from siopv.domain.entities.ml_feature_vector import MLFeatureVector
from siopv.domain.value_objects import (
    CVEId,
    CVSSScore,
    CVSSVector,
    EnrichmentData,
    EPSSScore,
    NVDEnrichment,
    OSINTResult,
    PackageVersion,
)

# === Fixtures ===


@pytest.fixture
def feature_engineer() -> FeatureEngineer:
    """Create a FeatureEngineer instance with default encoding."""
    return FeatureEngineer()


@pytest.fixture
def custom_cwe_encoding() -> dict[str, float]:
    """Create custom CWE target encoding for testing."""
    return {
        "CWE-79": 0.70,
        "CWE-89": 0.85,
        "DEFAULT": 0.30,
    }


@pytest.fixture
def sample_vulnerability() -> VulnerabilityRecord:
    """Create a sample vulnerability record for testing."""
    return VulnerabilityRecord(
        cve_id=CVEId(value="CVE-2021-44228"),
        package_name="log4j-core",
        installed_version=PackageVersion(value="2.14.0"),
        fixed_version=PackageVersion(value="2.17.0"),
        severity="CRITICAL",
        cvss_v3_score=CVSSScore(value=10.0),
        title="Log4Shell RCE",
        description="Remote code execution in Apache Log4j",
        primary_url="https://nvd.nist.gov/vuln/detail/CVE-2021-44228",
    )


@pytest.fixture
def sample_cvss_vector() -> CVSSVector:
    """Create a sample CVSS vector for testing."""
    return CVSSVector(
        attack_vector="N",
        attack_complexity="L",
        privileges_required="N",
        user_interaction="N",
        scope="C",
        confidentiality_impact="H",
        integrity_impact="H",
        availability_impact="H",
    )


@pytest.fixture
def sample_epss() -> EPSSScore:
    """Create a sample EPSS score for testing."""
    return EPSSScore(
        score=0.975,
        percentile=0.999,
    )


@pytest.fixture
def sample_nvd_enrichment(sample_cvss_vector: CVSSVector) -> NVDEnrichment:
    """Create a sample NVD enrichment for testing."""
    return NVDEnrichment(
        cve_id="CVE-2021-44228",
        description="Apache Log4j2 JNDI injection vulnerability",
        cvss_v3_score=10.0,
        cvss_v3_vector=sample_cvss_vector,
        published_date=datetime.now(UTC) - timedelta(days=365),
        cwe_ids=["CWE-502", "CWE-400"],
        has_exploit_ref=True,
        references=["https://example.com/exploit"],
    )


@pytest.fixture
def sample_enrichment(
    sample_nvd_enrichment: NVDEnrichment,
    sample_epss: EPSSScore,
) -> EnrichmentData:
    """Create a sample enrichment data for testing."""
    return EnrichmentData(
        cve_id="CVE-2021-44228",
        nvd=sample_nvd_enrichment,
        epss=sample_epss,
        osint_results=[],
    )


@pytest.fixture
def minimal_enrichment() -> EnrichmentData:
    """Create minimal enrichment data with only CVE ID."""
    return EnrichmentData(cve_id="CVE-2021-44228")


# === Test FeatureEngineer Initialization ===


class TestFeatureEngineerInit:
    """Tests for FeatureEngineer initialization."""

    def test_init_with_default_encoding(self) -> None:
        """Test initialization with default CWE encoding."""
        engineer = FeatureEngineer()
        assert engineer._cwe_encoding == CWE_TARGET_ENCODING

    def test_init_with_custom_encoding(self, custom_cwe_encoding: dict[str, float]) -> None:
        """Test initialization with custom CWE encoding."""
        engineer = FeatureEngineer(cwe_encoding=custom_cwe_encoding)
        assert engineer._cwe_encoding == custom_cwe_encoding
        assert engineer._cwe_encoding["CWE-79"] == 0.70


# === Test Single Feature Extraction ===


class TestExtractFeatures:
    """Tests for extract_features method."""

    def test_extract_features_full_data(
        self,
        feature_engineer: FeatureEngineer,
        sample_vulnerability: VulnerabilityRecord,
        sample_enrichment: EnrichmentData,
    ) -> None:
        """Test feature extraction with complete data."""
        result = feature_engineer.extract_features(sample_vulnerability, sample_enrichment)

        assert isinstance(result, MLFeatureVector)
        assert result.cve_id == "CVE-2021-44228"
        assert result.cvss_base_score == 10.0
        assert result.epss_score == 0.975
        assert result.epss_percentile == 0.999
        assert result.has_exploit_ref == 1

    def test_extract_features_cvss_vector_encoding(
        self,
        feature_engineer: FeatureEngineer,
        sample_vulnerability: VulnerabilityRecord,
        sample_enrichment: EnrichmentData,
    ) -> None:
        """Test CVSS vector is correctly encoded to numeric values."""
        result = feature_engineer.extract_features(sample_vulnerability, sample_enrichment)

        # N=3, A=2, L=1, P=0
        assert result.attack_vector == 3  # Network
        # L=1, H=0
        assert result.attack_complexity == 1  # Low
        # N=2, L=1, H=0
        assert result.privileges_required == 2  # None
        # N=1, R=0
        assert result.user_interaction == 1  # None
        # C=1, U=0
        assert result.scope == 1  # Changed
        # H=2, L=1, N=0
        assert result.confidentiality_impact == 2  # High
        assert result.integrity_impact == 2  # High
        assert result.availability_impact == 2  # High

    def test_extract_features_days_since_publication(
        self,
        feature_engineer: FeatureEngineer,
        sample_vulnerability: VulnerabilityRecord,
        sample_enrichment: EnrichmentData,
    ) -> None:
        """Test days since publication calculation."""
        result = feature_engineer.extract_features(sample_vulnerability, sample_enrichment)

        # Should be approximately 365 days (fixture sets 365 days ago)
        assert 360 <= result.days_since_publication <= 370

    def test_extract_features_cwe_encoding(
        self,
        feature_engineer: FeatureEngineer,
        sample_vulnerability: VulnerabilityRecord,
        sample_enrichment: EnrichmentData,
    ) -> None:
        """Test CWE target encoding."""
        result = feature_engineer.extract_features(sample_vulnerability, sample_enrichment)

        # CWE-502 (Deserialization) has encoding 0.78
        expected_cwe = CWE_TARGET_ENCODING.get("CWE-502", CWE_TARGET_ENCODING["DEFAULT"])
        assert result.cwe_category == expected_cwe

    def test_extract_features_minimal_enrichment(
        self,
        feature_engineer: FeatureEngineer,
        sample_vulnerability: VulnerabilityRecord,
        minimal_enrichment: EnrichmentData,
    ) -> None:
        """Test feature extraction with minimal enrichment data."""
        result = feature_engineer.extract_features(sample_vulnerability, minimal_enrichment)

        assert result.cve_id == "CVE-2021-44228"
        # Should fall back to vulnerability record CVSS
        assert result.cvss_base_score == 10.0
        # EPSS should be 0 when not available
        assert result.epss_score == 0.0
        assert result.epss_percentile == 0.0
        # No exploit references
        assert result.has_exploit_ref == 0
        # Default CWE encoding
        assert result.cwe_category == CWE_TARGET_ENCODING["DEFAULT"]

    def test_extract_features_exploit_in_osint(
        self,
        feature_engineer: FeatureEngineer,
        sample_vulnerability: VulnerabilityRecord,
    ) -> None:
        """Test exploit detection from OSINT results."""
        osint_result = OSINTResult(
            title="PoC Exploit for CVE-2021-44228",
            url="https://github.com/example/exploit",
            content="This is a proof of concept exploit for Log4Shell",
            score=0.95,
        )
        enrichment = EnrichmentData(
            cve_id="CVE-2021-44228",
            osint_results=[osint_result],
        )

        result = feature_engineer.extract_features(sample_vulnerability, enrichment)

        assert result.has_exploit_ref == 1

    def test_extract_features_no_cvss_score(
        self,
        feature_engineer: FeatureEngineer,
    ) -> None:
        """Test feature extraction when no CVSS score is available."""
        vuln = VulnerabilityRecord(
            cve_id=CVEId(value="CVE-2021-99999"),
            package_name="unknown-package",
            installed_version=PackageVersion(value="1.0.0"),
            severity="UNKNOWN",
            cvss_v3_score=None,
        )
        enrichment = EnrichmentData(cve_id="CVE-2021-99999")

        result = feature_engineer.extract_features(vuln, enrichment)

        assert result.cvss_base_score == 0.0

    def test_extract_features_returns_valid_array(
        self,
        feature_engineer: FeatureEngineer,
        sample_vulnerability: VulnerabilityRecord,
        sample_enrichment: EnrichmentData,
    ) -> None:
        """Test that extracted features can be converted to valid array."""
        result = feature_engineer.extract_features(sample_vulnerability, sample_enrichment)

        array = result.to_array()
        assert isinstance(array, np.ndarray)
        assert array.shape == (14,)
        assert array.dtype == np.float32
        assert not np.any(np.isnan(array))


# === Test Batch Feature Extraction ===


class TestExtractFeaturesBatch:
    """Tests for extract_features_batch method."""

    def test_extract_features_batch_basic(
        self,
        feature_engineer: FeatureEngineer,
    ) -> None:
        """Test batch extraction with multiple vulnerabilities."""
        # Create 3 vulnerabilities
        vulns = [
            VulnerabilityRecord(
                cve_id=CVEId(value=f"CVE-2021-{i:05d}"),
                package_name=f"package-{i}",
                installed_version=PackageVersion(value="1.0.0"),
                severity="HIGH",
                cvss_v3_score=CVSSScore(value=7.5 + i * 0.5),
            )
            for i in range(3)
        ]

        # Create enrichments for each
        enrichments = {
            "CVE-2021-00000": EnrichmentData(
                cve_id="CVE-2021-00000",
                epss=EPSSScore(score=0.5, percentile=0.7),
            ),
            "CVE-2021-00001": EnrichmentData(
                cve_id="CVE-2021-00001",
                epss=EPSSScore(score=0.6, percentile=0.8),
            ),
            "CVE-2021-00002": EnrichmentData(
                cve_id="CVE-2021-00002",
                epss=EPSSScore(score=0.7, percentile=0.9),
            ),
        }

        results = feature_engineer.extract_features_batch(vulns, enrichments)

        assert len(results) == 3
        assert all(isinstance(r, MLFeatureVector) for r in results)
        assert results[0].cve_id == "CVE-2021-00000"
        assert results[1].cve_id == "CVE-2021-00001"
        assert results[2].cve_id == "CVE-2021-00002"

    def test_extract_features_batch_missing_enrichment(
        self,
        feature_engineer: FeatureEngineer,
    ) -> None:
        """Test batch extraction handles missing enrichment gracefully."""
        vulns = [
            VulnerabilityRecord(
                cve_id=CVEId(value="CVE-2021-11111"),
                package_name="package-a",
                installed_version=PackageVersion(value="1.0.0"),
                severity="HIGH",
                cvss_v3_score=CVSSScore(value=8.0),
            ),
            VulnerabilityRecord(
                cve_id=CVEId(value="CVE-2021-22222"),
                package_name="package-b",
                installed_version=PackageVersion(value="2.0.0"),
                severity="MEDIUM",
                cvss_v3_score=CVSSScore(value=5.0),
            ),
        ]

        # Only provide enrichment for one CVE
        enrichments = {
            "CVE-2021-11111": EnrichmentData(
                cve_id="CVE-2021-11111",
                epss=EPSSScore(score=0.8, percentile=0.9),
            ),
            # CVE-2021-22222 is missing
        }

        results = feature_engineer.extract_features_batch(vulns, enrichments)

        assert len(results) == 2
        # First CVE has enrichment
        assert results[0].epss_score == 0.8
        # Second CVE should have default values (missing enrichment)
        assert results[1].epss_score == 0.0

    def test_extract_features_batch_empty_list(
        self,
        feature_engineer: FeatureEngineer,
    ) -> None:
        """Test batch extraction with empty vulnerability list."""
        results = feature_engineer.extract_features_batch([], {})
        assert results == []

    def test_extract_features_batch_preserves_order(
        self,
        feature_engineer: FeatureEngineer,
    ) -> None:
        """Test that batch extraction preserves vulnerability order."""
        cve_ids = [f"CVE-2021-{i:05d}" for i in range(10)]
        vulns = [
            VulnerabilityRecord(
                cve_id=CVEId(value=cve_id),
                package_name=f"pkg-{i}",
                installed_version=PackageVersion(value="1.0.0"),
                severity="HIGH",
            )
            for i, cve_id in enumerate(cve_ids)
        ]

        enrichments = {cve_id: EnrichmentData(cve_id=cve_id) for cve_id in cve_ids}

        results = feature_engineer.extract_features_batch(vulns, enrichments)

        assert len(results) == 10
        for i, result in enumerate(results):
            assert result.cve_id == cve_ids[i]

    def test_extract_features_batch_large_set(
        self,
        feature_engineer: FeatureEngineer,
    ) -> None:
        """Test batch extraction with larger dataset."""
        n_vulns = 100
        vulns = [
            VulnerabilityRecord(
                cve_id=CVEId(value=f"CVE-2021-{i:05d}"),
                package_name=f"package-{i}",
                installed_version=PackageVersion(value="1.0.0"),
                severity="HIGH",
                cvss_v3_score=CVSSScore(value=min(10.0, 5.0 + i * 0.05)),
            )
            for i in range(n_vulns)
        ]

        enrichments = {
            f"CVE-2021-{i:05d}": EnrichmentData(
                cve_id=f"CVE-2021-{i:05d}",
                epss=EPSSScore(score=min(1.0, i / n_vulns), percentile=i / n_vulns),
            )
            for i in range(n_vulns)
        }

        results = feature_engineer.extract_features_batch(vulns, enrichments)

        assert len(results) == n_vulns
        # Check first and last
        assert results[0].cve_id == "CVE-2021-00000"
        assert results[-1].cve_id == "CVE-2021-00099"


# === Test Private Methods ===


class TestPrivateMethods:
    """Tests for private helper methods."""

    def test_extract_cvss_score_from_nvd(
        self,
        feature_engineer: FeatureEngineer,
        sample_vulnerability: VulnerabilityRecord,
        sample_enrichment: EnrichmentData,
    ) -> None:
        """Test CVSS score extraction prioritizes NVD data."""
        # NVD has 10.0, vulnerability record also has 10.0
        score = feature_engineer._extract_cvss_score(sample_vulnerability, sample_enrichment)
        assert score == 10.0

    def test_extract_cvss_score_fallback_to_vulnerability(
        self,
        feature_engineer: FeatureEngineer,
        sample_vulnerability: VulnerabilityRecord,
        minimal_enrichment: EnrichmentData,
    ) -> None:
        """Test CVSS score falls back to vulnerability record."""
        score = feature_engineer._extract_cvss_score(sample_vulnerability, minimal_enrichment)
        assert score == 10.0

    def test_extract_epss_with_data(
        self,
        feature_engineer: FeatureEngineer,
        sample_enrichment: EnrichmentData,
    ) -> None:
        """Test EPSS extraction with data."""
        score, percentile = feature_engineer._extract_epss(sample_enrichment)
        assert score == 0.975
        assert percentile == 0.999

    def test_extract_epss_without_data(
        self,
        feature_engineer: FeatureEngineer,
        minimal_enrichment: EnrichmentData,
    ) -> None:
        """Test EPSS extraction without data returns zeros."""
        score, percentile = feature_engineer._extract_epss(minimal_enrichment)
        assert score == 0.0
        assert percentile == 0.0

    def test_encode_cwe_known(
        self,
        feature_engineer: FeatureEngineer,
        sample_enrichment: EnrichmentData,
    ) -> None:
        """Test CWE encoding for known CWE."""
        encoded = feature_engineer._encode_cwe(sample_enrichment)
        # CWE-502 (first CWE in fixture) has encoding 0.78
        assert encoded == CWE_TARGET_ENCODING["CWE-502"]

    def test_encode_cwe_unknown(
        self,
        feature_engineer: FeatureEngineer,
    ) -> None:
        """Test CWE encoding for unknown CWE falls back to default."""
        nvd = NVDEnrichment(
            cve_id="CVE-2021-99999",
            cwe_ids=["CWE-999999"],  # Unknown CWE
        )
        enrichment = EnrichmentData(cve_id="CVE-2021-99999", nvd=nvd)

        encoded = feature_engineer._encode_cwe(enrichment)
        assert encoded == CWE_TARGET_ENCODING["DEFAULT"]

    def test_encode_cwe_no_cwe(
        self,
        feature_engineer: FeatureEngineer,
        minimal_enrichment: EnrichmentData,
    ) -> None:
        """Test CWE encoding when no CWE available."""
        encoded = feature_engineer._encode_cwe(minimal_enrichment)
        assert encoded == CWE_TARGET_ENCODING["DEFAULT"]

    def test_check_exploit_references_nvd(
        self,
        feature_engineer: FeatureEngineer,
        sample_enrichment: EnrichmentData,
    ) -> None:
        """Test exploit reference detection from NVD."""
        has_exploit = feature_engineer._check_exploit_references(sample_enrichment)
        assert has_exploit is True

    def test_check_exploit_references_osint_keywords(
        self,
        feature_engineer: FeatureEngineer,
    ) -> None:
        """Test exploit detection via OSINT keywords."""
        osint = OSINTResult(
            title="CVE Analysis",
            url="https://example.com",
            content="This vulnerability has a working RCE exploit available",
            score=0.9,
        )
        enrichment = EnrichmentData(
            cve_id="CVE-2021-44228",
            osint_results=[osint],
        )

        has_exploit = feature_engineer._check_exploit_references(enrichment)
        assert has_exploit is True

    def test_check_exploit_references_no_exploit(
        self,
        feature_engineer: FeatureEngineer,
        minimal_enrichment: EnrichmentData,
    ) -> None:
        """Test no exploit detection when none available."""
        has_exploit = feature_engineer._check_exploit_references(minimal_enrichment)
        assert has_exploit is False


# === Test Custom CWE Encoding ===


class TestCustomCWEEncoding:
    """Tests for custom CWE encoding."""

    def test_custom_encoding_used(
        self,
        custom_cwe_encoding: dict[str, float],
        sample_vulnerability: VulnerabilityRecord,
    ) -> None:
        """Test that custom encoding is used when provided."""
        engineer = FeatureEngineer(cwe_encoding=custom_cwe_encoding)

        nvd = NVDEnrichment(
            cve_id="CVE-2021-44228",
            cwe_ids=["CWE-79"],
        )
        enrichment = EnrichmentData(cve_id="CVE-2021-44228", nvd=nvd)

        result = engineer.extract_features(sample_vulnerability, enrichment)

        assert result.cwe_category == 0.70  # Custom encoding for CWE-79

    def test_custom_encoding_default_fallback(
        self,
        custom_cwe_encoding: dict[str, float],
        sample_vulnerability: VulnerabilityRecord,
    ) -> None:
        """Test custom encoding DEFAULT value is used for unknown CWEs."""
        engineer = FeatureEngineer(cwe_encoding=custom_cwe_encoding)

        nvd = NVDEnrichment(
            cve_id="CVE-2021-44228",
            cwe_ids=["CWE-999"],  # Not in custom encoding
        )
        enrichment = EnrichmentData(cve_id="CVE-2021-44228", nvd=nvd)

        result = engineer.extract_features(sample_vulnerability, enrichment)

        assert result.cwe_category == 0.30  # Custom DEFAULT value


# === Test Edge Cases ===


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_zero_days_since_publication(
        self,
        feature_engineer: FeatureEngineer,
        sample_vulnerability: VulnerabilityRecord,
    ) -> None:
        """Test handling of just-published CVE."""
        nvd = NVDEnrichment(
            cve_id="CVE-2021-44228",
            published_date=datetime.now(UTC),  # Today
        )
        enrichment = EnrichmentData(cve_id="CVE-2021-44228", nvd=nvd)

        result = feature_engineer.extract_features(sample_vulnerability, enrichment)

        assert result.days_since_publication >= 0

    def test_future_publication_date(
        self,
        feature_engineer: FeatureEngineer,
        sample_vulnerability: VulnerabilityRecord,
    ) -> None:
        """Test handling of future publication date (edge case)."""
        nvd = NVDEnrichment(
            cve_id="CVE-2021-44228",
            published_date=datetime.now(UTC) + timedelta(days=1),  # Tomorrow
        )
        enrichment = EnrichmentData(cve_id="CVE-2021-44228", nvd=nvd)

        result = feature_engineer.extract_features(sample_vulnerability, enrichment)

        # Should clamp to 0 for future dates
        assert result.days_since_publication == 0

    def test_exploit_keywords_case_insensitive(
        self,
        feature_engineer: FeatureEngineer,
    ) -> None:
        """Test exploit keyword detection is case insensitive."""
        osint = OSINTResult(
            title="Analysis",
            url="https://example.com",
            content="PROOF OF CONCEPT exploit available",
            score=0.9,
        )
        enrichment = EnrichmentData(
            cve_id="CVE-2021-44228",
            osint_results=[osint],
        )

        has_exploit = feature_engineer._check_exploit_references(enrichment)
        assert has_exploit is True

    def test_multiple_cwe_uses_first(
        self,
        feature_engineer: FeatureEngineer,
        sample_vulnerability: VulnerabilityRecord,
    ) -> None:
        """Test that first CWE is used when multiple are present."""
        nvd = NVDEnrichment(
            cve_id="CVE-2021-44228",
            cwe_ids=["CWE-78", "CWE-79", "CWE-89"],  # Multiple CWEs
        )
        enrichment = EnrichmentData(cve_id="CVE-2021-44228", nvd=nvd)

        result = feature_engineer.extract_features(sample_vulnerability, enrichment)

        # Should use first CWE (CWE-78 = 0.85)
        assert result.cwe_category == CWE_TARGET_ENCODING["CWE-78"]


__all__ = [
    "TestCustomCWEEncoding",
    "TestEdgeCases",
    "TestExtractFeatures",
    "TestExtractFeaturesBatch",
    "TestFeatureEngineerInit",
    "TestPrivateMethods",
]
