# Hallucination Check Report — Remediation-Hardening Final
**Agent:** hallucination-detector
**Date:** 2026-03-16
**Scope:** Remediation-hardening outputs (Phase 6 + infrastructure DI)

---

## Hallucination Check Results

### ✅ VERIFIED USAGE

#### Python stdlib (functools, asyncio, typing, enum)

1. **`functools.lru_cache`** (import) — `authorization.py` line 34
   Correct import from `functools`. The decorator itself exists and is valid. (See critical issue below on usage with unhashable arguments.)

2. **`asyncio.get_running_loop()`** — `haiku_validator.py` line 83, `dual_layer_adapter.py` line 103
   Correct API. Returns the running event loop. Available since Python 3.7.

3. **`loop.run_in_executor(None, functools.partial(...))`** — both DLP adapters
   Correct usage pattern. First argument `None` uses the default thread pool executor. `functools.partial` correctly wraps the synchronous `messages.create` call.

4. **`functools.partial`** — `haiku_validator.py`, `dual_layer_adapter.py`
   Correct. Keyword arguments passed via `functools.partial` for `model`, `max_tokens`, `messages`, and `system` are all valid `messages.create` parameters.

5. **`types.ModuleType`** — `discrepancy.py` line 14
   Correct stdlib import and usage as a return type annotation.

6. **`from typing import Protocol, runtime_checkable, TYPE_CHECKING, Literal, Annotated`** — across ports and CLI
   All correct typing constructs.

7. **`Path.mkdir(parents=True, exist_ok=True)`** — `main.py` line 88
   Correct stdlib API.

8. **`Path.write_text(...)`** — `main.py` line 125
   Correct stdlib API.

9. **`csv.DictReader`** — `main.py`
   Correct stdlib usage. `reader.fieldnames` is `list[str] | None` — the `is None` guard is correct.

#### structlog 24.x API

10. **`structlog.processors.ExceptionRenderer()`** — `setup.py` line 46
    VERIFIED against installed library (structlog 24.x). `ExceptionRenderer` exists in `structlog.processors`. Correct usage in JSON path only (comment correctly notes ConsoleRenderer handles exceptions natively).

11. **`structlog.processors.UnicodeDecoder()`** — `setup.py` line 31
    VERIFIED. Exists in `structlog.processors`.

12. **`structlog.processors.CallsiteParameterAdder({...})`** — `setup.py` lines 32–38
    VERIFIED. Accepts a set of `CallsiteParameter` enum values. `FILENAME`, `FUNC_NAME`, `LINENO` are all valid `CallsiteParameter` members.

13. **`structlog.processors.TimeStamper(fmt="iso")`** — `setup.py` line 29
    VERIFIED. Correct constructor and `fmt` parameter.

14. **`structlog.processors.StackInfoRenderer()`** — `setup.py` line 30
    VERIFIED. Exists and callable.

15. **`structlog.processors.JSONRenderer()`** — `setup.py` line 43
    VERIFIED. Exists in `structlog.processors`.

16. **`structlog.stdlib.filter_by_level`** — `setup.py` line 25
    VERIFIED. Correct (note: function reference, not called).

17. **`structlog.stdlib.add_logger_name`** — `setup.py` line 26
    VERIFIED.

18. **`structlog.stdlib.add_log_level`** — `setup.py` line 27
    VERIFIED.

19. **`structlog.stdlib.PositionalArgumentsFormatter()`** — `setup.py` line 28
    VERIFIED.

20. **`structlog.stdlib.BoundLogger`** — `setup.py` lines 62, 87
    VERIFIED. Valid class in `structlog.stdlib`.

21. **`structlog.stdlib.LoggerFactory()`** — `setup.py` line 63
    VERIFIED.

22. **`structlog.stdlib.ProcessorFormatter`** — `setup.py` lines 45, 53, 60, 68
    VERIFIED. Class exists.

23. **`structlog.stdlib.ProcessorFormatter.remove_processors_meta`** — `setup.py` lines 45, 53
    VERIFIED against installed library. Static method/callable exists on `ProcessorFormatter`.

24. **`structlog.stdlib.ProcessorFormatter.wrap_for_formatter`** — `setup.py` line 60
    VERIFIED. Exists on `ProcessorFormatter`.

25. **`structlog.dev.ConsoleRenderer(colors=True)`** — `setup.py` line 51
    VERIFIED. Correct class and parameter.

26. **`structlog.configure(...)`** — `setup.py` lines 57–64
    VERIFIED. All keyword arguments (`processors`, `wrapper_class`, `logger_factory`, `cache_logger_on_first_use`) are correct for structlog 24.x.

27. **`structlog.get_logger(__name__)`** — all adapter files
    VERIFIED. Correct API.

#### anthropic SDK

28. **`anthropic.Anthropic(api_key=api_key)`** — `_haiku_utils.py` line 14
    VERIFIED. Constructor accepts `api_key` as keyword argument.

29. **`anthropic.types.Message`** — `_haiku_utils.py` line 6
    VERIFIED. Type exists in `anthropic.types`.

30. **`anthropic.types.TextBlock`** — `_haiku_utils.py` line 6, test files
    VERIFIED. Type exists in `anthropic.types`.

