# Estándares Python 2026

Referencia de estándares de código Python para proyectos generados.

---

## Type Hints (Python 3.11+)

### Correcto
```python
def process(items: list[str]) -> dict[str, int]:
    ...

def get_user(id: int) -> User | None:
    ...

def fetch_data() -> list[dict[str, Any]]:
    ...

# Tipos complejos
type JsonDict = dict[str, Any]
type Callback = Callable[[str], None]
```

### Prohibido
```python
from typing import List, Dict, Optional, Union

def process(items: List[str]) -> Dict[str, int]:  # ❌
    ...

def get_user(id: int) -> Optional[User]:  # ❌
    ...
```

---

## Pydantic v2

### Correcto
```python
from pydantic import BaseModel, ConfigDict, field_validator, Field

class Vulnerability(BaseModel):
    model_config = ConfigDict(
        strict=True,
        frozen=True,
        extra="forbid",
    )

    cve_id: str = Field(..., pattern=r"^CVE-\d{4}-\d+$")
    severity: str
    description: str | None = None

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        allowed = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
        if v.upper() not in allowed:
            raise ValueError(f"severity must be one of {allowed}")
        return v.upper()
```

### Prohibido
```python
class Vulnerability(BaseModel):
    class Config:  # ❌ Pydantic v1
        frozen = True

    cve_id: str

    @validator("severity")  # ❌ Pydantic v1
    def validate_severity(cls, v):
        ...
```

---

## HTTP Async (httpx)

### Correcto
```python
import httpx

async def fetch_cve(cve_id: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"https://api.nvd.nist.gov/cve/{cve_id}",
        )
        response.raise_for_status()
        return response.json()

# O con timeouts específicos por operación
async def fetch_with_custom_timeout(url: str) -> dict[str, Any]:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            timeout=httpx.Timeout(10.0, connect=5.0, read=30.0),
        )
        response.raise_for_status()
        return response.json()
```

### Timeouts Recomendados
- **Default (API calls):** 30.0 segundos
- **Health checks / Pings:** 5.0-10.0 segundos
- **Large file downloads:** 60.0-120.0 segundos
- **Connection establishment:** 5.0 segundos

### Prohibido
```python
import requests  # ❌

def fetch_cve(cve_id: str) -> dict:
    response = requests.get(url)  # ❌ Sync
    response = requests.get(url, timeout=None)  # ❌ No timeout
    ...
```

---

## Logging (structlog)

### Correcto
```python
import structlog

logger = structlog.get_logger(__name__)

def process_vulnerability(vuln: Vulnerability) -> None:
    logger.info(
        "processing_vulnerability",
        cve_id=vuln.cve_id,
        severity=vuln.severity,
    )
    try:
        result = analyze(vuln)
        logger.info("analysis_complete", result=result)
    except AnalysisError as e:
        logger.error("analysis_failed", error=str(e), cve_id=vuln.cve_id)
        raise
```

### Prohibido
```python
print(f"Processing {vuln.cve_id}")  # ❌
print("Error:", e)  # ❌
```

---

## Paths (pathlib)

### Correcto
```python
from pathlib import Path

def load_config() -> dict[str, Any]:
    config_path = Path(__file__).parent / "config" / "settings.json"
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")
    return json.loads(config_path.read_text())

def save_report(data: str, output_dir: Path) -> Path:
    output_path = output_dir / "report.pdf"
    output_path.write_text(data)
    return output_path
```

### Prohibido
```python
import os

config_path = os.path.join(os.path.dirname(__file__), "config", "settings.json")  # ❌
if not os.path.exists(config_path):  # ❌
    ...
```

---

## Error Handling

### Correcto
```python
from src.exceptions import ValidationError, APIError

async def fetch_and_process(cve_id: str) -> Result:
    try:
        data = await fetch_cve(cve_id)
    except httpx.HTTPStatusError as e:
        logger.error("api_error", status=e.response.status_code)
        raise APIError(f"Failed to fetch CVE: {e}") from e
    except httpx.TimeoutException:
        logger.warning("api_timeout", cve_id=cve_id)
        raise APIError("Request timed out")

    try:
        return process(data)
    except ValueError as e:
        logger.error("validation_error", error=str(e))
        raise ValidationError(str(e)) from e
```

### Prohibido
```python
try:
    ...
except:  # ❌ Bare except
    pass  # ❌ Silent failure

try:
    ...
except Exception as e:  # ❌ Too broad
    print(e)  # ❌
```

---

## Async Patterns

### Correcto
```python
import asyncio
from collections.abc import Sequence

async def process_all(items: Sequence[str]) -> list[Result]:
    """Process items concurrently with rate limiting."""
    semaphore = asyncio.Semaphore(10)  # Max 10 concurrent

    async def process_one(item: str) -> Result:
        async with semaphore:
            return await process(item)

    tasks = [process_one(item) for item in items]
    return await asyncio.gather(*tasks)
```

---

## Configuration

### Correcto
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
    )

    api_key: str
    database_url: str
    debug: bool = False
    max_workers: int = 4

settings = Settings()
```

---

## Testing

### Correcto
```python
import pytest
from unittest.mock import AsyncMock

@pytest.fixture
def mock_client(mocker) -> AsyncMock:
    return mocker.patch("src.api.httpx.AsyncClient")

@pytest.mark.asyncio
async def test_fetch_cve_success(mock_client: AsyncMock):
    # Arrange
    mock_client.return_value.__aenter__.return_value.get.return_value = AsyncMock(
        json=lambda: {"cve": "data"},
        raise_for_status=lambda: None,
    )

    # Act
    result = await fetch_cve("CVE-2024-1234")

    # Assert
    assert result == {"cve": "data"}

@pytest.mark.parametrize("severity,expected", [
    ("CRITICAL", 10),
    ("HIGH", 8),
    ("MEDIUM", 5),
    ("LOW", 2),
])
def test_severity_score(severity: str, expected: int):
    assert calculate_score(severity) == expected
```

---

## Summary Table

| Aspecto | Moderno (✅) | Legacy (❌) |
|---------|-------------|------------|
| Type hints | `list[str]`, `X \| None` | `List[str]`, `Optional[X]` |
| Pydantic | `ConfigDict`, `@field_validator` | `class Config`, `@validator` |
| HTTP | `httpx` async | `requests` sync |
| Logging | `structlog` | `print()` |
| Paths | `pathlib.Path` | `os.path` |
| Strings | f-strings | `.format()`, `%` |
