"""Unit tests for OpenFGAAdapter.

Tests cover:
- AuthorizationPort: check, batch_check, check_relation, list_user_relations
- AuthorizationStorePort: write_tuple, write_tuples, delete_tuple, delete_tuples, read_tuples
- AuthorizationModelPort: get_model_id, validate_model, health_check
- Error handling and circuit breaker behavior
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from siopv.adapters.authorization import OpenFGAAdapter
from siopv.domain.authorization import (
    Action,
    ActionNotMappedError,
    AuthorizationCheckError,
    AuthorizationContext,
    AuthorizationModelError,
    Relation,
    RelationshipTuple,
    ResourceId,
    ResourceType,
    StoreNotFoundError,
    TupleValidationError,
    UserId,
)
from siopv.infrastructure.resilience import CircuitBreakerError


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
def adapter_with_mock_client(
    mock_settings: MagicMock,
    mock_openfga_client: AsyncMock,
) -> OpenFGAAdapter:
    """Create adapter with injected mock client."""
    return OpenFGAAdapter(mock_settings, client=mock_openfga_client)


@pytest.fixture
def sample_user() -> UserId:
    """Create sample user ID."""
    return UserId(value="alice")


@pytest.fixture
def sample_resource() -> ResourceId:
    """Create sample resource ID."""
    return ResourceId.for_project("test-project")


@pytest.fixture
def sample_context(sample_user: UserId, sample_resource: ResourceId) -> AuthorizationContext:
    """Create sample authorization context."""
    return AuthorizationContext.for_action(
        user_id=sample_user.value,
        resource=sample_resource,
        action=Action.VIEW,
    )


@pytest.fixture
def sample_tuple(sample_user: UserId) -> RelationshipTuple:
    """Create sample relationship tuple."""
    return RelationshipTuple.create(
        user_id=sample_user.value,
        relation=Relation.VIEWER,
        resource_type=ResourceType.PROJECT,
        resource_id="test-project",
    )


class TestOpenFGAAdapterInitialization:
    """Tests for adapter initialization."""

    def test_initialization_with_settings(self, mock_settings: MagicMock) -> None:
        """Test adapter initializes correctly with settings."""
        adapter = OpenFGAAdapter(mock_settings)

        assert adapter._api_url == "http://localhost:8080"
        assert adapter._store_id == "test-store-id"
        assert adapter._owned_client is None

    def test_initialization_with_injected_client(
        self,
        mock_settings: MagicMock,
        mock_openfga_client: AsyncMock,
    ) -> None:
        """Test adapter initializes with injected client."""
        adapter = OpenFGAAdapter(mock_settings, client=mock_openfga_client)

        assert adapter._external_client is mock_openfga_client

    @pytest.mark.asyncio
    async def test_initialize_without_api_url_raises_error(
        self,
        mock_settings: MagicMock,
    ) -> None:
        """Test initialize raises StoreNotFoundError without API URL."""
        mock_settings.openfga_api_url = None
        adapter = OpenFGAAdapter(mock_settings)

        with pytest.raises(StoreNotFoundError):
            await adapter.initialize()

    @pytest.mark.asyncio
    async def test_initialize_without_store_id_raises_error(
        self,
        mock_settings: MagicMock,
    ) -> None:
        """Test initialize raises StoreNotFoundError without store ID."""
        mock_settings.openfga_store_id = None
        adapter = OpenFGAAdapter(mock_settings)

        with pytest.raises(StoreNotFoundError):
            await adapter.initialize()

    @pytest.mark.asyncio
    async def test_initialize_with_external_client_skips_creation(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
    ) -> None:
        """Test initialize skips client creation with external client."""
        await adapter_with_mock_client.initialize()

        # Should not create owned client
        assert adapter_with_mock_client._owned_client is None

    @pytest.mark.asyncio
    async def test_initialize_creates_owned_client(
        self,
        mock_settings: MagicMock,
    ) -> None:
        """Test initialize creates owned OpenFGA client."""
        adapter = OpenFGAAdapter(mock_settings)

        with patch(
            "siopv.adapters.authorization.openfga_adapter.OpenFgaClient"
        ) as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_class.return_value = mock_client_instance

            await adapter.initialize()

            assert adapter._owned_client is mock_client_instance
            mock_client_instance.__aenter__.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_closes_owned_client(
        self,
        mock_settings: MagicMock,
    ) -> None:
        """Test close() closes owned client."""
        adapter = OpenFGAAdapter(mock_settings)

        with patch(
            "siopv.adapters.authorization.openfga_adapter.OpenFgaClient"
        ) as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_class.return_value = mock_client_instance
            await adapter.initialize()

            await adapter.close()

            mock_client_instance.__aexit__.assert_called_once()
            mock_client_instance.close.assert_called_once()
            assert adapter._owned_client is None

    @pytest.mark.asyncio
    async def test_get_client_raises_error_if_not_initialized(
        self,
        mock_settings: MagicMock,
    ) -> None:
        """Test _get_client raises error if client not initialized."""
        adapter = OpenFGAAdapter(mock_settings)

        with pytest.raises(StoreNotFoundError, match="not initialized"):
            await adapter._get_client()

    @pytest.mark.asyncio
    async def test_get_client_returns_owned_client_after_initialize(
        self,
        mock_settings: MagicMock,
    ) -> None:
        """Test _get_client returns owned client after initialization."""
        adapter = OpenFGAAdapter(mock_settings)

        with patch(
            "siopv.adapters.authorization.openfga_adapter.OpenFgaClient"
        ) as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_class.return_value = mock_client_instance
            await adapter.initialize()

            # Now _get_client should return the owned client
            result = await adapter._get_client()
            assert result is mock_client_instance

    @pytest.mark.asyncio
    async def test_close_without_owned_client_is_noop(
        self,
        mock_settings: MagicMock,
    ) -> None:
        """Test close() is no-op when no owned client exists."""
        adapter = OpenFGAAdapter(mock_settings)

        # Should not raise - close() without owned client is safe
        await adapter.close()
        assert adapter._owned_client is None


class TestAuthorizationPortCheck:
    """Tests for AuthorizationPort.check method."""

    @pytest.mark.asyncio
    async def test_check_allowed(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
        sample_context: AuthorizationContext,
    ) -> None:
        """Test check returns allowed result."""
        # Mock check response
        mock_response = MagicMock()
        mock_response.allowed = True
        mock_openfga_client.check.return_value = mock_response

        result = await adapter_with_mock_client.check(sample_context)

        assert result.allowed is True
        assert result.context == sample_context
        mock_openfga_client.check.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_denied(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
        sample_context: AuthorizationContext,
    ) -> None:
        """Test check returns denied result."""
        mock_response = MagicMock()
        mock_response.allowed = False
        mock_openfga_client.check.return_value = mock_response

        result = await adapter_with_mock_client.check(sample_context)

        assert result.allowed is False
        assert "lacks" in result.reason

    @pytest.mark.asyncio
    async def test_check_with_direct_relation(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
        sample_resource: ResourceId,
    ) -> None:
        """Test check uses direct relation when specified."""
        context = AuthorizationContext.for_relation_check(
            user_id="alice",
            resource=sample_resource,
            relation=Relation.OWNER,
        )

        mock_response = MagicMock()
        mock_response.allowed = True
        mock_openfga_client.check.return_value = mock_response

        result = await adapter_with_mock_client.check(context)

        assert result.allowed is True
        assert result.checked_relation == Relation.OWNER

    @pytest.mark.asyncio
    async def test_check_with_contextual_tuples(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
        sample_user: UserId,
        sample_resource: ResourceId,
        sample_tuple: RelationshipTuple,
    ) -> None:
        """Test check includes contextual tuples."""
        context = AuthorizationContext.for_action(
            user_id=sample_user.value,
            resource=sample_resource,
            action=Action.VIEW,
            contextual_tuples=[sample_tuple],
        )

        mock_response = MagicMock()
        mock_response.allowed = True
        mock_openfga_client.check.return_value = mock_response

        result = await adapter_with_mock_client.check(context)

        assert result.allowed is True
        # Verify contextual tuples were passed
        call_args = mock_openfga_client.check.call_args
        request = call_args[0][0]
        assert request.contextual_tuples is not None

    @pytest.mark.asyncio
    async def test_check_records_duration(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
        sample_context: AuthorizationContext,
    ) -> None:
        """Test check records check duration."""
        mock_response = MagicMock()
        mock_response.allowed = True
        mock_openfga_client.check.return_value = mock_response

        result = await adapter_with_mock_client.check(sample_context)

        assert result.check_duration_ms >= 0

    @pytest.mark.asyncio
    async def test_check_with_cached_model_id(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
        sample_context: AuthorizationContext,
    ) -> None:
        """Test check uses cached model ID in options."""
        adapter_with_mock_client._cached_model_id = "model-123"

        mock_response = MagicMock()
        mock_response.allowed = True
        mock_openfga_client.check.return_value = mock_response

        await adapter_with_mock_client.check(sample_context)

        # Verify options included model ID
        call_args = mock_openfga_client.check.call_args
        options = call_args[0][1]
        assert options["authorization_model_id"] == "model-123"

    @pytest.mark.asyncio
    async def test_check_with_action_not_mapped_raises_error(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        sample_user: UserId,
        sample_resource: ResourceId,
    ) -> None:
        """Test check raises ActionNotMappedError for unmapped action."""
        # Create context with action that has no mapping
        adapter_with_mock_client._action_mappings = {}
        context = AuthorizationContext.for_action(
            user_id=sample_user.value,
            resource=sample_resource,
            action=Action.VIEW,
        )

        with pytest.raises(ActionNotMappedError):
            await adapter_with_mock_client.check(context)

    @pytest.mark.asyncio
    async def test_check_reraises_store_not_found_error(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
        sample_context: AuthorizationContext,
    ) -> None:
        """Test check reraises StoreNotFoundError."""
        mock_openfga_client.check.side_effect = StoreNotFoundError()

        with pytest.raises(StoreNotFoundError):
            await adapter_with_mock_client.check(sample_context)


class TestAuthorizationPortBatchCheck:
    """Tests for AuthorizationPort.batch_check method."""

    @pytest.mark.asyncio
    async def test_batch_check_all_allowed(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
        sample_resource: ResourceId,
    ) -> None:
        """Test batch_check with all allowed results."""
        contexts = [
            AuthorizationContext.for_action(
                user_id="alice",
                resource=sample_resource,
                action=Action.VIEW,
            ),
            AuthorizationContext.for_action(
                user_id="bob",
                resource=sample_resource,
                action=Action.VIEW,
            ),
        ]

        # Mock batch check response
        mock_result1 = MagicMock()
        mock_result1.allowed = True
        mock_result2 = MagicMock()
        mock_result2.allowed = True

        mock_response = MagicMock()
        mock_response.result = [mock_result1, mock_result2]
        mock_openfga_client.batch_check.return_value = mock_response

        result = await adapter_with_mock_client.batch_check(contexts)

        assert result.all_allowed is True
        assert result.any_denied is False
        assert len(result.results) == 2

    @pytest.mark.asyncio
    async def test_batch_check_some_denied(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
        sample_resource: ResourceId,
    ) -> None:
        """Test batch_check with some denied results."""
        contexts = [
            AuthorizationContext.for_action(
                user_id="alice",
                resource=sample_resource,
                action=Action.VIEW,
            ),
            AuthorizationContext.for_action(
                user_id="bob",
                resource=sample_resource,
                action=Action.DELETE,
            ),
        ]

        mock_result1 = MagicMock()
        mock_result1.allowed = True
        mock_result2 = MagicMock()
        mock_result2.allowed = False

        mock_response = MagicMock()
        mock_response.result = [mock_result1, mock_result2]
        mock_openfga_client.batch_check.return_value = mock_response

        result = await adapter_with_mock_client.batch_check(contexts)

        assert result.all_allowed is False
        assert result.any_denied is True
        assert result.allowed_count == 1
        assert result.denied_count == 1

    @pytest.mark.asyncio
    async def test_batch_check_empty_list_raises_error(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
    ) -> None:
        """Test batch_check raises ValueError for empty list."""
        with pytest.raises(ValueError, match="cannot be empty"):
            await adapter_with_mock_client.batch_check([])

    @pytest.mark.asyncio
    async def test_batch_check_exceeds_max_size_raises_error(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        sample_resource: ResourceId,
    ) -> None:
        """Test batch_check raises ValueError for oversized list."""
        contexts = [
            AuthorizationContext.for_action(
                user_id=f"user{i}",
                resource=sample_resource,
                action=Action.VIEW,
            )
            for i in range(101)
        ]

        with pytest.raises(ValueError, match="exceeds maximum batch size"):
            await adapter_with_mock_client.batch_check(contexts)

    @pytest.mark.asyncio
    async def test_batch_check_with_contextual_tuples_and_model_id(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
        sample_resource: ResourceId,
        sample_tuple: RelationshipTuple,
    ) -> None:
        """Test batch_check with contextual tuples and cached model ID."""
        adapter_with_mock_client._cached_model_id = "model-456"

        contexts = [
            AuthorizationContext.for_action(
                user_id="alice",
                resource=sample_resource,
                action=Action.VIEW,
                contextual_tuples=[sample_tuple],
            ),
        ]

        mock_result = MagicMock()
        mock_result.allowed = True
        mock_response = MagicMock()
        mock_response.result = [mock_result]
        mock_openfga_client.batch_check.return_value = mock_response

        result = await adapter_with_mock_client.batch_check(contexts)

        assert len(result.results) == 1
        # Verify options included model ID
        call_args = mock_openfga_client.batch_check.call_args
        options = call_args[0][1]
        assert options["authorization_model_id"] == "model-456"

    @pytest.mark.asyncio
    async def test_batch_check_with_fallback_iteration(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
        sample_resource: ResourceId,
    ) -> None:
        """Test batch_check fallback when response.result doesn't exist."""
        contexts = [
            AuthorizationContext.for_action(
                user_id="alice",
                resource=sample_resource,
                action=Action.VIEW,
            ),
        ]

        # Mock response without 'result' attribute (fallback path)
        mock_check_result = MagicMock()
        mock_check_result.allowed = True
        mock_response = [mock_check_result]  # Iterable, but no .result attribute
        mock_openfga_client.batch_check.return_value = mock_response

        result = await adapter_with_mock_client.batch_check(contexts)

        assert len(result.results) == 1
        assert result.all_allowed is True

    @pytest.mark.asyncio
    async def test_batch_check_circuit_breaker_error(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        sample_resource: ResourceId,
    ) -> None:
        """Test batch_check handles CircuitBreakerError."""
        contexts = [
            AuthorizationContext.for_action(
                user_id="alice",
                resource=sample_resource,
                action=Action.VIEW,
            ),
        ]

        # Simulate circuit breaker open by patching _check_state
        async def raise_circuit_error() -> None:
            raise CircuitBreakerError("openfga_auth")

        with (
            patch.object(
                adapter_with_mock_client._circuit_breaker,
                "_check_state",
                side_effect=raise_circuit_error,
            ),
            pytest.raises(AuthorizationCheckError, match="unavailable"),
        ):
            await adapter_with_mock_client.batch_check(contexts)

    @pytest.mark.asyncio
    async def test_batch_check_generic_error(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
        sample_resource: ResourceId,
    ) -> None:
        """Test batch_check handles generic exceptions."""
        contexts = [
            AuthorizationContext.for_action(
                user_id="alice",
                resource=sample_resource,
                action=Action.VIEW,
            ),
        ]

        mock_openfga_client.batch_check.side_effect = RuntimeError("Batch failed")

        with pytest.raises(AuthorizationCheckError, match="Batch check failed"):
            await adapter_with_mock_client.batch_check(contexts)

    @pytest.mark.asyncio
    async def test_batch_check_store_not_found_error_propagates(
        self,
        mock_settings: MagicMock,
        sample_resource: ResourceId,
    ) -> None:
        """Test batch_check propagates StoreNotFoundError."""
        # Create adapter without initializing client
        adapter = OpenFGAAdapter(mock_settings)

        contexts = [
            AuthorizationContext.for_action(
                user_id="alice",
                resource=sample_resource,
                action=Action.VIEW,
            ),
        ]

        # Should raise StoreNotFoundError (not wrapped)
        with pytest.raises(StoreNotFoundError):
            await adapter.batch_check(contexts)


