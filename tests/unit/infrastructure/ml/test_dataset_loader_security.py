"""Security unit tests for CISAKEVLoader.

Tests for:
- M-02: Schema validation (Pydantic models, CVE ID format, Content-Type, size limits)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import pytest
from pydantic import ValidationError

from siopv.domain.exceptions import SchemaValidationError
from siopv.infrastructure.ml.dataset_loader import (
    CVE_ID_REGEX,
    EXPECTED_CONTENT_TYPES,
    MAX_RESPONSE_SIZE,
    CISAKEVLoader,
    KEVCatalog,
    KEVVulnerability,
)

# === Fixtures ===


@pytest.fixture
def valid_vulnerability_data() -> dict:
    """Create valid vulnerability data matching KEVVulnerability schema."""
    return {
        "cveID": "CVE-2021-44228",
        "vendorProject": "Apache",
        "product": "Log4j",
        "vulnerabilityName": "Log4Shell RCE",
        "dateAdded": "2021-12-10",
        "shortDescription": "Apache Log4j2 Remote Code Execution",
        "requiredAction": "Apply updates per vendor instructions",
        "dueDate": "2021-12-24",
        "knownRansomwareCampaignUse": "Known",
        "notes": "Widely exploited",
    }


@pytest.fixture
def valid_catalog_data(valid_vulnerability_data: dict) -> dict:
    """Create valid KEV catalog data matching KEVCatalog schema."""
    return {
        "title": "CISA Known Exploited Vulnerabilities Catalog",
        "catalogVersion": "2024.01.15",
        "dateReleased": "2024-01-15",
        "count": 1,
        "vulnerabilities": [valid_vulnerability_data],
    }


@pytest.fixture
def kev_loader() -> CISAKEVLoader:
    """Create a CISAKEVLoader instance."""
    return CISAKEVLoader()


# === M-02: Schema Validation Tests ===


class TestKEVVulnerabilitySchema:
    """Tests for KEVVulnerability Pydantic model validation."""

    def test_valid_vulnerability_parses_correctly(self, valid_vulnerability_data: dict) -> None:
        """Test that valid vulnerability data parses correctly."""
        vuln = KEVVulnerability.model_validate(valid_vulnerability_data)

        assert vuln.cve_id == "CVE-2021-44228"
        assert vuln.vendor_project == "Apache"
        assert vuln.product == "Log4j"
        assert vuln.vulnerability_name == "Log4Shell RCE"
        assert vuln.date_added == "2021-12-10"
        assert vuln.due_date == "2021-12-24"

    @pytest.mark.parametrize(
        "invalid_cve_id,description",
        [
            ("CVE-21-44228", "Two-digit year"),
            ("CVE-2021-123", "Three-digit sequence"),
            ("CVE2021-44228", "Missing first hyphen"),
            ("CVE-202144228", "Missing second hyphen"),
            ("cve-2021-44228", "Lowercase CVE"),
            ("CVE-2021-4422a", "Letter in sequence"),
            ("CVE-ABCD-44228", "Non-numeric year"),
            ("", "Empty string"),
            ("CVE-", "Incomplete ID"),
            ("VULN-2021-44228", "Wrong prefix"),
            ("CVE-2021-0001-extra", "Extra segment"),
        ],
        ids=[
            "two-digit-year",
            "three-digit-sequence",
            "missing-first-hyphen",
            "missing-second-hyphen",
            "lowercase",
            "letter-in-sequence",
            "non-numeric-year",
            "empty-string",
            "incomplete",
            "wrong-prefix",
            "extra-segment",
        ],
    )
    def test_invalid_cve_id_format_rejected(
        self, valid_vulnerability_data: dict, invalid_cve_id: str, description: str
    ) -> None:
        """Test that invalid CVE ID formats are rejected."""
        valid_vulnerability_data["cveID"] = invalid_cve_id

        with pytest.raises(ValidationError) as exc_info:
            KEVVulnerability.model_validate(valid_vulnerability_data)

        # Check error is about cve_id/cveID field (may use alias)
        errors = exc_info.value.errors()
        assert any("cve" in str(e.get("loc", ())).lower() for e in errors)

    @pytest.mark.parametrize(
        "valid_cve_id",
        [
            "CVE-2021-44228",
            "CVE-2024-0001",
            "CVE-1999-99999",
            "CVE-2025-123456",
            "CVE-2000-10000",
        ],
        ids=[
            "standard",
            "short-sequence",
            "old-year",
            "long-sequence",
            "year-2000",
        ],
    )
    def test_valid_cve_id_formats_accepted(
        self, valid_vulnerability_data: dict, valid_cve_id: str
    ) -> None:
        """Test that valid CVE ID formats are accepted."""
        valid_vulnerability_data["cveID"] = valid_cve_id

        vuln = KEVVulnerability.model_validate(valid_vulnerability_data)
        assert vuln.cve_id == valid_cve_id

    @pytest.mark.parametrize(
        "missing_field",
        [
            "cveID",
            "vendorProject",
            "product",
            "vulnerabilityName",
            "dateAdded",
            "shortDescription",
            "requiredAction",
            "dueDate",
        ],
    )
    def test_missing_required_fields_rejected(
        self, valid_vulnerability_data: dict, missing_field: str
    ) -> None:
        """Test that missing required fields are rejected."""
        del valid_vulnerability_data[missing_field]

        with pytest.raises(ValidationError) as exc_info:
            KEVVulnerability.model_validate(valid_vulnerability_data)

        errors = exc_info.value.errors()
        assert len(errors) > 0

    @pytest.mark.parametrize(
        "invalid_date,field",
        [
            ("2021/12/10", "dateAdded"),
            ("12-10-2021", "dateAdded"),
            ("2021-13-10", "dateAdded"),
            ("2021-12-32", "dateAdded"),
            ("not-a-date", "dateAdded"),
            # Note: Single-digit months/days are accepted by strptime
            # ("2021-1-10", "dueDate"),  # Python strptime accepts this
            # ("2021-12-1", "dueDate"),  # Python strptime accepts this
        ],
        ids=[
            "slash-separator",
            "wrong-order",
            "invalid-month",
            "invalid-day",
            "not-a-date",
        ],
    )
    def test_invalid_date_format_rejected(
        self, valid_vulnerability_data: dict, invalid_date: str, field: str
    ) -> None:
        """Test that invalid date formats are rejected."""
        valid_vulnerability_data[field] = invalid_date

        with pytest.raises(ValidationError):
            KEVVulnerability.model_validate(valid_vulnerability_data)

    def test_optional_fields_have_defaults(self) -> None:
        """Test that optional fields have correct defaults."""
        minimal_data = {
            "cveID": "CVE-2021-44228",
            "vendorProject": "Apache",
            "product": "Log4j",
            "vulnerabilityName": "Log4Shell",
            "dateAdded": "2021-12-10",
            "shortDescription": "RCE vulnerability",
            "requiredAction": "Apply updates",
            "dueDate": "2021-12-24",
        }

        vuln = KEVVulnerability.model_validate(minimal_data)

        assert vuln.known_ransomware_campaign_use == "Unknown"
        assert vuln.notes == ""

    def test_extra_fields_are_ignored(self, valid_vulnerability_data: dict) -> None:
        """Test that extra fields are ignored (ConfigDict extra='ignore')."""
        valid_vulnerability_data["unknownField"] = "should be ignored"
        valid_vulnerability_data["anotherExtra"] = 12345

        vuln = KEVVulnerability.model_validate(valid_vulnerability_data)

        assert not hasattr(vuln, "unknownField")
        assert not hasattr(vuln, "anotherExtra")

    def test_whitespace_is_stripped(self, valid_vulnerability_data: dict) -> None:
        """Test that string whitespace is stripped."""
        valid_vulnerability_data["vendorProject"] = "  Apache  "
        valid_vulnerability_data["product"] = "\tLog4j\n"

        vuln = KEVVulnerability.model_validate(valid_vulnerability_data)

        assert vuln.vendor_project == "Apache"
        assert vuln.product == "Log4j"


class TestKEVCatalogSchema:
    """Tests for KEVCatalog Pydantic model validation."""

    def test_valid_catalog_parses_correctly(self, valid_catalog_data: dict) -> None:
        """Test that valid catalog data parses correctly."""
        catalog = KEVCatalog.model_validate(valid_catalog_data)

        assert catalog.title == "CISA Known Exploited Vulnerabilities Catalog"
        assert catalog.catalog_version == "2024.01.15"
        assert catalog.count == 1
        assert len(catalog.vulnerabilities) == 1

    def test_invalid_vulnerability_in_catalog_rejected(self, valid_catalog_data: dict) -> None:
        """Test that invalid vulnerability data is rejected in catalog."""
        valid_catalog_data["vulnerabilities"][0]["cveID"] = "INVALID"

        with pytest.raises(ValidationError):
            KEVCatalog.model_validate(valid_catalog_data)

    def test_negative_count_rejected(self, valid_catalog_data: dict) -> None:
        """Test that negative count is rejected."""
        valid_catalog_data["count"] = -1

        with pytest.raises(ValidationError) as exc_info:
            KEVCatalog.model_validate(valid_catalog_data)

        errors = exc_info.value.errors()
        assert any("count" in str(e.get("loc", ())) for e in errors)

    def test_empty_vulnerabilities_list_accepted(self, valid_catalog_data: dict) -> None:
        """Test that empty vulnerabilities list is accepted."""
        valid_catalog_data["vulnerabilities"] = []
        valid_catalog_data["count"] = 0

        catalog = KEVCatalog.model_validate(valid_catalog_data)
        assert len(catalog.vulnerabilities) == 0

    @pytest.mark.parametrize(
        "missing_field",
        ["title", "catalogVersion", "dateReleased", "count", "vulnerabilities"],
    )
    def test_missing_required_fields_rejected(
        self, valid_catalog_data: dict, missing_field: str
    ) -> None:
        """Test that missing required catalog fields are rejected."""
        del valid_catalog_data[missing_field]

        with pytest.raises(ValidationError):
            KEVCatalog.model_validate(valid_catalog_data)


class TestCVEIDRegex:
    """Tests for the CVE ID format regex."""

    @pytest.mark.parametrize(
        "valid_id",
        [
            "CVE-2021-44228",
            "CVE-2024-0001",
            "CVE-1999-9999",
            "CVE-2025-123456",
            "CVE-2000-1234567890",
        ],
    )
    def test_regex_matches_valid_ids(self, valid_id: str) -> None:
        """Test regex matches valid CVE IDs."""
        assert CVE_ID_REGEX.match(valid_id) is not None

    @pytest.mark.parametrize(
        "invalid_id",
        [
            "CVE-21-44228",
            "CVE-2021-123",
            "cve-2021-44228",
            "CVE2021-44228",
            "CVE-202144228",
            "",
            "VULN-2021-44228",
        ],
    )
    def test_regex_rejects_invalid_ids(self, invalid_id: str) -> None:
        """Test regex rejects invalid CVE IDs."""
        assert CVE_ID_REGEX.match(invalid_id) is None


class TestContentTypeValidation:
    """Tests for Content-Type header validation (M-02)."""

    @pytest.mark.asyncio
    async def test_valid_content_type_accepted(
        self, kev_loader: CISAKEVLoader, valid_catalog_data: dict
    ) -> None:
        """Test that valid Content-Type is accepted."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.json.return_value = valid_catalog_data
            mock_response.raise_for_status = Mock()
            mock_response.headers = {"content-type": "application/json"}
            mock_response.content = b'{"test": "data"}'
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            cve_ids = await kev_loader.load_kev_catalog()
            assert len(cve_ids) == 1

    @pytest.mark.asyncio
    async def test_content_type_with_charset_accepted(
        self, kev_loader: CISAKEVLoader, valid_catalog_data: dict
    ) -> None:
        """Test that Content-Type with charset is accepted."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.json.return_value = valid_catalog_data
            mock_response.raise_for_status = Mock()
            mock_response.headers = {"content-type": "application/json; charset=utf-8"}
            mock_response.content = b'{"test": "data"}'
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            cve_ids = await kev_loader.load_kev_catalog()
            assert len(cve_ids) == 1

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "invalid_content_type",
        [
            "text/html",
            "text/plain",
            "application/xml",
            "application/octet-stream",
            "image/png",
            "",
        ],
        ids=[
            "html",
            "plain-text",
            "xml",
            "octet-stream",
            "image",
            "empty",
        ],
    )
    async def test_invalid_content_type_rejected(
        self, kev_loader: CISAKEVLoader, invalid_content_type: str
    ) -> None:
        """Test that invalid Content-Type is rejected."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_response.headers = {"content-type": invalid_content_type}
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(SchemaValidationError, match="Content-Type"):
                await kev_loader.load_kev_catalog()


