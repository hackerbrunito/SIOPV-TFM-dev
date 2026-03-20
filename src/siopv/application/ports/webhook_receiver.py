"""Port interface for webhook payload reception in SIOPV.

Defines the contract for receiving and validating inbound webhook payloads
(e.g., from CI/CD pipelines sending Trivy scan results).
Implementations live in adapters/inbound/.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class WebhookReceiverPort(ABC):
    """Port interface for receiving webhook payloads.

    Implementations must handle:
    - Payload signature verification (e.g., HMAC-SHA256)
    - Payload parsing and validation
    - Asynchronous pipeline triggering
    """

    @abstractmethod
    async def receive_payload(
        self,
        payload: bytes,
        signature: str | None,
    ) -> dict[str, Any]:
        """Receive and validate a webhook payload.

        Args:
            payload: Raw request body bytes
            signature: Cryptographic signature from the webhook sender
                (e.g., HMAC-SHA256 hex digest). None if header was absent.

        Returns:
            Parsed payload as a dictionary

        Raises:
            WebhookAuthenticationError: If signature verification fails
            WebhookPayloadError: If payload is malformed or invalid
        """
        ...


__all__ = [
    "WebhookReceiverPort",
]
