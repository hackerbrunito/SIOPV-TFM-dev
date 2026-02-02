"""Unit tests for CISAKEVLoader.

Tests CISA KEV catalog loading and negative class sampling.

FIXED: Proper async mock configuration for httpx.AsyncClient with respx patterns.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from siopv.domain.exceptions import SchemaValidationError
from siopv.infrastructure.ml.dataset_loader import (
    CISA_KEV_URL,
    CISAKEVLoader,
    KEVCatalog,
    KEVVulnerability,
)

# === Fixtures ===


@pytest.fixture
def sample_kev_response() -> dict:
    """Create a sample CISA KEV catalog response."""
    return {
        "title": "CISA Known Exploited Vulnerabilities Catalog",
        "catalogVersion": "2024.01.15",
        "dateReleased": "2024-01-15",
        "count": 3,
        "vulnerabilities": [
            {
                "cveID": "CVE-2021-44228",
                "vendorProject": "Apache",
                "product": "Log4j",
                "vulnerabilityName": "Log4Shell",
                "dateAdded": "2021-12-10",
                "shortDescription": "Apache Log4j2 RCE",
                "requiredAction": "Apply updates",
                "dueDate": "2021-12-24",
            },
            {
                "cveID": "CVE-2021-34473",
                "vendorProject": "Microsoft",
                "product": "Exchange Server",
                "vulnerabilityName": "ProxyShell",
                "dateAdded": "2021-08-18",
                "shortDescription": "Microsoft Exchange RCE",
                "requiredAction": "Apply updates",
                "dueDate": "2021-09-01",
            },
            {
                "cveID": "CVE-2020-1472",
                "vendorProject": "Microsoft",
                "product": "Windows Server",
                "vulnerabilityName": "Zerologon",
                "dateAdded": "2020-09-18",
                "shortDescription": "Netlogon elevation of privilege",
                "requiredAction": "Apply updates",
                "dueDate": "2020-10-02",
            },
        ],
    }


@pytest.fixture
def kev_loader() -> CISAKEVLoader:
    """Create a CISAKEVLoader instance."""
    return CISAKEVLoader()


@pytest.fixture
def mock_httpx_response(sample_kev_response: dict) -> Mock:
    """Create a properly configured mock httpx Response.

    FIXED: Includes all required attributes for the loader.
    """
    mock = Mock()
    mock.status_code = 200
    mock.headers = {"content-type": "application/json"}
    mock.json.return_value = sample_kev_response
    mock.content = json.dumps(sample_kev_response).encode()
    mock.raise_for_status = Mock()
    return mock


# === Pydantic Model Tests ===


class TestKEVVulnerability:
    """Tests for KEVVulnerability Pydantic model."""

    def test_valid_vulnerability(self):
        """Test creating a valid vulnerability."""
        vuln = KEVVulnerability(
            cveID="CVE-2021-44228",
            vendorProject="Apache",
            product="Log4j",
            vulnerabilityName="Log4Shell",
            dateAdded="2021-12-10",
            shortDescription="RCE vulnerability",
            requiredAction="Apply updates",
            dueDate="2021-12-24",
        )

        assert vuln.cve_id == "CVE-2021-44228"
        assert vuln.vendor_project == "Apache"

    def test_invalid_cve_id_format(self):
        """Test that invalid CVE ID format is rejected."""
        with pytest.raises(ValueError, match="Invalid CVE ID format"):
            KEVVulnerability(
                cveID="INVALID-ID",
                vendorProject="Apache",
                product="Log4j",
                vulnerabilityName="Test",
                dateAdded="2021-12-10",
                shortDescription="Test",
                requiredAction="Test",
                dueDate="2021-12-24",
            )

    def test_invalid_date_format(self):
        """Test that invalid date format is rejected."""
        with pytest.raises(ValueError, match="Invalid date format"):
            KEVVulnerability(
                cveID="CVE-2021-44228",
                vendorProject="Apache",
                product="Log4j",
                vulnerabilityName="Test",
                dateAdded="12-10-2021",  # Wrong format
                shortDescription="Test",
                requiredAction="Test",
                dueDate="2021-12-24",
            )


class TestKEVCatalog:
    """Tests for KEVCatalog Pydantic model."""

    def test_valid_catalog(self, sample_kev_response: dict):
        """Test creating a valid catalog."""
        catalog = KEVCatalog.model_validate(sample_kev_response)

        assert catalog.title == "CISA Known Exploited Vulnerabilities Catalog"
        assert catalog.count == 3
        assert len(catalog.vulnerabilities) == 3

    def test_negative_count_rejected(self, sample_kev_response: dict):
        """Test that negative count is rejected."""
        sample_kev_response["count"] = -1

        with pytest.raises(ValueError, match="cannot be negative"):
            KEVCatalog.model_validate(sample_kev_response)


# === Initialization Tests ===


class TestCISAKEVLoaderInit:
    """Tests for CISAKEVLoader initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        loader = CISAKEVLoader()

        assert loader._kev_url == CISA_KEV_URL
        assert loader._timeout == 30.0
        assert loader._cached_kev is None
        assert loader._cache_timestamp is None

    def test_init_with_custom_url(self):
        """Test initialization with custom URL."""
        custom_url = "https://custom.example.com/kev.json"
        loader = CISAKEVLoader(kev_url=custom_url)

        assert loader._kev_url == custom_url

    def test_init_with_custom_timeout(self):
        """Test initialization with custom timeout."""
        loader = CISAKEVLoader(timeout=60.0)

        assert loader._timeout == 60.0

    def test_init_with_custom_max_response_size(self):
        """Test initialization with custom max response size."""
        loader = CISAKEVLoader(max_response_size=5 * 1024 * 1024)

        assert loader._max_response_size == 5 * 1024 * 1024


