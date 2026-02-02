"""Application settings using Pydantic Settings.

Configuration loaded from environment variables and .env file.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
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


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
