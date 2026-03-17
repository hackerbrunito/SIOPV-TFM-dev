"""Port interface for Jira ticket management in SIOPV Phase 8.

Defines the contract for creating and managing Jira security tickets
from classified vulnerabilities. Implementations live in adapters/.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class JiraClientPort(ABC):
    """Port interface for Jira API client.

    Implementations must handle:
    - Authentication (API token or OAuth)
    - Rate limiting per Jira Cloud/Server limits
    - Field mapping from SIOPV vulnerability data to Jira issue fields
    """

    @abstractmethod
    async def create_ticket(self, vulnerability_data: dict[str, Any]) -> str:
        """Create a Jira ticket for a classified vulnerability.

        Args:
            vulnerability_data: Dictionary with vulnerability details
                (cve_id, severity, risk_score, recommendation, etc.)

        Returns:
            Jira ticket key (e.g., 'SEC-123')

        Raises:
            JiraClientError: On API errors after retries exhausted
        """
        ...

    @abstractmethod
    async def update_ticket(self, ticket_key: str, fields: dict[str, Any]) -> None:
        """Update fields on an existing Jira ticket.

        Args:
            ticket_key: Jira issue key (e.g., 'SEC-123')
            fields: Dictionary of field names to new values

        Raises:
            JiraClientError: On API errors or if ticket not found
        """
        ...

    @abstractmethod
    async def find_ticket_by_cve(self, cve_id: str) -> str | None:
        """Find an existing Jira ticket for a CVE identifier.

        Uses JQL search to locate tickets by CVE ID custom field or summary.

        Args:
            cve_id: CVE identifier (e.g., 'CVE-2021-44228')

        Returns:
            Jira ticket key if found, None otherwise

        Raises:
            JiraClientError: On API errors during search
        """
        ...


__all__ = [
    "JiraClientPort",
]
