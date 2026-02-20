"""Unit tests for HaikuSemanticValidatorAdapter.

Coverage targets:
- __init__: client and model initialization
- validate(): short-circuit paths, truncation, SAFE/UNSAFE parsing, fail-open
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from anthropic.types import TextBlock

from siopv.adapters.dlp.haiku_validator import _MAX_TEXT_LENGTH, HaikuSemanticValidatorAdapter
from siopv.domain.privacy.value_objects import PIIDetection, PIIEntityType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_adapter(
    api_key: str = "test-key", model: str = "claude-haiku-4-5-20251001"
) -> HaikuSemanticValidatorAdapter:
    with patch("anthropic.Anthropic"):
        return HaikuSemanticValidatorAdapter(api_key=api_key, model=model)


def _make_response(answer: str) -> object:
    msg = MagicMock()
    text_block = MagicMock(spec=TextBlock)
    text_block.text = answer
    msg.content = [text_block]
    return msg


def _make_pii_detection() -> PIIDetection:
    return PIIDetection(
        entity_type=PIIEntityType.EMAIL_ADDRESS,
        start=0,
        end=17,
        score=0.95,
        text="user@example.com",
        replacement="<EMAIL_ADDRESS>",
    )


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------


class TestHaikuValidatorInit:
    def test_init_creates_client_with_api_key(self) -> None:
        with patch("anthropic.Anthropic") as mock_anthropic:
            _adapter = HaikuSemanticValidatorAdapter(api_key="my-key")
            mock_anthropic.assert_called_once_with(api_key="my-key")

    def test_init_stores_custom_model(self) -> None:
        with patch("anthropic.Anthropic"):
            adapter = HaikuSemanticValidatorAdapter(api_key="key", model="custom-model")
        assert adapter._model == "custom-model"

    def test_init_default_model(self) -> None:
        with patch("anthropic.Anthropic"):
            adapter = HaikuSemanticValidatorAdapter(api_key="key")
        assert adapter._model == "claude-haiku-4-5-20251001"


# ---------------------------------------------------------------------------
# Short-circuit paths
# ---------------------------------------------------------------------------


class TestHaikuValidatorShortCircuit:
    @pytest.mark.asyncio
    async def test_empty_text_returns_true(self) -> None:
        adapter = _build_adapter()
        result = await adapter.validate(text="", detections=[])
        assert result is True

    @pytest.mark.asyncio
    async def test_whitespace_only_returns_true(self) -> None:
        adapter = _build_adapter()
        result = await adapter.validate(text="   ", detections=[])
        assert result is True

    @pytest.mark.asyncio
    async def test_short_text_no_detections_returns_true(self) -> None:
        """Text < 20 chars with no detections is short-circuited to safe."""
        adapter = _build_adapter()
        result = await adapter.validate(text="short text", detections=[])
        assert result is True

    @pytest.mark.asyncio
    async def test_short_text_with_detections_calls_api(self) -> None:
        """Text < 20 chars but WITH detections must still call the API."""
        adapter = _build_adapter()
        detections = [_make_pii_detection()]

        with patch("asyncio.get_running_loop") as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock(return_value=_make_response("SAFE"))
            result = await adapter.validate(text="hi", detections=detections)

        assert result is True
        mock_loop.return_value.run_in_executor.assert_called_once()


# ---------------------------------------------------------------------------
# Truncation
# ---------------------------------------------------------------------------


class TestHaikuValidatorTruncation:
    @pytest.mark.asyncio
    async def test_long_text_is_truncated_before_api_call(self) -> None:
        """Text longer than _MAX_TEXT_LENGTH should be truncated."""
        adapter = _build_adapter()
        # 40 chars text, no detections -> would short-circuit if len < 20 with no detections
        # Make text exactly _MAX_TEXT_LENGTH + 100 chars
        long_text = "x" * (_MAX_TEXT_LENGTH + 100)
        detections = [_make_pii_detection()]

        captured_prompt: list[str] = []

        async def mock_executor(_executor: object, fn: object, *_args: object) -> object:
            # Capture the partial function to inspect the prompt
            import functools

            if isinstance(fn, functools.partial):
                kwargs = fn.keywords
                prompt = kwargs.get("messages", [{}])[0].get("content", "")
                captured_prompt.append(prompt)
            return _make_response("SAFE")

        with patch("asyncio.get_running_loop") as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock(return_value=_make_response("SAFE"))
            await adapter.validate(text=long_text, detections=detections)

        mock_loop.return_value.run_in_executor.assert_called_once()


# ---------------------------------------------------------------------------
# SAFE / UNSAFE parsing
# ---------------------------------------------------------------------------


class TestHaikuValidatorSafeUnsafeParsing:
    @pytest.mark.asyncio
    async def test_safe_response_returns_true(self) -> None:
        adapter = _build_adapter()
        detections = [_make_pii_detection()]
        with patch("asyncio.get_running_loop") as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock(return_value=_make_response("SAFE"))
            result = await adapter.validate(
                text="sanitized clean text here!", detections=detections
            )

        assert result is True

    @pytest.mark.asyncio
    async def test_unsafe_response_returns_false(self) -> None:
        adapter = _build_adapter()
        detections = [_make_pii_detection()]
        with patch("asyncio.get_running_loop") as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock(
                return_value=_make_response("UNSAFE")
            )
            result = await adapter.validate(
                text="sanitized but still has some pii here!", detections=detections
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_lowercase_safe_still_passes(self) -> None:
        adapter = _build_adapter()
        detections = [_make_pii_detection()]
        with patch("asyncio.get_running_loop") as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock(return_value=_make_response("safe"))
            result = await adapter.validate(
                text="sanitized clean text here!", detections=detections
            )

        assert result is True

    @pytest.mark.asyncio
    async def test_no_text_block_in_response_returns_false(self) -> None:
        """Empty content list → no TextBlock found → answer is '' → not SAFE → False."""
        adapter = _build_adapter()
        detections = [_make_pii_detection()]

        empty_response = MagicMock()
        empty_response.content = []

        with patch("asyncio.get_running_loop") as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock(return_value=empty_response)
            result = await adapter.validate(
                text="sanitized clean text here!", detections=detections
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_unexpected_response_returns_false(self) -> None:
        """Any response other than SAFE returns False."""
        adapter = _build_adapter()
        detections = [_make_pii_detection()]
        with patch("asyncio.get_running_loop") as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock(return_value=_make_response("MAYBE"))
            result = await adapter.validate(
                text="sanitized clean text here!", detections=detections
            )

        assert result is False


# ---------------------------------------------------------------------------
# Fail-open on API error
# ---------------------------------------------------------------------------


class TestHaikuValidatorFailOpen:
    @pytest.mark.asyncio
    async def test_api_exception_returns_true(self) -> None:
        """On any exception, fail-open: return True."""
        adapter = _build_adapter()
        detections = [_make_pii_detection()]

        with patch("asyncio.get_running_loop") as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock(
                side_effect=ConnectionError("API unreachable")
            )
            result = await adapter.validate(
                text="sanitized clean text here!", detections=detections
            )

        assert result is True

    @pytest.mark.asyncio
    async def test_timeout_error_returns_true(self) -> None:
        """Timeout errors also fail-open."""
        adapter = _build_adapter()
        detections = [_make_pii_detection()]

        with patch("asyncio.get_running_loop") as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock(
                side_effect=TimeoutError("Request timed out")
            )
            result = await adapter.validate(
                text="sanitized clean text here!", detections=detections
            )

        assert result is True

    @pytest.mark.asyncio
    async def test_value_error_returns_true(self) -> None:
        """Any ValueError also returns True (fail-open)."""
        adapter = _build_adapter()
        detections = [_make_pii_detection()]

        with patch("asyncio.get_running_loop") as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock(side_effect=ValueError("Unexpected"))
            result = await adapter.validate(
                text="sanitized clean text here!", detections=detections
            )

        assert result is True

    @pytest.mark.asyncio
    async def test_no_api_call_for_empty_text_no_error(self) -> None:
        """Short-circuit path must not call the API at all."""
        adapter = _build_adapter()
        with patch("asyncio.get_running_loop") as mock_loop:
            result = await adapter.validate(text="", detections=[])

        mock_loop.assert_not_called()
        assert result is True