# === Load KEV Catalog Tests ===


class TestCISAKEVLoaderLoadCatalog:
    """Tests for loading KEV catalog."""

    @pytest.mark.asyncio
    async def test_load_kev_catalog_success(
        self, kev_loader: CISAKEVLoader, sample_kev_response: dict
    ):
        """Test successful KEV catalog loading."""
        # Create mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = sample_kev_response
        mock_response.content = json.dumps(sample_kev_response).encode()
        mock_response.raise_for_status = Mock()

        # Create mock client
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("siopv.infrastructure.ml.dataset_loader.httpx.AsyncClient") as mock_client_class:
            # Setup async context manager
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

            cve_ids = await kev_loader.load_kev_catalog()

            assert len(cve_ids) == 3
            assert "CVE-2021-44228" in cve_ids
            assert "CVE-2021-34473" in cve_ids
            assert "CVE-2020-1472" in cve_ids

    @pytest.mark.asyncio
    async def test_load_kev_catalog_caches_data(
        self, kev_loader: CISAKEVLoader, sample_kev_response: dict
    ):
        """Test that loading caches the catalog data."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = sample_kev_response
        mock_response.content = json.dumps(sample_kev_response).encode()
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("siopv.infrastructure.ml.dataset_loader.httpx.AsyncClient") as mock_client_class:
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

            await kev_loader.load_kev_catalog()

            assert kev_loader._cached_kev is not None
            assert len(kev_loader._cached_kev) == 3
            assert kev_loader._cache_timestamp is not None

    @pytest.mark.asyncio
    async def test_load_kev_catalog_http_error(self, kev_loader: CISAKEVLoader):
        """Test handling of HTTP errors."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.HTTPError("Network error"))

        with patch("siopv.infrastructure.ml.dataset_loader.httpx.AsyncClient") as mock_client_class:
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

            with pytest.raises(httpx.HTTPError):
                await kev_loader.load_kev_catalog()

    @pytest.mark.asyncio
    async def test_load_kev_catalog_timeout(self, kev_loader: CISAKEVLoader):
        """Test handling of timeout."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

        with patch("siopv.infrastructure.ml.dataset_loader.httpx.AsyncClient") as mock_client_class:
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

            with pytest.raises(httpx.TimeoutException):
                await kev_loader.load_kev_catalog()

    @pytest.mark.asyncio
    async def test_load_kev_catalog_wrong_content_type(self, kev_loader: CISAKEVLoader):
        """Test rejection of wrong Content-Type."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/html"}  # Wrong type
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("siopv.infrastructure.ml.dataset_loader.httpx.AsyncClient") as mock_client_class:
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

            with pytest.raises(SchemaValidationError, match="Content-Type"):
                await kev_loader.load_kev_catalog()

    @pytest.mark.asyncio
    async def test_load_kev_catalog_oversized_response(self):
        """Test rejection of oversized response."""
        loader = CISAKEVLoader(max_response_size=100)  # Very small limit

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json", "content-length": "1000"}
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("siopv.infrastructure.ml.dataset_loader.httpx.AsyncClient") as mock_client_class:
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

            with pytest.raises(SchemaValidationError, match="exceeds maximum"):
                await loader.load_kev_catalog()

    @pytest.mark.asyncio
    async def test_load_kev_catalog_invalid_json(self, kev_loader: CISAKEVLoader):
        """Test handling of invalid JSON."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.content = b"not valid json"
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("siopv.infrastructure.ml.dataset_loader.httpx.AsyncClient") as mock_client_class:
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

            with pytest.raises(SchemaValidationError, match="parse JSON"):
                await kev_loader.load_kev_catalog()

    @pytest.mark.asyncio
    async def test_load_kev_catalog_schema_validation_failure(self, kev_loader: CISAKEVLoader):
        """Test handling of schema validation failure."""
        invalid_response = {"invalid": "data"}  # Missing required fields

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = invalid_response
        mock_response.content = json.dumps(invalid_response).encode()
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("siopv.infrastructure.ml.dataset_loader.httpx.AsyncClient") as mock_client_class:
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

            with pytest.raises(SchemaValidationError, match="schema validation"):
                await kev_loader.load_kev_catalog()


# === Negative Class Sampling Tests ===


class TestCISAKEVLoaderNegativeSampling:
    """Tests for negative class sampling."""

    @pytest.mark.asyncio
    async def test_sample_negative_class_placeholder(self, kev_loader: CISAKEVLoader):
        """Test negative class sampling (placeholder implementation)."""
        exclude_cves = {"CVE-2021-44228", "CVE-2021-34473"}

        negative_samples = await kev_loader.sample_negative_class(
            exclude_cves=exclude_cves,
            sample_size=100,
        )

        # Placeholder returns empty list
        assert negative_samples == []

    @pytest.mark.asyncio
    async def test_sample_negative_class_with_params(self, kev_loader: CISAKEVLoader):
        """Test negative sampling with custom parameters."""
        exclude_cves: set[str] = set()

        negative_samples = await kev_loader.sample_negative_class(
            exclude_cves=exclude_cves,
            sample_size=500,
            max_epss=0.05,
            min_age_days=365,
        )

        # Still placeholder
        assert negative_samples == []


# === KEV Details Tests ===


class TestCISAKEVLoaderDetails:
    """Tests for getting KEV details."""

    @pytest.mark.asyncio
    async def test_get_kev_details_found(
        self, kev_loader: CISAKEVLoader, sample_kev_response: dict
    ):
        """Test getting details for a CVE in the catalog."""
        # Load catalog first
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = sample_kev_response
        mock_response.content = json.dumps(sample_kev_response).encode()
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("siopv.infrastructure.ml.dataset_loader.httpx.AsyncClient") as mock_client_class:
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

            await kev_loader.load_kev_catalog()

        details = kev_loader.get_kev_details("CVE-2021-44228")

        assert details is not None
        assert details["cveID"] == "CVE-2021-44228"
        assert details["vendorProject"] == "Apache"
        assert details["product"] == "Log4j"

    @pytest.mark.asyncio
    async def test_get_kev_details_not_found(
        self, kev_loader: CISAKEVLoader, sample_kev_response: dict
    ):
        """Test getting details for CVE not in catalog."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = sample_kev_response
        mock_response.content = json.dumps(sample_kev_response).encode()
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("siopv.infrastructure.ml.dataset_loader.httpx.AsyncClient") as mock_client_class:
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

            await kev_loader.load_kev_catalog()

        details = kev_loader.get_kev_details("CVE-9999-99999")

        assert details is None

    def test_get_kev_details_no_cache(self, kev_loader: CISAKEVLoader):
        """Test getting details when catalog not loaded."""
        details = kev_loader.get_kev_details("CVE-2021-44228")

        assert details is None