class TestAuthorizationPortCheckRelation:
    """Tests for AuthorizationPort.check_relation method."""

    @pytest.mark.asyncio
    async def test_check_relation_allowed(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
        sample_user: UserId,
        sample_resource: ResourceId,
    ) -> None:
        """Test check_relation returns allowed result."""
        mock_response = MagicMock()
        mock_response.allowed = True
        mock_openfga_client.check.return_value = mock_response

        result = await adapter_with_mock_client.check_relation(
            sample_user,
            Relation.OWNER,
            sample_resource,
        )

        assert result.allowed is True
        assert result.checked_relation == Relation.OWNER

    @pytest.mark.asyncio
    async def test_check_relation_denied(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
        sample_user: UserId,
        sample_resource: ResourceId,
    ) -> None:
        """Test check_relation returns denied result."""
        mock_response = MagicMock()
        mock_response.allowed = False
        mock_openfga_client.check.return_value = mock_response

        result = await adapter_with_mock_client.check_relation(
            sample_user,
            Relation.OWNER,
            sample_resource,
        )

        assert result.allowed is False

    @pytest.mark.asyncio
    async def test_check_relation_circuit_breaker_error(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        sample_user: UserId,
        sample_resource: ResourceId,
    ) -> None:
        """Test check_relation handles CircuitBreakerError."""

        async def raise_circuit_error() -> None:
            raise CircuitBreakerError("openfga_auth")

        with (
            patch.object(
                adapter_with_mock_client._circuit_breaker,
                "_check_state",
                side_effect=raise_circuit_error,
            ),
            pytest.raises(AuthorizationCheckError, match="unavailable"),
        ):
            await adapter_with_mock_client.check_relation(
                sample_user,
                Relation.VIEWER,
                sample_resource,
            )

    @pytest.mark.asyncio
    async def test_check_relation_generic_error(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
        sample_user: UserId,
        sample_resource: ResourceId,
    ) -> None:
        """Test check_relation handles generic exceptions."""
        mock_openfga_client.check.side_effect = RuntimeError("Check failed")

        with pytest.raises(AuthorizationCheckError, match="Relation check failed"):
            await adapter_with_mock_client.check_relation(
                sample_user,
                Relation.VIEWER,
                sample_resource,
            )


