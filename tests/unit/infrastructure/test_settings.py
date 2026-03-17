"""Unit tests for settings configuration."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from siopv.infrastructure.config.settings import Settings, get_settings


@pytest.fixture
def settings_no_env_file(monkeypatch):  # noqa: ARG001
    """Fixture that prevents Settings from loading the .env file."""
    import os as os_module

    env_path = Path(".env")
    env_backup = Path(".env.test_backup")

    # Temporarily rename .env to prevent loading
    if env_path.exists():
        os_module.rename(str(env_path), str(env_backup))
        try:
            yield
        finally:
            # Restore .env
            if env_backup.exists():
                os_module.rename(str(env_backup), str(env_path))
    else:
        yield


# === Basic Settings Tests ===


def test_settings_defaults():
    """Test Settings with default values."""
    # Arrange & Act
    with patch.dict(os.environ, {"SIOPV_ANTHROPIC_API_KEY": "test-key"}, clear=True):
        settings = Settings()

    # Assert
    assert settings.app_name == "SIOPV"
    assert settings.environment == "development"
    assert settings.debug is False
    assert settings.log_level == "INFO"


def test_settings_from_env():
    """Test Settings loads from environment variables with SIOPV_ prefix."""
    # Arrange
    env_vars = {
        "SIOPV_ANTHROPIC_API_KEY": "sk-ant-test123",
        "SIOPV_APP_NAME": "CustomSIOPV",
        "SIOPV_ENVIRONMENT": "production",
        "SIOPV_DEBUG": "true",
        "SIOPV_LOG_LEVEL": "DEBUG",
    }

    # Act
    with patch.dict(os.environ, env_vars, clear=True):
        settings = Settings()

    # Assert
    assert settings.app_name == "CustomSIOPV"
    assert settings.environment == "production"
    assert settings.debug is True
    assert settings.log_level == "DEBUG"
    assert settings.anthropic_api_key.get_secret_value() == "sk-ant-test123"


@pytest.mark.usefixtures("settings_no_env_file")
def test_settings_anthropic_api_key_required():
    """Test Settings requires anthropic_api_key."""
    # Arrange & Act & Assert
    with patch.dict(os.environ, {}, clear=True), pytest.raises(ValidationError) as exc_info:
        Settings()

    assert "anthropic_api_key" in str(exc_info.value)


# === API Configuration Tests ===


@pytest.mark.usefixtures("settings_no_env_file")
def test_settings_nvd_defaults():
    """Test NVD API default configuration."""
    # Arrange & Act
    with patch.dict(os.environ, {"SIOPV_ANTHROPIC_API_KEY": "test-key"}, clear=True):
        settings = Settings()

    # Assert
    assert settings.nvd_api_key is None
    assert settings.nvd_base_url == "https://services.nvd.nist.gov/rest/json/cves/2.0"
    assert settings.nvd_rate_limit == 5


def test_settings_nvd_with_api_key():
    """Test NVD configuration with API key."""
    # Arrange
    env_vars = {
        "SIOPV_ANTHROPIC_API_KEY": "test-key",
        "SIOPV_NVD_API_KEY": "nvd-key-123",
        "SIOPV_NVD_RATE_LIMIT": "50",
    }

    # Act
    with patch.dict(os.environ, env_vars, clear=True):
        settings = Settings()

    # Assert
    assert settings.nvd_api_key is not None
    assert settings.nvd_api_key.get_secret_value() == "nvd-key-123"
    assert settings.nvd_rate_limit == 50


def test_settings_github_configuration():
    """Test GitHub configuration."""
    # Arrange
    env_vars = {
        "SIOPV_ANTHROPIC_API_KEY": "test-key",
        "SIOPV_GITHUB_TOKEN": "ghp_token123",
    }

    # Act
    with patch.dict(os.environ, env_vars, clear=True):
        settings = Settings()

    # Assert
    assert settings.github_token is not None
    assert settings.github_token.get_secret_value() == "ghp_token123"
    assert settings.github_graphql_url == "https://api.github.com/graphql"


def test_settings_epss_defaults():
    """Test EPSS API defaults."""
    # Arrange & Act
    with patch.dict(os.environ, {"SIOPV_ANTHROPIC_API_KEY": "test-key"}, clear=True):
        settings = Settings()

    # Assert
    assert settings.epss_base_url == "https://api.first.org/data/v1/epss"


# === Jira Configuration Tests ===


@pytest.mark.usefixtures("settings_no_env_file")
def test_settings_jira_optional():
    """Test Jira configuration is optional."""
    # Arrange & Act
    with patch.dict(os.environ, {"SIOPV_ANTHROPIC_API_KEY": "test-key"}, clear=True):
        settings = Settings()

    # Assert
    assert settings.jira_base_url is None
    assert settings.jira_email is None
    assert settings.jira_api_token is None
    assert settings.jira_project_key is None


def test_settings_jira_full_configuration():
    """Test Jira with all fields configured."""
    # Arrange
    env_vars = {
        "SIOPV_ANTHROPIC_API_KEY": "test-key",
        "SIOPV_JIRA_BASE_URL": "https://company.atlassian.net",
        "SIOPV_JIRA_EMAIL": "user@example.com",
        "SIOPV_JIRA_API_TOKEN": "jira-token-123",
        "SIOPV_JIRA_PROJECT_KEY": "SEC",
    }

    # Act
    with patch.dict(os.environ, env_vars, clear=True):
        settings = Settings()

    # Assert
    assert settings.jira_base_url == "https://company.atlassian.net"
    assert settings.jira_email == "user@example.com"
    assert settings.jira_api_token.get_secret_value() == "jira-token-123"
    assert settings.jira_project_key == "SEC"


# === ChromaDB Tests ===


def test_settings_chroma_defaults():
    """Test ChromaDB default configuration."""
    # Arrange & Act
    with patch.dict(os.environ, {"SIOPV_ANTHROPIC_API_KEY": "test-key"}, clear=True):
        settings = Settings()

    # Assert
    assert settings.chroma_persist_dir == Path("./chroma_data")
    assert settings.chroma_collection_name == "siopv_embeddings"
    assert settings.chroma_cache_size_mb == 4096


def test_settings_chroma_custom_path():
    """Test ChromaDB with custom persist directory."""
    # Arrange
    env_vars = {
        "SIOPV_ANTHROPIC_API_KEY": "test-key",
        "SIOPV_CHROMA_PERSIST_DIR": "/custom/path/chroma",
    }

    # Act
    with patch.dict(os.environ, env_vars, clear=True):
        settings = Settings()

    # Assert
    assert settings.chroma_persist_dir == Path("/custom/path/chroma")


# === ML Model Tests ===


def test_settings_ml_model_defaults():
    """Test ML model default configuration."""
    # Arrange & Act
    with patch.dict(os.environ, {"SIOPV_ANTHROPIC_API_KEY": "test-key"}, clear=True):
        settings = Settings()

    # Assert
    assert settings.model_path == Path("./models/xgboost_risk_model.json")


def test_settings_ml_model_custom():
    """Test ML model with custom path."""
    # Arrange
    env_vars = {
        "SIOPV_ANTHROPIC_API_KEY": "test-key",
        "SIOPV_MODEL_PATH": "/opt/models/custom_model.json",
    }

    # Act
    with patch.dict(os.environ, env_vars, clear=True):
        settings = Settings()

    # Assert
    assert settings.model_path == Path("/opt/models/custom_model.json")


# === Circuit Breaker Tests ===


def test_settings_circuit_breaker_defaults():
    """Test circuit breaker default configuration."""
    # Arrange & Act
    with patch.dict(os.environ, {"SIOPV_ANTHROPIC_API_KEY": "test-key"}, clear=True):
        settings = Settings()

    # Assert
    assert settings.circuit_breaker_failure_threshold == 5
    assert settings.circuit_breaker_recovery_timeout == 60


def test_settings_circuit_breaker_custom():
    """Test circuit breaker with custom values."""
    # Arrange
    env_vars = {
        "SIOPV_ANTHROPIC_API_KEY": "test-key",
        "SIOPV_CIRCUIT_BREAKER_FAILURE_THRESHOLD": "10",
        "SIOPV_CIRCUIT_BREAKER_RECOVERY_TIMEOUT": "120",
    }

    # Act
    with patch.dict(os.environ, env_vars, clear=True):
        settings = Settings()

    # Assert
    assert settings.circuit_breaker_failure_threshold == 10
    assert settings.circuit_breaker_recovery_timeout == 120


# === Claude Model Configuration Tests ===


def test_settings_claude_model_defaults():
    """Test Claude model defaults."""
    # Arrange & Act
    with patch.dict(os.environ, {"SIOPV_ANTHROPIC_API_KEY": "test-key"}, clear=True):
        settings = Settings()

    # Assert
    assert settings.claude_haiku_model == "claude-haiku-4-5-20251001"
    assert settings.claude_sonnet_model == "claude-sonnet-4-5-20250929"


def test_settings_claude_models_custom():
    """Test Claude models with custom values."""
    # Arrange
    env_vars = {
        "SIOPV_ANTHROPIC_API_KEY": "test-key",
        "SIOPV_CLAUDE_HAIKU_MODEL": "claude-3-haiku-20240307",
        "SIOPV_CLAUDE_SONNET_MODEL": "claude-3-sonnet-20240229",
    }

    # Act
    with patch.dict(os.environ, env_vars, clear=True):
        settings = Settings()

    # Assert
    assert settings.claude_haiku_model == "claude-3-haiku-20240307"
    assert settings.claude_sonnet_model == "claude-3-sonnet-20240229"


# === Environment Validation Tests ===


def test_settings_environment_literal_validation():
    """Test environment accepts only valid literals."""
    # Arrange
    env_vars = {
        "SIOPV_ANTHROPIC_API_KEY": "test-key",
        "SIOPV_ENVIRONMENT": "production",
    }

    # Act
    with patch.dict(os.environ, env_vars, clear=True):
        settings = Settings()

    # Assert
    assert settings.environment == "production"


def test_settings_log_level_literal_validation():
    """Test log_level accepts only valid literals."""
    # Arrange
    env_vars = {
        "SIOPV_ANTHROPIC_API_KEY": "test-key",
        "SIOPV_LOG_LEVEL": "ERROR",
    }

    # Act
    with patch.dict(os.environ, env_vars, clear=True):
        settings = Settings()

    # Assert
    assert settings.log_level == "ERROR"


# === OpenFGA Tests ===


@pytest.mark.usefixtures("settings_no_env_file")
def test_settings_openfga_optional():
    """Test OpenFGA configuration is optional."""
    # Arrange & Act
    with patch.dict(os.environ, {"SIOPV_ANTHROPIC_API_KEY": "test-key"}, clear=True):
        settings = Settings()

    # Assert
    assert settings.openfga_api_url is None
    assert settings.openfga_store_id is None


def test_settings_openfga_configured():
    """Test OpenFGA with configuration."""
    # Arrange
    env_vars = {
        "SIOPV_ANTHROPIC_API_KEY": "test-key",
        "SIOPV_OPENFGA_API_URL": "http://localhost:8080",
        "SIOPV_OPENFGA_STORE_ID": "store-123",
    }

    # Act
    with patch.dict(os.environ, env_vars, clear=True):
        settings = Settings()

    # Assert
    assert settings.openfga_api_url == "http://localhost:8080"
    assert settings.openfga_store_id == "store-123"


# === OpenFGA Authentication Tests ===


@pytest.mark.usefixtures("settings_no_env_file")
def test_settings_openfga_auth_defaults():
    """Test OpenFGA auth fields have correct defaults."""
    with patch.dict(os.environ, {"SIOPV_ANTHROPIC_API_KEY": "test-key"}, clear=True):
        settings = Settings()

    # Fields default to empty strings, not None
    assert settings.openfga_authorization_model_id == ""
    assert settings.openfga_auth_method == "none"
    assert settings.openfga_client_id == ""
    assert settings.openfga_api_audience == ""
    assert settings.openfga_api_token_issuer == ""


def test_settings_openfga_api_token_from_env():
    """Test OpenFGA API token loads from env as SecretStr."""
    env_vars = {
        "SIOPV_ANTHROPIC_API_KEY": "test-key",
        "SIOPV_OPENFGA_API_TOKEN": "my-secret-token",
        "SIOPV_OPENFGA_AUTH_METHOD": "api_token",
    }
    with patch.dict(os.environ, env_vars, clear=True):
        settings = Settings()

    assert settings.openfga_api_token is not None
    assert settings.openfga_api_token.get_secret_value() == "my-secret-token"
    assert settings.openfga_auth_method == "api_token"


def test_settings_openfga_oidc_from_env():
    """Test OpenFGA OIDC settings load from env."""
    env_vars = {
        "SIOPV_ANTHROPIC_API_KEY": "test-key",
        "SIOPV_OPENFGA_AUTH_METHOD": "client_credentials",
        "SIOPV_OPENFGA_CLIENT_ID": "my-client-id",
        "SIOPV_OPENFGA_CLIENT_SECRET": "my-client-secret",
        "SIOPV_OPENFGA_API_AUDIENCE": "openfga-audience",
        "SIOPV_OPENFGA_API_TOKEN_ISSUER": "https://idp.example.com/",
    }
    with patch.dict(os.environ, env_vars, clear=True):
        settings = Settings()

    assert settings.openfga_auth_method == "client_credentials"
    assert settings.openfga_client_id == "my-client-id"
    assert settings.openfga_client_secret.get_secret_value() == "my-client-secret"
    assert settings.openfga_api_audience == "openfga-audience"
    assert settings.openfga_api_token_issuer == "https://idp.example.com/"


# === get_settings() Cache Tests ===


def test_get_settings_returns_cached_instance():
    """Test get_settings() returns cached singleton."""
    # Arrange
    with patch.dict(os.environ, {"SIOPV_ANTHROPIC_API_KEY": "test-key"}, clear=True):
        # Act
        settings1 = get_settings()
        settings2 = get_settings()

    # Assert
    assert settings1 is settings2


def test_get_settings_cache_info():
    """Test get_settings() uses lru_cache."""
    # Arrange
    get_settings.cache_clear()

    # Act
    with patch.dict(os.environ, {"SIOPV_ANTHROPIC_API_KEY": "test-key"}, clear=True):
        get_settings()
        cache_info = get_settings.cache_info()

    # Assert
    assert cache_info.hits == 0
    assert cache_info.misses == 1


# === SecretStr Tests ===


def test_settings_secret_str_hidden():
    """Test SecretStr fields don't expose secrets in repr."""
    # Arrange
    env_vars = {
        "SIOPV_ANTHROPIC_API_KEY": "super-secret-key",
        "SIOPV_NVD_API_KEY": "nvd-secret",
    }

    # Act
    with patch.dict(os.environ, env_vars, clear=True):
        settings = Settings()

    # Assert
    settings_repr = repr(settings)
    assert "super-secret-key" not in settings_repr
    assert "nvd-secret" not in settings_repr
    assert "SecretStr" in settings_repr


