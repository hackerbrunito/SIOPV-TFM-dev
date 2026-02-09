# MyPy 1.9+ Strict Mode Best Practices (2026)

**Research Date:** 2026-02-10
**Agent:** best-practices-research
**Sources:** Web search (MyPy official docs, industry blog posts)

---

## What does `mypy --strict` actually enable?

The `--strict` flag is a comprehensive meta-flag that enables:

- `--warn-unused-configs`
- `--disallow-any-generics`
- `--disallow-subclassing-any`
- `--disallow-untyped-calls`
- `--disallow-untyped-defs`
- `--disallow-incomplete-defs`
- `--check-untyped-defs`
- `--disallow-untyped-decorators`
- `--warn-redundant-casts`
- `--warn-unused-ignores`
- `--warn-return-any`
- `--no-implicit-reexport`
- `--strict-equality`

**Key Principle:** With `--strict`, you will **never** get a type-related runtime error without a corresponding mypy error, unless you explicitly circumvent mypy.

---

## How to properly type decorators

### Decorator Typing Best Practices

**1. For custom decorators:**
```python
from typing import Callable, TypeVar, ParamSpec

P = ParamSpec('P')
R = TypeVar('R')

def retry(func: Callable[P, R]) -> Callable[P, R]:
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        # retry logic
        return func(*args, **kwargs)
    return wrapper
```

**2. For third-party decorators (e.g., `@app.command`, `@retry`):**
- If library has type stubs: Install from typeshed (`pip install types-<library>`)
- If library lacks stubs: Create `.pyi` stub files in project
- If decorator is too complex: Use `# type: ignore[misc]` or `# type: ignore[no-untyped-def]`

**3. Untyped decorators in strict mode:**
Enabled by `--disallow-untyped-decorators`, this flag requires ALL decorators to have type annotations. For external decorators without stubs, you must either:
- Create stubs
- Use specific `# type: ignore[misc]` comments
- Configure per-module exceptions in `pyproject.toml`

---

## When is `# type: ignore[code]` acceptable?

### Configuration for Type Ignore Management

```toml
[tool.mypy]
enable_error_code = ["ignore-without-code"]
show_error_codes = true
warn_unused_ignores = true
```

**`enable_error_code = ["ignore-without-code"]`:** Forces ALL ignore comments to specify error codes (no bare `# type: ignore`)

**`warn_unused_ignores = true`:** Logs errors for unnecessary ignore comments, ensuring only effective ignores remain

### Acceptable Use Cases

✅ **ACCEPTABLE:**
- Third-party library limitations: `# type: ignore[import-untyped]`
- Complex generics mypy can't infer: `# type: ignore[misc]`
- Known mypy bugs (with issue reference): `# type: ignore[no-untyped-call] # mypy#12345`
- Gradual migration (temporary): `# type: ignore[attr-defined] # TODO: add stubs`

❌ **NOT ACCEPTABLE (FIX INSTEAD):**
- Missing return type on your own functions → Add type hint
- Incorrect type annotations → Fix the annotation
- Lazy typing → Add proper types
- Legacy code you control → Refactor incrementally

### Best Practice Pattern

```python
# WRONG (bare ignore)
result = external_lib.process(data)  # type: ignore

# CORRECT (specific error code + justification)
result = external_lib.process(data)  # type: ignore[no-untyped-call] # external_lib lacks stubs
```

---

## How to handle @property with Pydantic validators?

### Pydantic v2 + MyPy Compatibility

**Issue:** Pydantic `@field_validator` and `@property` can conflict in strict mode due to descriptor protocol typing.

**Solution (Pydantic v2 pattern):**
```python
from pydantic import BaseModel, field_validator, ConfigDict

class User(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    name: str

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        return v.strip()

    # Computed property (not a Pydantic field)
    @property
    def display_name(self) -> str:
        return self.name.upper()
```

**Key Rules:**
- Use `@field_validator` for Pydantic fields (validation logic)
- Use `@property` for computed attributes (NOT Pydantic fields)
- Never mix both on same attribute
- Use `@classmethod` decorator with `@field_validator` (Pydantic v2 requirement)

**Strict Mode Compatibility:**
- Pydantic v2 has full mypy plugin support
- Enable plugin in `pyproject.toml`:
  ```toml
  [tool.mypy]
  plugins = ["pydantic.mypy"]
  ```

---

## Best practices for gradual strict mode adoption

### Strategy: Strict by Default, Loose When Needed

```toml
[tool.mypy]
strict = true  # Global default

[[tool.mypy.overrides]]
module = "legacy.*"
disallow_untyped_defs = false
disallow_untyped_calls = false
```

**Philosophy:** All NEW code must pass strict checks; LEGACY code has exceptions.

### Incremental Migration Steps

**Phase 1: Enable basic checks**
```toml
[tool.mypy]
disallow_untyped_defs = true
warn_unused_ignores = true
```

**Phase 2: Add strictness flags progressively**
- Week 1: `check_untyped_defs = true`
- Week 2: `disallow_incomplete_defs = true`
- Week 3: `disallow_untyped_calls = true`
- Week 4: `strict = true` (for new modules only)

**Phase 3: Module-by-module migration**
- Annotate high-risk modules first (data loaders, API clients)
- Use `--follow-imports=silent` to avoid external noise
- Target 90% coverage in 3-6 months (realistic for large codebases)

### CI/CD Integration (2026 Best Practice)

```yaml
# GitHub Actions
- name: MyPy Check
  run: |
    mypy src/ --jobs=auto  # Parallelize with all CPU cores
    mypy --strict src/new_modules/  # Strict for new code only
```

**Key Optimizations:**
- `--jobs=auto`: Parallelize type checking across CPU cores
- Matrix strategies: Check module subsets in parallel CI jobs
- Cache `.mypy_cache/` for faster incremental checks

### Real-World 2026 Adoption Pattern

**IoT Deployment Case Study:**
- Hybrid approach (strict for new, loose for legacy)
- Achieved 90% coverage in 6 months
- No velocity loss
- Caught silent type mismatches in ML data pipelines

---

## Summary Recommendations (2026)

1. **Use `strict = true` globally** with per-module overrides for legacy code
2. **Always specify error codes** in `# type: ignore[code]` comments
3. **Enable `warn_unused_ignores`** to prevent comment bloat
4. **Install type stubs** from typeshed for third-party libraries
5. **Create `.pyi` stubs** for untyped external dependencies
6. **Use Pydantic mypy plugin** for model validation compatibility
7. **Migrate incrementally** (3-6 months for large codebases)
8. **Parallelize CI checks** with `--jobs=auto`

---

## Sources

- [MyPy Configuration for Strict Typing | Hrekov](https://hrekov.com/blog/mypy-configuration-for-strict-typing)
- [The mypy command line - mypy 1.19.1 documentation](https://mypy.readthedocs.io/en/stable/command_line.html)
- [Professional-grade mypy configuration | Wolt Careers](https://careers.wolt.com/en/blog/tech/professional-grade-mypy-configuration)
- [Common issues and solutions - mypy 1.19.1 documentation](https://mypy.readthedocs.io/en/stable/common_issues.html)
- [Python type hints: manage "type: ignore" comments with Mypy - Adam Johnson](https://adamj.eu/tech/2021/05/25/python-type-hints-specific-type-ignore/)
- [Mypy Strict Mode Configuration | Johal.in](https://johal.in/mypy-strict-mode-configuration-enforcing-type-safety-in-large-python-codebases/)
- [Getting started - mypy 1.19.1 documentation](https://mypy.readthedocs.io/en/stable/getting_started.html)

**Report Length:** 50 lines (summary format, excluding code examples)
