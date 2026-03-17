"""Anthropic Claude adapter for LLM-based vulnerability analysis.

Uses Claude Sonnet for deep vulnerability analysis and Claude Haiku for
faster confidence evaluation. Fail-open design: any API error returns
safe defaults with warning logs.
"""

from __future__ import annotations

import asyncio
import functools
import json
from typing import Any

import structlog

from siopv.adapters.dlp._haiku_utils import create_haiku_client, extract_text_from_response
from siopv.application.ports.llm_analysis import LLMAnalysisPort, VulnerabilityAnalysis

logger = structlog.get_logger(__name__)

DEFAULT_RELEVANCE: float = 0.5
DEFAULT_CONFIDENCE: float = 0.5
MAX_CONTEXT_LENGTH: int = 6_000

_ANALYSIS_SYSTEM_PROMPT = """\
You are an expert cybersecurity analyst specializing in vulnerability assessment. \
Your role is to analyze CVE vulnerabilities and provide actionable intelligence. \
Always respond with valid JSON matching the requested schema. Be precise and concise.\
"""

_ANALYSIS_USER_PROMPT = """\
Analyze the following vulnerability and provide a structured assessment.

CVE ID: {cve_id}

Context:
{context}

Respond with a JSON object containing exactly these fields:
- "summary": A concise technical summary of the vulnerability (2-3 sentences).
- "remediation_recommendation": Specific actionable remediation steps.
- "relevance_assessment": A float between 0.0 and 1.0 indicating how relevant/impactful \
this vulnerability is (1.0 = critical, actively exploited; 0.0 = theoretical, no real impact).
- "reasoning": Your chain-of-thought reasoning for the relevance assessment.

Respond ONLY with the JSON object, no markdown fences or extra text.\
"""

_CONFIDENCE_SYSTEM_PROMPT = """\
You are a cybersecurity classification validator. Evaluate the confidence of \
vulnerability classifications by cross-referencing enrichment data. \
Respond with a single JSON object.\
"""

_CONFIDENCE_USER_PROMPT = """\
Evaluate the confidence of the following vulnerability classification.

CVE ID: {cve_id}

Classification:
{classification}

Enrichment Data:
{enrichment}

Respond with a JSON object containing exactly one field:
- "confidence": A float between 0.0 and 1.0 indicating how confident you are \
in the classification (1.0 = highly confident, strong evidence; 0.0 = no confidence, \
contradictory evidence).

Respond ONLY with the JSON object, no markdown fences or extra text.\
"""


def _truncate_context(text: str) -> str:
    """Truncate context text to avoid excessive token cost."""
    return text[:MAX_CONTEXT_LENGTH]


def _format_context(context: dict[str, Any]) -> str:
    """Format enrichment context dict into a readable string for the prompt."""
    try:
        return _truncate_context(json.dumps(context, indent=2, default=str))
    except (TypeError, ValueError):
        return _truncate_context(str(context))


def _parse_analysis_response(raw_text: str) -> dict[str, Any]:
    """Parse JSON response from analysis, stripping markdown fences if present."""
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [line for line in lines if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()
    result: dict[str, Any] = json.loads(text)
    return result


class AnthropicAnalysisAdapter(LLMAnalysisPort):
    """LLM analysis adapter using Anthropic Claude models.

    Uses the synchronous Anthropic client called from an executor so the
    async interface is non-blocking.

    Args:
        api_key: Anthropic API key.
        sonnet_model: Model identifier for deep analysis (Claude Sonnet).
        haiku_model: Model identifier for confidence evaluation (Claude Haiku).
    """

    def __init__(
        self,
        api_key: str,
        sonnet_model: str,
        haiku_model: str,
    ) -> None:
        self._client = create_haiku_client(api_key)
        self._sonnet_model = sonnet_model
        self._haiku_model = haiku_model

    async def _call_model(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
    ) -> str:
        """Call an Anthropic model via executor and return raw response text."""
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            functools.partial(
                self._client.messages.create,
                model=model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            ),
        )
        return extract_text_from_response(response)

    async def analyze_vulnerability(
        self, cve_id: str, context: dict[str, Any]
    ) -> VulnerabilityAnalysis:
        """Analyze a vulnerability using Claude Sonnet.

        On any API or parsing error, returns safe defaults with warning log.
        """
        try:
            user_prompt = _ANALYSIS_USER_PROMPT.format(
                cve_id=cve_id,
                context=_format_context(context),
            )
            raw = await self._call_model(
                model=self._sonnet_model,
                system_prompt=_ANALYSIS_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                max_tokens=1024,
            )
            parsed = _parse_analysis_response(raw)
            relevance = float(parsed.get("relevance_assessment", DEFAULT_RELEVANCE))
            relevance = max(0.0, min(1.0, relevance))

            result = VulnerabilityAnalysis(
                summary=str(parsed.get("summary", "")),
                remediation_recommendation=str(parsed.get("remediation_recommendation", "")),
                relevance_assessment=relevance,
                reasoning=str(parsed.get("reasoning", "")),
            )
        except Exception:
            logger.warning(
                "llm_analysis_error_fail_open",
                cve_id=cve_id,
                exc_info=True,
            )
            return VulnerabilityAnalysis(
                summary="",
                remediation_recommendation="",
                relevance_assessment=DEFAULT_RELEVANCE,
                reasoning="",
            )
        else:
            logger.info(
                "llm_analysis_complete",
                cve_id=cve_id,
                relevance=result.relevance_assessment,
            )
            return result

    async def evaluate_confidence(
        self,
        cve_id: str,
        classification: dict[str, Any],
        enrichment: dict[str, Any],
    ) -> float:
        """Evaluate classification confidence using Claude Haiku.

        On any API or parsing error, returns 0.5 (neutral confidence) with warning log.
        """
        try:
            user_prompt = _CONFIDENCE_USER_PROMPT.format(
                cve_id=cve_id,
                classification=_format_context(classification),
                enrichment=_format_context(enrichment),
            )
            raw = await self._call_model(
                model=self._haiku_model,
                system_prompt=_CONFIDENCE_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                max_tokens=128,
            )
            parsed = _parse_analysis_response(raw)
            confidence = float(parsed.get("confidence", DEFAULT_CONFIDENCE))
            confidence = max(0.0, min(1.0, confidence))

        except Exception:
            logger.warning(
                "llm_confidence_eval_error_fail_open",
                cve_id=cve_id,
                exc_info=True,
            )
            return DEFAULT_CONFIDENCE
        else:
            logger.info(
                "llm_confidence_eval_complete",
                cve_id=cve_id,
                confidence=confidence,
            )
            return confidence


__all__ = ["AnthropicAnalysisAdapter"]