def test_settings_secret_str_get_secret_value():
    """Test SecretStr.get_secret_value() returns actual value."""
    # Arrange
    env_vars = {
        "SIOPV_ANTHROPIC_API_KEY": "actual-secret",
    }

    # Act
    with patch.dict(os.environ, env_vars, clear=True):
        settings = Settings()

    # Assert
    assert settings.anthropic_api_key.get_secret_value() == "actual-secret"


# === Extra Fields Tests ===


def test_settings_ignores_extra_fields():
    """Test Settings ignores unknown environment variables."""
    # Arrange
    env_vars = {
        "SIOPV_ANTHROPIC_API_KEY": "test-key",
        "SIOPV_UNKNOWN_FIELD": "should-be-ignored",
        "SIOPV_ANOTHER_UNKNOWN": "also-ignored",
    }

    # Act & Assert (should not raise ValidationError)
    with patch.dict(os.environ, env_vars, clear=True):
        settings = Settings()
        assert settings.app_name == "SIOPV"  # Normal field works


# === OpenFGA Validation Warning Tests ===


def test_settings_openfga_auth_method_api_token_missing_token_warns():
    """Test warning when api_token auth method but token not set."""
    with (
        pytest.warns(
            UserWarning,
            match="SIOPV_OPENFGA_AUTH_METHOD=api_token but SIOPV_OPENFGA_API_TOKEN is not set",
        ),
        patch.dict(
            os.environ,
            {
                "SIOPV_ANTHROPIC_API_KEY": "test-key",
                "SIOPV_OPENFGA_AUTH_METHOD": "api_token",
            },
            clear=True,
        ),
    ):
        Settings()