class TestAuthorizationPortListUserRelations:
    """Tests for AuthorizationPort.list_user_relations method."""

    @pytest.mark.asyncio
    async def test_list_user_relations_finds_multiple(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
        sample_user: UserId,
        sample_resource: ResourceId,
    ) -> None:
        """Test list_user_relations finds multiple relations."""

        # Make check return True for VIEWER and ANALYST, False for others
        async def mock_check(request: Any, _options: Any = None) -> MagicMock:
            response = MagicMock()
            response.allowed = request.relation in ("viewer", "analyst")
            return response

        mock_openfga_client.check.side_effect = mock_check

        relations = await adapter_with_mock_client.list_user_relations(
            sample_user,
            sample_resource,
        )

        assert Relation.VIEWER in relations
        assert Relation.ANALYST in relations

    @pytest.mark.asyncio
    async def test_list_user_relations_empty(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
        sample_user: UserId,
        sample_resource: ResourceId,
    ) -> None:
        """Test list_user_relations returns empty when no relations."""
        mock_response = MagicMock()
        mock_response.allowed = False
        mock_openfga_client.check.return_value = mock_response

        relations = await adapter_with_mock_client.list_user_relations(
            sample_user,
            sample_resource,
        )

        assert relations == []

    @pytest.mark.asyncio
    async def test_list_user_relations_skips_failed_checks(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
        sample_user: UserId,
        sample_resource: ResourceId,
    ) -> None:
        """Test list_user_relations skips relations that fail to check."""
        call_count = 0

        async def mock_check_with_errors(_request: Any, _options: Any = None) -> MagicMock:
            nonlocal call_count
            call_count += 1
            if call_count % 2 == 0:
                raise AuthorizationCheckError(sample_user, "test", sample_resource)
            response = MagicMock()
            response.allowed = True
            return response

        mock_openfga_client.check.side_effect = mock_check_with_errors

        relations = await adapter_with_mock_client.list_user_relations(
            sample_user,
            sample_resource,
        )

        # Should have some relations despite errors
        assert len(relations) > 0

    @pytest.mark.asyncio
    async def test_list_user_relations_graceful_degradation(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
        sample_user: UserId,
        sample_resource: ResourceId,
    ) -> None:
        """Test list_user_relations handles check failures gracefully.

        When individual relation checks fail, the method continues checking
        other relations rather than failing completely. This provides graceful
        degradation when some relations aren't valid for the resource type.
        """
        # All checks fail - should return empty list
        mock_openfga_client.check.side_effect = RuntimeError("Unexpected failure")

        result = await adapter_with_mock_client.list_user_relations(
            sample_user,
            sample_resource,
        )

        # Should return empty list (all checks failed and were skipped)
        assert result == []


