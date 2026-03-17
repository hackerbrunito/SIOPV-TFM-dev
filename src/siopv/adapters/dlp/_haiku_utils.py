"""Shared utilities for Haiku-based DLP adapters.

Re-exports from infrastructure.clients.anthropic for backward compatibility.
New code should import directly from siopv.infrastructure.clients.anthropic.
"""

from __future__ import annotations

from siopv.infrastructure.clients.anthropic import (
    MAX_TEXT_LENGTH,
    create_haiku_client,
    extract_text_from_response,
    truncate_for_haiku,
)

__all__ = [
    "MAX_TEXT_LENGTH",
    "create_haiku_client",
    "extract_text_from_response",
    "truncate_for_haiku",
]
