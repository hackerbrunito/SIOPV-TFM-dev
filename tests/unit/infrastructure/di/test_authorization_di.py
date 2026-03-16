"""Unit tests for authorization DI factory functions.

Tests cover:
- create_authorization_adapter: Creates and configures OpenFGAAdapter
- get_authorization_port: Returns AuthorizationPort implementation
- get_authorization_store_port: Returns AuthorizationStorePort implementation
- get_authorization_model_port: Returns AuthorizationModelPort implementation
- Proper settings handling and logging
- Cache behavior with lru_cache
"""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest

from siopv.adapters.authorization import OpenFGAAdapter
from siopv.application.ports import (
    AuthorizationModelPort,
    AuthorizationPort,
    AuthorizationStorePort,
)
from siopv.infrastructure.di.authorization import (
    create_authorization_adapter,
    get_authorization_model_port,
    get_authorization_port,
    get_authorization_store_port,
)


@pytest.fixture
def mock_settings() -> MagicMock:
    """Create mock settings for authorization DI tests."""
    settings = MagicMock()
    settings.openfga_api_url = "http://localhost:8080"
    settings.openfga_store_id = "test-store-id"
    settings.openfga_api_token = None
    settings.openfga_authorization_model_id = None
    settings.openfga_auth_method = "none"
    settings.openfga_client_id = None
    settings.openfga_client_secret = None
    settings.openfga_api_audience = None
    settings.openfga_api_token_issuer = None
    settings.circuit_breaker_failure_threshold = 5
    settings.circuit_breaker_recovery_timeout = 60
    return settings


@pytest.fixture(autouse=True)
def clear_authorization_caches() -> None:
    """Clear all authorization DI caches before each test to ensure isolation."""
    create_authorization_adapter.cache_clear()
    get_authorization_port.cache_clear()
    get_authorization_store_port.cache_clear()
    get_authorization_model_port.cache_clear()


@pytest.fixture(autouse=True)
def patch_get_settings(mock_settings: MagicMock) -> MagicMock:
    """Patch get_settings in the authorization DI module for all tests."""
    with patch(
        "siopv.infrastructure.di.authorization.get_settings", return_value=mock_settings
    ) as mock:
        yield mock


class TestCreateAuthorizationAdapter:
    """Tests for create_authorization_adapter factory function."""

    def test_creates_openfga_adapter_instance(self) -> None:
        """Test that factory creates OpenFGAAdapter instance."""
        adapter = create_authorization_adapter()

        assert adapter is not None
        assert isinstance(adapter, OpenFGAAdapter)

    def test_adapter_receives_settings(self, mock_settings: MagicMock) -> None:
        """Test that adapter is initialized with settings from get_settings()."""
        adapter = create_authorization_adapter()

        assert adapter._api_url == mock_settings.openfga_api_url
        assert adapter._store_id == mock_settings.openfga_store_id

    def test_adapter_circuit_breaker_configured(self) -> None:
        """Test that adapter's circuit breaker is configured from settings."""
        adapter = create_authorization_adapter()

        assert adapter._circuit_breaker is not None
        assert adapter._circuit_breaker.failure_threshold == 5
        assert adapter._circuit_breaker.recovery_timeout == timedelta(seconds=60)

    def test_adapter_has_action_mappings(self) -> None:
        """Test that adapter has default action mappings initialized."""
        adapter = create_authorization_adapter()

        assert adapter._action_mappings is not None
        assert len(adapter._action_mappings) > 0

    def test_multiple_calls_return_same_cached_instance(self) -> None:
        """Test that lru_cache returns the same singleton adapter."""
        adapter1 = create_authorization_adapter()
        adapter2 = create_authorization_adapter()

        assert adapter1 is adapter2

    def test_adapter_not_initialized_after_creation(self) -> None:
        """Test that adapter is not initialized (client is None) after creation."""
        adapter = create_authorization_adapter()

        assert adapter._owned_client is None

    def test_logging_on_adapter_creation(self) -> None:
        """Test that adapter creation logs appropriate messages."""
        with patch("siopv.infrastructure.di.authorization.logger") as mock_logger:
            adapter = create_authorization_adapter()

            assert mock_logger.debug.called or mock_logger.info.called
            assert adapter is not None

    def test_get_settings_called_internally(self, patch_get_settings: MagicMock) -> None:
        """Test that get_settings() is called internally (no settings parameter)."""
        create_authorization_adapter()

        patch_get_settings.assert_called_once()


class TestGetAuthorizationPort:
    """Tests for get_authorization_port factory function."""

    def test_returns_authorization_port(self) -> None:
        """Test that function returns AuthorizationPort implementation."""
        port = get_authorization_port()

        assert port is not None
        assert isinstance(port, AuthorizationPort)

    def test_returns_openfga_adapter(self) -> None:
        """Test that returned port is actually an OpenFGAAdapter."""
        port = get_authorization_port()

        assert isinstance(port, OpenFGAAdapter)

    def test_port_implements_interface(self) -> None:
        """Test that returned port implements AuthorizationPort interface."""
        port = get_authorization_port()

        assert hasattr(port, "check")
        assert hasattr(port, "batch_check")
        assert hasattr(port, "check_relation")
        assert hasattr(port, "list_user_relations")

    def test_cache_returns_same_instance(self) -> None:
        """Test that lru_cache returns the same instance."""
        get_authorization_port.cache_clear()

        port1 = get_authorization_port()
        port2 = get_authorization_port()

        assert port1 is port2


