"""Dependency injection factory functions for enrichment components.

Factory functions for creating enrichment adapters (NVD, EPSS, GitHub,
Tavily/OSINT, ChromaDB vector store) that implement the corresponding ports.
Supports graceful degradation when optional API keys are not configured.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

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

if TYPE_CHECKING:
    from siopv.application.ports.llm_analysis import LLMAnalysisPort
    from siopv.infrastructure.config import Settings

logger = structlog.get_logger(__name__)


def build_nvd_client(settings: Settings) -> NVDClientPort:
    """Create a configured NVD API client from application settings.

    Args:
        settings: Application settings with NVD configuration

    Returns:
        NVDClientPort implementation backed by NVDClient
    """
    adapter = NVDClient(settings)
    logger.info(
        "nvd_client_created",
        base_url=settings.nvd_base_url,
        has_api_key=settings.nvd_api_key is not None,
    )
    return adapter


def build_epss_client(settings: Settings) -> EPSSClientPort:
    """Create a configured EPSS API client from application settings.

    EPSS requires no API key — always returns a client.

    Args:
        settings: Application settings with EPSS configuration

    Returns:
        EPSSClientPort implementation backed by EPSSClient
    """
    adapter = EPSSClient(settings)
    logger.info("epss_client_created", base_url=settings.epss_base_url)
    return adapter


def build_github_client(settings: Settings) -> GitHubAdvisoryClientPort | None:
    """Create a configured GitHub Advisory client from application settings.

    Args:
        settings: Application settings with GitHub configuration

    Returns:
        GitHubAdvisoryClientPort implementation, or None if github_token is not set
    """
    if settings.github_token is None:
        logger.warning("github_client_skipped", reason="github_token not configured")
        return None

    adapter = GitHubAdvisoryClient(settings)
    logger.info("github_client_created", graphql_url=settings.github_graphql_url)
    return adapter


def build_osint_client(settings: Settings) -> OSINTSearchClientPort | None:
    """Create a configured Tavily OSINT search client from application settings.

    Args:
        settings: Application settings with Tavily configuration

    Returns:
        OSINTSearchClientPort implementation, or None if tavily_api_key is not set
    """
    if settings.tavily_api_key is None:
        logger.warning("osint_client_skipped", reason="tavily_api_key not configured")
        return None

    adapter = TavilyClient(settings)
    logger.info("osint_client_created")
    return adapter


def build_vector_store(settings: Settings) -> VectorStorePort:
    """Create a configured ChromaDB vector store from application settings.

    Args:
        settings: Application settings with ChromaDB configuration

    Returns:
        VectorStorePort implementation backed by ChromaDBAdapter
    """
    adapter = ChromaDBAdapter(settings)
    logger.info(
        "vector_store_created",
        persist_dir=str(settings.chroma_persist_dir),
        collection_name=settings.chroma_collection_name,
    )
    return adapter


def build_llm_analysis(settings: Settings) -> LLMAnalysisPort | None:
    """Create a configured Anthropic LLM analysis adapter from application settings.

    Args:
        settings: Application settings with Anthropic configuration

    Returns:
        LLMAnalysisPort implementation, or None if anthropic_api_key is not set
    """
    from siopv.adapters.llm.anthropic_adapter import AnthropicAnalysisAdapter  # noqa: PLC0415
    from siopv.application.ports.llm_analysis import (  # noqa: PLC0415
        LLMAnalysisPort as _LLMPort,
    )

    api_key = settings.anthropic_api_key.get_secret_value()
    if not api_key:
        logger.warning("llm_analysis_skipped", reason="anthropic_api_key is empty")
        return None

    adapter: _LLMPort = AnthropicAnalysisAdapter(
        api_key=api_key,
        sonnet_model=settings.claude_sonnet_model,
        haiku_model=settings.claude_haiku_model,
    )
    logger.info(
        "llm_analysis_created",
        sonnet_model=settings.claude_sonnet_model,
        haiku_model=settings.claude_haiku_model,
    )
    return adapter


__all__ = [
    "build_epss_client",
    "build_github_client",
    "build_llm_analysis",
    "build_nvd_client",
    "build_osint_client",
    "build_vector_store",
]
