"""Unit tests for PresidioAdapter and helper functions.

Coverage targets:
- _build_analyzer(): happy path and PresidioUnavailableError when not installed
- _build_anonymizer(): happy path and PresidioUnavailableError when not installed
- _run_presidio(): no-detections path, successful sanitization, SanitizationError on failure
- PresidioAdapter.__init__: with/without semantic validation
- PresidioAdapter.sanitize(): empty text, no PII, PII found, with Haiku validation
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from siopv.adapters.dlp.presidio_adapter import (
    PresidioAdapter,
    _build_analyzer,
    _build_anonymizer,
    _run_presidio,
)
from siopv.domain.privacy.entities import SanitizationContext
from siopv.domain.privacy.exceptions import PresidioUnavailableError, SanitizationError
from siopv.domain.privacy.value_objects import PIIDetection, PIIEntityType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_presidio_result(
    entity_type: str = "EMAIL_ADDRESS", start: int = 0, end: int = 17
) -> object:
    """Create a mock Presidio RecognizerResult."""
    result = MagicMock()
    result.entity_type = entity_type
    result.start = start
    result.end = end
    result.score = 0.85
    return result


def _make_anonymized(text: str = "<EMAIL_ADDRESS> is the admin") -> object:
    anon = MagicMock()
    anon.text = text
    return anon


# ---------------------------------------------------------------------------
# _build_analyzer
# ---------------------------------------------------------------------------


class TestBuildAnalyzer:
    def test_raises_when_presidio_unavailable(self) -> None:
        import siopv.adapters.dlp.presidio_adapter as mod

        original = mod.AnalyzerEngine
        try:
            mod.AnalyzerEngine = None  # type: ignore[assignment]
            with pytest.raises(
                PresidioUnavailableError, match="presidio-analyzer is not installed"
            ):
                _build_analyzer()
        finally:
            mod.AnalyzerEngine = original

    def test_returns_configured_analyzer(self) -> None:
        mock_analyzer = MagicMock()
        mock_pattern_cls = MagicMock()
        mock_recognizer_cls = MagicMock()

        import siopv.adapters.dlp.presidio_adapter as mod

        original_engine = mod.AnalyzerEngine
        original_pattern = mod.Pattern
        original_recognizer = mod.PatternRecognizer
        try:
            mod.AnalyzerEngine = MagicMock(return_value=mock_analyzer)  # type: ignore[assignment]
            mod.Pattern = mock_pattern_cls  # type: ignore[assignment]
            mod.PatternRecognizer = mock_recognizer_cls  # type: ignore[assignment]
            result = _build_analyzer()
        finally:
            mod.AnalyzerEngine = original_engine
            mod.Pattern = original_pattern
            mod.PatternRecognizer = original_recognizer

        assert result is mock_analyzer
        mock_analyzer.registry.add_recognizer.assert_called_once()


# ---------------------------------------------------------------------------
# _build_anonymizer
# ---------------------------------------------------------------------------


class TestBuildAnonymizer:
    def test_raises_when_presidio_anonymizer_unavailable(self) -> None:
        import siopv.adapters.dlp.presidio_adapter as mod

        original = mod.AnonymizerEngine
        try:
            mod.AnonymizerEngine = None  # type: ignore[assignment]
            with pytest.raises(
                PresidioUnavailableError, match="presidio-anonymizer is not installed"
            ):
                _build_anonymizer()
        finally:
            mod.AnonymizerEngine = original

    def test_returns_anonymizer_engine(self) -> None:
        mock_anonymizer = MagicMock()
        import siopv.adapters.dlp.presidio_adapter as mod

        original = mod.AnonymizerEngine
        try:
            mod.AnonymizerEngine = MagicMock(return_value=mock_anonymizer)  # type: ignore[assignment]
            result = _build_anonymizer()
        finally:
            mod.AnonymizerEngine = original

        assert result is mock_anonymizer


# ---------------------------------------------------------------------------
# _run_presidio
# ---------------------------------------------------------------------------


class TestRunPresidio:
    def test_no_detections_returns_original_text(self) -> None:
        analyzer = MagicMock()
        analyzer.analyze.return_value = []  # No PII found
        anonymizer = MagicMock()

        ctx = SanitizationContext(text="This is clean text with no PII.")
        sanitized, detections = _run_presidio(analyzer, anonymizer, ctx)

        assert sanitized == ctx.text
        assert detections == []
        anonymizer.anonymize.assert_not_called()

    def test_detections_triggers_anonymization(self) -> None:
        presidio_result = _make_presidio_result("EMAIL_ADDRESS", 0, 17)
        analyzer = MagicMock()
        analyzer.analyze.return_value = [presidio_result]

        anonymizer = MagicMock()
        anonymizer.anonymize.return_value = _make_anonymized("<EMAIL_ADDRESS> is the admin")

        import siopv.adapters.dlp.presidio_adapter as mod

        original_op = mod.OperatorConfig
        try:
            mod.OperatorConfig = MagicMock()  # type: ignore[assignment]
            ctx = SanitizationContext(text="user@example.com is the admin")
            sanitized, detections = _run_presidio(analyzer, anonymizer, ctx)
        finally:
            mod.OperatorConfig = original_op

        assert "<EMAIL_ADDRESS>" in sanitized
        assert len(detections) == 1
        assert detections[0].entity_type == PIIEntityType.EMAIL_ADDRESS

    def test_presidio_exception_raises_sanitization_error(self) -> None:
        analyzer = MagicMock()
        analyzer.analyze.side_effect = RuntimeError("Presidio internal error")
        anonymizer = MagicMock()

        ctx = SanitizationContext(text="some text to analyze")
        with pytest.raises(SanitizationError, match="Presidio processing failed"):
            _run_presidio(analyzer, anonymizer, ctx)

    def test_multiple_entity_types_all_redacted(self) -> None:
        person_result = _make_presidio_result("PERSON", 0, 8)
        email_result = _make_presidio_result("EMAIL_ADDRESS", 20, 37)

        analyzer = MagicMock()
        analyzer.analyze.return_value = [person_result, email_result]

        anonymizer = MagicMock()
        anonymizer.anonymize.return_value = _make_anonymized("<PERSON> contact at <EMAIL_ADDRESS>")

        import siopv.adapters.dlp.presidio_adapter as mod

        original_op = mod.OperatorConfig
        try:
            mod.OperatorConfig = MagicMock()  # type: ignore[assignment]
            ctx = SanitizationContext(text="John Doe contact at john@example.com")
            _sanitized, detections = _run_presidio(analyzer, anonymizer, ctx)
        finally:
            mod.OperatorConfig = original_op

        assert len(detections) == 2

    def test_passes_language_and_threshold_to_analyzer(self) -> None:
        analyzer = MagicMock()
        analyzer.analyze.return_value = []
        anonymizer = MagicMock()

        ctx = SanitizationContext(
            text="clean text longer than usual",
            language="fr",
            score_threshold=0.8,
            entities_to_detect=["PERSON"],
        )
        _run_presidio(analyzer, anonymizer, ctx)

        analyzer.analyze.assert_called_once_with(
            text=ctx.text,
            language="fr",
            entities=["PERSON"],
            score_threshold=0.8,
        )


# ---------------------------------------------------------------------------
# PresidioAdapter.__init__
# ---------------------------------------------------------------------------


def _build_presidio_adapter(
    api_key: str = "test-key",
    enable_semantic_validation: bool = True,
) -> PresidioAdapter:
    with (
        patch("siopv.adapters.dlp.presidio_adapter._build_analyzer") as mock_ana,
        patch("siopv.adapters.dlp.presidio_adapter._build_anonymizer") as mock_anon,
        patch("anthropic.Anthropic"),
    ):
        mock_ana.return_value = MagicMock()
        mock_anon.return_value = MagicMock()
        return PresidioAdapter(
            api_key=api_key,
            haiku_model="claude-haiku-4-5-20251001",
            enable_semantic_validation=enable_semantic_validation,
        )


class TestPresidioAdapterInit:
    def test_init_with_semantic_validation_enabled(self) -> None:
        adapter = _build_presidio_adapter(enable_semantic_validation=True)
        assert adapter._haiku_validator is not None

    def test_init_with_semantic_validation_disabled(self) -> None:
        adapter = _build_presidio_adapter(enable_semantic_validation=False)
        assert adapter._haiku_validator is None

    def test_init_empty_api_key_disables_haiku(self) -> None:
        with (
            patch("siopv.adapters.dlp.presidio_adapter._build_analyzer") as mock_ana,
            patch("siopv.adapters.dlp.presidio_adapter._build_anonymizer") as mock_anon,
            patch("anthropic.Anthropic"),
        ):
            mock_ana.return_value = MagicMock()
            mock_anon.return_value = MagicMock()
            adapter = PresidioAdapter(
                api_key="", haiku_model="claude-haiku-4-5-20251001", enable_semantic_validation=True
            )

        assert adapter._haiku_validator is None

    def test_init_stores_analyzer_and_anonymizer(self) -> None:
        adapter = _build_presidio_adapter()
        assert adapter._analyzer is not None
        assert adapter._anonymizer is not None

    def test_custom_haiku_model_passed_through(self) -> None:
        with (
            patch("siopv.adapters.dlp.presidio_adapter._build_analyzer") as mock_ana,
            patch("siopv.adapters.dlp.presidio_adapter._build_anonymizer") as mock_anon,
            patch(
                "siopv.adapters.dlp.presidio_adapter.HaikuSemanticValidatorAdapter"
            ) as mock_haiku_cls,
        ):
            mock_ana.return_value = MagicMock()
            mock_anon.return_value = MagicMock()
            PresidioAdapter(
                api_key="key", haiku_model="custom-model", enable_semantic_validation=True
            )

        mock_haiku_cls.assert_called_once_with(api_key="key", model="custom-model")


# ---------------------------------------------------------------------------
# PresidioAdapter.sanitize
# ---------------------------------------------------------------------------


class TestPresidioAdapterSanitize:
    @pytest.mark.asyncio
    async def test_empty_text_returns_safe_without_presidio(self) -> None:
        adapter = _build_presidio_adapter()
        ctx = SanitizationContext(text="")
        result = await adapter.sanitize(ctx)

        assert result.sanitized_text == ""
        assert result.presidio_passed is True
        assert result.total_redactions == 0

    @pytest.mark.asyncio
    async def test_whitespace_only_returns_safe(self) -> None:
        adapter = _build_presidio_adapter()
        ctx = SanitizationContext(text="   ")
        result = await adapter.sanitize(ctx)

        assert result.total_redactions == 0
        assert result.presidio_passed is True

    @pytest.mark.asyncio
    async def test_no_pii_returns_original_text(self) -> None:
        adapter = _build_presidio_adapter(enable_semantic_validation=False)

        with patch("asyncio.get_running_loop") as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock(
                return_value=("clean text here!", [])
            )
            ctx = SanitizationContext(text="clean text here!")
            result = await adapter.sanitize(ctx)

        assert result.sanitized_text == "clean text here!"
        assert result.total_redactions == 0
        assert result.presidio_passed is True
        assert result.semantic_passed is True

    @pytest.mark.asyncio
    async def test_pii_found_returns_redacted_text(self) -> None:
        adapter = _build_presidio_adapter(enable_semantic_validation=False)
        detection = PIIDetection(
            entity_type=PIIEntityType.EMAIL_ADDRESS,
            start=0,
            end=17,
            score=0.95,
            text="user@example.com",
            replacement="<EMAIL_ADDRESS>",
        )

        with patch("asyncio.get_running_loop") as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock(
                return_value=("<EMAIL_ADDRESS> is the admin", [detection])
            )
            ctx = SanitizationContext(text="user@example.com is the admin")
            result = await adapter.sanitize(ctx)

        assert result.total_redactions == 1
        assert result.sanitized_text == "<EMAIL_ADDRESS> is the admin"
        assert result.presidio_passed is True

    @pytest.mark.asyncio
    async def test_haiku_validation_called_when_enabled(self) -> None:
        adapter = _build_presidio_adapter(enable_semantic_validation=True)

        mock_haiku = AsyncMock()
        mock_haiku.validate = AsyncMock(return_value=True)
        adapter._haiku_validator = mock_haiku

        detection = PIIDetection(
            entity_type=PIIEntityType.EMAIL_ADDRESS,
            start=0,
            end=17,
            score=0.95,
            text="user@example.com",
            replacement="<EMAIL_ADDRESS>",
        )

        with patch("asyncio.get_running_loop") as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock(
                return_value=("<EMAIL_ADDRESS> is here", [detection])
            )
            ctx = SanitizationContext(text="user@example.com is here")
            result = await adapter.sanitize(ctx)

        mock_haiku.validate.assert_called_once()
        assert result.semantic_passed is True

    @pytest.mark.asyncio
    async def test_haiku_returns_false_sets_semantic_failed(self) -> None:
        adapter = _build_presidio_adapter(enable_semantic_validation=True)

        mock_haiku = AsyncMock()
        mock_haiku.validate = AsyncMock(return_value=False)
        adapter._haiku_validator = mock_haiku

        with patch("asyncio.get_running_loop") as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock(
                return_value=("still has something: sk-abc123", [])
            )
            ctx = SanitizationContext(text="still has something: sk-abc123")
            result = await adapter.sanitize(ctx)

        assert result.semantic_passed is False

    @pytest.mark.asyncio
    async def test_haiku_skipped_when_disabled(self) -> None:
        adapter = _build_presidio_adapter(enable_semantic_validation=False)
        assert adapter._haiku_validator is None

        with patch("asyncio.get_running_loop") as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock(
                return_value=("clean text here!", [])
            )
            ctx = SanitizationContext(text="clean text here!")
            result = await adapter.sanitize(ctx)

        assert result.semantic_passed is True  # Default True when Haiku skipped

    @pytest.mark.asyncio
    async def test_result_contains_original_text(self) -> None:
        adapter = _build_presidio_adapter(enable_semantic_validation=False)
        original = "some text for testing purposes"

        with patch("asyncio.get_running_loop") as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock(return_value=(original, []))
            ctx = SanitizationContext(text=original)
            result = await adapter.sanitize(ctx)

        assert result.original_text == original
