"""Tests for JiraClientPort ABC interface compliance."""

from __future__ import annotations

from typing import Any

import pytest

from siopv.application.ports.jira_client import JiraClientPort


class TestJiraClientPortInterface:
    """Tests for JiraClientPort ABC definition."""

    def test_jira_client_port_is_abstract(self) -> None:
        """JiraClientPort should not be directly instantiable."""
        with pytest.raises(TypeError):
            JiraClientPort()  # type: ignore[abstract]

    def test_concrete_implementation_instantiable(self) -> None:
        """A class implementing all abstract methods should be instantiable."""

        class ConcreteJiraClient(JiraClientPort):
            async def create_ticket(self, _vulnerability_data: dict[str, Any]) -> str:
                return "SEC-001"

            async def update_ticket(self, _ticket_key: str, _fields: dict[str, Any]) -> None:
                return None

            async def find_ticket_by_cve(self, _cve_id: str) -> str | None:
                return None

        client = ConcreteJiraClient()
        assert isinstance(client, JiraClientPort)

    def test_partial_implementation_not_instantiable(self) -> None:
        """A class missing abstract methods should not be instantiable."""

        class PartialJiraClient(JiraClientPort):
            async def create_ticket(self, _vulnerability_data: dict[str, Any]) -> str:
                return "SEC-001"

        with pytest.raises(TypeError):
            PartialJiraClient()  # type: ignore[abstract]

    @pytest.mark.asyncio
    async def test_create_ticket_returns_string(self) -> None:
        """create_ticket should return a ticket key string."""

        class StubJiraClient(JiraClientPort):
            async def create_ticket(self, _vulnerability_data: dict[str, Any]) -> str:
                return "SEC-123"

            async def update_ticket(self, _ticket_key: str, _fields: dict[str, Any]) -> None:
                return None

            async def find_ticket_by_cve(self, _cve_id: str) -> str | None:
                return None

        client = StubJiraClient()
        result = await client.create_ticket({"cve_id": "CVE-2024-1234"})
        assert result == "SEC-123"

    @pytest.mark.asyncio
    async def test_find_ticket_by_cve_returns_none_when_not_found(self) -> None:
        """find_ticket_by_cve should return None when no ticket exists."""

        class StubJiraClient(JiraClientPort):
            async def create_ticket(self, _vulnerability_data: dict[str, Any]) -> str:
                return "SEC-001"

            async def update_ticket(self, _ticket_key: str, _fields: dict[str, Any]) -> None:
                return None

            async def find_ticket_by_cve(self, _cve_id: str) -> str | None:
                return None

        client = StubJiraClient()
        result = await client.find_ticket_by_cve("CVE-2024-9999")
        assert result is None

    def test_port_importable_from_ports_package(self) -> None:
        """JiraClientPort should be importable from the ports package."""
        from siopv.application.ports import JiraClientPort as PortFromPackage

        assert PortFromPackage is JiraClientPort