31. **`client.messages.create(model=..., max_tokens=..., messages=[...], system=...)`** — `haiku_validator.py` line 87–91, `dual_layer_adapter.py` lines 108–113
    VERIFIED. All parameters are valid:
    - `model: ModelParam` ✓
    - `max_tokens: int` ✓ (required)
    - `messages: Iterable[MessageParam]` ✓
    - `system: str | Iterable[TextBlockParam]` ✓ (used only in `dual_layer_adapter.py`)

    Note: All required parameters (`model`, `max_tokens`, `messages`) are provided in both call sites.

32. **`response.content` iteration with `isinstance(b, TextBlock)` guard** — `_haiku_utils.py` line 27
    VERIFIED. The `Message.content` field is a list that may contain `TextBlock` and other block types; the `isinstance` guard is correct API usage.

#### pytest patterns

33. **`@pytest.mark.asyncio`** — all async test methods
    VERIFIED. Standard pytest-asyncio decorator.

34. **`pytest.raises(ExceptionClass, match="...")`** — `test_presidio_adapter.py`
    VERIFIED. Correct context manager usage with `match` parameter.

35. **`pytest.MonkeyPatch`** — `test_dual_layer_adapter.py` line 302
    VERIFIED. Standard pytest fixture type annotation.

36. **`MagicMock(spec=TextBlock)`** — test files
    VERIFIED. `unittest.mock.MagicMock` with `spec=` is correct.

37. **`AsyncMock`, `MagicMock`, `patch`** — all test files
    VERIFIED. All from `unittest.mock`, correct standard library.

#### typer CLI

38. **`typer.Typer(name=..., help=..., no_args_is_help=True)`** — `main.py` line 18
    VERIFIED. All parameters are valid typer constructor arguments.

39. **`typer.Option(...)`, `typer.Argument(exists=..., readable=...)`** — `main.py`
    VERIFIED. Standard typer parameter declarations.

40. **`typer.Exit(code=1)`** — `main.py`
    VERIFIED. Correct exception to raise for CLI exit.

41. **`typer.echo(..., err=True)`** — `main.py`
    VERIFIED. `err=True` writes to stderr.

---

### ⚠️ HALLUCINATED / INCORRECT USAGE

#### CRITICAL: `@lru_cache(maxsize=1)` applied to functions with `Settings` parameter

**Files affected:**
- `src/siopv/infrastructure/di/authorization.py` — lines 52, 106, 141, 180
- `src/siopv/infrastructure/di/dlp.py` — lines 55, 104 (also checked, same issue)
- `src/siopv/infrastructure/di/authentication.py` — line 100 (same pattern)

**What the code does:**
```python
@lru_cache(maxsize=1)
def create_authorization_adapter(settings: Settings) -> OpenFGAAdapter:
    ...

@lru_cache(maxsize=1)
def get_authorization_port(settings: Settings) -> AuthorizationPort:
    ...
```

**Why this fails:**
`functools.lru_cache` requires all function arguments to be hashable (it uses them as cache keys in a dict). `Settings` is a Pydantic `BaseSettings` / `BaseModel` subclass. Pydantic v2 explicitly sets `__hash__ = None` on all `BaseModel` subclasses (making them unhashable), because they implement `__eq__` without `__hash__`.

**Confirmed runtime failure:**
```
TypeError: unhashable type: 'Settings'
```
This was verified by running the actual code path:
```python
from siopv.infrastructure.config.settings import get_settings
from siopv.infrastructure.di.authorization import get_authorization_port
settings = get_settings()
port = get_authorization_port(settings)  # → TypeError: unhashable type: 'Settings'
```
Same failure confirmed for `get_dual_layer_dlp_port(settings)` in `di/dlp.py`.

**Impact:** Any call to the DI factory functions with a real `Settings` instance raises `TypeError` at runtime. The CLI `process_report` command would immediately fail. This is a critical runtime defect masked by tests using `MagicMock(spec=Settings)` (mocks are hashable).

**Correct alternative:** Use a module-level singleton pattern, or cache the result using the `get_settings()` singleton as the indirection (no argument passed to cached function):
```python
@lru_cache(maxsize=1)
def _create_authorization_adapter_cached() -> OpenFGAAdapter:
    return OpenFGAAdapter(get_settings())
```

---

## Summary

| Category | Count |
|----------|-------|
| Total library API usages checked | 41 |
| VERIFIED (correct API usage) | 40 |
| HALLUCINATED / INCORRECT | 1 (critical — affects 8+ function definitions across 3 files) |

### Usages Checked by Library
- Python stdlib (functools, asyncio, typing, csv, pathlib, types): 9 usages — 8 VERIFIED, 1 FAILED
- structlog 24.x: 18 usages — 18 VERIFIED
- anthropic SDK: 5 usages — 5 VERIFIED
- pytest/unittest.mock: 5 usages — 5 VERIFIED
- typer: 4 usages — 4 VERIFIED

---

## Verdict

**FAIL**

One category of incorrect API usage was found and confirmed with runtime execution:

`@lru_cache(maxsize=1)` applied to functions that accept `Settings` (a Pydantic `BaseModel` subclass) as an argument causes `TypeError: unhashable type: 'Settings'` at runtime in all three DI modules (`di/authorization.py`, `di/dlp.py`, `di/authentication.py`). This is a real runtime defect, not a style issue. The defect is masked in unit tests because `MagicMock` objects are hashable.

All other library usages (structlog 24.x processors, anthropic SDK, asyncio, pytest patterns, typer) are correctly applied against their documented APIs.

**Recommended fix:** Remove `settings` parameter from the `lru_cache`-decorated functions and instead call `get_settings()` internally, or use a module-level singleton variable initialized at import time.
