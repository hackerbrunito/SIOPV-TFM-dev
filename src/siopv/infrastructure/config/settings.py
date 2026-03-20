"""Application settings using Pydantic Settings.

Configuration loaded from environment variables and .env file.
"""

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
    claude_sonnet_model: str = "claude-sonnet-4-6"
    llm_max_context_length: int = 6_000
    llm_analysis_max_tokens: int = 1024
    llm_confidence_max_tokens: int = 128
    haiku_max_text_length: int = 4_000
    haiku_max_tokens: int = 512
    haiku_validation_max_tokens: int = 10
    haiku_min_short_text_length: int = 20

    # === NVD API ===
    nvd_api_key: SecretStr | None = None
    nvd_base_url: str = "https://services.nvd.nist.gov/rest/json/cves/2.0"
    nvd_rate_limit_with_key: int = 50
    nvd_rate_limit_without_key: int = 5
    nvd_rate_limit_period_seconds: float = 30.0
    nvd_timeout_connect: float = 5.0
    nvd_timeout_read: float = 30.0
    nvd_timeout_write: float = 5.0
    nvd_timeout_pool: float = 5.0
    nvd_max_concurrent: int = 5

    # === GitHub Security Advisories ===
    github_token: SecretStr | None = None
    github_graphql_url: str = "https://api.github.com/graphql"
    github_rate_limit_with_token: int = 5000
    github_rate_limit_without_token: int = 60
    github_rate_limit_period_seconds: float = 3600.0
    github_timeout_connect: float = 5.0
    github_timeout_read: float = 30.0
    github_timeout_write: float = 5.0
    github_timeout_pool: float = 5.0

    # === EPSS API ===
    epss_base_url: str = "https://api.first.org/data/v1/epss"
    epss_rate_limit_rps: float = 10.0
    epss_burst_size: int = 20
    epss_timeout_connect: float = 5.0
    epss_timeout_read: float = 15.0
    epss_timeout_write: float = 5.0
    epss_timeout_pool: float = 5.0
    epss_batch_chunk_size: int = 100

    # === Tavily Search ===
    tavily_api_key: SecretStr | None = None
    tavily_base_url: str = "https://api.tavily.com/search"

    # === Rate Limiter ===
    rate_limiter_max_queue_size: int = 100

    # === Jira ===
    jira_base_url: str | None = None
    jira_email: str | None = None
    jira_api_token: SecretStr | None = None
    jira_project_key: str | None = None
    jira_issue_type: str = "Task"

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
            msg = "SIOPV_OPENFGA_AUTH_METHOD=api_token but SIOPV_OPENFGA_API_TOKEN is not set"
            raise ValueError(msg)
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
                raise ValueError(msg)
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

    # === Uncertainty Threshold (spec section 3.4) ===
    uncertainty_threshold: float = 0.3
    confidence_floor: float = 0.7
    adaptive_percentile: int = 90
    discrepancy_history_size: int = 500
    default_confidence: float = 0.5

    # === Human-in-the-Loop Timeouts ===
    hitl_timeout_level1_hours: int = 4
    hitl_timeout_level2_hours: int = 8
    hitl_timeout_level3_hours: int = 24
    review_deadline_hours: int = 24

    # === ML Model ===
    model_path: Path = Path("./models/xgboost_risk_model.json")
    # Defined for configurability. Wiring to ML loader is a future task.
    model_base_path: Path = Path("./models")
    model_max_size_bytes: int = 104_857_600  # 100MB
    model_signing_key: SecretStr | None = None  # HMAC key for model integrity

    # === Database ===
    # Defined for future general-purpose persistence layer (audit logs, metrics
    # storage). Current pipeline uses checkpoint_db_path for LangGraph SQLite
    # checkpointer. Wiring to a persistence adapter is a future task.
    database_url: SecretStr = SecretStr("sqlite+aiosqlite:///./siopv.db")
    # checkpoint_db_path: LangGraph SQLite checkpointer file path
    checkpoint_db_path: str = "siopv_checkpoints.db"

    # === API Client Cache ===
    api_client_cache_max_size: int = 1000

    # === Circuit Breaker ===
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_recovery_timeout: int = 60  # seconds

    # === Webhook ===
    webhook_enabled: bool = False
    webhook_secret: SecretStr | None = None
    webhook_host: str = "0.0.0.0"
    webhook_port: int = 8080

    # === PDF Output (Phase 8) ===
    output_dir: Path = Path("./output")
    pdf_include_cot: bool = False


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
