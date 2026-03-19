"""External API adapters for SIOPV."""

from siopv.adapters.external_apis.base_client import BaseAPIClient
from siopv.adapters.external_apis.epss_client import EPSSClient, EPSSClientError
from siopv.adapters.external_apis.github_advisory_client import (
    GitHubAdvisoryClient,
    GitHubAdvisoryClientError,
)
from siopv.adapters.external_apis.nvd_client import NVDClient, NVDClientError
from siopv.adapters.external_apis.tavily_client import TavilyClient, TavilyClientError
from siopv.adapters.external_apis.trivy_parser import TrivyParser, parse_trivy_report

__all__ = [
    # Base
    "BaseAPIClient",
    # Phase 2 - Enrichment clients
    "EPSSClient",
    "EPSSClientError",
    "GitHubAdvisoryClient",
    "GitHubAdvisoryClientError",
    "NVDClient",
    "NVDClientError",
    "TavilyClient",
    "TavilyClientError",
    # Phase 1 - Ingestion
    "TrivyParser",
    "parse_trivy_report",
]
