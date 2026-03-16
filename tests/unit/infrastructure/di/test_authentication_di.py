"""Unit tests for authentication DI factory functions.

Tests factory functions for creating authentication components:
- create_oidc_adapter: Creates KeycloakOIDCAdapter with logging
- get_oidc_authentication_port: Singleton factory via lru_cache
- create_oidc_middleware: Creates OIDCAuthenticationMiddleware with wired deps
"""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

from siopv.adapters.authentication.keycloak_oidc_adapter import KeycloakOIDCAdapter
from siopv.infrastructure.config.settings import Settings
from siopv.infrastructure.di.authentication import (
    create_oidc_adapter,
    create_oidc_middleware,
    get_oidc_authentication_port,
)
from siopv.infrastructure.middleware.oidc_middleware import OIDCAuthenticationMiddleware

# === Fixtures ===


@pytest.fixture
def settings() -> Settings:
    """Settings with OIDC configuration."""
    return Settings(
        oidc_enabled=True,
        oidc_issuer_url="http://localhost:8888/realms/siopv",
        oidc_audience="siopv-api",
        oidc_jwks_cache_ttl_seconds=3600,
        oidc_allowed_clock_skew_seconds=30,
        openfga_api_url="http://localhost:8080",
        openfga_store_id="test-store",
        openfga_authorization_model_id="test-model",
    )


@pytest.fixture(autouse=True)
def _clear_cache() -> Generator[None, None, None]:
    """Clear lru_cache before and after each test."""
    get_oidc_authentication_port.cache_clear()
    yield
    get_oidc_authentication_port.cache_clear()


@pytest.fixture(autouse=True)
def patch_get_settings(settings: Settings) -> Generator[MagicMock, None, None]:
    """Patch get_settings in the authentication DI module for all tests."""
    with patch(
        "siopv.infrastructure.di.authentication.get_settings", return_value=settings
    ) as mock:
        yield mock


# === Test create_oidc_adapter ===


class TestCreateOIDCAdapter:
    """Tests for the create_oidc_adapter factory function."""

    def test_create_oidc_adapter_success(self) -> None:
        """Happy path: factory returns a properly initialized KeycloakOIDCAdapter."""
        result = create_oidc_adapter()

        assert isinstance(result, KeycloakOIDCAdapter)

    def test_create_oidc_adapter_logging(self) -> None:
        """Factory logs debug and info events with correct structured fields."""
        with patch("siopv.infrastructure.di.authentication.logger") as mock_logger:
            result = create_oidc_adapter()

            mock_logger.debug.assert_called_once_with(
                "creating_oidc_adapter",
                issuer_url="http://localhost:8888/realms/siopv",
                audience="siopv-api",
                enabled=True,
                jwks_cache_ttl=3600,
            )
            mock_logger.info.assert_called_once_with(
                "oidc_adapter_created",
                adapter_class="KeycloakOIDCAdapter",
            )

        assert isinstance(result, KeycloakOIDCAdapter)

    def test_get_settings_called_internally(self, patch_get_settings: MagicMock) -> None:
        """Test that get_settings() is called internally (no settings parameter)."""
        create_oidc_adapter()

        patch_get_settings.assert_called()


# === Test get_oidc_authentication_port ===


class TestGetOIDCAuthenticationPort:
    """Tests for the get_oidc_authentication_port singleton factory."""

    def test_get_oidc_authentication_port_cached(self) -> None:
        """Calling twice returns the identical object."""
        first = get_oidc_authentication_port()
        second = get_oidc_authentication_port()

        assert first is second

    def test_get_oidc_authentication_port_returns_adapter(self) -> None:
        """Returned object is a KeycloakOIDCAdapter (which implements OIDCAuthenticationPort)."""
        port = get_oidc_authentication_port()

        assert isinstance(port, KeycloakOIDCAdapter)


# === Test create_oidc_middleware ===


class TestCreateOIDCMiddleware:
    """Tests for the create_oidc_middleware factory function."""

    def test_create_oidc_middleware_success(self) -> None:
        """Happy path: factory returns a properly wired OIDCAuthenticationMiddleware."""
        result = create_oidc_middleware()

        assert isinstance(result, OIDCAuthenticationMiddleware)

    def test_create_oidc_middleware_logging(self, settings: Settings) -> None:
        """Factory logs debug and info events during middleware creation."""
        with patch("siopv.infrastructure.di.authentication.logger") as mock_logger:
            result = create_oidc_middleware()

            mock_logger.debug.assert_any_call(
                "creating_oidc_middleware",
                enabled=settings.oidc_enabled,
            )
            mock_logger.info.assert_any_call(
                "oidc_middleware_created",
                middleware_class="OIDCAuthenticationMiddleware",
            )

        assert isinstance(result, OIDCAuthenticationMiddleware)