class TestResponseSizeLimit:
    """Tests for response size limit enforcement (M-02)."""

    def test_default_max_response_size(self) -> None:
        """Test default max response size is 10MB."""
        assert MAX_RESPONSE_SIZE == 10 * 1024 * 1024

    def test_custom_max_response_size(self) -> None:
        """Test custom max response size is stored."""
        custom_size = 5 * 1024 * 1024
        loader = CISAKEVLoader(max_response_size=custom_size)
        assert loader._max_response_size == custom_size

    @pytest.mark.asyncio
    async def test_content_length_exceeds_limit_rejected(self) -> None:
        """Test that Content-Length exceeding limit is rejected."""
        small_limit = 1000  # 1KB
        loader = CISAKEVLoader(max_response_size=small_limit)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_response.headers = {
                "content-type": "application/json",
                "content-length": "2000",  # Exceeds 1KB limit
            }
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(SchemaValidationError, match="exceeds maximum"):
                await loader.load_kev_catalog()

    @pytest.mark.asyncio
    async def test_actual_content_exceeds_limit_rejected(self) -> None:
        """Test that actual content exceeding limit is rejected."""
        small_limit = 100  # 100 bytes
        loader = CISAKEVLoader(max_response_size=small_limit)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_response.headers = {"content-type": "application/json"}
            # Content larger than limit
            mock_response.content = b"x" * 200
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(SchemaValidationError, match="exceeds maximum"):
                await loader.load_kev_catalog()

    @pytest.mark.asyncio
    async def test_response_within_limit_accepted(self, valid_catalog_data: dict) -> None:
        """Test that response within limit is accepted."""
        loader = CISAKEVLoader(max_response_size=10 * 1024 * 1024)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.json.return_value = valid_catalog_data
            mock_response.raise_for_status = Mock()
            mock_response.headers = {
                "content-type": "application/json",
                "content-length": "500",
            }
            mock_response.content = b'{"small": "data"}'
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            cve_ids = await loader.load_kev_catalog()
            assert len(cve_ids) == 1


