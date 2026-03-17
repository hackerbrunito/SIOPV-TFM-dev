"""Unit tests for enrichment DI factory functions.

Tests factory functions for creating enrichment adapters:
- build_nvd_client: Always returns NVDClient
- build_epss_client: Always returns EPSSClient (no auth required)
- build_github_client: Returns GitHubAdvisoryClient or None
- build_osint_client: Returns TavilyClient or None
- build_vector_store: Always returns ChromaDBAdapter
"""

from __future__ import annotations

import pytest

from siopv.adapters.external_apis.epss_client import EPSSClient
from siopv.adapters.external_apis.github_advisory_client import GitHubAdvisoryClient
from siopv.adapters.external_apis.nvd_client import NVDClient
from siopv.adapters.external_apis.tavily_client import TavilyClient
from siopv.adapters.vectorstore.chroma_adapter import ChromaDBAdapter
from siopv.application.ports.enrichment_clients import (
    EPSSClientPort,
    GitHubAdvisoryClientPort,
    NVDClientPort,
    OSINTSearchClientPort,
)
from siopv.application.ports.vector_store import VectorStorePort
from siopv.infrastructure.config.settings import Settings
from siopv.infrastructure.di.enrichment import (
    build_epss_client,
    build_github_client,
    build_nvd_client,
    build_osint_client,
    build_vector_store,
)

# === Fixtures ===


@pytest.fixture
def settings_full() -> Settings:
    """Settings with all enrichment API keys configured."""
    return Settings(
        nvd_api_key="test-nvd-key",
        github_token="test-github-token",
        tavily_api_key="test-tavily-key",
    )


@pytest.fixture
def settings_minimal() -> Settings:
    """Settings with no optional API keys configured."""
    return Settings(
        nvd_api_key=None,
        github_token=None,
        tavily_api_key=None,
    )


# === Test build_nvd_client ===


class TestBuildNvdClient:
    """Tests for build_nvd_client factory."""

    def test_returns_nvd_client_port(self, settings_full: Settings) -> None:
        client = build_nvd_client(settings_full)
        assert isinstance(client, NVDClientPort)
        assert isinstance(client, NVDClient)

    def test_returns_client_without_api_key(self, settings_minimal: Settings) -> None:
        client = build_nvd_client(settings_minimal)
        assert isinstance(client, NVDClient)


# === Test build_epss_client ===


class TestBuildEpssClient:
    """Tests for build_epss_client factory."""

    def test_returns_epss_client_port(self, settings_full: Settings) -> None:
        client = build_epss_client(settings_full)
        assert isinstance(client, EPSSClientPort)
        assert isinstance(client, EPSSClient)

    def test_always_returns_client(self, settings_minimal: Settings) -> None:
        client = build_epss_client(settings_minimal)
        assert isinstance(client, EPSSClient)


# === Test build_github_client ===


class TestBuildGithubClient:
    """Tests for build_github_client factory."""

    def test_returns_github_client_port(self, settings_full: Settings) -> None:
        client = build_github_client(settings_full)
        assert isinstance(client, GitHubAdvisoryClientPort)
        assert isinstance(client, GitHubAdvisoryClient)

    def test_returns_none_without_token(self, settings_minimal: Settings) -> None:
        client = build_github_client(settings_minimal)
        assert client is None


# === Test build_osint_client ===


class TestBuildOsintClient:
    """Tests for build_osint_client factory."""

    def test_returns_osint_client_port(self, settings_full: Settings) -> None:
        client = build_osint_client(settings_full)
        assert isinstance(client, OSINTSearchClientPort)
        assert isinstance(client, TavilyClient)

    def test_returns_none_without_api_key(self, settings_minimal: Settings) -> None:
        client = build_osint_client(settings_minimal)
        assert client is None


# === Test build_vector_store ===


class TestBuildVectorStore:
    """Tests for build_vector_store factory."""

    def test_returns_vector_store_port(self, settings_full: Settings) -> None:
        client = build_vector_store(settings_full)
        assert isinstance(client, VectorStorePort)
        assert isinstance(client, ChromaDBAdapter)

    def test_returns_store_with_minimal_settings(self, settings_minimal: Settings) -> None:
        client = build_vector_store(settings_minimal)
        assert isinstance(client, ChromaDBAdapter)


# === Test exports ===


class TestEnrichmentDiExports:
    """Tests for enrichment DI module exports via __init__.py."""

    def test_importable_from_di_package(self) -> None:
        from siopv.infrastructure.di import (
            build_epss_client,
            build_github_client,
            build_nvd_client,
            build_osint_client,
            build_vector_store,
        )

        assert callable(build_nvd_client)
        assert callable(build_epss_client)
        assert callable(build_github_client)
        assert callable(build_osint_client)
        assert callable(build_vector_store)