# === KEV Statistics Tests ===


class TestCISAKEVLoaderStats:
    """Tests for KEV catalog statistics."""

    def test_get_kev_stats_not_loaded(self, kev_loader: CISAKEVLoader):
        """Test getting stats when catalog not loaded."""
        stats = kev_loader.get_kev_stats()

        assert stats == {"status": "not_loaded"}

    @pytest.mark.asyncio
    async def test_get_kev_stats_loaded(self, kev_loader: CISAKEVLoader, sample_kev_response: dict):
        """Test getting stats after loading catalog."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = sample_kev_response
        mock_response.content = json.dumps(sample_kev_response).encode()
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("siopv.infrastructure.ml.dataset_loader.httpx.AsyncClient") as mock_client_class:
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

            await kev_loader.load_kev_catalog()

        stats = kev_loader.get_kev_stats()

        assert stats["total_vulnerabilities"] == 3
        assert stats["unique_vendors"] >= 2  # At least Apache and Microsoft
        assert stats["unique_products"] >= 3
        assert "by_year" in stats
        assert stats["cache_timestamp"] is not None
        assert stats["schema_validated"] is True

    @pytest.mark.asyncio
    async def test_get_kev_stats_counts_by_year(
        self, kev_loader: CISAKEVLoader, sample_kev_response: dict
    ):
        """Test that stats include year breakdown."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = sample_kev_response
        mock_response.content = json.dumps(sample_kev_response).encode()
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("siopv.infrastructure.ml.dataset_loader.httpx.AsyncClient") as mock_client_class:
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

            await kev_loader.load_kev_catalog()

        stats = kev_loader.get_kev_stats()

        # Should have breakdown by year
        assert "2021" in stats["by_year"]
        assert "2020" in stats["by_year"]
        assert stats["by_year"]["2021"] == 2  # Two CVEs from 2021
        assert stats["by_year"]["2020"] == 1  # One CVE from 2020


