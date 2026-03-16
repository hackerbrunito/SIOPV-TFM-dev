# Python Constants & Magic Values Best Practices 2026

**Date:** 2026-02-10
**Focus:** PLR2004 fixes, DDD/hexagonal architecture placement, naming conventions

---

## PLR2004 Rule Overview

- Detects "magic" unnamed numerical constants in comparisons ([Ruff docs](https://docs.astral.sh/ruff/rules/magic-value-comparison/))
- Auto-excludes common values: 0, 1, -1, 0.0, 1.0, "", "__main__"
- Strict by default - can be noisy for legitimate use cases
- Solution: named constants OR `# noqa: PLR2004` for well-known values

## When to Extract vs When to Use # noqa

**Extract to constants:**
- Domain-specific thresholds (e.g., ML confidence scores: 0.6, 0.8)
- Business logic values (e.g., max retries: 3, timeout: 30)
- Configuration values repeated across modules

**Safe to use # noqa:**
- HTTP status codes (use `http.HTTPStatus` instead, [TestDriven.io](https://testdriven.io/tips/866f6c46-c3b1-410d-8569-9140f5db6eac/))
- Well-known protocol values (TCP ports, exit codes)
- Single-use values with clear context in comments

## Constants Placement in DDD/Hexagonal Architecture

**Domain Layer** (`src/siopv/domain/`):
- Business constants that express domain rules
- Enums for domain concepts (VulnerabilitySeverity, RiskLevel)
- Should NOT depend on infrastructure concerns

**Shared Module** (create `src/siopv/domain/constants.py`):
- Cross-cutting domain constants (max retries, timeouts)
- ML thresholds if used across multiple aggregates
- Format: `UPPER_SNAKE_CASE` module-level constants

**Adapter Layer** (`src/siopv/adapters/`):
- Adapter-specific constants (API endpoints, external service configs)
- Keep close to usage (e.g., `nvd_client.py` → `NVD_BASE_URL`)

**Recommendation for SIOPV project:**
```
src/siopv/domain/
  constants.py          # Shared domain constants
  value_objects.py      # Enums for domain concepts
src/siopv/adapters/ml/
  model_config.py       # ML-specific thresholds (0.1, 0.6, 0.8)
```

## Naming Conventions

- **Module constants:** `UPPER_SNAKE_CASE` ([Python PEP 8](https://peps.python.org/pep-0008/))
- **Enums:** PascalCase class, UPPER_SNAKE_CASE members
- **Dataclass configs:** lowercase field names with type hints

## Enum vs Module Constants vs Dataclass Configs

**Enums** ([ArjanCodes](https://arjancodes.com/blog/python-enum-classes-for-managing-constants/)):
- Best for: Fixed sets of related values (status codes, severity levels)
- Type-safe, IDE autocomplete, grouped namespace
- Example: `class Severity(Enum): LOW = 1; MEDIUM = 2; HIGH = 3`

**Module-level constants:**
- Best for: Simple numeric/string constants
- Lightweight, no boilerplate
- Example: `DEFAULT_TIMEOUT = 30`

**Dataclass configs** ([Python docs](https://docs.python.org/3/library/dataclasses.html)):
- Best for: Configuration objects with multiple fields
- Structured, type-hinted, easy to validate with Pydantic
- Example: `@dataclass class MLConfig: threshold: float = 0.6`

## ML-Specific Constants (0.1, 0.6, 0.8)

- **Context matters:** These are often precision/recall trade-off thresholds ([MachineLearningMastery](https://machinelearningmastery.com/threshold-moving-for-imbalanced-classification/))
- **Extract when:** Used across multiple models/modules
- **Keep inline when:** Model-specific tuning, documented in comments
- **Naming:** `CONFIDENCE_THRESHOLD_LOW = 0.1`, `PRECISION_THRESHOLD = 0.6`
- **Note:** Default 0.5 is often suboptimal for imbalanced datasets ([Ploomber](https://ploomber.io/blog/threshold/))

---

## Sources

- [magic-value-comparison (PLR2004) | Ruff](https://docs.astral.sh/ruff/rules/magic-value-comparison/)
- [Tips and Tricks - Python - avoid HTTP status code magic numbers with http.HTTPStatus() | TestDriven.io](https://testdriven.io/tips/866f6c46-c3b1-410d-8569-9140f5db6eac/)
- [Building Maintainable Python Applications with Hexagonal Architecture and Domain-Driven Design - DEV Community](https://dev.to/hieutran25/building-maintainable-python-applications-with-hexagonal-architecture-and-domain-driven-design-chp)
- [Python Enums: Effective Constant Management Techniques | ArjanCodes](https://arjancodes.com/blog/python-enum-classes-for-managing-constants/)
- [A Gentle Introduction to Threshold-Moving for Imbalanced Classification - MachineLearningMastery.com](https://machinelearningmastery.com/threshold-moving-for-imbalanced-classification/)
- [Stop using 0.5 as the threshold for your binary classifier](https://ploomber.io/blog/threshold/)
