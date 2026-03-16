---
name: coding-standards-2026
description: "Python 2026 coding standards: modern type hints, Pydantic v2, httpx, structlog, pathlib. USE WHEN writing or reviewing Python code."
user-invocable: false
---

# Python Coding Standards 2026

Modern Python standards enforced in SIOPV. Focus on what's PROHIBITED — Claude knows the correct patterns natively.

## When to use

Check these standards when writing or reviewing any Python code in SIOPV. Pay special
attention to the PROHIBITED patterns below.

## Quick checklist

1. **Type hints:** Use `list[str]`, `dict[str, int]`, `X | None` — NEVER `from typing import List, Dict, Optional`
2. **Pydantic v2:** Use `model_config = ConfigDict(...)` + `@field_validator` + `@classmethod` — NEVER `class Config:` or `@validator`
3. **HTTP client:** Use `httpx.AsyncClient` with explicit `Timeout(connect, read, write, pool)` — NEVER `import requests`
4. **Logging:** Use `structlog.get_logger(__name__)` with structured key=value — NEVER `print()` or `logging.getLogger()`
5. **Paths:** Use `pathlib.Path` and `/` operator — NEVER `os.path.join()` or `os.path.exists()`
6. **Strings:** Use f-strings — NEVER `.format()` or `%` formatting
7. **Async:** Use `await` for ALL I/O operations — sync I/O is prohibited in the pipeline
8. **DTOs:** Use `@dataclass` for simple data holders, `BaseModel` for validated domain objects

## PROHIBITED imports (auto-fail in review)

```
from typing import List, Dict, Optional, Tuple, Union  # Use builtins
import requests                                          # Use httpx
import os.path                                           # Use pathlib
```

## Full reference

For complete code examples with ✅ correct and ❌ prohibited patterns (type hints, Pydantic v2,
async/await, structlog, pathlib, dataclasses, error handling, context managers),
see [coding-standards-2026-reference.md](coding-standards-2026-reference.md).
