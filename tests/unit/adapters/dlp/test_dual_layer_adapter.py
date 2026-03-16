"""Unit tests for DualLayerDLPAdapter.

Tests cover:
- Layer 1 (Presidio) path when entities are found (Haiku skipped).
- Layer 2 (Haiku) path when Presidio finds 0 entities.
- Haiku fail-open behaviour on API error.
- _HaikuDLPAdapter JSON parsing including markdown fence stripping.
- DualLayerDLPAdapter empty-text short-circuit.
- create_dual_layer_adapter factory wiring.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from siopv.adapters.dlp.dual_layer_adapter import (
    DualLayerDLPAdapter,
    _HaikuDLPAdapter,
    create_dual_layer_adapter,
)
from siopv.domain.privacy.entities import DLPResult, SanitizationContext
from siopv.domain.privacy.value_objects import PIIDetection, PIIEntityType

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_pii_detection() -> PIIDetection:
    return PIIDetection(
        entity_type=PIIEntityType.EMAIL_ADDRESS,
        start=0,
        end=17,
        score=0.95,
        text="user@example.com",
        replacement="<EMAIL_ADDRESS>",
    )


def _clean_result(text: str = "clean text") -> DLPResult:
    return DLPResult.safe_text(text)


def _redacted_result(original: str = "user@example.com is the admin") -> DLPResult:
    detection = _make_pii_detection()
    return DLPResult(
        original_text=original,
        sanitized_text="<EMAIL_ADDRESS> is the admin",
        detections=[detection],
        presidio_passed=True,
        semantic_passed=True,
    )


# ---------------------------------------------------------------------------
# DualLayerDLPAdapter tests
# ---------------------------------------------------------------------------


class TestDualLayerDLPAdapterLayer1Wins:
    """When Presidio finds entities, Haiku must NOT be called."""

    @pytest.mark.asyncio
    async def test_haiku_skipped_when_presidio_finds_entities(self) -> None:
        presidio = AsyncMock()
        presidio.sanitize = AsyncMock(return_value=_redacted_result())

        haiku = AsyncMock()
        haiku.sanitize = AsyncMock()

        adapter = DualLayerDLPAdapter(presidio=presidio, haiku=haiku)
        ctx = SanitizationContext(text="user@example.com is the admin")
        result = await adapter.sanitize(ctx)

        haiku.sanitize.assert_not_called()
        assert result.total_redactions == 1
        assert "<EMAIL_ADDRESS>" in result.sanitized_text

    @pytest.mark.asyncio
    async def test_returns_presidio_result_directly(self) -> None:
        expected = _redacted_result()
        presidio = AsyncMock()
        presidio.sanitize = AsyncMock(return_value=expected)

        haiku = AsyncMock()
        haiku.sanitize = AsyncMock()

        adapter = DualLayerDLPAdapter(presidio=presidio, haiku=haiku)
        ctx = SanitizationContext(text="some text")
        result = await adapter.sanitize(ctx)

        assert result is expected


class TestDualLayerDLPAdapterLayer2Fallback:
    """When Presidio finds 0 entities, Haiku must be called."""

    @pytest.mark.asyncio
    async def test_haiku_called_when_presidio_clean(self) -> None:
        presidio = AsyncMock()
        presidio.sanitize = AsyncMock(return_value=_clean_result("no pii here"))

        haiku_result = DLPResult(
            original_text="no pii here",
            sanitized_text="no pii here",
            detections=[],
            presidio_passed=True,
            semantic_passed=True,
        )
        haiku = AsyncMock()
        haiku.sanitize = AsyncMock(return_value=haiku_result)

        adapter = DualLayerDLPAdapter(presidio=presidio, haiku=haiku)
        ctx = SanitizationContext(text="no pii here")
        result = await adapter.sanitize(ctx)

        haiku.sanitize.assert_called_once_with(ctx)
        assert result is haiku_result

    @pytest.mark.asyncio
    async def test_haiku_semantic_flag_propagated(self) -> None:
        presidio = AsyncMock()
        presidio.sanitize = AsyncMock(return_value=_clean_result("my secret token: abc123"))

        haiku_result = DLPResult(
            original_text="my secret token: abc123",
            sanitized_text="my secret token: <REDACTED>",
            detections=[],
            presidio_passed=True,
            semantic_passed=False,  # Haiku found something
        )
        haiku = AsyncMock()
        haiku.sanitize = AsyncMock(return_value=haiku_result)

        adapter = DualLayerDLPAdapter(presidio=presidio, haiku=haiku)
        ctx = SanitizationContext(text="my secret token: abc123")
        result = await adapter.sanitize(ctx)

        assert result.semantic_passed is False
        assert "<REDACTED>" in result.sanitized_text


# ---------------------------------------------------------------------------
# _HaikuDLPAdapter tests
# ---------------------------------------------------------------------------


def _build_haiku_adapter(api_key: str = "test-key") -> _HaikuDLPAdapter:
    with patch("anthropic.Anthropic"):
        return _HaikuDLPAdapter(api_key=api_key, model="claude-haiku-4-5-20251001")


class TestHaikuDLPAdapterEmptyText:
    @pytest.mark.asyncio
    async def test_empty_text_returns_safe(self) -> None:
        adapter = _build_haiku_adapter()
        ctx = SanitizationContext(text="")
        result = await adapter.sanitize(ctx)

        assert result.sanitized_text == ""
        assert result.semantic_passed is True
        assert result.total_redactions == 0

    @pytest.mark.asyncio
    async def test_whitespace_only_returns_safe(self) -> None:
        adapter = _build_haiku_adapter()
        ctx = SanitizationContext(text="   ")
        result = await adapter.sanitize(ctx)

        assert result.semantic_passed is True


class TestHaikuDLPAdapterJSONParsing:
    """Test JSON response parsing including edge cases."""

    def _make_response(self, json_body: str) -> object:
        from anthropic.types import TextBlock

        msg = MagicMock()
        text_block = MagicMock(spec=TextBlock)
        text_block.text = json_body
        msg.content = [text_block]
        return msg

    @pytest.mark.asyncio
    async def test_clean_json_no_sensitive_data(self) -> None:
        adapter = _build_haiku_adapter()
        text = "Vulnerability in libssl version 1.0.2"
        response_json = (
            '{"contains_sensitive": false, '
            '"sanitized_text": "Vulnerability in libssl version 1.0.2", '
            '"reason": "No PII or credentials found"}'
        )
        adapter._client.messages.create = MagicMock(  # type: ignore[attr-defined]
            return_value=self._make_response(response_json)
        )

        ctx = SanitizationContext(text=text)
        with patch("asyncio.get_running_loop") as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock(
                return_value=self._make_response(response_json)
            )
            result = await adapter.sanitize(ctx)

        assert result.semantic_passed is True
        assert result.sanitized_text == text

    @pytest.mark.asyncio
    async def test_sensitive_found_returns_sanitized_text(self) -> None:
        adapter = _build_haiku_adapter()
        text = "API key is sk-abc123 for the prod server"
        sanitized = "API key is <REDACTED> for the prod server"
        response_json = (
            f'{{"contains_sensitive": true, '
            f'"sanitized_text": "{sanitized}", '
            f'"reason": "API key detected"}}'
        )
        ctx = SanitizationContext(text=text)
        with patch("asyncio.get_running_loop") as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock(
                return_value=self._make_response(response_json)
            )
            result = await adapter.sanitize(ctx)

        assert result.semantic_passed is False
        assert result.sanitized_text == sanitized
        assert result.original_text == text

    @pytest.mark.asyncio
    async def test_markdown_fence_stripped(self) -> None:
        adapter = _build_haiku_adapter()
        text = "clean text"
        response_with_fence = (
            "```json\n"
            '{"contains_sensitive": false, '
            '"sanitized_text": "clean text", '
            '"reason": "Nothing found"}\n'
            "```"
        )
        ctx = SanitizationContext(text=text)
        with patch("asyncio.get_running_loop") as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock(
                return_value=self._make_response(response_with_fence)
            )
            result = await adapter.sanitize(ctx)

        assert result.semantic_passed is True

    @pytest.mark.asyncio
    async def test_api_error_fail_open(self) -> None:
        adapter = _build_haiku_adapter()
        text = "some vulnerability text"
        ctx = SanitizationContext(text=text)

        with patch("asyncio.get_running_loop") as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock(
                side_effect=ConnectionError("API unreachable")
            )
            result = await adapter.sanitize(ctx)

        # Fail-open: original text returned, no exception raised
        assert result.semantic_passed is True
        assert result.sanitized_text == text
        assert result.total_redactions == 0

    @pytest.mark.asyncio
    async def test_invalid_json_fail_open(self) -> None:
        adapter = _build_haiku_adapter()
        text = "some text"
        ctx = SanitizationContext(text=text)

        with patch("asyncio.get_running_loop") as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock(
                return_value=self._make_response("not valid json at all")
            )
            result = await adapter.sanitize(ctx)

        assert result.semantic_passed is True
        assert result.sanitized_text == text


# ---------------------------------------------------------------------------
# create_dual_layer_adapter factory
# ---------------------------------------------------------------------------


class TestCreateDualLayerAdapter:
    def test_returns_dual_layer_instance(self) -> None:
        with (
            patch("siopv.adapters.dlp.dual_layer_adapter.PresidioAdapter") as mock_presidio_cls,
            patch("anthropic.Anthropic"),
        ):
            mock_presidio_cls.return_value = MagicMock()
            adapter = create_dual_layer_adapter(
                api_key="test-key", haiku_model="claude-haiku-4-5-20251001"
            )

        assert isinstance(adapter, DualLayerDLPAdapter)

    def test_reads_api_key_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key-123")
        with (
            patch("siopv.adapters.dlp.dual_layer_adapter.PresidioAdapter") as mock_presidio_cls,
            patch("anthropic.Anthropic") as mock_anthropic,
        ):
            mock_presidio_cls.return_value = MagicMock()
            mock_anthropic.return_value = MagicMock()
            create_dual_layer_adapter(haiku_model="claude-haiku-4-5-20251001")  # no api_key param

        mock_anthropic.assert_called_once_with(api_key="env-key-123")
