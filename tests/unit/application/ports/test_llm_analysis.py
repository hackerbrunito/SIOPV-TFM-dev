"""Tests for LLMAnalysisPort ABC interface compliance."""

from __future__ import annotations

from typing import Any

import pytest

from siopv.application.ports.llm_analysis import (
    LLMAnalysisPort,
    VulnerabilityAnalysis,
)


class TestLLMAnalysisPortInterface:
    """Tests for LLMAnalysisPort ABC definition."""

    def test_llm_analysis_port_is_abstract(self) -> None:
        """LLMAnalysisPort should not be directly instantiable."""
        with pytest.raises(TypeError):
            LLMAnalysisPort()  # type: ignore[abstract]

    def test_concrete_implementation_instantiable(self) -> None:
        """A class implementing all abstract methods should be instantiable."""

        class ConcreteLLMAnalysis(LLMAnalysisPort):
            async def analyze_vulnerability(
                self, _cve_id: str, _context: dict[str, Any]
            ) -> VulnerabilityAnalysis:
                return VulnerabilityAnalysis(
                    summary="test",
                    remediation_recommendation="patch",
                    relevance_assessment=0.8,
                    reasoning="because",
                )

            async def evaluate_confidence(
                self,
                _cve_id: str,
                _classification: dict[str, Any],
                _enrichment: dict[str, Any],
            ) -> float:
                return 0.9

        adapter = ConcreteLLMAnalysis()
        assert isinstance(adapter, LLMAnalysisPort)

    def test_partial_implementation_not_instantiable(self) -> None:
        """Missing abstract methods should prevent instantiation."""

        class PartialLLM(LLMAnalysisPort):
            async def analyze_vulnerability(
                self, _cve_id: str, _context: dict[str, Any]
            ) -> VulnerabilityAnalysis:
                return VulnerabilityAnalysis(
                    summary="",
                    remediation_recommendation="",
                    relevance_assessment=0.0,
                    reasoning="",
                )

        with pytest.raises(TypeError):
            PartialLLM()  # type: ignore[abstract]


class TestVulnerabilityAnalysis:
    """Tests for VulnerabilityAnalysis dataclass."""

    def test_creation(self) -> None:
        """VulnerabilityAnalysis should be creatable with all fields."""
        analysis = VulnerabilityAnalysis(
            summary="RCE via Log4j JNDI injection",
            remediation_recommendation="Upgrade to Log4j 2.17.1+",
            relevance_assessment=0.95,
            reasoning="Actively exploited, CVSS 10.0, public PoC available",
        )
        assert analysis.summary == "RCE via Log4j JNDI injection"
        assert analysis.remediation_recommendation == "Upgrade to Log4j 2.17.1+"
        assert analysis.relevance_assessment == 0.95
        assert analysis.reasoning == "Actively exploited, CVSS 10.0, public PoC available"

    def test_frozen(self) -> None:
        """VulnerabilityAnalysis should be immutable (frozen dataclass)."""
        analysis = VulnerabilityAnalysis(
            summary="test",
            remediation_recommendation="fix",
            relevance_assessment=0.5,
            reasoning="reason",
        )
        with pytest.raises(AttributeError):
            analysis.summary = "changed"  # type: ignore[misc]
