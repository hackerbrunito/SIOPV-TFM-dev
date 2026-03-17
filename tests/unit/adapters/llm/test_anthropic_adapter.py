"""Tests for AnthropicAnalysisAdapter."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from siopv.adapters.llm.anthropic_adapter import (
    DEFAULT_CONFIDENCE,
    DEFAULT_RELEVANCE,
    AnthropicAnalysisAdapter,
    _format_context,
    _parse_analysis_response,
)
from siopv.application.ports.llm_analysis import LLMAnalysisPort, VulnerabilityAnalysis


@pytest.fixture
def mock_anthropic_client() -> MagicMock:
    """Create a mock Anthropic client."""
    return MagicMock()


@pytest.fixture
def adapter(mock_anthropic_client: MagicMock) -> AnthropicAnalysisAdapter:
    """Create an AnthropicAnalysisAdapter with mocked client."""
    with patch(
        "siopv.adapters.llm.anthropic_adapter.create_haiku_client",
        return_value=mock_anthropic_client,
    ):
        return AnthropicAnalysisAdapter(
            api_key="test-key",
            sonnet_model="claude-sonnet-4-5-20250929",
            haiku_model="claude-haiku-4-5-20251001",
        )


def _make_text_block(text: str) -> MagicMock:
    """Create a mock TextBlock."""
    block = MagicMock()
    block.text = text
    # Make isinstance check work for extract_text_from_response
    block.__class__ = type("TextBlock", (), {})
    return block


def _make_response(text: str) -> MagicMock:
    """Create a mock Anthropic Message response with a TextBlock."""
    from anthropic.types import TextBlock

    response = MagicMock()
    text_block = TextBlock(type="text", text=text)
    response.content = [text_block]
    return response


class TestAnthropicAnalysisAdapterInterface:
    """Test that adapter implements LLMAnalysisPort."""

    def test_implements_port(self, adapter: AnthropicAnalysisAdapter) -> None:
        """Adapter should be an instance of LLMAnalysisPort."""
        assert isinstance(adapter, LLMAnalysisPort)


class TestAnalyzeVulnerability:
    """Tests for analyze_vulnerability method."""

    @pytest.mark.asyncio
    async def test_successful_analysis(
        self, adapter: AnthropicAnalysisAdapter, mock_anthropic_client: MagicMock
    ) -> None:
        """Should parse a valid JSON response into VulnerabilityAnalysis."""
        response_data = {
            "summary": "Critical RCE in Log4j via JNDI injection",
            "remediation_recommendation": "Upgrade to Log4j 2.17.1+",
            "relevance_assessment": 0.95,
            "reasoning": "Actively exploited with public PoCs",
        }
        mock_anthropic_client.messages.create.return_value = _make_response(
            json.dumps(response_data)
        )

        result = await adapter.analyze_vulnerability(
            cve_id="CVE-2021-44228",
            context={"description": "Log4j JNDI injection"},
        )

        assert isinstance(result, VulnerabilityAnalysis)
        assert result.summary == "Critical RCE in Log4j via JNDI injection"
        assert result.remediation_recommendation == "Upgrade to Log4j 2.17.1+"
        assert result.relevance_assessment == 0.95
        assert result.reasoning == "Actively exploited with public PoCs"

    @pytest.mark.asyncio
    async def test_uses_sonnet_model(
        self, adapter: AnthropicAnalysisAdapter, mock_anthropic_client: MagicMock
    ) -> None:
        """Should use the Sonnet model for vulnerability analysis."""
        mock_anthropic_client.messages.create.return_value = _make_response(
            json.dumps(
                {
                    "summary": "s",
                    "remediation_recommendation": "r",
                    "relevance_assessment": 0.5,
                    "reasoning": "re",
                }
            )
        )

        await adapter.analyze_vulnerability("CVE-2024-0001", {})

        call_kwargs = mock_anthropic_client.messages.create.call_args
        assert call_kwargs.kwargs["model"] == "claude-sonnet-4-5-20250929"

    @pytest.mark.asyncio
    async def test_clamps_relevance_above_one(
        self, adapter: AnthropicAnalysisAdapter, mock_anthropic_client: MagicMock
    ) -> None:
        """Should clamp relevance_assessment to 1.0 if LLM returns > 1."""
        mock_anthropic_client.messages.create.return_value = _make_response(
            json.dumps(
                {
                    "summary": "s",
                    "remediation_recommendation": "r",
                    "relevance_assessment": 1.5,
                    "reasoning": "re",
                }
            )
        )

        result = await adapter.analyze_vulnerability("CVE-2024-0001", {})
        assert result.relevance_assessment == 1.0

    @pytest.mark.asyncio
    async def test_clamps_relevance_below_zero(
        self, adapter: AnthropicAnalysisAdapter, mock_anthropic_client: MagicMock
    ) -> None:
        """Should clamp relevance_assessment to 0.0 if LLM returns < 0."""
        mock_anthropic_client.messages.create.return_value = _make_response(
            json.dumps(
                {
                    "summary": "s",
                    "remediation_recommendation": "r",
                    "relevance_assessment": -0.5,
                    "reasoning": "re",
                }
            )
        )

        result = await adapter.analyze_vulnerability("CVE-2024-0001", {})
        assert result.relevance_assessment == 0.0

    @pytest.mark.asyncio
    async def test_fail_open_on_api_error(
        self, adapter: AnthropicAnalysisAdapter, mock_anthropic_client: MagicMock
    ) -> None:
        """Should return safe defaults on API error (fail-open)."""
        mock_anthropic_client.messages.create.side_effect = RuntimeError("API down")

        result = await adapter.analyze_vulnerability("CVE-2024-0001", {})

        assert isinstance(result, VulnerabilityAnalysis)
        assert result.summary == ""
        assert result.remediation_recommendation == ""
        assert result.relevance_assessment == DEFAULT_RELEVANCE
        assert result.reasoning == ""

    @pytest.mark.asyncio
    async def test_fail_open_on_invalid_json(
        self, adapter: AnthropicAnalysisAdapter, mock_anthropic_client: MagicMock
    ) -> None:
        """Should return safe defaults when LLM returns invalid JSON."""
        mock_anthropic_client.messages.create.return_value = _make_response(
            "This is not JSON at all"
        )

        result = await adapter.analyze_vulnerability("CVE-2024-0001", {})

        assert result.summary == ""
        assert result.relevance_assessment == DEFAULT_RELEVANCE

    @pytest.mark.asyncio
    async def test_prompt_includes_cve_id(
        self, adapter: AnthropicAnalysisAdapter, mock_anthropic_client: MagicMock
    ) -> None:
        """Should include CVE ID in the user prompt."""
        mock_anthropic_client.messages.create.return_value = _make_response(
            json.dumps(
                {
                    "summary": "s",
                    "remediation_recommendation": "r",
                    "relevance_assessment": 0.5,
                    "reasoning": "re",
                }
            )
        )

        await adapter.analyze_vulnerability(
            "CVE-2021-44228",
            {"description": "test"},
        )

        call_kwargs = mock_anthropic_client.messages.create.call_args
        messages = call_kwargs.kwargs["messages"]
        assert "CVE-2021-44228" in messages[0]["content"]


class TestEvaluateConfidence:
    """Tests for evaluate_confidence method."""

    @pytest.mark.asyncio
    async def test_successful_confidence_eval(
        self, adapter: AnthropicAnalysisAdapter, mock_anthropic_client: MagicMock
    ) -> None:
        """Should parse confidence score from valid JSON response."""
        mock_anthropic_client.messages.create.return_value = _make_response(
            json.dumps({"confidence": 0.85})
        )

        result = await adapter.evaluate_confidence(
            cve_id="CVE-2024-0001",
            classification={"risk_level": "HIGH"},
            enrichment={"epss_score": 0.7},
        )

        assert result == 0.85

    @pytest.mark.asyncio
    async def test_uses_haiku_model(
        self, adapter: AnthropicAnalysisAdapter, mock_anthropic_client: MagicMock
    ) -> None:
        """Should use the Haiku model for confidence evaluation."""
        mock_anthropic_client.messages.create.return_value = _make_response(
            json.dumps({"confidence": 0.5})
        )

        await adapter.evaluate_confidence("CVE-2024-0001", {}, {})

        call_kwargs = mock_anthropic_client.messages.create.call_args
        assert call_kwargs.kwargs["model"] == "claude-haiku-4-5-20251001"

    @pytest.mark.asyncio
    async def test_clamps_confidence(
        self, adapter: AnthropicAnalysisAdapter, mock_anthropic_client: MagicMock
    ) -> None:
        """Should clamp confidence to [0.0, 1.0]."""
        mock_anthropic_client.messages.create.return_value = _make_response(
            json.dumps({"confidence": 2.0})
        )
        result = await adapter.evaluate_confidence("CVE-2024-0001", {}, {})
        assert result == 1.0

    @pytest.mark.asyncio
    async def test_fail_open_on_error(
        self, adapter: AnthropicAnalysisAdapter, mock_anthropic_client: MagicMock
    ) -> None:
        """Should return default confidence on API error (fail-open)."""
        mock_anthropic_client.messages.create.side_effect = RuntimeError("timeout")

        result = await adapter.evaluate_confidence("CVE-2024-0001", {}, {})

        assert result == DEFAULT_CONFIDENCE

    @pytest.mark.asyncio
    async def test_fail_open_on_invalid_json(
        self, adapter: AnthropicAnalysisAdapter, mock_anthropic_client: MagicMock
    ) -> None:
        """Should return default confidence when LLM returns invalid JSON."""
        mock_anthropic_client.messages.create.return_value = _make_response("not json")

        result = await adapter.evaluate_confidence("CVE-2024-0001", {}, {})
        assert result == DEFAULT_CONFIDENCE


class TestHelperFunctions:
    """Tests for module-level helper functions."""

    def test_format_context_dict(self) -> None:
        """Should format a dict as indented JSON."""
        ctx: dict[str, Any] = {"key": "value", "num": 42}
        result = _format_context(ctx)
        assert '"key": "value"' in result

    def test_format_context_truncation(self) -> None:
        """Should truncate context exceeding MAX_CONTEXT_LENGTH."""
        long_ctx: dict[str, str] = {"data": "x" * 10_000}
        result = _format_context(long_ctx)
        assert len(result) <= 6_000

    def test_parse_analysis_response_plain_json(self) -> None:
        """Should parse plain JSON."""
        raw = '{"summary": "test", "confidence": 0.9}'
        parsed = _parse_analysis_response(raw)
        assert parsed["summary"] == "test"

    def test_parse_analysis_response_with_markdown_fences(self) -> None:
        """Should strip markdown fences before parsing."""
        raw = '```json\n{"summary": "test"}\n```'
        parsed = _parse_analysis_response(raw)
        assert parsed["summary"] == "test"
