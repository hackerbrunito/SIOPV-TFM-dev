# Verification Report: Pydantic & OpenFGA Audit Findings

**Date:** 2026-03-05
**Agent:** Verification Agent (Context7 + Code Inspection)
**Scope:** Findings H5, I2, Pydantic v2 ConfigDict spot-check, M3

---

## Methodology

Each finding was verified using one or more of:
1. Direct code inspection (Read tool on actual project files)
2. Context7 MCP — library `/pydantic/pydantic` (742 snippets, High reputation, score 88.9)
3. Context7 MCP — library `/websites/openfga_dev` (2476 snippets, High reputation, score 82.7)
4. Context7 MCP — library `/openfga/cli` (49 snippets, High reputation)

Training data was NOT used as a source of truth for any finding.

---

## Finding H5: `SHAPValues.validate_shap_values()` is a no-op Pydantic v2 validator

### Code Inspected

File: `/Users/bruno/siopv/src/siopv/domain/value_objects/risk_score.py` (lines 48-52)

```python
@field_validator("shap_values")
@classmethod
def validate_shap_values(cls, v: list[float]) -> list[float]:
    """Validate SHAP values have same length as feature names."""
    return v
```

The docstring says "Validate SHAP values have same length as feature names" but the body only does `return v` — no length check is performed.

### Context7 Findings

**Q1: Is `return v` a valid passthrough in a Pydantic v2 `@field_validator`?**

Yes — from Context7 `/pydantic/pydantic`:

> "Validators can transform values (like converting to lowercase) or raise ValueError with custom error messages when validation fails."

The `@field_validator` pattern always requires returning the (possibly modified) value. `return v` is the correct pattern for a passthrough. This part is not a bug.

**Q2: Can `@field_validator` validate cross-field consistency?**

No — from Context7 `/pydantic/pydantic`:

> "@field_validator decorator allows custom validation logic for specific fields with support for before, after, wrap, and plain modes. Validators are class methods that receive the field value and can access OTHER field values through the `info` parameter's `data` attribute."

Important caveat from the same source: `info.data` only contains fields that have already been validated at the time the validator runs. Since `feature_names` is declared before `shap_values` in the class, it would be available in `info.data`. However, accessing `info.data.get("feature_names")` in a `@field_validator` for `shap_values` is fragile — it silently skips the check if `feature_names` validation fails first.

**Q3: What is the correct Pydantic v2 pattern for cross-field length validation?**

From Context7 `/pydantic/pydantic` — `model_validator` examples:

```python
@model_validator(mode='after')
def validate_area(self) -> Self:
    if self.area is not None:
        calculated = self.width * self.height
        if abs(self.area - calculated) > 0.01:
            raise ValueError(f'area {self.area} does not match width*height={calculated}')
    return self
```

And cross-field validation:

```python
@model_validator(mode='after')
def check_dates(self) -> Self:
    if self.start_date > self.end_date:
        raise ValueError('start_date must be before end_date')
    return self
```

The canonical Pydantic v2 pattern for `len(feature_names) == len(shap_values)` is:

```python
@model_validator(mode='after')
def validate_length_consistency(self) -> Self:
    if len(self.feature_names) != len(self.shap_values):
        raise ValueError(
            f"feature_names length {len(self.feature_names)} != "
            f"shap_values length {len(self.shap_values)}"
        )
    return self
```

### Verdict: CONFIRMED

The audit finding is correct. The `@field_validator("shap_values")` with body `return v` is a **no-op validator** — it does nothing despite its docstring claiming it validates length consistency. This is a logic bug, not a Pydantic API misuse.

The fix requires replacing it with a `@model_validator(mode='after')` that can see both `self.feature_names` and `self.shap_values` simultaneously.

Note: The existing `to_dict()` method uses `zip(..., strict=True)` which WILL raise a `ValueError` at runtime if lengths differ — but only when `to_dict()` is called, not at model construction time. The validator was intended to catch this at construction.

---

## Finding I2: `ingest_trivy.py` importing concrete adapter violates hexagonal architecture

### Code Inspected

File: `/Users/bruno/siopv/src/siopv/application/use_cases/ingest_trivy.py` (line 17):

```python
from siopv.adapters.external_apis.trivy_parser import TrivyParser
```

File: `/Users/bruno/siopv/src/siopv/application/ports/__init__.py` — ports available:

```
authorization.py      → AuthorizationModelPort, AuthorizationPort, AuthorizationStorePort
enrichment_clients.py → EPSSClientPort, GitHubAdvisoryClientPort, NVDClientPort, OSINTSearchClientPort
ml_classifier.py      → DatasetLoaderPort, MLClassifierPort, ModelTrainerPort
oidc_authentication.py → OIDCAuthenticationPort
vector_store.py       → VectorStorePort
dlp.py                → (DLP ports)
```

