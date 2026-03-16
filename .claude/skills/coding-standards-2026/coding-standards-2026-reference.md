# Python 2026 Coding Standards — Reference

> Extracted from SKILL.md. Full code examples with correct/prohibited patterns.

---

## Type Hints Modernos (Python 3.11+)

```python
# ✅ CORRECTO - Sintaxis moderna
def process_items(items: list[str]) -> dict[str, int]:
    return {item: len(item) for item in items}

def get_user(user_id: int) -> User | None:
    return db.get(user_id)

def fetch_data(url: str, timeout: float = 30.0) -> tuple[bytes, int]:
    ...

# ❌ PROHIBIDO - Sintaxis legacy
from typing import List, Dict, Optional, Tuple, Union

def process_items(items: List[str]) -> Dict[str, int]:  # NO
def get_user(user_id: int) -> Optional[User]:  # NO
def fetch_data(url: str) -> Tuple[bytes, int]:  # NO
```

---

## Pydantic v2 Patterns

```python
# ✅ CORRECTO - Pydantic v2
from pydantic import BaseModel, ConfigDict, field_validator

class Vulnerability(BaseModel):
    model_config = ConfigDict(
        strict=True,
        frozen=True,
        str_strip_whitespace=True,
    )

    cve_id: str
    severity: str
    score: float | None = None

    @field_validator("cve_id")
    @classmethod
    def validate_cve_format(cls, v: str) -> str:
        if not v.startswith("CVE-"):
            raise ValueError("CVE ID must start with 'CVE-'")
        return v

# ❌ PROHIBIDO - Pydantic v1
class Vulnerability(BaseModel):
    class Config:  # NO - usar model_config
        frozen = True

    @validator("cve_id")  # NO - usar @field_validator
    def validate_cve_format(cls, v):
        ...
```

---

## Async/Await para I/O

```python
# ✅ CORRECTO - httpx async
import httpx

async def fetch_cve(cve_id: str) -> dict:
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0)
    ) as client:
        response = await client.get(
            f"https://services.nvd.nist.gov/rest/json/cves/2.0",
            params={"cveId": cve_id}
        )
        response.raise_for_status()
        return response.json()

# ❌ PROHIBIDO - requests sync
import requests  # NO

def fetch_cve(cve_id: str) -> dict:  # NO - debe ser async
    response = requests.get(...)  # NO - usar httpx
```

---

## Logging con structlog

```python
# ✅ CORRECTO - structlog
import structlog

logger = structlog.get_logger(__name__)

async def process_vulnerability(cve_id: str) -> None:
    logger.info("processing_vulnerability", cve_id=cve_id)
    try:
        result = await fetch_data(cve_id)
        logger.info("vulnerability_processed", cve_id=cve_id, result=result)
    except Exception as e:
        logger.error("vulnerability_processing_failed", cve_id=cve_id, error=str(e))
        raise

# ❌ PROHIBIDO - print
print(f"Processing {cve_id}")  # NO
print(f"Error: {e}")  # NO
```

---

## Paths con pathlib

```python
# ✅ CORRECTO - pathlib
from pathlib import Path

def load_config(config_dir: Path) -> dict:
    config_file = config_dir / "settings.json"
    if not config_file.exists():
        raise FileNotFoundError(f"Config not found: {config_file}")
    return json.loads(config_file.read_text())

# ❌ PROHIBIDO - os.path
import os  # NO para paths

config_file = os.path.join(config_dir, "settings.json")  # NO
if not os.path.exists(config_file):  # NO
```

---

## Dataclasses para DTOs simples

```python
# ✅ CORRECTO - dataclass para datos simples
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class ScanResult:
    cve_id: str
    severity: str
    detected_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def is_critical(self) -> bool:
        return self.severity == "CRITICAL"
```

---

## Error Handling Moderno

```python
# ✅ CORRECTO - excepciones tipadas
class VulnerabilityNotFoundError(Exception):
    def __init__(self, cve_id: str) -> None:
        self.cve_id = cve_id
        super().__init__(f"Vulnerability not found: {cve_id}")

async def get_vulnerability(cve_id: str) -> Vulnerability:
    result = await fetch_cve(cve_id)
    if not result:
        raise VulnerabilityNotFoundError(cve_id)
    return Vulnerability(**result)
```

---

## Context Managers Async

```python
# ✅ CORRECTO - async context manager
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

@asynccontextmanager
async def get_db_connection() -> AsyncGenerator[Connection, None]:
    conn = await create_connection()
    try:
        yield conn
    finally:
        await conn.close()

# Uso
async with get_db_connection() as conn:
    await conn.execute(query)
```