class TestAuthorizationStorePortWriteTuple:
    """Tests for AuthorizationStorePort.write_tuple method."""

    @pytest.mark.asyncio
    async def test_write_tuple_success(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
        sample_tuple: RelationshipTuple,
    ) -> None:
        """Test write_tuple succeeds."""
        mock_openfga_client.write.return_value = MagicMock()

        await adapter_with_mock_client.write_tuple(sample_tuple)

        mock_openfga_client.write.assert_called_once()

    @pytest.mark.asyncio
    async def test_write_tuple_validation_error(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
        sample_tuple: RelationshipTuple,
    ) -> None:
        """Test write_tuple raises TupleValidationError on validation failure."""
        from openfga_sdk.exceptions import FgaValidationException

        mock_openfga_client.write.side_effect = FgaValidationException("Invalid tuple")

        with pytest.raises(TupleValidationError):
            await adapter_with_mock_client.write_tuple(sample_tuple)

    @pytest.mark.asyncio
    async def test_write_tuple_with_cached_model_id(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
        sample_tuple: RelationshipTuple,
    ) -> None:
        """Test write_tuple uses cached model ID."""
        adapter_with_mock_client._cached_model_id = "model-789"
        mock_openfga_client.write.return_value = MagicMock()

        await adapter_with_mock_client.write_tuple(sample_tuple)

        call_args = mock_openfga_client.write.call_args
        options = call_args[0][1]
        assert options["authorization_model_id"] == "model-789"

    @pytest.mark.asyncio
    async def test_write_tuple_circuit_breaker_error(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        sample_tuple: RelationshipTuple,
    ) -> None:
        """Test write_tuple handles CircuitBreakerError."""

        async def raise_circuit_error() -> None:
            raise CircuitBreakerError("openfga_auth")

        with (
            patch.object(
                adapter_with_mock_client._circuit_breaker,
                "_check_state",
                side_effect=raise_circuit_error,
            ),
            pytest.raises(AuthorizationCheckError, match="unavailable"),
        ):
            await adapter_with_mock_client.write_tuple(sample_tuple)

    @pytest.mark.asyncio
    async def test_write_tuple_generic_error(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
        sample_tuple: RelationshipTuple,
    ) -> None:
        """Test write_tuple handles generic exceptions."""
        mock_openfga_client.write.side_effect = RuntimeError("Write failed")

        with pytest.raises(AuthorizationCheckError, match="Failed to write tuple"):
            await adapter_with_mock_client.write_tuple(sample_tuple)