class TestMalformedJSONHandling:
    """Tests for malformed JSON response handling (M-02)."""

    @pytest.mark.asyncio
    async def test_malformed_json_raises_schema_error(self, kev_loader: CISAKEVLoader) -> None:
        """Test that malformed JSON raises SchemaValidationError."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_response.headers = {"content-type": "application/json"}
            mock_response.content = b'{"invalid json'
            mock_response.json.side_effect = ValueError("Invalid JSON")
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(SchemaValidationError, match="Failed to parse JSON"):
                await kev_loader.load_kev_catalog()

    @pytest.mark.asyncio
    async def test_schema_mismatch_raises_error(self, kev_loader: CISAKEVLoader) -> None:
        """Test that schema mismatch raises SchemaValidationError."""
        invalid_structure = {
            "wrongField": "value",
            "noVulnerabilities": True,
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.json.return_value = invalid_structure
            mock_response.raise_for_status = Mock()
            mock_response.headers = {"content-type": "application/json"}
            mock_response.content = b'{"wrongField": "value"}'
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(SchemaValidationError, match="schema validation failed"):
                await kev_loader.load_kev_catalog()


class TestHTTPClientSecurity:
    """Tests for secure HTTP client configuration (M-02)."""

    @pytest.mark.asyncio
    async def test_ssl_verification_enabled(self, valid_catalog_data: dict) -> None:
        """Test that SSL verification is enabled (verify=True)."""
        loader = CISAKEVLoader()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.json.return_value = valid_catalog_data
            mock_response.raise_for_status = Mock()
            mock_response.headers = {"content-type": "application/json"}
            mock_response.content = b'{"test": "data"}'
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await loader.load_kev_catalog()

            # Verify AsyncClient was called with verify=True
            call_kwargs = mock_client_class.call_args[1]
            assert call_kwargs.get("verify") is True

    @pytest.mark.asyncio
    async def test_redirects_disabled(self, valid_catalog_data: dict) -> None:
        """Test that redirects are disabled (follow_redirects=False)."""
        loader = CISAKEVLoader()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.json.return_value = valid_catalog_data
            mock_response.raise_for_status = Mock()
            mock_response.headers = {"content-type": "application/json"}
            mock_response.content = b'{"test": "data"}'
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await loader.load_kev_catalog()

            # Verify AsyncClient was called with follow_redirects=False
            call_kwargs = mock_client_class.call_args[1]
            assert call_kwargs.get("follow_redirects") is False

    @pytest.mark.asyncio
    async def test_timeout_is_configured(self, valid_catalog_data: dict) -> None:
        """Test that timeout is configured."""
        custom_timeout = 60.0
        loader = CISAKEVLoader(timeout=custom_timeout)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.json.return_value = valid_catalog_data
            mock_response.raise_for_status = Mock()
            mock_response.headers = {"content-type": "application/json"}
            mock_response.content = b'{"test": "data"}'
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await loader.load_kev_catalog()

            # Verify AsyncClient was called with timeout
            call_kwargs = mock_client_class.call_args[1]
            assert call_kwargs.get("timeout") == custom_timeout


class TestExpectedContentTypes:
    """Tests for EXPECTED_CONTENT_TYPES constant."""

    def test_expected_content_types_includes_json(self) -> None:
        """Test that expected content types include application/json."""
        assert "application/json" in EXPECTED_CONTENT_TYPES

    def test_expected_content_types_includes_json_utf8(self) -> None:
        """Test that expected content types include json with charset."""
        assert "application/json; charset=utf-8" in EXPECTED_CONTENT_TYPES


class TestSchemaValidationIntegration:
    """Integration tests for complete schema validation flow."""

    @pytest.mark.asyncio
    async def test_full_validation_pipeline(self, valid_catalog_data: dict) -> None:
        """Test complete validation pipeline from HTTP response to parsed data."""
        loader = CISAKEVLoader()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.json.return_value = valid_catalog_data
            mock_response.raise_for_status = Mock()
            mock_response.headers = {
                "content-type": "application/json",
                "content-length": "500",
            }
            mock_response.content = b'{"small": "data"}'
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            cve_ids = await loader.load_kev_catalog()

            # Verify result
            assert len(cve_ids) == 1
            assert "CVE-2021-44228" in cve_ids

            # Verify cache was populated with validated data
            assert loader._cached_kev is not None
            assert len(loader._cached_kev) == 1
            assert loader._cached_kev[0].cve_id == "CVE-2021-44228"

    @pytest.mark.asyncio
    async def test_multiple_vulnerabilities_all_validated(self) -> None:
        """Test that all vulnerabilities in catalog are validated."""
        catalog_data = {
            "title": "CISA KEV",
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
                    "shortDescription": "RCE",
                    "requiredAction": "Update",
                    "dueDate": "2021-12-24",
                },
                {
                    "cveID": "CVE-2021-34473",
                    "vendorProject": "Microsoft",
                    "product": "Exchange",
                    "vulnerabilityName": "ProxyShell",
                    "dateAdded": "2021-08-18",
                    "shortDescription": "RCE",
                    "requiredAction": "Update",
                    "dueDate": "2021-09-01",
                },
                {
                    "cveID": "CVE-2020-1472",
                    "vendorProject": "Microsoft",
                    "product": "Windows",
                    "vulnerabilityName": "Zerologon",
                    "dateAdded": "2020-09-18",
                    "shortDescription": "EoP",
                    "requiredAction": "Update",
                    "dueDate": "2020-10-02",
                },
            ],
        }

        loader = CISAKEVLoader()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.json.return_value = catalog_data
            mock_response.raise_for_status = Mock()
            mock_response.headers = {"content-type": "application/json"}
            mock_response.content = b'{"test": "data"}'
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            cve_ids = await loader.load_kev_catalog()

            assert len(cve_ids) == 3
            assert "CVE-2021-44228" in cve_ids
            assert "CVE-2021-34473" in cve_ids
            assert "CVE-2020-1472" in cve_ids

    @pytest.mark.asyncio
    async def test_one_invalid_vulnerability_fails_entire_catalog(self) -> None:
        """Test that one invalid vulnerability fails the entire catalog validation."""
        catalog_data = {
            "title": "CISA KEV",
            "catalogVersion": "2024.01.15",
            "dateReleased": "2024-01-15",
            "count": 2,
            "vulnerabilities": [
                {
                    "cveID": "CVE-2021-44228",
                    "vendorProject": "Apache",
                    "product": "Log4j",
                    "vulnerabilityName": "Log4Shell",
                    "dateAdded": "2021-12-10",
                    "shortDescription": "RCE",
                    "requiredAction": "Update",
                    "dueDate": "2021-12-24",
                },
                {
                    "cveID": "INVALID-CVE-ID",  # Invalid format
                    "vendorProject": "Test",
                    "product": "Test",
                    "vulnerabilityName": "Test",
                    "dateAdded": "2021-01-01",
                    "shortDescription": "Test",
                    "requiredAction": "Test",
                    "dueDate": "2021-01-15",
                },
            ],
        }

        loader = CISAKEVLoader()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.json.return_value = catalog_data
            mock_response.raise_for_status = Mock()
            mock_response.headers = {"content-type": "application/json"}
            mock_response.content = b'{"test": "data"}'
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(SchemaValidationError, match="schema validation failed"):
                await loader.load_kev_catalog()
