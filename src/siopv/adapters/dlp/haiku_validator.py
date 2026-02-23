"""Haiku semantic validator adapter for DLP second-pass validation.

Uses Claude Haiku to perform semantic validation of text after Presidio
has already run its rule-based sanitization. This catches contextual PII
that pattern matching may miss.

Fail-open design: any API error returns True (safe) so that Presidio's
first pass is still the primary protection layer.
"""

from __future__ import annotations

import asyncio
import functools
from typing import TYPE_CHECKING

import structlog

from siopv.adapters.dlp._haiku_utils import (
    MAX_TEXT_LENGTH,
    create_haiku_client,
    extract_text_from_response,
    truncate_for_haiku,
)

MIN_SHORT_TEXT_LENGTH = 20

# Backward-compatible alias used by existing tests
_MAX_TEXT_LENGTH = MAX_TEXT_LENGTH

if TYPE_CHECKING:
    from siopv.domain.privacy.value_objects import PIIDetection

logger = structlog.get_logger(__name__)

_VALIDATION_PROMPT = """\
You are a privacy validator. Analyze the following text and determine if it contains any \
personally identifiable information (PII), secrets, API keys, passwords, or other sensitive data \
that should be redacted.

Text to analyze:
{text}

Respond with exactly one word:
- "SAFE" if the text is clean and contains no sensitive information
- "UNSAFE" if the text still contains sensitive information that needs redaction

Response:\
"""


class HaikuSemanticValidatorAdapter:
    """Semantic validator using Claude Haiku as the LLM backend.

    Implements the SemanticValidatorPort protocol via structural subtyping.
    Uses the synchronous Anthropic client called from an executor so the
    async interface is non-blocking.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-haiku-4-5-20251001",
    ) -> None:
        """Initialise the adapter.

        Args:
            api_key: Anthropic API key.
            model: Claude model identifier (defaults to Haiku).
        """
        self._client = create_haiku_client(api_key)
        self._model = model

    async def _call_haiku(self, prompt: str) -> str:
        """Call Haiku API and return the raw response text.

        Args:
            prompt: Formatted validation prompt to send to the model.

        Returns:
            Raw text content from the Haiku response.
        """
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            functools.partial(
                self._client.messages.create,
                model=self._model,
                max_tokens=10,
                messages=[{"role": "user", "content": prompt}],
            ),
        )
        return extract_text_from_response(response)

    async def _run_haiku_check(
        self,
        text_to_validate: str,
        detections: list[PIIDetection],
    ) -> bool:
        """Invoke Haiku, interpret the SAFE/UNSAFE response, and handle errors.

        Args:
            text_to_validate: The (possibly truncated) text to check.
            detections: PII detections from Presidio (for logging context).

        Returns:
            True if Haiku reports SAFE or on any API error (fail-open).
        """
        try:
            prompt = _VALIDATION_PROMPT.format(text=text_to_validate)
            answer = (await self._call_haiku(prompt)).upper()
            is_safe = answer == "SAFE"
            logger.info(
                "haiku_validator_result",
                response=answer,
                is_safe=is_safe,
                text_length=len(text_to_validate),
                detection_count=len(detections),
            )
        except Exception:
            # Fail-open: Presidio has already run; log and allow to proceed
            logger.warning(
                "haiku_validator_api_error_fail_open",
                model=self._model,
                exc_info=True,
            )
            return True
        else:
            return is_safe

    async def validate(self, text: str, detections: list[PIIDetection]) -> bool:
        """Validate that sanitized text contains no remaining PII.

        Short-circuits to True when:
        - Text is empty or very short (< 20 chars) and no detections found.
        - Text exceeds MAX_TEXT_LENGTH (truncated validation would be unreliable).

        On any API error, logs a warning and returns True (fail-open).

        Args:
            text: The already-sanitized text to validate.
            detections: PII detections from the first-pass Presidio scan.

        Returns:
            True if text is safe, False if remaining PII detected.
        """
        # Short-circuit: trivially safe text
        if not text.strip() or (len(text) < MIN_SHORT_TEXT_LENGTH and not detections):
            logger.debug("haiku_validator_skip_short_text", text_length=len(text))
            return True

        # Truncate very long texts to avoid runaway costs
        text_to_validate = truncate_for_haiku(text)
        if len(text) > MAX_TEXT_LENGTH:
            logger.warning(
                "haiku_validator_text_truncated",
                original_length=len(text),
                truncated_to=MAX_TEXT_LENGTH,
            )

        return await self._run_haiku_check(text_to_validate, detections)


__all__ = ["HaikuSemanticValidatorAdapter"]