def test_settings_openfga_auth_method_client_credentials_missing_client_id_warns():
    """Test warning when client_credentials auth method but client_id not set."""
    expected_match = (
        "SIOPV_OPENFGA_AUTH_METHOD=client_credentials but missing: SIOPV_OPENFGA_CLIENT_ID"
    )
    with (
        pytest.warns(UserWarning, match=expected_match),
        patch.dict(
            os.environ,
            {
                "SIOPV_ANTHROPIC_API_KEY": "test-key",
                "SIOPV_OPENFGA_AUTH_METHOD": "client_credentials",
                "SIOPV_OPENFGA_CLIENT_SECRET": "secret",
                "SIOPV_OPENFGA_API_TOKEN_ISSUER": "https://idp.example.com/",
            },
            clear=True,
        ),
    ):
        Settings()


def test_settings_openfga_auth_method_client_credentials_missing_client_secret_warns():
    """Test warning when client_credentials auth method but client_secret not set."""
    expected_match = (
        "SIOPV_OPENFGA_AUTH_METHOD=client_credentials but missing: SIOPV_OPENFGA_CLIENT_SECRET"
    )
    with (
        pytest.warns(UserWarning, match=expected_match),
        patch.dict(
            os.environ,
            {
                "SIOPV_ANTHROPIC_API_KEY": "test-key",
                "SIOPV_OPENFGA_AUTH_METHOD": "client_credentials",
                "SIOPV_OPENFGA_CLIENT_ID": "client-id",
                "SIOPV_OPENFGA_API_TOKEN_ISSUER": "https://idp.example.com/",
            },
            clear=True,
        ),
    ):
        Settings()


