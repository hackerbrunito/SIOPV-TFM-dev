"""Dataset loader for ML training data.

Handles CISA KEV catalog download and negative class sampling.
Based on specification section 3.3 (Dataset de Entrenamiento).

Security features (M-02 fix):
- Pydantic schema validation for external JSON
- CVE ID format validation with regex
- Content-Type header verification
- Max response size limits
- Secure HTTP client configuration
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Annotated

import httpx
import structlog
from pydantic import BaseModel, ConfigDict, Field, field_validator

from siopv.application.ports.ml_classifier import DatasetLoaderPort
from siopv.domain.exceptions import SchemaValidationError

logger = structlog.get_logger(__name__)


# CISA KEV Catalog URL
CISA_KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"

# CVE ID format regex: CVE-YYYY-NNNNN (4-digit year, 4+ digit sequence)
CVE_ID_REGEX = re.compile(r"^CVE-\d{4}-\d{4,}$")

# Maximum response size: 10MB
MAX_RESPONSE_SIZE = 10 * 1024 * 1024

# Expected Content-Type for JSON responses
EXPECTED_CONTENT_TYPES = {"application/json", "application/json; charset=utf-8"}


class KEVVulnerability(BaseModel):
    """Pydantic model for a single KEV vulnerability entry.

    Validates the structure and format of vulnerability data from CISA KEV.
    """

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    cve_id: Annotated[str, Field(alias="cveID")]
    vendor_project: Annotated[str, Field(alias="vendorProject")]
    product: str
    vulnerability_name: Annotated[str, Field(alias="vulnerabilityName")]
    date_added: Annotated[str, Field(alias="dateAdded")]
    short_description: Annotated[str, Field(alias="shortDescription")]
    required_action: Annotated[str, Field(alias="requiredAction")]
    due_date: Annotated[str, Field(alias="dueDate")]
    known_ransomware_campaign_use: Annotated[str, Field(alias="knownRansomwareCampaignUse")] = (
        "Unknown"
    )
    notes: str = ""

    @field_validator("cve_id")
    @classmethod
    def validate_cve_id_format(cls, v: str) -> str:
        """Validate CVE ID matches expected format."""
        if not CVE_ID_REGEX.match(v):
            msg = f"Invalid CVE ID format: {v}. Expected format: CVE-YYYY-NNNNN"
            raise ValueError(msg)
        return v

    @field_validator("date_added", "due_date")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        """Validate date is in YYYY-MM-DD format."""
        try:
            datetime.strptime(v, "%Y-%m-%d").replace(tzinfo=UTC)
        except ValueError as e:
            msg = f"Invalid date format: {v}. Expected YYYY-MM-DD"
            raise ValueError(msg) from e
        return v


class KEVCatalog(BaseModel):
    """Pydantic model for the complete KEV catalog response.

    Validates the overall structure of the CISA KEV JSON response.
    """

    model_config = ConfigDict(extra="ignore")

    title: str
    catalog_version: Annotated[str, Field(alias="catalogVersion")]
    date_released: Annotated[str, Field(alias="dateReleased")]
    count: int
    vulnerabilities: list[KEVVulnerability]

    @field_validator("count")
    @classmethod
    def validate_count_positive(cls, v: int) -> int:
        """Ensure count is non-negative."""
        if v < 0:
            msg = "Vulnerability count cannot be negative"
            raise ValueError(msg)
        return v


class CISAKEVLoader(DatasetLoaderPort):
    """Loader for CISA Known Exploited Vulnerabilities catalog.

    The CISA KEV catalog provides ground truth for the "exploited" class.
    Contains ~1,200 CVEs (as of January 2026) confirmed as actively exploited.

    Security features:
    - Schema validation via Pydantic models
    - Content-Type verification
    - Response size limits
    - Secure HTTP client (verify=True, follow_redirects=False)
    """

    def __init__(
        self,
        *,
        kev_url: str = CISA_KEV_URL,
        timeout: float = 30.0,
        max_response_size: int = MAX_RESPONSE_SIZE,
    ) -> None:
        """Initialize KEV loader.

        Args:
            kev_url: URL to CISA KEV JSON feed
            timeout: HTTP request timeout in seconds
            max_response_size: Maximum allowed response size in bytes (default 10MB)
        """
        self._kev_url = kev_url
        self._timeout = timeout
        self._max_response_size = max_response_size
        self._cached_kev: list[KEVVulnerability] | None = None
        self._cache_timestamp: datetime | None = None

        logger.info(
            "cisa_kev_loader_initialized",
            url=kev_url,
            max_response_size_mb=max_response_size / (1024 * 1024),
        )

    async def load_kev_catalog(self) -> list[str]:
        """Load CISA Known Exploited Vulnerabilities catalog.

        Returns:
            List of CVE IDs confirmed as exploited

        Raises:
            httpx.HTTPError: On network errors
            SchemaValidationError: On invalid JSON structure or data
        """
        logger.info("loading_kev_catalog")

        # Use secure HTTP client configuration (M-02 fix)
        async with httpx.AsyncClient(
            timeout=self._timeout,
            verify=True,  # Enforce SSL certificate verification
            follow_redirects=False,  # Don't follow redirects (security)
        ) as client:
            response = await client.get(self._kev_url)
            response.raise_for_status()

            # Verify Content-Type header (M-02 fix)
            content_type = response.headers.get("content-type", "").lower().split(";")[0].strip()
            if content_type not in EXPECTED_CONTENT_TYPES:
                msg = f"Unexpected Content-Type: {content_type}. Expected application/json"
                raise SchemaValidationError(
                    msg,
                    details={
                        "received_content_type": content_type,
                        "expected": list(EXPECTED_CONTENT_TYPES),
                    },
                )

            # Check response size before parsing (M-02 fix)
            content_length = response.headers.get("content-length")
            if content_length and int(content_length) > self._max_response_size:
                msg = (
                    f"Response size ({content_length} bytes) exceeds maximum "
                    f"allowed ({self._max_response_size} bytes)"
                )
                raise SchemaValidationError(
                    msg,
                    details={
                        "content_length": int(content_length),
                        "max_size": self._max_response_size,
                    },
                )

            # Also check actual content size
            content = response.content
            if len(content) > self._max_response_size:
                msg = (
                    f"Response size ({len(content)} bytes) exceeds maximum "
                    f"allowed ({self._max_response_size} bytes)"
                )
                raise SchemaValidationError(
                    msg,
                    details={
                        "actual_size": len(content),
                        "max_size": self._max_response_size,
                    },
                )

            # Parse JSON
            try:
                raw_data = response.json()
            except Exception as e:
                msg = f"Failed to parse JSON response: {e}"
                raise SchemaValidationError(
                    msg,
                    details={"error": str(e)},
                ) from e

        # Validate against Pydantic schema (M-02 fix)
        try:
            catalog = KEVCatalog.model_validate(raw_data)
        except Exception as e:
            msg = f"KEV catalog schema validation failed: {e}"
            raise SchemaValidationError(
                msg,
                details={"validation_error": str(e)},
            ) from e

        # Extract CVE IDs from validated data
        cve_ids = [v.cve_id for v in catalog.vulnerabilities]

        # Cache the validated data
        self._cached_kev = catalog.vulnerabilities
        self._cache_timestamp = datetime.now(UTC)

        logger.info(
            "kev_catalog_loaded",
            n_vulnerabilities=len(cve_ids),
            catalog_version=catalog.catalog_version,
            schema_validated=True,
        )

        return cve_ids

    async def sample_negative_class(
        self,
        exclude_cves: set[str],
        *,
        sample_size: int = 3600,
        max_epss: float = 0.1,
        min_age_days: int = 730,
    ) -> list[str]:
        """Sample CVEs for negative class.

        The negative class consists of CVEs that:
        - Are NOT in the KEV catalog
        - Have EPSS score < 0.1 (low exploitation probability)
        - Are older than 2 years without reported exploitation

        Note: This is a placeholder implementation. In production,
        this would query NVD API with filters.

        Args:
            exclude_cves: CVE IDs to exclude (from KEV)
            sample_size: Number of negative samples (default 3600 for 1:3 ratio)
            max_epss: Maximum EPSS score for negative samples
            min_age_days: Minimum age in days without exploitation

        Returns:
            List of CVE IDs for negative class
        """
        logger.info(
            "sampling_negative_class",
            sample_size=sample_size,
            max_epss=max_epss,
            min_age_days=min_age_days,
            n_excluded=len(exclude_cves),
        )

        # In production, this would:
        # 1. Query NVD API for CVEs older than min_age_days
        # 2. Filter by EPSS score < max_epss
        # 3. Exclude CVEs in exclude_cves set
        # 4. Random sample to get sample_size

        # Placeholder: Return empty list (requires actual NVD/EPSS queries)
        logger.warning(
            "negative_sampling_placeholder",
            message="Production implementation requires NVD/EPSS API integration",
        )

        return []

    def get_kev_details(self, cve_id: str) -> dict[str, object] | None:
        """Get detailed KEV information for a CVE.

        Args:
            cve_id: CVE identifier

        Returns:
            KEV entry details or None if not found
        """
        if self._cached_kev is None:
            return None

        for vuln in self._cached_kev:
            if vuln.cve_id == cve_id:
                return vuln.model_dump(by_alias=True)

        return None

    def get_kev_stats(self) -> dict[str, object]:
        """Get statistics about the KEV catalog.

        Returns:
            Dictionary with catalog statistics
        """
        if self._cached_kev is None:
            return {"status": "not_loaded"}

        vendors: set[str] = set()
        products: set[str] = set()
        years: dict[str, int] = {}

        for vuln in self._cached_kev:
            vendors.add(vuln.vendor_project)
            products.add(vuln.product)

            if vuln.cve_id.startswith("CVE-"):
                year = vuln.cve_id.split("-")[1]
                years[year] = years.get(year, 0) + 1

        return {
            "total_vulnerabilities": len(self._cached_kev),
            "unique_vendors": len(vendors),
            "unique_products": len(products),
            "by_year": dict(sorted(years.items())),
            "cache_timestamp": self._cache_timestamp.isoformat() if self._cache_timestamp else None,
            "schema_validated": True,
        }


__all__ = ["CISAKEVLoader", "KEVCatalog", "KEVVulnerability"]
