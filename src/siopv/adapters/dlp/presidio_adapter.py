"""Presidio-based DLP adapter implementing the DLPPort.

Combines Microsoft Presidio (rule-based PII detection + anonymization) with
an optional Claude Haiku semantic validation pass.

Presidio's analyze() and anonymize() are synchronous; they are run in a
thread-pool executor so the async interface remains non-blocking.
"""

from __future__ import annotations

import asyncio
import functools
import importlib

import structlog

from siopv.adapters.dlp.haiku_validator import HaikuSemanticValidatorAdapter
from siopv.domain.privacy.entities import DLPResult, SanitizationContext
from siopv.domain.privacy.exceptions import PresidioUnavailableError, SanitizationError
from siopv.domain.privacy.value_objects import PIIDetection

_presidio_analyzer_err: ImportError | None = None
try:
    _pa = importlib.import_module("presidio_analyzer")
    AnalyzerEngine = _pa.AnalyzerEngine
    Pattern = _pa.Pattern
    PatternRecognizer = _pa.PatternRecognizer
except ImportError as exc:
    AnalyzerEngine = Pattern = PatternRecognizer = None
    _presidio_analyzer_err = exc

_presidio_anonymizer_err: ImportError | None = None
try:
    _pam = importlib.import_module("presidio_anonymizer")
    AnonymizerEngine = _pam.AnonymizerEngine
except ImportError as exc:
    AnonymizerEngine = None
    _presidio_anonymizer_err = exc

try:
    _pame = importlib.import_module("presidio_anonymizer.entities")
    OperatorConfig = _pame.OperatorConfig
except ImportError:
    OperatorConfig = None

logger = structlog.get_logger(__name__)

# Custom API-key / secret pattern recognizer regex
_API_KEY_REGEX = (
    r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]{20,})['\"]?"
)
_API_KEY_ENTITY = "API_KEY"


def _build_analyzer() -> object:
    """Build and return a configured Presidio AnalyzerEngine.

    Adds a custom PatternRecognizer for API keys / secrets beyond the
    built-in Presidio defaults.

    Returns:
        Configured AnalyzerEngine instance.

    Raises:
        PresidioUnavailableError: If presidio_analyzer cannot be imported.
    """
    if AnalyzerEngine is None:
        msg = "presidio-analyzer is not installed"
        raise PresidioUnavailableError(msg) from _presidio_analyzer_err

    analyzer = AnalyzerEngine()

    # Custom recognizer for API keys, tokens, secrets, passwords
    api_key_pattern = Pattern(
        name="api_key_pattern",
        regex=_API_KEY_REGEX,
        score=0.85,
    )
    api_key_recognizer = PatternRecognizer(
        supported_entity=_API_KEY_ENTITY,
        patterns=[api_key_pattern],
    )
    analyzer.registry.add_recognizer(api_key_recognizer)

    logger.debug("presidio_analyzer_initialized", custom_recognizers=["API_KEY"])
    return analyzer


def _build_anonymizer() -> object:
    """Build and return a configured Presidio AnonymizerEngine.

    Returns:
        AnonymizerEngine instance.

    Raises:
        PresidioUnavailableError: If presidio_anonymizer cannot be imported.
    """
    if AnonymizerEngine is None:
        msg = "presidio-anonymizer is not installed"
        raise PresidioUnavailableError(msg) from _presidio_anonymizer_err

    logger.debug("presidio_anonymizer_initialized")
    return AnonymizerEngine()