class TestAuthorizationStorePortWriteTuples:
    """Tests for AuthorizationStorePort.write_tuples method."""

    @pytest.mark.asyncio
    async def test_write_tuples_success(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
    ) -> None:
        """Test write_tuples succeeds with multiple tuples."""
        tuples = [
            RelationshipTuple.create("alice", Relation.VIEWER, ResourceType.PROJECT, "p1"),
            RelationshipTuple.create("bob", Relation.VIEWER, ResourceType.PROJECT, "p1"),
        ]

        mock_openfga_client.write.return_value = MagicMock()

        await adapter_with_mock_client.write_tuples(tuples)

        mock_openfga_client.write.assert_called_once()

    @pytest.mark.asyncio
    async def test_write_tuples_empty_list_raises_error(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
    ) -> None:
        """Test write_tuples raises ValueError for empty list."""
        with pytest.raises(ValueError, match="cannot be empty"):
            await adapter_with_mock_client.write_tuples([])

    @pytest.mark.asyncio
    async def test_write_tuples_exceeds_max_size_raises_error(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
    ) -> None:
        """Test write_tuples raises ValueError for oversized list."""
        tuples = [
            RelationshipTuple.create(f"user{i}", Relation.VIEWER, ResourceType.PROJECT, "p1")
            for i in range(101)
        ]

        with pytest.raises(ValueError, match="exceeds maximum batch size"):
            await adapter_with_mock_client.write_tuples(tuples)

    @pytest.mark.asyncio
    async def test_write_tuples_with_model_id(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
    ) -> None:
        """Test write_tuples uses cached model ID."""
        adapter_with_mock_client._cached_model_id = "model-999"
        tuples = [
            RelationshipTuple.create("alice", Relation.VIEWER, ResourceType.PROJECT, "p1"),
        ]

        mock_openfga_client.write.return_value = MagicMock()

        await adapter_with_mock_client.write_tuples(tuples)

        call_args = mock_openfga_client.write.call_args
        options = call_args[0][1]
        assert options["authorization_model_id"] == "model-999"

    @pytest.mark.asyncio
    async def test_write_tuples_validation_error(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
    ) -> None:
        """Test write_tuples handles validation errors."""
        from openfga_sdk.exceptions import FgaValidationException

        tuples = [
            RelationshipTuple.create("alice", Relation.VIEWER, ResourceType.PROJECT, "p1"),
        ]

        mock_openfga_client.write.side_effect = FgaValidationException("Invalid batch")

        with pytest.raises(TupleValidationError, match="Batch write validation failed"):
            await adapter_with_mock_client.write_tuples(tuples)

    @pytest.mark.asyncio
    async def test_write_tuples_circuit_breaker_error(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
    ) -> None:
        """Test write_tuples handles CircuitBreakerError."""
        tuples = [
            RelationshipTuple.create("alice", Relation.VIEWER, ResourceType.PROJECT, "p1"),
        ]

        async def raise_circuit_error() -> None:
            raise CircuitBreakerError("openfga_auth")

        with (
            patch.object(
                adapter_with_mock_client._circuit_breaker,
                "_check_state",
                side_effect=raise_circuit_error,
            ),
            pytest.raises(AuthorizationCheckError, match="unavailable"),
        ):
            await adapter_with_mock_client.write_tuples(tuples)

    @pytest.mark.asyncio
    async def test_write_tuples_generic_error(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
    ) -> None:
        """Test write_tuples handles generic exceptions."""
        tuples = [
            RelationshipTuple.create("alice", Relation.VIEWER, ResourceType.PROJECT, "p1"),
        ]

        mock_openfga_client.write.side_effect = RuntimeError("Batch write failed")

        with pytest.raises(AuthorizationCheckError, match="Batch write failed"):
            await adapter_with_mock_client.write_tuples(tuples)


