"""Unit tests for DLP DI factory functions.

Tests factory functions for creating DLP components:
- create_presidio_adapter: Creates PresidioAdapter with Presidio engines
- get_dlp_port: Singleton factory via lru_cache
- create_dual_layer_dlp_adapter: Creates DualLayerDLPAdapter
- get_dual_layer_dlp_port: Singleton factory via lru_cache
"""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

from siopv.infrastructure.config.settings import Settings
from siopv.infrastructure.di.dlp import (
    create_dual_layer_dlp_adapter,
    create_presidio_adapter,
    get_dlp_port,
    get_dual_layer_dlp_port,
)

# === Fixtures ===


@pytest.fixture
def settings() -> Settings:
    """Settings with Anthropic API key configured."""
    return Settings(
        anthropic_api_key="test-api-key-for-dlp",
        claude_haiku_model="claude-haiku-4-5-20251001",
    )


@pytest.fixture
def settings_empty_key() -> Settings:
    """Settings with empty API key (graceful degradation)."""
    return Settings(
        anthropic_api_key="",
        claude_haiku_model="claude-haiku-4-5-20251001",
    )


@pytest.fixture(autouse=True)
def _clear_caches() -> Generator[None, None, None]:
    """Clear lru_cache singletons before and after each test."""
    get_dlp_port.cache_clear()
    get_dual_layer_dlp_port.cache_clear()
    yield
    get_dlp_port.cache_clear()
    get_dual_layer_dlp_port.cache_clear()


@pytest.fixture(autouse=True)
def patch_get_settings(settings: Settings) -> Generator[MagicMock, None, None]:
    """Patch get_settings in the DLP DI module for all tests."""
    with patch("siopv.infrastructure.di.dlp.get_settings", return_value=settings) as mock:
        yield mock


# === Test create_presidio_adapter ===


class TestCreatePresidioAdapter:
    """Tests for the create_presidio_adapter factory function."""

    @patch("siopv.infrastructure.di.dlp.PresidioAdapter")
    def test_returns_presidio_adapter(self, mock_cls: MagicMock) -> None:
        """Happy path: factory calls PresidioAdapter with correct args."""
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance

        result = create_presidio_adapter()

        assert result is mock_instance
        mock_cls.assert_called_once_with(
            api_key="test-api-key-for-dlp",
            haiku_model="claude-haiku-4-5-20251001",
            enable_semantic_validation=True,
        )

    def test_logging_on_creation(self) -> None:
        """Factory logs debug and info events with correct structured fields."""
        with (
            patch("siopv.infrastructure.di.dlp.PresidioAdapter"),
            patch("siopv.infrastructure.di.dlp.logger") as mock_logger,
        ):
            create_presidio_adapter()

            mock_logger.debug.assert_called_once_with(
                "creating_presidio_adapter",
                haiku_model="claude-haiku-4-5-20251001",
                semantic_validation=True,
            )
            mock_logger.info.assert_called_once_with(
                "presidio_adapter_created",
                adapter_class="PresidioAdapter",
            )

    @patch("siopv.infrastructure.di.dlp.PresidioAdapter")
    def test_semantic_validation_disabled_with_empty_key(
        self,
        mock_cls: MagicMock,
        settings_empty_key: Settings,
    ) -> None:
        """Semantic validation is disabled when API key is empty."""
        with (
            patch("siopv.infrastructure.di.dlp.get_settings", return_value=settings_empty_key),
            patch("siopv.infrastructure.di.dlp.logger") as mock_logger,
        ):
            create_presidio_adapter()

            mock_cls.assert_called_once_with(
                api_key="",
                haiku_model="claude-haiku-4-5-20251001",
                enable_semantic_validation=False,
            )
            mock_logger.debug.assert_called_once_with(
                "creating_presidio_adapter",
                haiku_model="claude-haiku-4-5-20251001",
                semantic_validation=False,
            )


# === Test get_dlp_port ===


class TestGetDlpPort:
    """Tests for the get_dlp_port singleton factory."""

    @patch("siopv.infrastructure.di.dlp.PresidioAdapter")
    def test_returns_adapter(self, mock_cls: MagicMock) -> None:
        """Returned object is the PresidioAdapter instance."""
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance

        port = get_dlp_port()

        assert port is mock_instance

    @patch("siopv.infrastructure.di.dlp.PresidioAdapter")
    def test_cached_singleton(self, mock_cls: MagicMock) -> None:
        """Calling twice returns the identical object."""
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance

        first = get_dlp_port()
        second = get_dlp_port()

        assert first is second
        mock_cls.assert_called_once()


# === Test create_dual_layer_dlp_adapter ===


class TestCreateDualLayerDlpAdapter:
    """Tests for the create_dual_layer_dlp_adapter factory function."""

    @patch("siopv.infrastructure.di.dlp.create_dual_layer_adapter")
    def test_returns_adapter(self, mock_factory: MagicMock) -> None:
        """Happy path: factory delegates to create_dual_layer_adapter."""
        mock_instance = MagicMock()
        mock_factory.return_value = mock_instance

        result = create_dual_layer_dlp_adapter()

        assert result is mock_instance
        mock_factory.assert_called_once_with(
            api_key="test-api-key-for-dlp",
            haiku_model="claude-haiku-4-5-20251001",
        )

    def test_logging_on_creation(self) -> None:
        """Factory logs debug and info events."""
        with (
            patch("siopv.infrastructure.di.dlp.create_dual_layer_adapter"),
            patch("siopv.infrastructure.di.dlp.logger") as mock_logger,
        ):
            create_dual_layer_dlp_adapter()

            mock_logger.debug.assert_called_once_with(
                "creating_dual_layer_dlp_adapter",
                haiku_model="claude-haiku-4-5-20251001",
            )
            mock_logger.info.assert_called_once_with(
                "dual_layer_dlp_adapter_created",
                adapter_class="DualLayerDLPAdapter",
            )


# === Test get_dual_layer_dlp_port ===


class TestGetDualLayerDlpPort:
    """Tests for the get_dual_layer_dlp_port singleton factory."""

    @patch("siopv.infrastructure.di.dlp.create_dual_layer_adapter")
    def test_returns_adapter(self, mock_factory: MagicMock) -> None:
        """Returned object is the DualLayerDLPAdapter instance."""
        mock_instance = MagicMock()
        mock_factory.return_value = mock_instance

        port = get_dual_layer_dlp_port()

        assert port is mock_instance

    @patch("siopv.infrastructure.di.dlp.create_dual_layer_adapter")
    def test_cached_singleton(self, mock_factory: MagicMock) -> None:
        """Calling twice returns the identical object."""
        mock_instance = MagicMock()
        mock_factory.return_value = mock_instance

        first = get_dual_layer_dlp_port()
        second = get_dual_layer_dlp_port()

        assert first is second
        mock_factory.assert_called_once()


# === Test exports ===


class TestDlpDiExports:
    """Tests for DLP DI module exports via __init__.py."""

    def test_importable_from_di_package(self) -> None:
        from siopv.infrastructure.di import get_dlp_port, get_dual_layer_dlp_port

        assert callable(get_dlp_port)
        assert callable(get_dual_layer_dlp_port)
