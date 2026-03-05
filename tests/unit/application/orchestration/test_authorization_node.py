"""Unit tests for authorization_node (Phase 5 gatekeeper).

Tests cover:
- Authorization allowed scenario
- Authorization denied scenario
- Skipped authorization (no user_id)
- Degraded mode (no authorization port)
- Error handling (AuthorizationCheckError)
- Routing function (route_after_authorization)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from siopv.application.orchestration.nodes.authorization_node import (
    authorization_node,
    route_after_authorization,
)
from siopv.domain.authorization import (
    Action,
    AuthorizationCheckError,
    AuthorizationContext,
    AuthorizationResult,
    Relation,
    ResourceId,
    ResourceType,
)


@pytest.fixture
def mock_authorization_port() -> MagicMock:
    """Create mock authorization port."""
    port = MagicMock()
    port.check = AsyncMock()
    return port


@pytest.fixture
def sample_context() -> AuthorizationContext:
    """Create sample authorization context."""
    resource = ResourceId(resource_type=ResourceType.PROJECT, identifier="project-456")
    return AuthorizationContext.for_action(
        user_id="user-123",
        resource=resource,
        action=Action.VIEW,
    )


@pytest.fixture
def allowed_result(sample_context: AuthorizationContext) -> AuthorizationResult:
    """Create an allowed authorization result."""
    return AuthorizationResult(
        allowed=True,
        context=sample_context,
        checked_relation=Relation.VIEWER,
        decision_id=uuid4(),
        check_duration_ms=5.0,
    )


@pytest.fixture
def denied_result(sample_context: AuthorizationContext) -> AuthorizationResult:
    """Create a denied authorization result."""
    return AuthorizationResult(
        allowed=False,
        context=sample_context,
        checked_relation=Relation.VIEWER,
        decision_id=uuid4(),
        check_duration_ms=5.0,
    )


@pytest.fixture
def base_state() -> dict[str, object]:
    """Create base pipeline state."""
    return {
        "thread_id": "test-thread-123",
        "user_id": "user-123",
        "project_id": "project-456",
        "vulnerabilities": [],
        "errors": [],
    }


class TestAuthorizationNode:
    """Tests for authorization_node function."""

    async def test_authorization_allowed(
        self,
        mock_authorization_port: MagicMock,
        allowed_result: AuthorizationResult,
        base_state: dict[str, object],
    ) -> None:
        """Test that allowed authorization returns correct state."""
        mock_authorization_port.check.return_value = allowed_result

        result = await authorization_node(
            base_state,  # type: ignore[arg-type]
            authorization_port=mock_authorization_port,
        )

        assert result["authorization_allowed"] is True
        assert result["authorization_skipped"] is False
        assert result["current_node"] == "authorize"
        assert result["authorization_result"] is not None
        assert result["authorization_result"]["allowed"] is True
        assert "user_id_hash" in result["authorization_result"]  # Pseudonymized
        assert result["authorization_result"]["project_id"] == "project-456"

    async def test_authorization_denied(
        self,
        mock_authorization_port: MagicMock,
        denied_result: AuthorizationResult,
        base_state: dict[str, object],
    ) -> None:
        """Test that denied authorization returns correct state with error."""
        mock_authorization_port.check.return_value = denied_result

        result = await authorization_node(
            base_state,  # type: ignore[arg-type]
            authorization_port=mock_authorization_port,
        )

        assert result["authorization_allowed"] is False
        assert result["authorization_skipped"] is False
        assert result["current_node"] == "authorize"
        assert result["authorization_result"]["allowed"] is False
        assert "user_id_hash" in result["authorization_result"]  # Pseudonymized
        assert "errors" in result
        assert len(result["errors"]) == 1
        assert "insufficient permissions" in result["errors"][0]

    async def test_denied_no_user_id_without_system_execution(
        self,
        mock_authorization_port: MagicMock,
    ) -> None:
        """Test authorization is denied when no user_id and no system_execution flag."""
        state = {
            "thread_id": "test-thread",
            "user_id": None,
            "project_id": "project-123",
        }

        result = await authorization_node(
            state,  # type: ignore[arg-type]
            authorization_port=mock_authorization_port,
        )

        assert result["authorization_allowed"] is False
        assert result["authorization_skipped"] is False
        assert "errors" in result
        assert "system_execution" in result["errors"][0]
        # Port should not be called
        mock_authorization_port.check.assert_not_called()

    async def test_skipped_with_system_execution_flag(
        self,
        mock_authorization_port: MagicMock,
    ) -> None:
        """Test authorization is skipped when system_execution flag is set."""
        state = {
            "thread_id": "test-thread",
            "user_id": None,
            "project_id": "project-123",
            "system_execution": True,
        }

        result = await authorization_node(
            state,  # type: ignore[arg-type]
            authorization_port=mock_authorization_port,
        )

        assert result["authorization_allowed"] is True
        assert result["authorization_skipped"] is True
        assert result["authorization_result"] is None
        # Port should not be called
        mock_authorization_port.check.assert_not_called()

    async def test_fail_secure_no_port(
        self,
        base_state: dict[str, object],
    ) -> None:
        """Test fail-secure denial when no authorization port provided."""
        result = await authorization_node(
            base_state,  # type: ignore[arg-type]
            authorization_port=None,
        )

        assert result["authorization_allowed"] is False
        assert result["authorization_skipped"] is False
        assert "errors" in result
        assert "fail-secure" in result["errors"][0]

    async def test_default_project_id(
        self,
        mock_authorization_port: MagicMock,
        allowed_result: AuthorizationResult,
    ) -> None:
        """Test default project_id is used when not provided."""
        mock_authorization_port.check.return_value = allowed_result
        state = {
            "thread_id": "test-thread",
            "user_id": "user-123",
            "project_id": None,
        }

        result = await authorization_node(
            state,  # type: ignore[arg-type]
            authorization_port=mock_authorization_port,
        )

        assert result["authorization_allowed"] is True
        # Verify the check was called (project_id defaulted to "default")
        mock_authorization_port.check.assert_called_once()

    async def test_authorization_check_error(
        self,
        mock_authorization_port: MagicMock,
        base_state: dict[str, object],
    ) -> None:
        """Test handling of AuthorizationCheckError."""
        resource = ResourceId(resource_type=ResourceType.PROJECT, identifier="project-456")
        mock_authorization_port.check.side_effect = AuthorizationCheckError(
            user="user-123",
            action=Action.VIEW,
            resource=resource,
            reason="Connection failed",
        )

        result = await authorization_node(
            base_state,  # type: ignore[arg-type]
            authorization_port=mock_authorization_port,
        )

        assert result["authorization_allowed"] is False
        assert result["authorization_skipped"] is False
        assert "errors" in result
        assert "Authorization check failed" in result["errors"][0]

    async def test_generic_exception(
        self,
        mock_authorization_port: MagicMock,
        base_state: dict[str, object],
    ) -> None:
        """Test handling of generic exceptions."""
        mock_authorization_port.check.side_effect = RuntimeError("Unexpected error")

        result = await authorization_node(
            base_state,  # type: ignore[arg-type]
            authorization_port=mock_authorization_port,
        )

        assert result["authorization_allowed"] is False
        assert result["authorization_skipped"] is False
        assert "errors" in result
        assert "Authorization node error" in result["errors"][0]


class TestRouteAfterAuthorization:
    """Tests for route_after_authorization function."""

    def test_route_to_ingest_when_allowed(self) -> None:
        """Test routing to ingest when authorization is allowed."""
        state = {"authorization_allowed": True}

        result = route_after_authorization(state)

        assert result == "ingest"

    def test_route_to_end_when_denied(self) -> None:
        """Test routing to end when authorization is denied."""
        state = {"authorization_allowed": False}

        result = route_after_authorization(state)

        assert result == "end"

    def test_route_to_end_when_missing(self) -> None:
        """Test routing to end when authorization_allowed is missing."""
        state: dict[str, object] = {}

        result = route_after_authorization(state)

        assert result == "end"

    def test_route_with_user_context(self) -> None:
        """Test routing includes user context in logs."""
        state = {
            "authorization_allowed": False,
            "user_id": "user-123",
            "project_id": "project-456",
        }

        result = route_after_authorization(state)

        assert result == "end"
