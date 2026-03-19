"""Shared utilities for Haiku-based Anthropic API calls.

Moved from adapters/dlp/_haiku_utils.py to infrastructure/clients/
to resolve cross-adapter hex-arch violation (Issue 2).
"""

from __future__ import annotations

import asyncio
import functools

import anthropic
from anthropic.types import Message, TextBlock

# Legacy constant kept for backward compatibility with callers that
# haven't been wired to settings yet.  New code should pass max_length
# explicitly (sourced from settings.haiku_max_text_length).
MAX_TEXT_LENGTH: int = 4_000


def create_haiku_client(api_key: str) -> anthropic.Anthropic:
    """Create a synchronous Anthropic client for Haiku API calls."""
    return anthropic.Anthropic(api_key=api_key)


def truncate_for_haiku(text: str, max_length: int = MAX_TEXT_LENGTH) -> str:
    """Truncate text to *max_length* characters.

    Args:
        text: The text to truncate.
        max_length: Maximum character count.  Defaults to MAX_TEXT_LENGTH
            for backward compatibility; callers should pass the value from
            ``settings.haiku_max_text_length`` when available.
    """
    return text[:max_length]


def extract_text_from_response(response: Message) -> str:
    """Extract and strip text content from an Anthropic Message response.

    Returns empty string if no TextBlock is present in the response.
    """
    text_block = next((b for b in response.content if isinstance(b, TextBlock)), None)
    return text_block.text.strip() if text_block else ""


async def async_call_haiku(
    client: anthropic.Anthropic,
    model: str,
    system: str,
    messages: list[dict[str, str]],
    max_tokens: int,
) -> str:
    """Call Anthropic API via executor and return extracted text.

    Consolidates the repeated pattern of ``run_in_executor`` +
    ``messages.create`` + ``extract_text_from_response`` used across
    multiple adapters.

    Args:
        client: Synchronous Anthropic client instance.
        model: Model identifier (e.g. claude-haiku-4-5).
        system: System prompt.
        messages: List of message dicts (role/content).
        max_tokens: Max tokens for the response.

    Returns:
        Extracted text content from the first TextBlock in the response.
    """
    loop = asyncio.get_running_loop()
    response = await loop.run_in_executor(
        None,
        functools.partial(
            client.messages.create,
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
        ),
    )
    return extract_text_from_response(response)


__all__ = [
    "MAX_TEXT_LENGTH",
    "async_call_haiku",
    "create_haiku_client",
    "extract_text_from_response",
    "truncate_for_haiku",
]