class TestAuthorizationStorePortDeleteTuple:
    """Tests for AuthorizationStorePort.delete_tuple method."""

    @pytest.mark.asyncio
    async def test_delete_tuple_success(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
        sample_tuple: RelationshipTuple,
    ) -> None:
        """Test delete_tuple succeeds."""
        mock_openfga_client.write.return_value = MagicMock()

        await adapter_with_mock_client.delete_tuple(sample_tuple)

        mock_openfga_client.write.assert_called_once()
        # Verify delete was called (not write)
        call_args = mock_openfga_client.write.call_args
        request = call_args[0][0]
        assert request.deletes is not None

    @pytest.mark.asyncio
    async def test_delete_tuple_with_model_id(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
        sample_tuple: RelationshipTuple,
    ) -> None:
        """Test delete_tuple uses cached model ID."""
        adapter_with_mock_client._cached_model_id = "model-888"
        mock_openfga_client.write.return_value = MagicMock()

        await adapter_with_mock_client.delete_tuple(sample_tuple)

        call_args = mock_openfga_client.write.call_args
        options = call_args[0][1]
        assert options["authorization_model_id"] == "model-888"

    @pytest.mark.asyncio
    async def test_delete_tuple_circuit_breaker_error(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        sample_tuple: RelationshipTuple,
    ) -> None:
        """Test delete_tuple handles CircuitBreakerError."""

        async def raise_circuit_error() -> None:
            raise CircuitBreakerError("openfga_auth")

        with (
            patch.object(
                adapter_with_mock_client._circuit_breaker,
                "_check_state",
                side_effect=raise_circuit_error,
            ),
            pytest.raises(AuthorizationCheckError, match="unavailable"),
        ):
            await adapter_with_mock_client.delete_tuple(sample_tuple)

    @pytest.mark.asyncio
    async def test_delete_tuple_generic_error(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
        sample_tuple: RelationshipTuple,
    ) -> None:
        """Test delete_tuple handles generic exceptions."""
        mock_openfga_client.write.side_effect = RuntimeError("Delete failed")

        with pytest.raises(AuthorizationCheckError, match="Failed to delete tuple"):
            await adapter_with_mock_client.delete_tuple(sample_tuple)


class TestAuthorizationStorePortDeleteTuples:
    """Tests for AuthorizationStorePort.delete_tuples method."""

    @pytest.mark.asyncio
    async def test_delete_tuples_success(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
    ) -> None:
        """Test delete_tuples succeeds with multiple tuples."""
        tuples = [
            RelationshipTuple.create("alice", Relation.VIEWER, ResourceType.PROJECT, "p1"),
            RelationshipTuple.create("bob", Relation.VIEWER, ResourceType.PROJECT, "p1"),
        ]

        mock_openfga_client.write.return_value = MagicMock()

        await adapter_with_mock_client.delete_tuples(tuples)

        mock_openfga_client.write.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_tuples_empty_list_raises_error(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
    ) -> None:
        """Test delete_tuples raises ValueError for empty list."""
        with pytest.raises(ValueError, match="cannot be empty"):
            await adapter_with_mock_client.delete_tuples([])

    @pytest.mark.asyncio
    async def test_delete_tuples_exceeds_max_size(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
    ) -> None:
        """Test delete_tuples raises ValueError for oversized list."""
        tuples = [
            RelationshipTuple.create(f"user{i}", Relation.VIEWER, ResourceType.PROJECT, "p1")
            for i in range(101)
        ]

        with pytest.raises(ValueError, match="exceeds maximum batch size"):
            await adapter_with_mock_client.delete_tuples(tuples)

    @pytest.mark.asyncio
    async def test_delete_tuples_with_model_id(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
    ) -> None:
        """Test delete_tuples uses cached model ID."""
        adapter_with_mock_client._cached_model_id = "model-777"
        tuples = [
            RelationshipTuple.create("alice", Relation.VIEWER, ResourceType.PROJECT, "p1"),
        ]

        mock_openfga_client.write.return_value = MagicMock()

        await adapter_with_mock_client.delete_tuples(tuples)

        call_args = mock_openfga_client.write.call_args
        options = call_args[0][1]
        assert options["authorization_model_id"] == "model-777"

    @pytest.mark.asyncio
    async def test_delete_tuples_circuit_breaker_error(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
    ) -> None:
        """Test delete_tuples handles CircuitBreakerError."""
        tuples = [
            RelationshipTuple.create("alice", Relation.VIEWER, ResourceType.PROJECT, "p1"),
        ]

        async def raise_circuit_error() -> None:
            raise CircuitBreakerError("openfga_auth")

        with (
            patch.object(
                adapter_with_mock_client._circuit_breaker,
                "_check_state",
                side_effect=raise_circuit_error,
            ),
            pytest.raises(AuthorizationCheckError, match="unavailable"),
        ):
            await adapter_with_mock_client.delete_tuples(tuples)

    @pytest.mark.asyncio
    async def test_delete_tuples_generic_error(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
    ) -> None:
        """Test delete_tuples handles generic exceptions."""
        tuples = [
            RelationshipTuple.create("alice", Relation.VIEWER, ResourceType.PROJECT, "p1"),
        ]

        mock_openfga_client.write.side_effect = RuntimeError("Batch delete failed")

        with pytest.raises(AuthorizationCheckError, match="Batch delete failed"):
            await adapter_with_mock_client.delete_tuples(tuples)