# === Integration Tests ===


class TestCISAKEVLoaderIntegration:
    """Integration tests for complete workflows."""

    @pytest.mark.asyncio
    async def test_full_load_and_query_workflow(
        self, kev_loader: CISAKEVLoader, sample_kev_response: dict
    ):
        """Test complete workflow: load, query, stats."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = sample_kev_response
        mock_response.content = json.dumps(sample_kev_response).encode()
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("siopv.infrastructure.ml.dataset_loader.httpx.AsyncClient") as mock_client_class:
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

            # Load catalog
            cve_ids = await kev_loader.load_kev_catalog()
            assert len(cve_ids) == 3

            # Query details
            log4shell = kev_loader.get_kev_details("CVE-2021-44228")
            assert log4shell is not None
            assert log4shell["vulnerabilityName"] == "Log4Shell"

            # Get stats
            stats = kev_loader.get_kev_stats()
            assert stats["total_vulnerabilities"] == 3

    @pytest.mark.asyncio
    async def test_multiple_loads_update_cache(self, kev_loader: CISAKEVLoader):
        """Test that multiple loads update the cache."""
        response1 = {
            "title": "KEV",
            "catalogVersion": "2024.01.15",
            "dateReleased": "2024-01-15",
            "count": 1,
            "vulnerabilities": [
                {
                    "cveID": "CVE-2021-0001",
                    "vendorProject": "Test",
                    "product": "Test",
                    "vulnerabilityName": "Test",
                    "dateAdded": "2021-01-01",
                    "shortDescription": "Test",
                    "requiredAction": "Test",
                    "dueDate": "2021-01-15",
                }
            ],
        }
        response2 = {
            "title": "KEV",
            "catalogVersion": "2024.01.16",
            "dateReleased": "2024-01-16",
            "count": 2,
            "vulnerabilities": [
                {
                    "cveID": "CVE-2021-0001",
                    "vendorProject": "Test",
                    "product": "Test",
                    "vulnerabilityName": "Test",
                    "dateAdded": "2021-01-01",
                    "shortDescription": "Test",
                    "requiredAction": "Test",
                    "dueDate": "2021-01-15",
                },
                {
                    "cveID": "CVE-2021-0002",
                    "vendorProject": "Test",
                    "product": "Test",
                    "vulnerabilityName": "Test2",
                    "dateAdded": "2021-01-02",
                    "shortDescription": "Test",
                    "requiredAction": "Test",
                    "dueDate": "2021-01-16",
                },
            ],
        }

        mock_response1 = Mock()
        mock_response1.status_code = 200
        mock_response1.headers = {"content-type": "application/json"}
        mock_response1.json.return_value = response1
        mock_response1.content = json.dumps(response1).encode()
        mock_response1.raise_for_status = Mock()

        mock_response2 = Mock()
        mock_response2.status_code = 200
        mock_response2.headers = {"content-type": "application/json"}
        mock_response2.json.return_value = response2
        mock_response2.content = json.dumps(response2).encode()
        mock_response2.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=[mock_response1, mock_response2])

        with patch("siopv.infrastructure.ml.dataset_loader.httpx.AsyncClient") as mock_client_class:
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

            # First load
            cve_ids1 = await kev_loader.load_kev_catalog()
            assert len(cve_ids1) == 1

            # Second load (mock returns different response)
            cve_ids2 = await kev_loader.load_kev_catalog()
            assert len(cve_ids2) == 2
