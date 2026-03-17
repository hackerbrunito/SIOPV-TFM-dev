"""Application settings using Pydantic Settings.

Configuration loaded from environment variables and .env file.
"""

import warnings
from functools import lru_cache
from pathlib import Path
from typing import Literal, Self

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """SIOPV application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="SIOPV_",
        extra="ignore",
    )

    # === Application ===
    app_name: str = "SIOPV"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # === Anthropic (Claude) ===
    anthropic_api_key: SecretStr = Field(default=...)
    claude_haiku_model: str = "claude-haiku-4-5-20251001"
    claude_sonnet_model: str = "claude-sonnet-4-5-20250929"

    # === NVD API ===
    nvd_api_key: SecretStr | None = None
    nvd_base_url: str = "https://services.nvd.nist.gov/rest/json/cves/2.0"
    nvd_rate_limit: int = 5  # requests per 30 seconds (50 with API key)

    # === GitHub Security Advisories ===
    github_token: SecretStr | None = None
    github_graphql_url: str = "https://api.github.com/graphql"

    # === EPSS API ===
    epss_base_url: str = "https://api.first.org/data/v1/epss"

    # === Tavily Search ===
    tavily_api_key: SecretStr | None = None

    # === Jira ===
    jira_base_url: str | None = None
    jira_email: str | None = None
    jira_api_token: SecretStr | None = None
    jira_project_key: str | None = None

    # === Database ===
    database_url: str = "sqlite+aiosqlite:///./siopv.db"

    # === ChromaDB ===
    chroma_persist_dir: Path = Path("./chroma_data")
    chroma_collection_name: str = "siopv_embeddings"
    chroma_cache_size_mb: int = 4096  # 4GB max cache

    # === OpenFGA ===
    openfga_api_url: str | None = None
    openfga_store_id: str | None = None
    openfga_api_token: SecretStr | None = None
    openfga_authorization_model_id: str = ""
    # === OpenFGA OIDC (client_credentials) ===
    openfga_auth_method: Literal["none", "api_token", "client_credentials"] = "none"
    openfga_client_id: str = ""
    openfga_client_secret: SecretStr | None = None
    openfga_api_audience: str = ""
    openfga_api_token_issuer: str = ""

    @model_validator(mode="after")
    def _validate_openfga_auth(self) -> Self:
        """Validate OpenFGA auth configuration consistency."""
        if self.openfga_auth_method == "api_token" and not self.openfga_api_token:
            warnings.warn(
                "SIOPV_OPENFGA_AUTH_METHOD=api_token but SIOPV_OPENFGA_API_TOKEN is not set",
                stacklevel=2,
            )
        if self.openfga_auth_method == "client_credentials":
            missing = []
            if not self.openfga_client_id:
                missing.append("SIOPV_OPENFGA_CLIENT_ID")
            if not self.openfga_client_secret:
                missing.append("SIOPV_OPENFGA_CLIENT_SECRET")
            if not self.openfga_api_token_issuer:
                missing.append("SIOPV_OPENFGA_API_TOKEN_ISSUER")
            if missing:
                msg = (
                    "SIOPV_OPENFGA_AUTH_METHOD=client_credentials but missing: "
                    f"{', '.join(missing)}"
                )
                warnings.warn(msg, stacklevel=2)
        return self

    # === OIDC Authentication (API clients → SIOPV) ===
    oidc_enabled: bool = False
    oidc_issuer_url: str = ""  # e.g., http://localhost:8888/realms/siopv
    oidc_audience: str = ""  # e.g., siopv-api
    oidc_jwks_cache_ttl_seconds: int = 3600  # 1 hour JWKS cache
    oidc_allowed_clock_skew_seconds: int = 30  # leeway for clock drift

    @model_validator(mode="after")
    def _validate_oidc_auth(self) -> Self:
        """Validate OIDC authentication configuration consistency."""
        if self.oidc_enabled:
            missing = []
            if not self.oidc_issuer_url:
                missing.append("SIOPV_OIDC_ISSUER_URL")
            if not self.oidc_audience:
                missing.append("SIOPV_OIDC_AUDIENCE")
            if missing:
                msg = f"SIOPV_OIDC_ENABLED=true but missing required fields: {', '.join(missing)}"
                raise ValueError(msg)
        return self

    # === ML Model ===
    model_path: Path = Path("./models/xgboost_risk_model.json")
    model_base_path: Path = Path("./models")
    model_max_size_bytes: int = 104857600  # 100MB
    model_signing_key: SecretStr | None = None  # HMAC key for model integrity
    uncertainty_threshold: float = 0.3

    # === Circuit Breaker ===
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_recovery_timeout: int = 60  # seconds

    # === Human-in-the-Loop ===
    hitl_timeout_level1_hours: int = 4
    hitl_timeout_level2_hours: int = 8
    hitl_timeout_level3_hours: int = 24

    # === PDF Output (Phase 8) ===
    output_dir: Path = Path("./output")
    pdf_include_cot: bool = False


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