class TestAuthorizationStorePortReadTuples:
    """Tests for AuthorizationStorePort.read_tuples method."""

    @pytest.mark.asyncio
    async def test_read_tuples_with_filters(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
        sample_user: UserId,
        sample_resource: ResourceId,
    ) -> None:
        """Test read_tuples with filters."""
        mock_tuple_key = MagicMock()
        mock_tuple_key.user = "user:alice"
        mock_tuple_key.relation = "viewer"
        mock_tuple_key.object = "project:test-project"

        mock_tuple = MagicMock()
        mock_tuple.key = mock_tuple_key

        mock_response = MagicMock()
        mock_response.tuples = [mock_tuple]
        mock_openfga_client.read.return_value = mock_response

        tuples = await adapter_with_mock_client.read_tuples(
            user=sample_user,
            relation=Relation.VIEWER,
            resource=sample_resource,
        )

        assert len(tuples) == 1
        mock_openfga_client.read.assert_called_once()

    @pytest.mark.asyncio
    async def test_read_tuples_empty_result(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
    ) -> None:
        """Test read_tuples returns empty list when no matches."""
        mock_response = MagicMock()
        mock_response.tuples = []
        mock_openfga_client.read.return_value = mock_response

        tuples = await adapter_with_mock_client.read_tuples()

        assert tuples == []

    @pytest.mark.asyncio
    async def test_read_tuples_without_tuples_attribute(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
    ) -> None:
        """Test read_tuples handles response without tuples attribute."""
        mock_response = MagicMock(spec=[])  # Response without 'tuples' attribute
        mock_openfga_client.read.return_value = mock_response

        tuples = await adapter_with_mock_client.read_tuples()

        assert tuples == []

    @pytest.mark.asyncio
    async def test_read_tuples_circuit_breaker_error(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        sample_user: UserId,
    ) -> None:
        """Test read_tuples handles CircuitBreakerError."""

        async def raise_circuit_error() -> None:
            raise CircuitBreakerError("openfga_auth")

        with (
            patch.object(
                adapter_with_mock_client._circuit_breaker,
                "_check_state",
                side_effect=raise_circuit_error,
            ),
            pytest.raises(AuthorizationCheckError, match="unavailable"),
        ):
            await adapter_with_mock_client.read_tuples(user=sample_user)

    @pytest.mark.asyncio
    async def test_read_tuples_generic_error(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
    ) -> None:
        """Test read_tuples handles generic exceptions."""
        mock_openfga_client.read.side_effect = RuntimeError("Read failed")

        with pytest.raises(AuthorizationCheckError, match="Failed to read tuples"):
            await adapter_with_mock_client.read_tuples()

    @pytest.mark.asyncio
    async def test_read_tuples_for_resource(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
        sample_resource: ResourceId,
    ) -> None:
        """Test read_tuples_for_resource delegates to read_tuples."""
        mock_response = MagicMock()
        mock_response.tuples = []
        mock_openfga_client.read.return_value = mock_response

        tuples = await adapter_with_mock_client.read_tuples_for_resource(sample_resource)

        assert tuples == []
        mock_openfga_client.read.assert_called_once()

    @pytest.mark.asyncio
    async def test_read_tuples_for_user(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
        sample_user: UserId,
    ) -> None:
        """Test read_tuples_for_user delegates to read_tuples."""
        mock_response = MagicMock()
        mock_response.tuples = []
        mock_openfga_client.read.return_value = mock_response

        tuples = await adapter_with_mock_client.read_tuples_for_user(sample_user)

        assert tuples == []
        mock_openfga_client.read.assert_called_once()


class TestAuthorizationStorePortTupleExists:
    """Tests for AuthorizationStorePort.tuple_exists method."""

    @pytest.mark.asyncio
    async def test_tuple_exists_true(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
        sample_user: UserId,
        sample_resource: ResourceId,
    ) -> None:
        """Test tuple_exists returns True when tuple exists."""
        mock_tuple_key = MagicMock()
        mock_tuple_key.user = "user:alice"
        mock_tuple_key.relation = "viewer"
        mock_tuple_key.object = "project:test-project"

        mock_tuple = MagicMock()
        mock_tuple.key = mock_tuple_key

        mock_response = MagicMock()
        mock_response.tuples = [mock_tuple]
        mock_openfga_client.read.return_value = mock_response

        exists = await adapter_with_mock_client.tuple_exists(
            sample_user,
            Relation.VIEWER,
            sample_resource,
        )

        assert exists is True

    @pytest.mark.asyncio
    async def test_tuple_exists_false(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
        sample_user: UserId,
        sample_resource: ResourceId,
    ) -> None:
        """Test tuple_exists returns False when tuple doesn't exist."""
        mock_response = MagicMock()
        mock_response.tuples = []
        mock_openfga_client.read.return_value = mock_response

        exists = await adapter_with_mock_client.tuple_exists(
            sample_user,
            Relation.OWNER,
            sample_resource,
        )

        assert exists is False


