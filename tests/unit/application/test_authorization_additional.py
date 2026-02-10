"""Additional tests for Authorization Use Cases - Edge cases and error paths.

Covers missing lines from authorization.py:
- Batch check error handling (lines 379-385)
- Batch check from contexts size limit (line 414)
- Batch grant permissions error handling (lines 649-656)
- Batch revoke permissions validation and errors (lines 680, 683, 705-712)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from siopv.application.ports.authorization import (
    AuthorizationPort,
    AuthorizationStorePort,
)
from siopv.application.use_cases.authorization import (
    BatchCheckAuthorizationUseCase,
    ManageRelationshipsUseCase,
)
from siopv.domain.authorization import (
    Action,
    AuthorizationCheckError,
    AuthorizationContext,
    AuthorizationResult,
    BatchAuthorizationResult,
    Relation,
    ResourceId,
    ResourceType,
)

# === BatchCheckAuthorizationUseCase Error Path Tests ===


class TestBatchCheckAuthorizationUseCaseErrors:
    """Test error paths in BatchCheckAuthorizationUseCase."""

    @pytest.mark.asyncio
    async def test_execute_batch_port_error(self):
        """Test that port errors in batch check are wrapped in AuthorizationCheckError."""
        mock_port = MagicMock(spec=AuthorizationPort)
        mock_port.batch_check = AsyncMock(side_effect=RuntimeError("Service unavailable"))

        use_case = BatchCheckAuthorizationUseCase(authorization_port=mock_port)

        checks = [
            ("alice", Action.VIEW, ResourceType.PROJECT, "siopv"),
        ]

        with pytest.raises(AuthorizationCheckError) as exc_info:
            await use_case.execute(checks)

        assert "Service unavailable" in str(exc_info.value)
        # Verify it's wrapped as an authorization check error
        assert exc_info.value.underlying_error is not None

    @pytest.mark.asyncio
    async def test_execute_from_contexts_exceeds_limit_raises(self):
        """Test that exceeding batch limit in execute_from_contexts raises ValueError."""
        mock_port = MagicMock(spec=AuthorizationPort)

        use_case = BatchCheckAuthorizationUseCase(
            authorization_port=mock_port,
            max_batch_size=5,
        )

        # Create 10 contexts (exceeds limit of 5)
        contexts = [
            AuthorizationContext.for_action(
                user_id=f"user{i}",
                resource=ResourceId(resource_type=ResourceType.PROJECT, identifier=f"project{i}"),
                action=Action.VIEW,
            )
            for i in range(10)
        ]

        with pytest.raises(ValueError, match="exceeds maximum"):
            await use_case.execute_from_contexts(contexts)

    @pytest.mark.asyncio
    async def test_execute_from_contexts_port_error(self):
        """Test port errors in execute_from_contexts."""
        mock_port = MagicMock(spec=AuthorizationPort)
        mock_port.batch_check = AsyncMock(side_effect=RuntimeError("Network error"))

        use_case = BatchCheckAuthorizationUseCase(authorization_port=mock_port)

        context = AuthorizationContext.for_action(
            user_id="alice",
            resource=ResourceId(resource_type=ResourceType.PROJECT, identifier="siopv"),
            action=Action.VIEW,
        )

        # This doesn't wrap errors in execute_from_contexts, just logs and propagates
        with pytest.raises(RuntimeError):
            await use_case.execute_from_contexts([context])


# === ManageRelationshipsUseCase Batch Error Tests ===


class TestManageRelationshipsUseCaseBatchErrors:
    """Test error paths in batch relationship management."""

    @pytest.mark.asyncio
    async def test_grant_permissions_batch_port_error(self):
        """Test port error in batch grant permissions."""
        mock_port = MagicMock(spec=AuthorizationStorePort)
        mock_port.write_tuples = AsyncMock(side_effect=RuntimeError("Database error"))

        use_case = ManageRelationshipsUseCase(store_port=mock_port)

        grants = [
            ("alice", Relation.VIEWER, ResourceType.PROJECT, "project1"),
            ("bob", Relation.ANALYST, ResourceType.PROJECT, "project2"),
        ]

        results = await use_case.grant_permissions_batch(grants)

        # All results should show failure
        assert len(results) == 2
        assert all(not r.success for r in results)
        assert all("Database error" in r.error for r in results)
        assert all(r.operation == "grant" for r in results)

    @pytest.mark.asyncio
    async def test_revoke_permissions_batch_empty_raises(self):
        """Test that empty revocations list raises ValueError."""
        mock_port = MagicMock(spec=AuthorizationStorePort)
        use_case = ManageRelationshipsUseCase(store_port=mock_port)

        with pytest.raises(ValueError, match="cannot be empty"):
            await use_case.revoke_permissions_batch([])

    @pytest.mark.asyncio
    async def test_revoke_permissions_batch_exceeds_limit_raises(self):
        """Test that exceeding batch limit in revoke raises ValueError."""
        mock_port = MagicMock(spec=AuthorizationStorePort)
        use_case = ManageRelationshipsUseCase(store_port=mock_port)

        # Create 101 revocations (exceeds default max of 100)
        revocations = [
            ("user", Relation.VIEWER, ResourceType.PROJECT, f"project{i}") for i in range(101)
        ]

        with pytest.raises(ValueError, match="exceeds maximum"):
            await use_case.revoke_permissions_batch(revocations)

    @pytest.mark.asyncio
    async def test_revoke_permissions_batch_port_error(self):
        """Test port error in batch revoke permissions."""
        mock_port = MagicMock(spec=AuthorizationStorePort)
        mock_port.delete_tuples = AsyncMock(side_effect=RuntimeError("Database error"))

        use_case = ManageRelationshipsUseCase(store_port=mock_port)

        revocations = [
            ("alice", Relation.VIEWER, ResourceType.PROJECT, "project1"),
            ("bob", Relation.ANALYST, ResourceType.PROJECT, "project2"),
        ]

        results = await use_case.revoke_permissions_batch(revocations)

        # All results should show failure
        assert len(results) == 2
        assert all(not r.success for r in results)
        assert all("Database error" in r.error for r in results)
        assert all(r.operation == "revoke" for r in results)

    @pytest.mark.asyncio
    async def test_revoke_permissions_batch_success(self):
        """Test successful batch revoke permissions."""
        mock_port = MagicMock(spec=AuthorizationStorePort)
        mock_port.delete_tuples = AsyncMock(return_value=None)

        use_case = ManageRelationshipsUseCase(store_port=mock_port)

        revocations = [
            ("alice", Relation.VIEWER, ResourceType.PROJECT, "project1"),
            ("bob", Relation.ANALYST, ResourceType.PROJECT, "project2"),
        ]

        results = await use_case.revoke_permissions_batch(revocations)

        assert len(results) == 2
        assert all(r.success for r in results)
        assert all(r.operation == "revoke" for r in results)
        assert all(r.error is None for r in results)
        mock_port.delete_tuples.assert_called_once()


# === Parametrized Integration Tests ===


class TestAuthorizationParametrized:
    """Parametrized tests for various scenarios."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("batch_size", [1, 50, 100])
    async def test_batch_check_various_sizes(
        self,
        batch_size: int,
    ):
        """Test batch checks with various sizes up to limit."""
        # Create sample results
        sample_result = AuthorizationResult.allowed_result(
            context=AuthorizationContext.for_action(
                user_id="alice",
                resource=ResourceId(resource_type=ResourceType.PROJECT, identifier="siopv"),
                action=Action.VIEW,
            ),
            checked_relation=Relation.VIEWER,
            reason="Test",
            check_duration_ms=5.0,
        )

        mock_port = MagicMock(spec=AuthorizationPort)
        mock_port.batch_check = AsyncMock(
            return_value=BatchAuthorizationResult(
                results=[sample_result] * batch_size,
                total_duration_ms=10.0,
            )
        )

        use_case = BatchCheckAuthorizationUseCase(authorization_port=mock_port)

        checks = [
            ("user", Action.VIEW, ResourceType.PROJECT, f"project{i}") for i in range(batch_size)
        ]

        result = await use_case.execute(checks)

        assert result.stats.total_checks == batch_size
        assert result.stats.allowed_count == batch_size

    @pytest.mark.asyncio
    @pytest.mark.parametrize("grant_count", [1, 50, 100])
    async def test_grant_permissions_batch_various_sizes(
        self,
        grant_count: int,
    ):
        """Test batch grants with various sizes up to limit."""
        mock_port = MagicMock(spec=AuthorizationStorePort)
        mock_port.write_tuples = AsyncMock(return_value=None)

        use_case = ManageRelationshipsUseCase(store_port=mock_port)

        grants = [
            ("user", Relation.VIEWER, ResourceType.PROJECT, f"project{i}")
            for i in range(grant_count)
        ]

        results = await use_case.grant_permissions_batch(grants)

        assert len(results) == grant_count
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("error_type", "error_msg"),
        [
            (RuntimeError, "Runtime error"),
            (ValueError, "Invalid value"),
            (Exception, "Generic error"),
        ],
    )
    async def test_batch_grant_various_error_types(
        self,
        error_type: type[Exception],
        error_msg: str,
    ):
        """Test batch grant with various error types."""
        mock_port = MagicMock(spec=AuthorizationStorePort)
        mock_port.write_tuples = AsyncMock(side_effect=error_type(error_msg))

        use_case = ManageRelationshipsUseCase(store_port=mock_port)

        grants = [
            ("alice", Relation.VIEWER, ResourceType.PROJECT, "project1"),
        ]

        results = await use_case.grant_permissions_batch(grants)

        assert len(results) == 1
        assert not results[0].success
        assert error_msg in results[0].error


__all__ = [
    "TestAuthorizationParametrized",
    "TestBatchCheckAuthorizationUseCaseErrors",
    "TestManageRelationshipsUseCaseBatchErrors",
]
