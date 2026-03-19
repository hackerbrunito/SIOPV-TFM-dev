"""Unit tests for ClassifyRiskUseCase.

Tests the ML classification pipeline including feature extraction,
prediction, and XAI explanations.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pytest

from siopv.adapters.ml.feature_engineer import FeatureEngineer
from siopv.application.ports.ml_classifier import MLClassifierPort
from siopv.application.use_cases.classify_risk import (
    ClassificationResult,
    ClassificationStats,
    ClassifyRiskUseCase,
    create_classify_risk_use_case,
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
    PackageVersion,
)
from siopv.domain.value_objects.risk_score import (
    LIMEExplanation,
    RiskScore,
    SHAPValues,
)

# === Fixtures ===


@pytest.fixture
def sample_vulnerability() -> VulnerabilityRecord:
    """Create a sample vulnerability for testing."""
    return VulnerabilityRecord(
        cve_id=CVEId(value="CVE-2021-44228"),
        package_name="log4j-core",
        installed_version=PackageVersion(value="2.14.0"),
        fixed_version=PackageVersion(value="2.17.0"),
        severity="CRITICAL",
        cvss_v3_score=CVSSScore(value=10.0),
    )


@pytest.fixture
def sample_enrichment() -> EnrichmentData:
    """Create sample enrichment data for testing."""
    return EnrichmentData(
        cve_id="CVE-2021-44228",
        nvd=NVDEnrichment(
            cve_id="CVE-2021-44228",
            description="Apache Log4j2 RCE vulnerability",
            cvss_v3_score=10.0,
            cvss_v3_vector=CVSSVector(
                attack_vector="N",
                attack_complexity="L",
                privileges_required="N",
                user_interaction="N",
                scope="C",
                confidentiality_impact="H",
                integrity_impact="H",
                availability_impact="H",
            ),
            has_exploit_ref=True,
            cwe_ids=["CWE-502"],
        ),
        epss=EPSSScore(score=0.975, percentile=0.999),
        relevance_score=0.9,
    )


@pytest.fixture
def sample_feature_vector() -> MLFeatureVector:
    """Create a sample feature vector for testing."""
    return MLFeatureVector(
        cve_id="CVE-2021-44228",
        cvss_base_score=10.0,
        attack_vector=3,
        attack_complexity=1,
        privileges_required=2,
        user_interaction=1,
        scope=1,
        confidentiality_impact=2,
        integrity_impact=2,
        availability_impact=2,
        epss_score=0.975,
        epss_percentile=0.999,
        days_since_publication=1000,
        has_exploit_ref=1,
        cwe_category=0.78,
    )


@pytest.fixture
def sample_shap_values() -> SHAPValues:
    """Create sample SHAP values for testing."""
    return SHAPValues(
        feature_names=[
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
            "cwe_category",
        ],
        shap_values=[
            0.15,
            0.08,
            0.03,
            0.05,
            0.02,
            0.04,
            0.06,
            0.05,
            0.04,
            0.25,
            0.10,
            -0.02,
            0.12,
            0.03,
        ],
        base_value=0.35,
    )


@pytest.fixture
def sample_lime_explanation() -> LIMEExplanation:
    """Create sample LIME explanation for testing."""
    return LIMEExplanation(
        feature_contributions=[
            ("epss_score > 0.9", 0.25),
            ("cvss_base_score > 9.0", 0.15),
            ("has_exploit_ref = 1", 0.12),
            ("attack_vector = Network", 0.08),
        ],
        prediction_local=0.92,
        intercept=0.35,
        model_score=0.85,
    )


@pytest.fixture
def sample_risk_score(sample_shap_values, sample_lime_explanation) -> RiskScore:
    """Create sample risk score for testing."""
    return RiskScore.from_prediction(
        cve_id="CVE-2021-44228",
        probability=0.92,
        shap_values=sample_shap_values,
        lime_explanation=sample_lime_explanation,
    )


@pytest.fixture
def mock_classifier(sample_risk_score) -> MagicMock:
    """Create a mock classifier."""
    mock = MagicMock(spec=MLClassifierPort)
    mock.is_loaded.return_value = True
    mock.predict.return_value = sample_risk_score
    mock.predict_proba.return_value = 0.92
    return mock


@pytest.fixture
def mock_feature_engineer(sample_feature_vector) -> MagicMock:
    """Create a mock feature engineer."""
    from siopv.application.ports.feature_engineering import FeatureEngineerPort

    mock = MagicMock(spec=FeatureEngineerPort)
    mock.extract_features.return_value = sample_feature_vector
    return mock


# === Value Objects Tests ===


class TestSHAPValues:
    """Tests for SHAPValues value object."""

    def test_create_shap_values(self, sample_shap_values: SHAPValues):
        """Test creating SHAP values."""
        assert len(sample_shap_values.feature_names) == 14
        assert len(sample_shap_values.shap_values) == 14
        assert sample_shap_values.base_value == 0.35

    def test_to_dict(self, sample_shap_values: SHAPValues):
        """Test converting to dictionary."""
        result = sample_shap_values.to_dict()
        assert "epss_score" in result
        assert result["epss_score"] == 0.25

    def test_top_contributors(self, sample_shap_values: SHAPValues):
        """Test getting top contributors."""
        top = sample_shap_values.top_contributors
        assert len(top) == 5
        # EPSS should be top contributor
        assert top[0][0] == "epss_score"

    def test_str_representation(self, sample_shap_values: SHAPValues):
        """Test string representation."""
        s = str(sample_shap_values)
        assert "SHAP" in s
        assert "epss_score" in s

    def test_mismatched_shap_values_length_raises(self):
        """Test that mismatched shap_values and feature_names lengths raise ValueError."""
        with pytest.raises(
            ValueError, match=r"shap_values length.*must match.*feature_names length"
        ):
            SHAPValues(
                feature_names=["a", "b", "c"],
                shap_values=[0.1, 0.2],
                base_value=0.5,
            )


class TestLIMEExplanation:
    """Tests for LIMEExplanation value object."""

    def test_create_lime_explanation(self, sample_lime_explanation: LIMEExplanation):
        """Test creating LIME explanation."""
        assert len(sample_lime_explanation.feature_contributions) == 4
        assert sample_lime_explanation.prediction_local == 0.92
        assert sample_lime_explanation.model_score == 0.85

    def test_positive_contributors(self, sample_lime_explanation: LIMEExplanation):
        """Test getting positive contributors."""
        positive = sample_lime_explanation.positive_contributors
        assert len(positive) == 4
        assert all(c > 0 for _, c in positive)

    def test_negative_contributors(self, sample_lime_explanation: LIMEExplanation):
        """Test getting negative contributors."""
        negative = sample_lime_explanation.negative_contributors
        assert len(negative) == 0

    def test_explain_top_factors(self, sample_lime_explanation: LIMEExplanation):
        """Test human-readable explanation."""
        explanation = sample_lime_explanation.explain_top_factors(n=2)
        assert "increased" in explanation
        assert "epss_score" in explanation

    def test_str_representation(self, sample_lime_explanation: LIMEExplanation):
        """Test string representation."""
        s = str(sample_lime_explanation)
        assert "LIME" in s
        assert "0.92" in s


class TestRiskScore:
    """Tests for RiskScore value object."""

    def test_create_from_prediction_critical(self):
        """Test creating critical risk score."""
        score = RiskScore.from_prediction(
            cve_id="CVE-2021-44228",
            probability=0.92,
        )
        assert score.risk_label == "CRITICAL"
        assert score.risk_probability == 0.92
        assert score.is_high_risk
        assert score.requires_immediate_action

    def test_create_from_prediction_high(self):
        """Test creating high risk score."""
        score = RiskScore.from_prediction(
            cve_id="CVE-2021-12345",
            probability=0.65,
        )
        assert score.risk_label == "HIGH"
        assert score.is_high_risk
        assert not score.requires_immediate_action

    def test_create_from_prediction_medium(self):
        """Test creating medium risk score."""
        score = RiskScore.from_prediction(
            cve_id="CVE-2021-12345",
            probability=0.45,
        )
        assert score.risk_label == "MEDIUM"
        assert not score.is_high_risk

    def test_create_from_prediction_low(self):
        """Test creating low risk score."""
        score = RiskScore.from_prediction(
            cve_id="CVE-2021-12345",
            probability=0.25,
        )
        assert score.risk_label == "LOW"

    def test_create_from_prediction_minimal(self):
        """Test creating minimal risk score."""
        score = RiskScore.from_prediction(
            cve_id="CVE-2021-12345",
            probability=0.10,
        )
        assert score.risk_label == "MINIMAL"

    def test_confidence_calculation(self):
        """Test confidence calculation."""
        # High confidence when far from 0.5
        score_high_conf = RiskScore.from_prediction(
            cve_id="CVE-2021-12345",
            probability=0.95,
        )
        assert abs(score_high_conf.confidence - 0.9) < 1e-6

        # Low confidence when near 0.5
        score_low_conf = RiskScore.from_prediction(
            cve_id="CVE-2021-12345",
            probability=0.55,
        )
        assert abs(score_low_conf.confidence - 0.1) < 1e-6

    def test_to_output_tuple(self, sample_risk_score: RiskScore):
        """Test output tuple for LangGraph."""
        prob, shap, lime = sample_risk_score.to_output_tuple()
        assert prob == 0.92
        assert shap is not None
        assert lime is not None


# === MLFeatureVector Tests ===


class TestMLFeatureVector:
    """Tests for MLFeatureVector entity."""

    def test_create_feature_vector(self, sample_feature_vector: MLFeatureVector):
        """Test creating feature vector."""
        assert sample_feature_vector.cve_id == "CVE-2021-44228"
        assert sample_feature_vector.cvss_base_score == 10.0
        assert sample_feature_vector.epss_score == 0.975

    def test_to_array(self, sample_feature_vector: MLFeatureVector):
        """Test converting to numpy array."""
        arr = sample_feature_vector.to_array()
        assert isinstance(arr, np.ndarray)
        assert arr.shape == (14,)
        assert arr[0] == 10.0  # cvss_base_score
        assert arr[9] == 0.975  # epss_score

    def test_to_dict(self, sample_feature_vector: MLFeatureVector):
        """Test converting to dictionary."""
        d = sample_feature_vector.to_dict()
        assert len(d) == 14
        assert d["cvss_base_score"] == 10.0
        assert abs(d["epss_score"] - 0.975) < 1e-3  # Float32 precision

    def test_feature_names(self, sample_feature_vector: MLFeatureVector):
        """Test feature names property."""
        names = sample_feature_vector.feature_names
        assert len(names) == 14
        assert "cvss_base_score" in names
        assert "epss_score" in names

    def test_from_enrichment(self):
        """Test creating from enrichment data."""
        fv = MLFeatureVector.from_enrichment(
            cve_id="CVE-2021-44228",
            cvss_base_score=10.0,
            cvss_vector={"attack_vector": 3, "attack_complexity": 1},
            epss_score=0.95,
            epss_percentile=0.99,
            days_since_publication=1000,
            has_exploit_ref=True,
            cwe_category=0.78,
        )
        assert fv.cve_id == "CVE-2021-44228"
        assert fv.cvss_base_score == 10.0
        assert fv.attack_vector == 3
        assert fv.has_exploit_ref == 1


# === FeatureEngineer Tests ===


class TestFeatureEngineer:
    """Tests for FeatureEngineer adapter."""

    def test_extract_features(
        self,
        sample_vulnerability: VulnerabilityRecord,
        sample_enrichment: EnrichmentData,
    ):
        """Test extracting features."""
        engineer = FeatureEngineer()
        fv = engineer.extract_features(sample_vulnerability, sample_enrichment)

        assert fv.cve_id == "CVE-2021-44228"
        assert fv.cvss_base_score == 10.0
        assert fv.epss_score == 0.975
        assert fv.has_exploit_ref == 1

    def test_extract_features_with_missing_data(self, sample_vulnerability: VulnerabilityRecord):
        """Test extracting features with minimal enrichment."""
        engineer = FeatureEngineer()
        minimal_enrichment = EnrichmentData(cve_id="CVE-2021-44228")

        fv = engineer.extract_features(sample_vulnerability, minimal_enrichment)

        assert fv.cve_id == "CVE-2021-44228"
        assert fv.epss_score == 0.0
        assert fv.has_exploit_ref == 0

    def test_cwe_encoding(self):
        """Test CWE target encoding."""
        engineer = FeatureEngineer()

        # Known CWE
        assert (
            engineer._encode_cwe(
                EnrichmentData(
                    cve_id="test",
                    nvd=NVDEnrichment(cve_id="test", cwe_ids=["CWE-89"]),
                )
            )
            == 0.80
        )

        # Unknown CWE uses default
        assert (
            engineer._encode_cwe(
                EnrichmentData(
                    cve_id="test",
                    nvd=NVDEnrichment(cve_id="test", cwe_ids=["CWE-99999"]),
                )
            )
            == 0.35
        )


# === ClassifyRiskUseCase Tests ===


class TestClassifyRiskUseCase:
    """Tests for ClassifyRiskUseCase."""

    def test_execute_successful(
        self,
        mock_classifier: MagicMock,
        mock_feature_engineer: MagicMock,
        sample_vulnerability: VulnerabilityRecord,
        sample_enrichment: EnrichmentData,
    ):
        """Test successful classification."""
        use_case = ClassifyRiskUseCase(
            classifier=mock_classifier, feature_engineer=mock_feature_engineer
        )
        result = use_case.execute(sample_vulnerability, sample_enrichment)

        assert result.is_successful
        assert result.risk_score is not None
        assert result.risk_score.risk_probability == 0.92
        assert result.error is None

    def test_execute_with_error(
        self,
        mock_feature_engineer: MagicMock,
        sample_vulnerability: VulnerabilityRecord,
        sample_enrichment: EnrichmentData,
    ):
        """Test classification with error."""
        mock_classifier = MagicMock(spec=MLClassifierPort)
        mock_classifier.is_loaded.return_value = True
        mock_classifier.predict.side_effect = RuntimeError("Model error")

        use_case = ClassifyRiskUseCase(
            classifier=mock_classifier, feature_engineer=mock_feature_engineer
        )
        result = use_case.execute(sample_vulnerability, sample_enrichment)

        assert not result.is_successful
        assert result.risk_score is None
        assert "Model error" in result.error

    def test_execute_batch(
        self,
        mock_classifier: MagicMock,
        mock_feature_engineer: MagicMock,
        sample_vulnerability: VulnerabilityRecord,
        sample_enrichment: EnrichmentData,
    ):
        """Test batch classification."""
        use_case = ClassifyRiskUseCase(
            classifier=mock_classifier, feature_engineer=mock_feature_engineer
        )

        vulnerabilities = [sample_vulnerability]
        enrichments = {sample_vulnerability.cve_id.value: sample_enrichment}

        batch_result = use_case.execute_batch(vulnerabilities, enrichments)

        assert batch_result.stats.total_processed == 1
        assert batch_result.stats.successful == 1
        assert batch_result.stats.failed == 0
        assert batch_result.stats.high_risk_count == 1

    def test_get_risk_summary(
        self,
        mock_classifier: MagicMock,
        mock_feature_engineer: MagicMock,
        sample_risk_score: RiskScore,
    ):
        """Test generating risk summary."""
        use_case = ClassifyRiskUseCase(
            classifier=mock_classifier, feature_engineer=mock_feature_engineer
        )

        results = [
            ClassificationResult(cve_id="CVE-2021-44228", risk_score=sample_risk_score),
        ]

        summary = use_case.get_risk_summary(results)

        assert summary["total_classified"] == 1
        assert "CRITICAL" in summary["by_risk_label"]
        assert len(summary["top_10_risks"]) == 1

    def test_factory_function(self, mock_classifier: MagicMock):
        """Test factory function."""
        use_case = create_classify_risk_use_case(classifier=mock_classifier)
        assert isinstance(use_case, ClassifyRiskUseCase)


# === ClassificationResult Tests ===


class TestClassificationResult:
    """Tests for ClassificationResult dataclass."""

    def test_is_successful(self, sample_risk_score: RiskScore):
        """Test successful result."""
        result = ClassificationResult(
            cve_id="CVE-2021-44228",
            risk_score=sample_risk_score,
        )
        assert result.is_successful

    def test_is_not_successful_with_error(self):
        """Test failed result."""
        result = ClassificationResult(
            cve_id="CVE-2021-44228",
            risk_score=None,
            error="Some error",
        )
        assert not result.is_successful

    def test_to_output_tuple(self, sample_risk_score: RiskScore):
        """Test output tuple generation."""
        result = ClassificationResult(
            cve_id="CVE-2021-44228",
            risk_score=sample_risk_score,
        )
        output = result.to_output_tuple()
        assert output is not None
        assert output[0] == 0.92

    def test_to_output_tuple_on_error(self):
        """Test output tuple on error."""
        result = ClassificationResult(
            cve_id="CVE-2021-44228",
            risk_score=None,
            error="Error",
        )
        assert result.to_output_tuple() is None


# === ClassificationStats Tests ===


class TestClassificationStats:
    """Tests for ClassificationStats dataclass."""

    def test_create_stats(self):
        """Test creating statistics."""
        stats = ClassificationStats(
            total_processed=10,
            successful=8,
            failed=2,
            high_risk_count=3,
            critical_count=1,
            avg_risk_probability=0.55,
        )

        assert stats.total_processed == 10
        assert stats.successful == 8
        assert stats.high_risk_count == 3