class TestAuthorizationModelPort:
    """Tests for AuthorizationModelPort methods."""

    @pytest.mark.asyncio
    async def test_get_model_id_success(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
    ) -> None:
        """Test get_model_id returns model ID."""
        mock_model = MagicMock()
        mock_model.id = "model-123"

        mock_response = MagicMock()
        mock_response.authorization_models = [mock_model]
        mock_openfga_client.read_authorization_models.return_value = mock_response

        model_id = await adapter_with_mock_client.get_model_id()

        assert model_id == "model-123"
        assert adapter_with_mock_client._cached_model_id == "model-123"

    @pytest.mark.asyncio
    async def test_get_model_id_no_models_raises_error(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
    ) -> None:
        """Test get_model_id raises error when no models exist."""
        mock_response = MagicMock()
        mock_response.authorization_models = []
        mock_openfga_client.read_authorization_models.return_value = mock_response

        with pytest.raises(AuthorizationModelError, match="No authorization models"):
            await adapter_with_mock_client.get_model_id()

    @pytest.mark.asyncio
    async def test_get_model_id_reraises_store_not_found(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
    ) -> None:
        """Test get_model_id reraises StoreNotFoundError."""
        mock_openfga_client.read_authorization_models.side_effect = StoreNotFoundError()

        with pytest.raises(StoreNotFoundError):
            await adapter_with_mock_client.get_model_id()

    @pytest.mark.asyncio
    async def test_get_model_id_circuit_breaker_error(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
    ) -> None:
        """Test get_model_id handles CircuitBreakerError."""

        async def raise_circuit_error() -> None:
            raise CircuitBreakerError("openfga_auth")

        with (
            patch.object(
                adapter_with_mock_client._circuit_breaker,
                "_check_state",
                side_effect=raise_circuit_error,
            ),
            pytest.raises(AuthorizationModelError, match="unavailable"),
        ):
            await adapter_with_mock_client.get_model_id()

    @pytest.mark.asyncio
    async def test_get_model_id_generic_error(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
    ) -> None:
        """Test get_model_id handles generic exceptions."""
        mock_openfga_client.read_authorization_models.side_effect = RuntimeError("API failed")

        with pytest.raises(AuthorizationModelError, match="Failed to get model ID"):
            await adapter_with_mock_client.get_model_id()

    @pytest.mark.asyncio
    async def test_validate_model_success(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
    ) -> None:
        """Test validate_model returns True for valid model."""
        mock_model = MagicMock()
        mock_model.id = "model-123"

        mock_response = MagicMock()
        mock_response.authorization_models = [mock_model]
        mock_openfga_client.read_authorization_models.return_value = mock_response

        is_valid = await adapter_with_mock_client.validate_model()

        assert is_valid is True

    @pytest.mark.asyncio
    async def test_validate_model_failure(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
    ) -> None:
        """Test validate_model returns False for invalid model."""
        mock_response = MagicMock()
        mock_response.authorization_models = []
        mock_openfga_client.read_authorization_models.return_value = mock_response

        is_valid = await adapter_with_mock_client.validate_model()

        assert is_valid is False

    @pytest.mark.asyncio
    async def test_validate_model_reraises_store_not_found(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
    ) -> None:
        """Test validate_model reraises StoreNotFoundError."""
        mock_openfga_client.read_authorization_models.side_effect = StoreNotFoundError()

        with pytest.raises(StoreNotFoundError):
            await adapter_with_mock_client.validate_model()

    @pytest.mark.asyncio
    async def test_health_check_success(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
    ) -> None:
        """Test health_check returns True when healthy."""
        mock_openfga_client.read_authorization_models.return_value = MagicMock()

        is_healthy = await adapter_with_mock_client.health_check()

        assert is_healthy is True

    @pytest.mark.asyncio
    async def test_health_check_failure(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
    ) -> None:
        """Test health_check returns False when unhealthy."""
        mock_openfga_client.read_authorization_models.side_effect = Exception("Connection failed")

        is_healthy = await adapter_with_mock_client.health_check()

        assert is_healthy is False


class TestCircuitBreakerBehavior:
    """Tests for circuit breaker integration."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_failures(
        self,
        mock_settings: MagicMock,
        mock_openfga_client: AsyncMock,
        sample_context: AuthorizationContext,
    ) -> None:
        """Test circuit breaker opens after consecutive failures."""
        mock_settings.circuit_breaker_failure_threshold = 2
        adapter = OpenFGAAdapter(mock_settings, client=mock_openfga_client)

        mock_openfga_client.check.side_effect = Exception("Service unavailable")

        # First failures
        for _ in range(2):
            with pytest.raises(AuthorizationCheckError):
                await adapter.check(sample_context)

        # Circuit should be open now
        with pytest.raises(AuthorizationCheckError, match="circuit breaker open"):
            await adapter.check(sample_context)


class TestErrorMapping:
    """Tests for error mapping to domain exceptions."""

    @pytest.mark.asyncio
    async def test_fga_validation_error_maps_to_model_error(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
        sample_context: AuthorizationContext,
    ) -> None:
        """Test FgaValidationException maps to AuthorizationModelError."""
        from openfga_sdk.exceptions import FgaValidationException

        mock_openfga_client.check.side_effect = FgaValidationException("Invalid model")

        with pytest.raises(AuthorizationModelError):
            await adapter_with_mock_client.check(sample_context)

    @pytest.mark.asyncio
    async def test_generic_error_maps_to_check_error(
        self,
        adapter_with_mock_client: OpenFGAAdapter,
        mock_openfga_client: AsyncMock,
        sample_context: AuthorizationContext,
    ) -> None:
        """Test generic exception maps to AuthorizationCheckError."""
        mock_openfga_client.check.side_effect = RuntimeError("Unexpected error")

        with pytest.raises(AuthorizationCheckError, match="Unexpected error"):
            await adapter_with_mock_client.check(sample_context)