def test_settings_openfga_auth_method_client_credentials_missing_issuer_warns():
    """Test warning when client_credentials auth method but api_token_issuer not set."""
    expected_match = (
        "SIOPV_OPENFGA_AUTH_METHOD=client_credentials but missing: SIOPV_OPENFGA_API_TOKEN_ISSUER"
    )
    with (
        pytest.warns(UserWarning, match=expected_match),
        patch.dict(
            os.environ,
            {
                "SIOPV_ANTHROPIC_API_KEY": "test-key",
                "SIOPV_OPENFGA_AUTH_METHOD": "client_credentials",
                "SIOPV_OPENFGA_CLIENT_ID": "client-id",
                "SIOPV_OPENFGA_CLIENT_SECRET": "secret",
            },
            clear=True,
        ),
    ):
        Settings()


def test_settings_openfga_auth_method_client_credentials_missing_all_warns():
    """Test warning when client_credentials auth method but all required fields missing."""
    expected_match = (
        "SIOPV_OPENFGA_AUTH_METHOD=client_credentials"
        " but missing: SIOPV_OPENFGA_CLIENT_ID,"
        " SIOPV_OPENFGA_CLIENT_SECRET,"
        " SIOPV_OPENFGA_API_TOKEN_ISSUER"
    )
    with (
        pytest.warns(UserWarning, match=expected_match),
        patch.dict(
            os.environ,
            {
                "SIOPV_ANTHROPIC_API_KEY": "test-key",
                "SIOPV_OPENFGA_AUTH_METHOD": "client_credentials",
            },
            clear=True,
        ),
    ):
        Settings()
