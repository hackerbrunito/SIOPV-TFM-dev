"""Shared Anthropic client utilities for all adapters.

Provides common functions for creating Anthropic clients and extracting
text from API responses. Used by both DLP and LLM adapters to avoid
cross-adapter imports.
"""

from __future__ import annotations

import anthropic
from anthropic.types import Message, TextBlock

# Maximum text length to send to Haiku (avoid excessive token cost)
MAX_TEXT_LENGTH: int = 4_000


def create_haiku_client(api_key: str) -> anthropic.Anthropic:
    """Create a synchronous Anthropic client for Haiku API calls."""
    return anthropic.Anthropic(api_key=api_key)


def truncate_for_haiku(text: str) -> str:
    """Truncate text to MAX_TEXT_LENGTH characters."""
    return text[:MAX_TEXT_LENGTH]


def extract_text_from_response(response: Message) -> str:
    """Extract and strip text content from an Anthropic Message response.

    Returns empty string if no TextBlock is present in the response.
    """
    text_block = next((b for b in response.content if isinstance(b, TextBlock)), None)
    return text_block.text.strip() if text_block else ""


__all__ = [
    "MAX_TEXT_LENGTH",
    "create_haiku_client",
    "extract_text_from_response",
    "truncate_for_haiku",
]