There is **no** `IngestionPort`, `ParserPort`, or `TrivyParserPort` in the application ports layer.

The use case instantiates the concrete adapter directly in `__init__`:

```python
def __init__(self) -> None:
    """Initialize the use case with a Trivy parser."""
    self._parser = TrivyParser()
```

### Verdict: CONFIRMED

The audit finding is correct. `IngestTrivyReportUseCase` imports and instantiates `TrivyParser` (a concrete adapter in `siopv.adapters.external_apis`) directly, bypassing the ports-and-adapters pattern. The application layer (`use_cases/`) should only depend on abstractions (ports), not on concrete adapter implementations.

Consequences:
- The use case is untestable with a mock parser without monkeypatching
- Swapping Trivy for another scanner (e.g., Grype) requires modifying the use case
- The dependency inversion principle is violated

The correct pattern would be:
1. Define a `ParserPort` (or `IngestionPort`) in `application/ports/`
2. Inject the port via `__init__(self, parser: ParserPort)`
3. Wire the concrete `TrivyParser` in the DI container (`infrastructure/di/`)

This is consistent with how other use cases in the project handle dependencies (e.g., `AuthorizationPort` injected via DI).

---

## Finding: Pydantic v2 `ConfigDict` usage throughout (spot-check)

### Code Inspected

**File: `/Users/bruno/siopv/src/siopv/infrastructure/config/settings.py` (lines 1-80)**

```python
from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="SIOPV_",
        extra="ignore",
    )
    anthropic_api_key: SecretStr = Field(default=...)
    nvd_api_key: SecretStr | None = None
    github_token: SecretStr | None = None
    openfga_api_token: SecretStr | None = None
    openfga_client_secret: SecretStr | None = None

    @model_validator(mode="after")
    def _validate_openfga_auth(self) -> Self: ...
```

**File: `/Users/bruno/siopv/src/siopv/domain/value_objects/risk_score.py`**

```python
from pydantic import BaseModel, ConfigDict, Field, field_validator

class SHAPValues(BaseModel):
    model_config = ConfigDict(frozen=True)

class LIMEExplanation(BaseModel):
    model_config = ConfigDict(frozen=True)

class RiskScore(BaseModel):
    model_config = ConfigDict(frozen=True)
```

**File: `/Users/bruno/siopv/src/siopv/domain/entities/ml_feature_vector.py`**

```python
from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

class MLFeatureVector(BaseModel):
    model_config = ConfigDict(frozen=True)
```

### Context7 Verification

From Context7 `/pydantic/pydantic` on `SettingsConfigDict`:

> "`BaseSettings`, the base object for Pydantic settings management, has been moved to a separate package, `pydantic-settings`."

The project correctly imports `BaseSettings` and `SettingsConfigDict` from `pydantic_settings`, not from `pydantic`. This is the correct v2 pattern.

From Context7 on `ConfigDict`:

```python
class StrictModel(BaseModel):
    model_config = ConfigDict(
        strict=True,
        frozen=True,
        extra='forbid',
        validate_assignment=True,
    )
```

The project's use of `ConfigDict(frozen=True)` on domain value objects is correct Pydantic v2 pattern.

`SecretStr` usage: Context7 shows `SecretStr` imported from `pydantic` and used for sensitive fields — matches the project exactly.

`model_validator(mode="after")` with `-> Self` return type: Confirmed as correct Pydantic v2 pattern per Context7 examples showing:

```python
@model_validator(mode='after')
def check_dates(self) -> Self:
    if self.start_date > self.end_date:
        raise ValueError('start_date must be before end_date')
    return self
```

### Verdict: CONFIRMED (no issues found)

The audit's positive finding is correct. The project uses Pydantic v2 patterns correctly throughout:
- `SettingsConfigDict` from `pydantic_settings` (not `pydantic.ConfigDict`)
- `ConfigDict(frozen=True)` on domain value objects
- `SecretStr` for all sensitive fields (API keys, tokens, secrets)
- `model_validator(mode="after")` with `Self` return type
- Modern union syntax `SecretStr | None` instead of `Optional[SecretStr]`
- `field_validator` with `@classmethod` decorator (Pydantic v2 requirement)

No Pydantic v1 patterns detected in inspected files.

---

## Finding M3: OpenFGA model not mounted in docker-compose

### Code Inspected