class TestGetAuthorizationStorePort:
    """Tests for get_authorization_store_port factory function."""

    def test_returns_authorization_store_port(self) -> None:
        """Test that function returns AuthorizationStorePort implementation."""
        port = get_authorization_store_port()

        assert port is not None
        assert isinstance(port, AuthorizationStorePort)

    def test_returns_openfga_adapter(self) -> None:
        """Test that returned port is actually an OpenFGAAdapter."""
        port = get_authorization_store_port()

        assert isinstance(port, OpenFGAAdapter)

    def test_port_implements_interface(self) -> None:
        """Test that returned port implements AuthorizationStorePort interface."""
        port = get_authorization_store_port()

        assert hasattr(port, "write_tuple")
        assert hasattr(port, "write_tuples")
        assert hasattr(port, "delete_tuple")
        assert hasattr(port, "delete_tuples")
        assert hasattr(port, "read_tuples")
        assert hasattr(port, "read_tuples_for_resource")
        assert hasattr(port, "read_tuples_for_user")
        assert hasattr(port, "tuple_exists")

    def test_cache_returns_same_instance(self) -> None:
        """Test that lru_cache returns the same instance."""
        get_authorization_store_port.cache_clear()

        port1 = get_authorization_store_port()
        port2 = get_authorization_store_port()

        assert port1 is port2


class TestGetAuthorizationModelPort:
    """Tests for get_authorization_model_port factory function."""

    def test_returns_authorization_model_port(self) -> None:
        """Test that function returns AuthorizationModelPort implementation."""
        port = get_authorization_model_port()

        assert port is not None
        assert isinstance(port, AuthorizationModelPort)

    def test_returns_openfga_adapter(self) -> None:
        """Test that returned port is actually an OpenFGAAdapter."""
        port = get_authorization_model_port()

        assert isinstance(port, OpenFGAAdapter)

    def test_port_implements_interface(self) -> None:
        """Test that returned port implements AuthorizationModelPort interface."""
        port = get_authorization_model_port()

        assert hasattr(port, "get_model_id")
        assert hasattr(port, "validate_model")
        assert hasattr(port, "health_check")

    def test_cache_returns_same_instance(self) -> None:
        """Test that lru_cache returns the same instance."""
        get_authorization_model_port.cache_clear()

        port1 = get_authorization_model_port()
        port2 = get_authorization_model_port()

        assert port1 is port2


class TestPortsReturnSameAdapter:
    """Tests that all port factories return the same underlying adapter instance."""

    def test_all_ports_return_same_instance(self) -> None:
        """Test that all port factory functions share the same underlying adapter.

        Because create_authorization_adapter is decorated with @lru_cache(maxsize=1),
        all three port getter functions call it and receive the same singleton
        OpenFGAAdapter, eliminating the 3-instance duplication (Hex violation #5).
        """
        port_auth = get_authorization_port()
        port_store = get_authorization_store_port()
        port_model = get_authorization_model_port()

        assert port_auth is port_store
        assert port_store is port_model
        assert isinstance(port_auth, OpenFGAAdapter)
        assert isinstance(port_store, OpenFGAAdapter)
        assert isinstance(port_model, OpenFGAAdapter)

    def test_repeated_calls_return_cached_instance(self) -> None:
        """Test that repeated calls to the same function return cached instance."""
        get_authorization_port.cache_clear()
        get_authorization_store_port.cache_clear()
        get_authorization_model_port.cache_clear()

        port1 = get_authorization_port()
        port2 = get_authorization_port()
        port3 = get_authorization_port()

        assert port1 is port2
        assert port2 is port3


class TestDIIntegration:
    """Integration tests for the authorization DI container."""

    def test_all_factories_work_together(self) -> None:
        """Test that all DI functions work correctly together."""
        get_authorization_port.cache_clear()
        get_authorization_store_port.cache_clear()
        get_authorization_model_port.cache_clear()

        adapter = create_authorization_adapter()
        port_auth = get_authorization_port()
        port_store = get_authorization_store_port()
        port_model = get_authorization_model_port()

        assert isinstance(adapter, OpenFGAAdapter)
        assert isinstance(port_auth, OpenFGAAdapter)
        assert isinstance(port_store, OpenFGAAdapter)
        assert isinstance(port_model, OpenFGAAdapter)

        assert isinstance(port_auth, AuthorizationPort)
        assert isinstance(port_store, AuthorizationStorePort)
        assert isinstance(port_model, AuthorizationModelPort)

    def test_adapter_creation_with_none_settings_fields(self) -> None:
        """Test that adapter creation succeeds even with None URL/store (init will fail later)."""
        with patch("siopv.infrastructure.di.authorization.get_settings") as mock_gs:
            incomplete = MagicMock()
            incomplete.openfga_api_url = None
            incomplete.openfga_store_id = None
            incomplete.circuit_breaker_failure_threshold = 5
            incomplete.circuit_breaker_recovery_timeout = 60
            mock_gs.return_value = incomplete

            adapter = create_authorization_adapter()
            assert isinstance(adapter, OpenFGAAdapter)
