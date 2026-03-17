"""Port interface for LLM-based vulnerability analysis.

Defines the contract for LLM adapters that provide vulnerability analysis,
remediation recommendations, and confidence evaluation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class VulnerabilityAnalysis:
    """Result of LLM-based vulnerability analysis.

    Attributes:
        summary: LLM-generated vulnerability summary.
        remediation_recommendation: LLM-generated fix recommendation.
        relevance_assessment: LLM-graded relevance score (0-1).
        reasoning: Chain-of-thought reasoning behind the assessment.
    """

    summary: str
    remediation_recommendation: str
    relevance_assessment: float
    reasoning: str


class LLMAnalysisPort(ABC):
    """Port interface for LLM-based vulnerability analysis.

    Implementations must handle:
    - Structured prompt engineering for security analysis
    - Response parsing and validation
    - Fail-open on API errors (return safe defaults)
    """

    @abstractmethod
    async def analyze_vulnerability(
        self, cve_id: str, context: dict[str, Any]
    ) -> VulnerabilityAnalysis:
        """Analyze a vulnerability using LLM reasoning.

        Args:
            cve_id: CVE identifier (e.g., "CVE-2021-44228").
            context: Enrichment context including NVD description, EPSS score,
                GitHub advisory data, and OSINT results.

        Returns:
            VulnerabilityAnalysis with summary, remediation, relevance, and reasoning.
        """
        ...

    @abstractmethod
    async def evaluate_confidence(
        self,
        cve_id: str,
        classification: dict[str, Any],
        enrichment: dict[str, Any],
    ) -> float:
        """Evaluate confidence in a classification result.

        Args:
            cve_id: CVE identifier.
            classification: Classification result (risk level, scores, etc.).
            enrichment: Enrichment context used during classification.

        Returns:
            Confidence score between 0.0 and 1.0.
        """
        ...


__all__ = [
    "LLMAnalysisPort",
    "VulnerabilityAnalysis",
]
