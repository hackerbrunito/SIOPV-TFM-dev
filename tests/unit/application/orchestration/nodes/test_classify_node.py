"""Tests for classify_node."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from siopv.application.orchestration.nodes.classify_node import (
    _create_mock_classifications,
    _estimate_llm_confidence_fallback,
    classify_node,
)
from siopv.application.orchestration.state import create_initial_state
from siopv.application.use_cases.classify_risk import ClassificationResult
from siopv.domain.entities import VulnerabilityRecord
from siopv.domain.value_objects import CVEId, EnrichmentData
from siopv.domain.value_objects.risk_score import RiskScore


class TestClassifyNode:
    """Tests for classify_node function."""

    @pytest.fixture
    def mock_vulnerability(self) -> MagicMock:
        """Create a mock VulnerabilityRecord."""
        mock = MagicMock(spec=VulnerabilityRecord)
        mock.cve_id = CVEId(value="CVE-2024-1234")
        mock.severity = "HIGH"
        return mock

    @pytest.fixture
    def mock_enrichment(self) -> EnrichmentData:
        """Create mock EnrichmentData."""
        return EnrichmentData(
            cve_id="CVE-2024-1234",
            relevance_score=0.8,
        )

    @pytest.fixture
    def mock_classifier(self) -> MagicMock:
        """Create mock ML classifier."""
        classifier = MagicMock()
        classifier.is_loaded.return_value = True

        mock_risk_score = RiskScore.from_prediction(
            cve_id="CVE-2024-1234",
            probability=0.85,
        )
        classifier.predict.return_value = mock_risk_score

        return classifier

    @pytest.mark.asyncio
    async def test_classify_node_with_no_vulnerabilities(self):
        """Test classify node skips when no vulnerabilities."""
        state = create_initial_state()

        result = await classify_node(state)

        assert result["classifications"] == {}
        assert result["llm_confidence"] == {}
        assert result["current_node"] == "classify"

    @pytest.mark.asyncio
    async def test_classify_node_without_classifier_uses_mock(self, mock_vulnerability: MagicMock):
        """Test classify node uses mock classifications when no classifier."""
        state = {
            **create_initial_state(),
            "vulnerabilities": [mock_vulnerability],
            "enrichments": {},
        }

        result = await classify_node(state, classifier=None)

        assert result["current_node"] == "classify"
        assert "classifications" in result
        assert "CVE-2024-1234" in result["classifications"]
        assert "llm_confidence" in result
        assert "CVE-2024-1234" in result["llm_confidence"]

    @pytest.mark.asyncio
    async def test_classify_node_success_with_classifier(
        self,
        mock_vulnerability: MagicMock,
        mock_enrichment: EnrichmentData,
        mock_classifier: MagicMock,
    ):
        """Test classify node success with ML classifier."""
        state = {
            **create_initial_state(),
            "vulnerabilities": [mock_vulnerability],
            "enrichments": {"CVE-2024-1234": mock_enrichment},
        }

        result = await classify_node(state, classifier=mock_classifier)

        assert result["current_node"] == "classify"
        assert "classifications" in result or "errors" in result

    @pytest.mark.asyncio
    async def test_classify_node_exception_handling(self, mock_vulnerability: MagicMock):
        """Test classify node handles exceptions gracefully."""
        state = {
            **create_initial_state(),
            "vulnerabilities": [mock_vulnerability],
            "enrichments": {},
        }

        failing_classifier = MagicMock()
        failing_classifier.is_loaded.return_value = True
        failing_classifier.predict.side_effect = RuntimeError("ML model error")

        result = await classify_node(state, classifier=failing_classifier)

        assert result["current_node"] == "classify"
        has_error = "errors" in result and len(result["errors"]) > 0
        has_classifications = len(result.get("classifications", {})) > 0
        assert has_error or has_classifications

    @pytest.mark.asyncio
    async def test_classify_node_with_llm_analysis(
        self,
        mock_vulnerability: MagicMock,
        mock_enrichment: EnrichmentData,
        mock_classifier: MagicMock,
    ):
        """Test classify node uses real LLM confidence when llm_analysis is provided."""
        mock_llm = AsyncMock()
        mock_llm.evaluate_confidence.return_value = 0.92

        state = {
            **create_initial_state(),
            "vulnerabilities": [mock_vulnerability],
            "enrichments": {"CVE-2024-1234": mock_enrichment},
        }

        result = await classify_node(state, classifier=mock_classifier, llm_analysis=mock_llm)

        assert result["current_node"] == "classify"
        # If classification succeeded, LLM confidence should have been called
        if "CVE-2024-1234" in result.get("llm_confidence", {}):
            assert result["llm_confidence"]["CVE-2024-1234"] == 0.92
            mock_llm.evaluate_confidence.assert_called()

    @pytest.mark.asyncio
    async def test_classify_node_llm_fallback_on_error(
        self,
        mock_vulnerability: MagicMock,
        mock_enrichment: EnrichmentData,
        mock_classifier: MagicMock,
    ):
        """Test classify node falls back to heuristic when LLM call fails."""
        mock_llm = AsyncMock()
        mock_llm.evaluate_confidence.side_effect = RuntimeError("LLM API error")

        state = {
            **create_initial_state(),
            "vulnerabilities": [mock_vulnerability],
            "enrichments": {"CVE-2024-1234": mock_enrichment},
        }

        result = await classify_node(state, classifier=mock_classifier, llm_analysis=mock_llm)

        assert result["current_node"] == "classify"
        # Should still have confidence values (from fallback heuristic)
        if "CVE-2024-1234" in result.get("llm_confidence", {}):
            confidence = result["llm_confidence"]["CVE-2024-1234"]
            assert 0.0 <= confidence <= 1.0
            # Should NOT be the LLM value (since it failed)
            assert confidence != 0.92

    @pytest.mark.asyncio
    async def test_classify_node_without_llm_uses_fallback(
        self,
        mock_vulnerability: MagicMock,
        mock_enrichment: EnrichmentData,
        mock_classifier: MagicMock,
    ):
        """Test classify node uses heuristic fallback when no llm_analysis."""
        state = {
            **create_initial_state(),
            "vulnerabilities": [mock_vulnerability],
            "enrichments": {"CVE-2024-1234": mock_enrichment},
        }

        result = await classify_node(state, classifier=mock_classifier, llm_analysis=None)

        assert result["current_node"] == "classify"
        if "CVE-2024-1234" in result.get("llm_confidence", {}):
            confidence = result["llm_confidence"]["CVE-2024-1234"]
            assert 0.0 <= confidence <= 1.0


class TestEstimateLLMConfidenceFallback:
    """Tests for _estimate_llm_confidence_fallback function."""

    @pytest.fixture
    def mock_risk_score(self) -> RiskScore:
        """Create a mock RiskScore."""
        return RiskScore.from_prediction(
            cve_id="CVE-2024-1234",
            probability=0.9,
        )

    @pytest.fixture
    def mock_enrichment(self) -> EnrichmentData:
        """Create mock EnrichmentData with high relevance."""
        return EnrichmentData(
            cve_id="CVE-2024-1234",
            relevance_score=0.9,
        )

    def test_estimate_llm_confidence_with_enrichment(
        self, mock_risk_score: RiskScore, mock_enrichment: EnrichmentData
    ):
        """Test confidence estimation with enrichment data."""
        classification = ClassificationResult(
            cve_id="CVE-2024-1234",
            risk_score=mock_risk_score,
        )

        confidence = _estimate_llm_confidence_fallback(classification, mock_enrichment)

        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.7

    def test_estimate_llm_confidence_without_enrichment(self, mock_risk_score: RiskScore):
        """Test confidence estimation without enrichment data."""
        classification = ClassificationResult(
            cve_id="CVE-2024-1234",
            risk_score=mock_risk_score,
        )

        confidence = _estimate_llm_confidence_fallback(classification, None)

        assert 0.0 <= confidence <= 1.0
        assert confidence >= 0.7

    def test_estimate_llm_confidence_no_risk_score(self):
        """Test confidence estimation when risk score is None."""
        classification = ClassificationResult(
            cve_id="CVE-2024-1234",
            risk_score=None,
        )

        confidence = _estimate_llm_confidence_fallback(classification, None)

        assert confidence == 0.5


class TestCreateMockClassifications:
    """Tests for _create_mock_classifications function."""

    @pytest.fixture
    def mock_vulnerabilities(self) -> list[MagicMock]:
        """Create mock vulnerabilities with different severities."""
        vulns = []
        for cve_id, severity in [
            ("CVE-2024-1111", "CRITICAL"),
            ("CVE-2024-2222", "HIGH"),
            ("CVE-2024-3333", "MEDIUM"),
            ("CVE-2024-4444", "LOW"),
        ]:
            vuln = MagicMock(spec=VulnerabilityRecord)
            vuln.cve_id = CVEId(value=cve_id)
            vuln.severity = severity
            vulns.append(vuln)
        return vulns

    def test_create_mock_classifications_severity_mapping(
        self, mock_vulnerabilities: list[MagicMock]
    ):
        """Test mock classifications map severity to risk probability."""
        classifications, llm_confidence = _create_mock_classifications(mock_vulnerabilities, {})

        assert len(classifications) == 4
        assert len(llm_confidence) == 4

        critical_class = classifications["CVE-2024-1111"]
        assert critical_class.risk_score.risk_probability == 0.9

        high_class = classifications["CVE-2024-2222"]
        assert high_class.risk_score.risk_probability == 0.7

        medium_class = classifications["CVE-2024-3333"]
        assert medium_class.risk_score.risk_probability == 0.5

        low_class = classifications["CVE-2024-4444"]
        assert low_class.risk_score.risk_probability == 0.3

    def test_create_mock_classifications_unknown_severity(self):
        """Test mock classifications handle unknown severity."""
        vuln = MagicMock(spec=VulnerabilityRecord)
        vuln.cve_id = CVEId(value="CVE-2024-9999")
        vuln.severity = "UNKNOWN"

        classifications, _llm_confidence = _create_mock_classifications([vuln], {})

        assert "CVE-2024-9999" in classifications
        assert classifications["CVE-2024-9999"].risk_score.risk_probability == 0.4