**`/Users/bruno/siopv/openfga/` directory contents:**
```
model.fga    (827 bytes — the authorization model in FGA DSL format)
model.json   (8175 bytes — JSON equivalent)
keycloak/    (directory)
```

**`/Users/bruno/siopv/docker-compose.yml` — OpenFGA service (lines 195-240):**

The docker-compose defines three OpenFGA-related services:
- `openfga-postgres` — PostgreSQL database
- `openfga-migrate` — runs `openfga migrate` to apply DB schema
- `openfga` — the main OpenFGA server

The `openfga` service:
```yaml
openfga:
  image: openfga/openfga:latest
  command: run
  environment:
    - OPENFGA_DATASTORE_ENGINE=postgres
    - OPENFGA_DATASTORE_URI=postgres://openfga:openfga@openfga-postgres:5432/openfga?sslmode=disable
    - OPENFGA_AUTHN_METHOD=${OPENFGA_AUTHN_METHOD:-preshared}
    - OPENFGA_AUTHN_PRESHARED_KEYS=dev-key-siopv-local-1
    ...
  depends_on:
    openfga-migrate:
      condition: service_completed_successfully
```

There is **no volume mount** for `./openfga/model.fga` and **no init container** that calls `fga model write` or `fga store create`. The `openfga-migrate` service only runs DB schema migrations, not model seeding.

### Context7 Findings on OpenFGA Bootstrap Pattern

From Context7 `/openfga/cli` — `fga model write` command:

```
fga model write --store-id=01H0H015178Y2V4CX10C2KGHF4 --file=model.fga
```

From Context7 `/openfga/cli` — `fga store create` with model:

```
fga store create --model Model.fga
```

From Context7 `/openfga/cli` — `fga store import`:

```
fga store import --file model.fga.yaml --store-id=...
```

**Key finding from OpenFGA docs:** There is no native docker-compose environment variable like `OPENFGA_BOOTSTRAP_MODEL` that auto-loads a model on startup. The OpenFGA server (`openfga run`) does NOT auto-apply model files from disk. The model must be loaded via:
1. A separate init container using `fga model write` or `fga store import`
2. An application-level bootstrap script called at startup

The project has `model.fga` and `model.json` in the `openfga/` directory but:
- Neither file is mounted as a volume in docker-compose
- No init container exists to apply the model
- No bootstrap script was found (only `testing-kit/run-tests.sh` exists)

This means every `docker compose up` starts a fresh OpenFGA instance with **no authorization model** loaded. The application code that uses `openfga_authorization_model_id` from settings would receive an empty string (the default) and would fail to perform authorization checks unless a developer manually runs `fga model write` after starting the stack.

### Verdict: CONFIRMED

The audit finding is correct. The `openfga/model.fga` file exists but is never applied when docker-compose starts. There is no init container, no volume mount, and no bootstrap script to load the model. This is a developer experience and correctness issue — the dev environment will not have authorization models loaded unless manually bootstrapped.

The standard fix is to add an init service to docker-compose:

```yaml
openfga-init:
  image: openfga/cli:latest  # or a curl-based init container
  depends_on:
    openfga:
      condition: service_healthy
  command: >
    fga store create --name siopv --model /openfga/model.fga
  volumes:
    - ./openfga/model.fga:/openfga/model.fga:ro
  environment:
    - FGA_API_URL=http://openfga:8080
```

---

## Summary

| Finding | Verdict | Confidence |
|---------|---------|------------|
| H5: `validate_shap_values()` is a no-op | CONFIRMED | HIGH — code is clear: `return v` with no check |
| I2: `ingest_trivy.py` imports concrete adapter | CONFIRMED | HIGH — `TrivyParser` imported directly, no port exists |
| Pydantic v2 ConfigDict spot-check | CONFIRMED (no issues) | HIGH — all patterns verified against Context7 |
| M3: OpenFGA model not mounted in docker-compose | CONFIRMED | HIGH — no volume mount, no init container, no bootstrap script |

---

## Key Evidence

### H5 — Critical detail
The `to_dict()` method uses `zip(..., strict=True)` which will raise at call time if lengths differ, but the validator was supposed to catch mismatches at model construction time. Both the validator body and docstring mismatch are bugs.

### I2 — Port inventory
`application/ports/` contains: authorization, enrichment_clients, ml_classifier, oidc_authentication, vector_store, dlp — **no parser/ingestion port exists**.

### M3 — OpenFGA bootstrap gap
OpenFGA does not support auto-loading models from disk at startup via environment variables. The only mechanisms are: CLI (`fga model write`), SDK API calls, or REST API calls. None are wired into the docker-compose stack.
