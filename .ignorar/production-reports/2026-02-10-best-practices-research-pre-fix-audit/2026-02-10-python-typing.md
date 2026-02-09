# Python 3.11+ Type Hints Best Practices - February 2026

**Research Date:** 2026-02-10
**Agent:** best-practices-researcher
**Scope:** Modern Python 3.11+ typing conventions, mypy strict mode compatibility

---

## Executive Summary

Python 3.11+ requires a shift from legacy `typing` module imports to native builtin generics and union operators. Key changes:
- **PEP 585 (Python 3.9+):** Use `list[str]` instead of `typing.List[str]`
- **PEP 604 (Python 3.10+):** Use `X | None` instead of `typing.Optional[X]`
- **PEP 695 (Python 3.12+):** Use `type` statement for type aliases

**Deprecated imports:** `List`, `Dict`, `Tuple`, `Set`, `Optional`, `Union` from `typing` module should be replaced with native syntax.

---

## 1. Modern Type Hint Syntax (Python 3.11+)

### PEP 585: Builtin Generics (since Python 3.9)

**Old (deprecated):**
```python
from typing import List, Dict, Tuple, Set

def process(items: List[str]) -> Dict[str, int]:
    pass
```

**New (correct):**
```python
def process(items: list[str]) -> dict[str, int]:
    pass
```

**Builtin generics available:**
- `list[T]` instead of `typing.List[T]`
- `dict[K, V]` instead of `typing.Dict[K, V]`
- `tuple[T, ...]` instead of `typing.Tuple[T, ...]`
- `set[T]` instead of `typing.Set[T]`
- `frozenset[T]` instead of `typing.FrozenSet[T]`

**Deprecation timeline:**
- Deprecated since Python 3.9
- Will be removed in Python 3.14+ (October 2025 EOL for Python 3.9)
- Type checkers may warn when target version is 3.9+

