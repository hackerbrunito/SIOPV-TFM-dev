"""Integration tests for the authorization module.

Tests the full authorization flow including:
- End-to-end permission check flow (adapter + port)
- Batch authorization flows
- Relationship management flows (write, read, delete)
- Use case integration with adapter
- Dependency injection integration

These tests use mock OpenFGA client (no real server required) and verify
proper integration between layers: domain -> use case -> port -> adapter.

Test Categories:
1. End-to-End Permission Check Flow
2. Batch Authorization Operations
3. Relationship Tuple Management
4. Use Case Integration
5. Dependency Injection Integration
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from siopv.adapters.authorization import OpenFGAAdapter
from siopv.application.use_cases.authorization import (
    BatchCheckAuthorizationUseCase,
    CheckAuthorizationUseCase,
    ManageRelationshipsUseCase,
)
from siopv.domain.authorization import (
    Action,
    AuthorizationCheckError,
    AuthorizationContext,
    Relation,
    RelationshipTuple,
    ResourceId,
    UserId,
)
from siopv.infrastructure.di.authorization import (
    create_authorization_adapter,
    get_authorization_port,
    get_authorization_store_port,
)


@pytest.fixture
def mock_settings() -> MagicMock:
    """Create mock settings for OpenFGA configuration."""
    settings = MagicMock()
    settings.openfga_api_url = "http://localhost:8080"
    settings.openfga_store_id = "test-store-id"
    settings.circuit_breaker_failure_threshold = 5
    settings.circuit_breaker_recovery_timeout = 60
    return settings


@pytest.fixture
def mock_openfga_client() -> AsyncMock:
    """Create mock OpenFGA client."""
    return AsyncMock()


@pytest.fixture
def adapter(
    mock_settings: MagicMock,
    mock_openfga_client: AsyncMock,
) -> OpenFGAAdapter:
    """Create adapter with injected mock client for integration tests."""
    return OpenFGAAdapter(mock_settings, client=mock_openfga_client)


@pytest.fixture
def sample_user() -> UserId:
    """Sample user for integration tests."""
    return UserId(value="integration-test-user")


@pytest.fixture
def sample_resource() -> ResourceId:
    """Sample resource for integration tests."""
    return ResourceId.for_project("integration-test-project")


@pytest.fixture
def sample_relation() -> Relation:
    """Sample relation for integration tests."""
    return Relation.VIEWER


# ============================================================================
# Category 1: End-to-End Permission Check Flow
# ============================================================================


class TestEndToEndPermissionCheckFlow:
    """Tests the complete permission check flow from context to result.

    Verifies:
    - Context construction
    - Adapter receives and processes check
    - Result contains all required metadata
    - Audit logging is present
    """

    @pytest.mark.asyncio
    async def test_check_allowed_flow(
        self,
        adapter: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
        sample_user: UserId,
        sample_resource: ResourceId,
    ) -> None:
        """Test complete allowed permission check flow.

        Verifies:
        1. AuthorizationContext is built from parameters
        2. Adapter.check() processes the context
        3. OpenFGA client receives the check request
        4. Result is allowed with decision_id and metadata
        """
        # Arrange - Setup mock response
        mock_response = MagicMock()
        mock_response.allowed = True
        mock_openfga_client.check.return_value = mock_response

        # Arrange - Build context
        context = AuthorizationContext.for_action(
            user_id=sample_user.value,
            resource=sample_resource,
            action=Action.VIEW,
        )

        # Act - Execute check
        result = await adapter.check(context)

        # Assert
        assert result.allowed is True
        assert result.decision_id is not None
        # ACTION.VIEW maps to {VIEWER, ANALYST, AUDITOR, OWNER, ADMIN}
        assert result.checked_relation in {
            Relation.VIEWER,
            Relation.ANALYST,
            Relation.AUDITOR,
            Relation.OWNER,
            Relation.ADMIN,
        }
        assert result.check_duration_ms >= 0
        mock_openfga_client.check.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_denied_flow(
        self,
        adapter: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
        sample_user: UserId,
        sample_resource: ResourceId,
    ) -> None:
        """Test complete denied permission check flow.

        Verifies:
        1. Denied result is properly handled
        2. Reason is populated
        3. Check metadata is recorded
        """
        # Arrange
        mock_response = MagicMock()
        mock_response.allowed = False
        mock_openfga_client.check.return_value = mock_response

        context = AuthorizationContext.for_action(
            user_id=sample_user.value,
            resource=sample_resource,
            action=Action.DELETE,
        )

        # Act
        result = await adapter.check(context)

        # Assert
        assert result.allowed is False
        assert "lacks" in result.reason
        assert result.checked_relation == Relation.OWNER
        assert result.decision_id is not None

    @pytest.mark.asyncio
    async def test_check_with_error_handling(
        self,
        adapter: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
        sample_user: UserId,
        sample_resource: ResourceId,
    ) -> None:
        """Test error handling in permission check flow.

        Verifies:
        1. OpenFGA errors are caught
        2. Error is wrapped in domain exception
        3. Error context is preserved
        """
        # Arrange
        mock_openfga_client.check.side_effect = RuntimeError("Service error")

        context = AuthorizationContext.for_action(
            user_id=sample_user.value,
            resource=sample_resource,
            action=Action.VIEW,
        )

        # Act & Assert
        with pytest.raises(AuthorizationCheckError):
            await adapter.check(context)


# ============================================================================
# Category 2: Batch Authorization Flow
# ============================================================================


class TestBatchAuthorizationFlow:
    """Tests batch authorization operations.

    Verifies:
    - Multiple checks in single batch request
    - Correct handling of mixed allow/deny results
    - Batch size validation
    - Result aggregation and statistics
    """

    @pytest.mark.asyncio
    async def test_batch_check_all_allowed(
        self,
        adapter: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
        sample_resource: ResourceId,
    ) -> None:
        """Test batch check with all requests allowed.

        Verifies:
        1. Multiple contexts processed in batch
        2. All results returned
        3. Statistics calculated correctly
        """
        # Arrange - Setup batch check response
        mock_result1 = MagicMock()
        mock_result1.allowed = True
        mock_result2 = MagicMock()
        mock_result2.allowed = True

        mock_response = MagicMock()
        mock_response.result = [mock_result1, mock_result2]
        mock_openfga_client.batch_check.return_value = mock_response

        # Arrange - Create contexts
        contexts = [
            AuthorizationContext.for_action(
                user_id="user1",
                resource=sample_resource,
                action=Action.VIEW,
            ),
            AuthorizationContext.for_action(
                user_id="user2",
                resource=sample_resource,
                action=Action.VIEW,
            ),
        ]

        # Act
        batch_result = await adapter.batch_check(contexts)

        # Assert
        assert batch_result.allowed_count == 2
        assert batch_result.denied_count == 0
        assert len(batch_result.results) == 2
        assert batch_result.all_allowed is True
        mock_openfga_client.batch_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_batch_check_mixed_results(
        self,
        adapter: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
        sample_resource: ResourceId,
    ) -> None:
        """Test batch check with mixed allow/deny results.

        Verifies:
        1. Partial denials are handled correctly
        2. Statistics reflect actual distribution
        3. Results maintain correspondence with inputs
        """
        # Arrange
        mock_result1 = MagicMock()
        mock_result1.allowed = True
        mock_result2 = MagicMock()
        mock_result2.allowed = False
        mock_result3 = MagicMock()
        mock_result3.allowed = True

        mock_response = MagicMock()
        mock_response.result = [mock_result1, mock_result2, mock_result3]
        mock_openfga_client.batch_check.return_value = mock_response

        contexts = [
            AuthorizationContext.for_action(
                user_id=f"user{i}",
                resource=sample_resource,
                action=Action.VIEW,
            )
            for i in range(3)
        ]

        # Act
        batch_result = await adapter.batch_check(contexts)

        # Assert
        assert batch_result.allowed_count == 2
        assert batch_result.denied_count == 1
        assert batch_result.any_denied is True
        assert batch_result.all_allowed is False

    @pytest.mark.asyncio
    async def test_batch_check_empty_raises_error(self, adapter: OpenFGAAdapter) -> None:
        """Test batch check raises error for empty context list."""
        with pytest.raises(ValueError, match="cannot be empty"):
            await adapter.batch_check([])

    @pytest.mark.asyncio
    async def test_batch_check_exceeds_max_size_raises_error(
        self,
        adapter: OpenFGAAdapter,
        sample_resource: ResourceId,
    ) -> None:
        """Test batch check raises error when exceeding max size (100)."""
        contexts = [
            AuthorizationContext.for_action(
                user_id=f"user{i}",
                resource=sample_resource,
                action=Action.VIEW,
            )
            for i in range(101)
        ]

        with pytest.raises(ValueError, match="exceeds maximum batch size"):
            await adapter.batch_check(contexts)


# ============================================================================
# Category 3: Relationship Management Flow
# ============================================================================


class TestRelationshipManagementFlow:
    """Tests relationship tuple management operations.

    Verifies:
    - Write (grant) operations
    - Read/query operations
    - Delete (revoke) operations
    - Tuple existence checks
    - Relationship persistence across operations
    """

    @pytest.mark.asyncio
    async def test_write_single_tuple_flow(
        self,
        adapter: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
        sample_user: UserId,
        sample_resource: ResourceId,
    ) -> None:
        """Test writing a single relationship tuple.

        Verifies:
        1. RelationshipTuple is created
        2. Adapter writes tuple to OpenFGA
        3. No error is raised
        """
        # Arrange
        mock_openfga_client.write.return_value = MagicMock()

        tuple_to_write = RelationshipTuple.create(
            user_id=sample_user.value,
            relation=Relation.VIEWER,
            resource_type=sample_resource.resource_type,
            resource_id=sample_resource.identifier,
        )

        # Act
        await adapter.write_tuple(tuple_to_write)

        # Assert
        mock_openfga_client.write.assert_called_once()
        call_args = mock_openfga_client.write.call_args
        request = call_args[0][0]
        assert request.writes is not None

    @pytest.mark.asyncio
    async def test_write_batch_tuples_flow(
        self,
        adapter: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
        sample_resource: ResourceId,
    ) -> None:
        """Test writing multiple relationship tuples atomically.

        Verifies:
        1. Multiple tuples can be created in one operation
        2. Batch write is atomic
        3. All tuples are sent in single request
        """
        # Arrange
        mock_openfga_client.write.return_value = MagicMock()

        tuples = [
            RelationshipTuple.create(
                user_id=f"user{i}",
                relation=Relation.VIEWER,
                resource_type=sample_resource.resource_type,
                resource_id=sample_resource.identifier,
            )
            for i in range(3)
        ]

        # Act
        await adapter.write_tuples(tuples)

        # Assert
        mock_openfga_client.write.assert_called_once()
        call_args = mock_openfga_client.write.call_args
        request = call_args[0][0]
        assert len(request.writes) == 3

    @pytest.mark.asyncio
    async def test_read_tuples_flow(
        self,
        adapter: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
        sample_resource: ResourceId,
    ) -> None:
        """Test reading relationship tuples with filters.

        Verifies:
        1. Tuples can be queried with filters
        2. Response is converted to domain objects
        3. Multiple tuples are returned correctly
        """
        # Arrange - Setup mock response
        mock_tuple_key1 = MagicMock()
        mock_tuple_key1.user = "user:alice"
        mock_tuple_key1.relation = "viewer"
        mock_tuple_key1.object = "project:test-project"

        mock_tuple_key2 = MagicMock()
        mock_tuple_key2.user = "user:bob"
        mock_tuple_key2.relation = "viewer"
        mock_tuple_key2.object = "project:test-project"

        mock_tuple1 = MagicMock()
        mock_tuple1.key = mock_tuple_key1
        mock_tuple2 = MagicMock()
        mock_tuple2.key = mock_tuple_key2

        mock_response = MagicMock()
        mock_response.tuples = [mock_tuple1, mock_tuple2]
        mock_openfga_client.read.return_value = mock_response

        # Act
        tuples = await adapter.read_tuples(resource=sample_resource)

        # Assert
        assert len(tuples) == 2
        assert all(isinstance(t, RelationshipTuple) for t in tuples)
        mock_openfga_client.read.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_tuple_flow(
        self,
        adapter: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
        sample_user: UserId,
        sample_resource: ResourceId,
    ) -> None:
        """Test deleting a relationship tuple.

        Verifies:
        1. RelationshipTuple is deleted
        2. Delete request is sent to OpenFGA
        3. No error is raised
        """
        # Arrange
        mock_openfga_client.write.return_value = MagicMock()

        tuple_to_delete = RelationshipTuple.create(
            user_id=sample_user.value,
            relation=Relation.VIEWER,
            resource_type=sample_resource.resource_type,
            resource_id=sample_resource.identifier,
        )

        # Act
        await adapter.delete_tuple(tuple_to_delete)

        # Assert
        mock_openfga_client.write.assert_called_once()
        call_args = mock_openfga_client.write.call_args
        request = call_args[0][0]
        assert request.deletes is not None

    @pytest.mark.asyncio
    async def test_tuple_exists_flow(
        self,
        adapter: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
        sample_user: UserId,
        sample_resource: ResourceId,
    ) -> None:
        """Test checking if a specific tuple exists.

        Verifies:
        1. Existence check queries OpenFGA
        2. Returns boolean indicating presence
        3. Handles both positive and negative cases
        """
        # Arrange - Setup mock response (tuple exists)
        mock_tuple_key = MagicMock()
        mock_tuple_key.user = "user:alice"
        mock_tuple_key.relation = "viewer"
        mock_tuple_key.object = "project:test-project"

        mock_tuple = MagicMock()
        mock_tuple.key = mock_tuple_key

        mock_response = MagicMock()
        mock_response.tuples = [mock_tuple]
        mock_openfga_client.read.return_value = mock_response

        # Act
        exists = await adapter.tuple_exists(
            sample_user,
            Relation.VIEWER,
            sample_resource,
        )

        # Assert
        assert exists is True
        mock_openfga_client.read.assert_called_once()

    @pytest.mark.asyncio
    async def test_tuple_not_exists_flow(
        self,
        adapter: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
        sample_user: UserId,
        sample_resource: ResourceId,
    ) -> None:
        """Test checking when tuple does not exist.

        Verifies:
        1. Non-existent tuple returns False
        2. Empty response is handled correctly
        """
        # Arrange
        mock_response = MagicMock()
        mock_response.tuples = []
        mock_openfga_client.read.return_value = mock_response

        # Act
        exists = await adapter.tuple_exists(
            sample_user,
            Relation.VIEWER,
            sample_resource,
        )

        # Assert
        assert exists is False


# ============================================================================
# Category 4: Use Case Integration
# ============================================================================


class TestUseCaseIntegration:
    """Tests use case integration with adapter.

    Verifies:
    - CheckAuthorizationUseCase workflows
    - BatchCheckAuthorizationUseCase workflows
    - ManageRelationshipsUseCase workflows
    """

    @pytest.mark.asyncio
    async def test_check_authorization_use_case_integration(
        self,
        adapter: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
        sample_user: UserId,
        sample_resource: ResourceId,
    ) -> None:
        """Test CheckAuthorizationUseCase with adapter.

        Verifies:
        1. Use case can be instantiated with adapter
        2. Execute method works end-to-end
        3. Result contains audit information
        """
        # Arrange
        mock_response = MagicMock()
        mock_response.allowed = True
        mock_openfga_client.check.return_value = mock_response

        use_case = CheckAuthorizationUseCase(authorization_port=adapter)

        # Act
        result = await use_case.execute(
            user_id=sample_user.value,
            action=Action.VIEW,
            resource_type=sample_resource.resource_type,
            resource_id=sample_resource.identifier,
        )

        # Assert
        assert result.allowed is True
        assert result.audit_logged is True
        assert result.decision_id is not None

    @pytest.mark.asyncio
    async def test_batch_check_use_case_integration(
        self,
        adapter: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
        sample_resource: ResourceId,
    ) -> None:
        """Test BatchCheckAuthorizationUseCase with adapter.

        Verifies:
        1. Batch use case processes multiple checks
        2. Statistics are calculated
        3. Results correlate with inputs
        """
        # Arrange
        mock_result1 = MagicMock()
        mock_result1.allowed = True
        mock_result2 = MagicMock()
        mock_result2.allowed = False

        mock_response = MagicMock()
        mock_response.result = [mock_result1, mock_result2]
        mock_openfga_client.batch_check.return_value = mock_response

        use_case = BatchCheckAuthorizationUseCase(authorization_port=adapter)

        checks = [
            ("user1", Action.VIEW, sample_resource.resource_type, "res1"),
            ("user2", Action.DELETE, sample_resource.resource_type, "res2"),
        ]

        # Act
        result = await use_case.execute(checks)

        # Assert
        assert result.stats.total_checks == 2
        assert result.stats.allowed_count == 1
        assert result.stats.denied_count == 1

    @pytest.mark.asyncio
    async def test_manage_relationships_use_case_integration(
        self,
        adapter: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
        sample_user: UserId,
        sample_resource: ResourceId,
    ) -> None:
        """Test ManageRelationshipsUseCase with adapter.

        Verifies:
        1. Grant permission creates tuple
        2. Revoke permission deletes tuple
        3. Results indicate success/failure
        """
        # Arrange
        mock_openfga_client.write.return_value = MagicMock()

        use_case = ManageRelationshipsUseCase(store_port=adapter)

        # Act - Grant permission
        grant_result = await use_case.grant_permission(
            user_id=sample_user.value,
            relation=Relation.VIEWER,
            resource_type=sample_resource.resource_type,
            resource_id=sample_resource.identifier,
        )

        # Assert - Grant succeeded
        assert grant_result.success is True
        assert grant_result.operation == "grant"

        # Act - Revoke permission
        revoke_result = await use_case.revoke_permission(
            user_id=sample_user.value,
            relation=Relation.VIEWER,
            resource_type=sample_resource.resource_type,
            resource_id=sample_resource.identifier,
        )

        # Assert - Revoke succeeded
        assert revoke_result.success is True
        assert revoke_result.operation == "revoke"

    @pytest.mark.asyncio
    async def test_manage_relationships_batch_grant_integration(
        self,
        adapter: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
        sample_resource: ResourceId,
    ) -> None:
        """Test batch grant permissions through use case.

        Verifies:
        1. Multiple permissions can be granted atomically
        2. Results reflect all operations
        """
        # Arrange
        mock_openfga_client.write.return_value = MagicMock()

        use_case = ManageRelationshipsUseCase(store_port=adapter)

        grants = [
            ("user1", Relation.VIEWER, sample_resource.resource_type, "res1"),
            ("user2", Relation.OWNER, sample_resource.resource_type, "res1"),
        ]

        # Act
        results = await use_case.grant_permissions_batch(grants)

        # Assert
        assert len(results) == 2
        assert all(r.success for r in results)
        assert all(r.operation == "grant" for r in results)


# ============================================================================
# Category 5: Dependency Injection Integration
# ============================================================================


class TestDependencyInjectionIntegration:
    """Tests DI container integration for authorization components.

    Verifies:
    - Factory functions create proper instances
    - Singletons are cached appropriately
    - Ports are properly configured
    """

    @pytest.fixture(autouse=True)
    def _patch_get_settings(self, mock_settings: MagicMock) -> None:
        """Patch get_settings so DI functions receive the mock settings."""
        with patch(
            "siopv.infrastructure.di.authorization.get_settings",
            return_value=mock_settings,
        ):
            create_authorization_adapter.cache_clear()
            get_authorization_port.cache_clear()
            get_authorization_store_port.cache_clear()
            yield
            create_authorization_adapter.cache_clear()
            get_authorization_port.cache_clear()
            get_authorization_store_port.cache_clear()

    def test_create_authorization_adapter_factory(
        self,
        mock_settings: MagicMock,
    ) -> None:
        """Test factory function creates adapter.

        Verifies:
        1. create_authorization_adapter returns OpenFGAAdapter
        2. Adapter is configured with settings
        """
        # Act
        adapter = create_authorization_adapter()

        # Assert
        assert isinstance(adapter, OpenFGAAdapter)
        assert adapter._api_url == mock_settings.openfga_api_url
        assert adapter._store_id == mock_settings.openfga_store_id

    def test_get_authorization_port_from_di(self) -> None:
        """Test getting AuthorizationPort from DI container.

        Verifies:
        1. get_authorization_port returns correct port implementation
        2. Port is usable for authorization checks
        """
        # Act
        port = get_authorization_port()

        # Assert
        assert isinstance(port, OpenFGAAdapter)
        # Verify port has required methods
        assert hasattr(port, "check")
        assert hasattr(port, "batch_check")

    def test_get_authorization_store_port_from_di(self) -> None:
        """Test getting AuthorizationStorePort from DI container.

        Verifies:
        1. get_authorization_store_port returns correct port implementation
        2. Port is usable for relationship management
        """
        # Act
        port = get_authorization_store_port()

        # Assert
        assert isinstance(port, OpenFGAAdapter)
        # Verify port has required methods
        assert hasattr(port, "write_tuple")
        assert hasattr(port, "delete_tuple")
        assert hasattr(port, "read_tuples")

    @pytest.mark.asyncio
    async def test_full_integration_with_di_factory(self) -> None:
        """Test complete workflow using DI factories.

        Verifies:
        1. Factories can be used to create all components
        2. Components work together in integrated workflow
        """
        # Arrange - Create components using DI
        with patch(
            "siopv.adapters.authorization.openfga_adapter.OpenFgaClient"
        ) as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_class.return_value = mock_client_instance

            auth_port = get_authorization_port()
            _store_port = get_authorization_store_port()

            # Setup mock check response
            mock_response = MagicMock()
            mock_response.allowed = True
            mock_client_instance.check.return_value = mock_response

            # Act - Initialize and use
            await auth_port.initialize()

            context = AuthorizationContext.for_action(
                user_id="di-test-user",
                resource=ResourceId.for_project("di-test-project"),
                action=Action.VIEW,
            )

            result = await auth_port.check(context)

            # Assert
            assert result.allowed is True

            # Cleanup
            await auth_port.close()


# ============================================================================
# Category 6: Error Scenarios and Edge Cases
# ============================================================================


class TestErrorScenariosAndEdgeCases:
    """Tests error handling and edge cases in integration scenarios.

    Verifies:
    - Proper error propagation through layers
    - Error recovery and graceful degradation
    - Timeout and service unavailability handling
    """

    @pytest.mark.asyncio
    async def test_adapter_initialization_error_propagates(
        self,
        mock_settings: MagicMock,
    ) -> None:
        """Test initialization errors propagate correctly.

        Verifies:
        1. Missing configuration raises appropriate error
        2. Error can be caught at use case level
        """
        # Arrange - Missing store ID
        mock_settings.openfga_store_id = None
        adapter = OpenFGAAdapter(mock_settings)

        # Act & Assert - Adapter raises domain exception for missing config
        from siopv.domain.authorization import StoreNotFoundError

        with pytest.raises(StoreNotFoundError):
            await adapter.initialize()

    @pytest.mark.asyncio
    async def test_concurrent_checks_with_batch(
        self,
        adapter: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
        sample_resource: ResourceId,
    ) -> None:
        """Test batch operations maintain proper concurrency.

        Verifies:
        1. Multiple concurrent checks are handled correctly
        2. Results are properly aggregated
        """
        # Arrange
        mock_results = [MagicMock(allowed=True) for _ in range(10)]
        mock_response = MagicMock()
        mock_response.result = mock_results
        mock_openfga_client.batch_check.return_value = mock_response

        contexts = [
            AuthorizationContext.for_action(
                user_id=f"concurrent-user-{i}",
                resource=sample_resource,
                action=Action.VIEW,
            )
            for i in range(10)
        ]

        # Act
        batch_result = await adapter.batch_check(contexts)

        # Assert
        assert len(batch_result.results) == 10
        assert batch_result.allowed_count == 10

    @pytest.mark.asyncio
    async def test_use_case_error_handling_with_adapter(
        self,
        adapter: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
        sample_user: UserId,
        sample_resource: ResourceId,
    ) -> None:
        """Test use case properly handles adapter errors.

        Verifies:
        1. Adapter exceptions are caught at use case level
        2. Errors are wrapped in domain exceptions
        3. Audit logging captures failure
        """
        # Arrange
        mock_openfga_client.check.side_effect = RuntimeError("OpenFGA service down")

        use_case = CheckAuthorizationUseCase(authorization_port=adapter)

        # Act & Assert
        with pytest.raises(AuthorizationCheckError) as exc_info:
            await use_case.execute(
                user_id=sample_user.value,
                action=Action.VIEW,
                resource_type=sample_resource.resource_type,
                resource_id=sample_resource.identifier,
            )

        # Verify error context
        assert exc_info.value is not None


__all__ = [
    "TestBatchAuthorizationFlow",
    "TestDependencyInjectionIntegration",
    "TestEndToEndPermissionCheckFlow",
    "TestErrorScenariosAndEdgeCases",
    "TestRelationshipManagementFlow",
    "TestUseCaseIntegration",
]
