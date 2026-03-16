# Pydantic Settings — Context7 Cache

## Current Version: pydantic-settings v2.x

## Key API Patterns

### BaseSettings
- `from pydantic_settings import BaseSettings, SettingsConfigDict`
- Separate package from pydantic core (pydantic-settings)
- `model_config = SettingsConfigDict(env_prefix="SIOPV_", env_file=".env", env_nested_delimiter="__")`

### Environment Variable Loading
- Fields auto-load from environment variables
- `env_prefix` prepends prefix to all field names for env lookup
- `env_nested_delimiter="__"` enables nested model loading: `SIOPV__DB__HOST=localhost`
- Case-insensitive env var matching by default

### Settings Sources (Priority Order)
1. `init_settings` — constructor kwargs
2. `env_settings` — environment variables
3. `dotenv_settings` — .env file
4. `file_secret_settings` — secrets directory
- Customizable via `settings_customise_sources()` classmethod

### SecretStr for Credentials
- `password: SecretStr` — never expose in logs/repr
- Access via `.get_secret_value()`
- NO default values for secrets (force explicit configuration)

### Deprecated
- `class Config:` → use `model_config = SettingsConfigDict(...)`
- `env` field parameter → use `validation_alias=AliasChoices(...)`