def _run_presidio(
    analyzer: object,
    anonymizer: object,
    context: SanitizationContext,
) -> tuple[str, list[PIIDetection]]:
    """Run Presidio analysis + anonymization synchronously.

    This function is intended to be called from a thread-pool executor so
    it does not block the event loop.

    Args:
        analyzer: Configured AnalyzerEngine.
        anonymizer: Configured AnonymizerEngine.
        context: SanitizationContext with text and parameters.

    Returns:
        Tuple of (sanitized_text, list_of_pii_detections).

    Raises:
        SanitizationError: On any Presidio processing error.
    """
    try:
        # Step 1: Detect PII
        analyzer_results = analyzer.analyze(  # type: ignore[attr-defined]
            text=context.text,
            language=context.language,
            entities=context.entities_to_detect,
            score_threshold=context.score_threshold,
        )

        if not analyzer_results:
            return context.text, []

        # Step 2: Build per-entity replacement operators (e.g. <PERSON>)
        entity_types: set[str] = {r.entity_type for r in analyzer_results}
        operators = {
            entity: OperatorConfig("replace", {"new_value": f"<{entity}>"})
            for entity in entity_types
        }
        # Fallback operator for any entity not explicitly mapped
        operators["DEFAULT"] = OperatorConfig("replace", {"new_value": "<REDACTED>"})

        # Step 3: Anonymize
        anonymized = anonymizer.anonymize(  # type: ignore[attr-defined]
            text=context.text,
            analyzer_results=analyzer_results,
            operators=operators,
        )

        # Step 4: Convert results to domain value objects
        detections: list[PIIDetection] = [
            PIIDetection.from_presidio(
                entity_type=r.entity_type,
                start=r.start,
                end=r.end,
                score=r.score,
                original_text=context.text,
            )
            for r in analyzer_results
        ]

    except Exception as exc:
        msg = f"Presidio processing failed: {exc}"
        raise SanitizationError(msg) from exc
    else:
        return anonymized.text, detections


class PresidioAdapter:
    """DLP adapter combining Presidio rule-based scanning with optional Haiku validation.

    Implements the DLPPort protocol via structural subtyping (no explicit
    inheritance required).

    Initialization is eager: Presidio engines are built in __init__ to
    surface import errors early rather than on first use.
    """

    def __init__(
        self,
        api_key: str,
        haiku_model: str = "claude-haiku-4-5-20251001",
        *,
        enable_semantic_validation: bool = True,
    ) -> None:
        """Initialise Presidio engines and optional Haiku validator.

        Args:
            api_key: Anthropic API key for Haiku semantic validation.
            haiku_model: Claude model ID to use for semantic validation.
            enable_semantic_validation: If False, skip Haiku validation step.
        """
        self._analyzer = _build_analyzer()
        self._anonymizer = _build_anonymizer()

        self._haiku_validator: HaikuSemanticValidatorAdapter | None = None
        if enable_semantic_validation and api_key:
            self._haiku_validator = HaikuSemanticValidatorAdapter(
                api_key=api_key,
                model=haiku_model,
            )
            logger.info(
                "presidio_adapter_initialized",
                semantic_validation=True,
                model=haiku_model,
            )
        else:
            logger.info(
                "presidio_adapter_initialized",
                semantic_validation=False,
            )

    async def sanitize(self, context: SanitizationContext) -> DLPResult:
        """Sanitize text using Presidio then optionally validate with Haiku.

        1. Runs Presidio analyze() + anonymize() in a thread-pool executor.
        2. If Haiku validator is configured, calls validate() on the result.
        3. Returns a DLPResult with all metadata.

        Args:
            context: SanitizationContext with text and detection parameters.

        Returns:
            DLPResult with sanitized text, detections, and validation flags.

        Raises:
            SanitizationError: If Presidio processing fails.
        """
        if not context.text.strip():
            return DLPResult.safe_text(context.text)

        # Run Presidio in thread-pool to avoid blocking the event loop
        loop = asyncio.get_running_loop()
        sanitized_text, detections = await loop.run_in_executor(
            None,
            functools.partial(
                _run_presidio,
                self._analyzer,
                self._anonymizer,
                context,
            ),
        )

        presidio_passed = True  # Presidio ran successfully (redactions applied if needed)

        # Optional semantic validation pass
        semantic_passed = True
        if self._haiku_validator is not None:
            semantic_passed = await self._haiku_validator.validate(
                text=sanitized_text,
                detections=detections,
            )

        logger.info(
            "dlp_sanitization_complete",
            original_length=len(context.text),
            sanitized_length=len(sanitized_text),
            detection_count=len(detections),
            presidio_passed=presidio_passed,
            semantic_passed=semantic_passed,
        )

        return DLPResult(
            original_text=context.text,
            sanitized_text=sanitized_text,
            detections=detections,
            presidio_passed=presidio_passed,
            semantic_passed=semantic_passed,
        )


__all__ = ["PresidioAdapter"]