**Source:** [PEP 585](https://peps.python.org/pep-0585/)

---

### PEP 604: Union Types (since Python 3.10)

**Old (deprecated):**
```python
from typing import Optional, Union

def authenticate(user: str, token: Optional[str]) -> Union[User, Error]:
    pass
```

**New (correct):**
```python
def authenticate(user: str, token: str | None) -> User | Error:
    pass
```

**Union operator rules:**
- `X | Y` equivalent to `Union[X, Y]`
- `X | None` equivalent to `Optional[X]`
- Can be used in `isinstance()` and `issubclass()`: `isinstance(5, int | str)`
- More concise and readable than legacy syntax

**Source:** [PEP 604](https://peps.python.org/pep-0604/)

---

### PEP 695: Type Statement for Aliases (since Python 3.12)

**Old:**
```python
from typing import TypeAlias

Vector: TypeAlias = list[tuple[float, float]]
```

**New (Python 3.12+):**
```python
type Vector = list[tuple[float, float]]
type GenericVector[T: float] = list[tuple[T, T]]
```

**Benefits:**
- Soft keyword `type` introduces cleaner syntax
- Native support for forward references
- Type parameter syntax `[T]` built into statement
- Runtime accessible via `typing.TypeAliasType`

**Note:** `TypeAlias` is deprecated in favor of `type` statement for Python 3.12+

**Source:** [PEP 695](https://peps.python.org/pep-0695/)

---

## 2. Deprecated Typing Imports (DO NOT USE)

| Deprecated Import | Modern Replacement | Since Python |
|-------------------|-------------------|--------------|
| `typing.List[X]` | `list[X]` | 3.9 |
| `typing.Dict[K, V]` | `dict[K, V]` | 3.9 |
| `typing.Tuple[X, Y]` | `tuple[X, Y]` | 3.9 |
| `typing.Set[X]` | `set[X]` | 3.9 |
| `typing.FrozenSet[X]` | `frozenset[X]` | 3.9 |
| `typing.Optional[X]` | `X \| None` | 3.10 |
| `typing.Union[X, Y]` | `X \| Y` | 3.10 |
| `typing.Callable[[X], Y]` | `collections.abc.Callable[[X], Y]` | 3.9 |
| `typing.TypeAlias` | `type` statement | 3.12 |

**Fully deprecated (removed soon):**
- `typing.AnyStr` - deprecated 3.13, removed in 3.18

**Sources:**
- [Deprecated typing constructs](https://docs.python.org/3/library/typing.html)
- [Historical and deprecated features](https://typing.python.org/en/latest/spec/historical.html)
- [Modernizing typing features](https://typing.python.org/en/latest/guides/modernizing.html)

---

## 3. Function Return Types & Parameters

### Required patterns for mypy strict mode:

**Parameter type hints:**
```python
# CORRECT: All params typed
def validate(data: dict[str, Any], strict: bool = False) -> ValidationResult:
    pass

# WRONG: Missing type hints (fails --disallow-untyped-defs)
def validate(data, strict=False):
    pass
```

**Return type hints:**
```python
# CORRECT: Explicit return type
def fetch_user(user_id: int) -> User | None:
    if user := db.get(user_id):
        return user
    return None

# WRONG: Missing return type (fails --disallow-untyped-defs)
def fetch_user(user_id: int):
    return db.get(user_id)
```

**Generator return types:**
```python
from collections.abc import Iterator

# CORRECT: Use collections.abc.Iterator
def get_items() -> Iterator[str]:
    yield from ["a", "b", "c"]

# WRONG: Using deprecated typing.Iterator
from typing import Iterator  # Deprecated
```

**Callable type hints:**
```python
from collections.abc import Callable

# CORRECT: Use collections.abc.Callable
def apply(func: Callable[[int], str], value: int) -> str:
    return func(value)

# WRONG: Using deprecated typing.Callable
from typing import Callable  # Deprecated
```

---

## 4. MyPy Strict Mode Requirements

### Strict mode flags (enabled with `--strict`):

```ini
[tool.mypy]
strict = true  # Enables all flags below

# Individual flags:
warn_unused_configs = true
disallow_any_generics = true
disallow_subclassing_any = true
disallow_untyped_calls = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_return_any = true
no_implicit_reexport = true
strict_equality = true
```

### Common strict mode gotchas:

**1. `disallow_any_generics` requires explicit type params:**
```python
# WRONG: Generic types without params
items = []  # Error: Need type annotation

# CORRECT: Explicit type param
items: list[str] = []
```

**2. `disallow_untyped_defs` requires all function signatures:**
```python
# WRONG: Missing return type
def process(data: dict[str, Any]):
    return data["result"]

# CORRECT: Explicit return type
def process(data: dict[str, Any]) -> Any:
    return data["result"]
```

**3. `no_implicit_optional` forbids `None` defaults without `| None`:**
```python
# WRONG: None default without | None type
def connect(timeout: int = None):  # Error
    pass

# CORRECT: Explicit | None
def connect(timeout: int | None = None) -> None:
    pass
```

**4. `warn_return_any` flags functions returning `Any`:**
```python
# WARNING: Returns Any (untyped dict access)
def get_value(data: dict[str, Any]) -> Any:
    return data["key"]

# BETTER: Use TypedDict or Pydantic model
from pydantic import BaseModel

class Config(BaseModel):
    key: str

def get_value(data: Config) -> str:
    return data.key
```

**Source:** [mypy documentation](https://mypy.readthedocs.io/)

---

## 5. Migration Checklist

### Step 1: Update builtin generics (PEP 585)
- [ ] Replace `List[X]` → `list[X]`
- [ ] Replace `Dict[K, V]` → `dict[K, V]`
- [ ] Replace `Tuple[X, Y]` → `tuple[X, Y]`
- [ ] Replace `Set[X]` → `set[X]`
- [ ] Remove `from typing import List, Dict, Tuple, Set`

### Step 2: Update union types (PEP 604)
- [ ] Replace `Optional[X]` → `X | None`
- [ ] Replace `Union[X, Y]` → `X | Y`
- [ ] Remove `from typing import Optional, Union`

### Step 3: Update collections.abc imports
- [ ] Replace `typing.Callable` → `collections.abc.Callable`
- [ ] Replace `typing.Iterator` → `collections.abc.Iterator`
- [ ] Replace `typing.Iterable` → `collections.abc.Iterable`

### Step 4: Fix mypy strict mode violations
- [ ] Add return type hints to all functions
- [ ] Add parameter type hints to all functions
- [ ] Replace `None` defaults with `X | None` type hints
- [ ] Replace `Any` returns with specific types (or use Pydantic)

### Step 5: Automated tooling
```bash
# Use ruff to auto-fix deprecated imports
ruff check --select UP --fix src/

# UP007: Use X | Y for unions (replaces Union)
# UP006: Use list[X] (replaces List)
# UP040: Use type statement (replaces TypeAlias)
```

**Source:** [Ruff UP rules](https://docs.astral.sh/ruff/rules/non-pep604-annotation-union/)

---

## 6. Summary Table: Legacy vs Modern

| Pattern | Legacy (Deprecated) | Modern (Python 3.11+) |
|---------|---------------------|----------------------|
| Optional param | `def f(x: Optional[int])` | `def f(x: int \| None)` |
| Union return | `def f() -> Union[X, Y]` | `def f() -> X \| Y` |
| List param | `def f(items: List[str])` | `def f(items: list[str])` |
| Dict return | `def f() -> Dict[str, int]` | `def f() -> dict[str, int]` |
| Tuple return | `def f() -> Tuple[int, str]` | `def f() -> tuple[int, str]` |
| Callable param | `Callable[[int], str]` | `collections.abc.Callable[[int], str]` |
| Type alias | `X: TypeAlias = list[int]` | `type X = list[int]` (3.12+) |

---

## Sources

- [PEP 604 – Allow writing union types as X | Y](https://peps.python.org/pep-0604/)
- [PEP 585 – Type Hinting Generics In Standard Collections](https://peps.python.org/pep-0585/)
- [PEP 695 – Type Parameter Syntax](https://peps.python.org/pep-0695/)
- [typing module documentation](https://docs.python.org/3/library/typing.html)
- [Historical and deprecated features](https://typing.python.org/en/latest/spec/historical.html)
- [Modernizing Superseded Typing Features](https://typing.python.org/en/latest/guides/modernizing.html)
- [mypy documentation](https://mypy.readthedocs.io/)
- [Ruff non-pep604-annotation-union](https://docs.astral.sh/ruff/rules/non-pep604-annotation-union/)
- [Medium: "typing" Module Deprecated in Python](https://medium.com/@anuraagkhare_/typing-module-deprecated-in-python-what-you-need-to-know-d4348b694141)
- [Medium: Python Typing in 2025](https://khaled-jallouli.medium.com/python-typing-in-2025-a-comprehensive-guide-d61b4f562b99)
