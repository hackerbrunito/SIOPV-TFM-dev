# Ruff 0.4+ Configuration Best Practices (2026)

**Date:** 2026-02-10
**Researcher:** best-practices-research agent
**Context:** Research for ML code linting configuration

---

## 1. Per-File-Ignores Configuration

**Modern syntax (Ruff 0.4+):**
```toml
[tool.ruff.lint.per-file-ignores]
"__init__.py" = ["F401", "E402"]
"tests/*.py" = ["D"]
"ml/models/*.py" = ["N803", "N806"]  # ML naming exceptions
```

**Legacy syntax (still supported):**
```toml
[tool.ruff]
per-file-ignores = { "__init__.py" = ["F401"], "tests/*.py" = ["D"] }
```

**Best Practice:** Use the modern `[tool.ruff.lint.per-file-ignores]` section for clarity.

**Source:** [Configuring Ruff | Ruff](https://docs.astral.sh/ruff/configuration/), [Settings | Ruff](https://docs.astral.sh/ruff/settings/)

---

## 2. ISC001 vs Formatter Conflict Resolution

**The Issue:** ISC001 (single-line-implicit-string-concatenation) was historically incompatible with `ruff format` because:
- Formatter would collapse implicit concatenations onto single lines
- ISC001 would flag those single-line concatenations
- Created non-reversible formatting cycles

**2026 Resolution:** As of recent updates (PR #15123), the formatter incompatibility warning was **removed** because:
- Formatter now tries to join implicit concatenated strings that fit on a single line
- Preserves multi-line implicit concatenations where auto-joining isn't supported

**Recommendation:** As of 2026, ISC001 and `ruff format` can coexist. If using older Ruff versions (<0.5), consider ignoring ISC001.

**Sources:**
- [Consider removing ISC001 from conflict list](https://github.com/astral-sh/ruff/issues/8272)
- [Remove formatter incompatibility warning (PR #15123)](https://github.com/astral-sh/ruff/pull/15123)
- [Implicit concatenated string formatting](https://github.com/astral-sh/ruff/issues/9457)

---

## 3. N803/N806 in ML Code (Uppercase Variable Exceptions)

**The Problem:** ML/data science code uses uppercase letters for matrices (X, Y) per mathematical convention, but PEP 8 (N803/N806) requires lowercase.

**Common violations:**
- N803: `Argument name X should be lowercase`
- N806: Non-lowercase variable in function

**Best Practice for ML Projects:**

**Option 1: Per-file ignores (recommended)**
```toml
[tool.ruff.lint.per-file-ignores]
"ml/**/*.py" = ["N803", "N806"]
"models/**/*.py" = ["N803", "N806"]
```

**Option 2: Global ignore (if entire project is ML-focused)**
```toml
[tool.ruff.lint]
ignore = ["N803", "N806"]
```

**Option 3: Selective # noqa comments**
```python
def fit(X, y):  # noqa: N803
    pass
```

**Precedent:** LSST DM project ignores N802, N803, N806 for scientific code.

**Sources:**
- [Allowed capitalized arg names for N803](https://github.com/astral-sh/ruff/issues/11090)
- [N806 non-lowercase-variable-in-function](https://docs.astral.sh/ruff/rules/non-lowercase-variable-in-function/)
- [DM Python Style Guide (scientific conventions)](https://developer.lsst.io/python/style.html)

---

## 4. PLR2004 Magic Value Extraction

**What it checks:** Unnamed numerical constants in comparisons (e.g., `if status == 200`).

**When to extract:**
- Non-obvious domain values (e.g., `if threshold == 0.73`)
- Repeated values across codebase
- Business logic constants

**When to ignore:**
- Well-known constants: HTTP status codes (200, 404), common math (0, 1, -1)
- Bytes conversion (1024 for KiB/MiB)
- Array indices and slicing

**Handling strategies:**

**1. Extract to named constant:**
```python
PREDICTION_THRESHOLD = 0.73
if score > PREDICTION_THRESHOLD:
```

**2. Use # noqa for obvious values:**
```python
if status_code == 200:  # noqa: PLR2004
```

**3. Disable for specific files:**
```toml
[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = ["PLR2004"]  # Test assertions often use literals
```

**Limitation:** Ruff lacks Pylint's `valid-magic-values` config (open issue #6256).

**Sources:**
- [magic-value-comparison (PLR2004)](https://docs.astral.sh/ruff/rules/magic-value-comparison/)
- [Allow common numbers for PLR2004](https://github.com/astral-sh/ruff/issues/15902)
- [Implement valid-magic-values setting](https://github.com/astral-sh/ruff/issues/6256)

---

## 5. ARG002 Unused Method Arguments

**When to fix (remove argument):**
- Truly unused parameter with no purpose
- Private methods/functions with no inheritance

**When to ignore (keep argument):**

**1. Method overrides (Liskov Substitution Principle):**
```python
class Base:
    def process(self, data: dict, context: Context) -> None:
        ...

class Derived(Base):
    def process(self, data: dict, context: Context) -> None:  # noqa: ARG002
        # Only uses 'data', not 'context', but must match signature
        print(data)
```

**2. Callback signatures:**
```python
def on_click(event: Event, metadata: dict) -> None:  # noqa: ARG002
    # Framework requires 'metadata' param even if unused
    print("Clicked!")
```

**3. Pytest fixtures:**
```python
def test_feature(db_session):  # noqa: ARG002
    # Fixture ensures DB setup, but not directly used
    assert True
```

**Suppression techniques:**

**1. Prefix with underscore (preferred):**
```python
def process(self, data: dict, _context: Context) -> None:
    print(data)
```

**2. Per-line # noqa:**
```python
def callback(event, metadata):  # noqa: ARG002
```

**3. Delete/assign to underscore:**
```python
def process(self, data: dict, context: Context) -> None:
    del context  # or: _ = context
    print(data)
```

**Sources:**
- [unused-method-argument (ARG002)](https://docs.astral.sh/ruff/rules/unused-method-argument/)
- [ARG002 violates Liskov's Substitution Principle](https://github.com/astral-sh/ruff/issues/15952)
- [ARG002 on callbacks](https://github.com/astral-sh/ruff/issues/10409)

---

## 6. Rules to Disable When Using `ruff format`

**ISC001:** As of 2026, **no longer conflicts** (see section 2). Can be enabled.

**W191 (tab indentation):** Formatter handles indentation, disable this if using format.

**E111/E114/E117 (indentation):** Formatter controls indentation, these are redundant.

**E501 (line too long):** Formatter respects `line-length` setting, but doesn't enforce it on comments/strings. Keep enabled if you want strict enforcement.

**Recommendation:**
```toml
[tool.ruff.lint]
# No longer need to ignore ISC001 in 2026
extend-ignore = []  # Formatter handles indentation automatically
```

**Source:** [The Ruff Formatter](https://docs.astral.sh/ruff/formatter/)

---

## Summary Table

| Issue | Recommendation | Configuration |
|-------|----------------|---------------|
| Per-file ignores | Use modern `[tool.ruff.lint.per-file-ignores]` | See section 1 |
| ISC001 conflict | **No longer conflicts** in 2026 | Enable if on Ruff 0.5+ |
| ML naming (N803/N806) | Per-file ignore for `ml/` dirs | `"ml/**/*.py" = ["N803", "N806"]` |
| PLR2004 magic values | Extract non-obvious, # noqa for well-known | Case-by-case |
| ARG002 unused args | Prefix with `_` or # noqa for overrides | See section 5 |
| Formatter conflicts | None in 2026 | Use `ruff format` freely |

---

## Recommended ML Project Config

```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "ANN", "S", "B", "A", "C4", "DTZ", "T10", "ISC", "ICN", "PT", "Q", "RET", "SIM", "TID", "ARG", "PTH", "PD", "PL", "TRY", "NPY", "RUF"]
ignore = []

[tool.ruff.lint.per-file-ignores]
# ML code uses uppercase matrix names (X, y)
"ml/**/*.py" = ["N803", "N806"]
"models/**/*.py" = ["N803", "N806"]

# Test files: allow magic values and unused fixtures
"tests/**/*.py" = ["PLR2004", "ARG002"]

# __init__.py: allow unused imports for re-exports
"__init__.py" = ["F401"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

---

**Research Status:** Complete (web search fallback, Context7 MCP unavailable in teammate environment)
**Limitation:** Could not query Context7 directly; used official Ruff docs + GitHub issues instead
**Confidence:** High (all sources are official Ruff documentation or maintainer responses)
