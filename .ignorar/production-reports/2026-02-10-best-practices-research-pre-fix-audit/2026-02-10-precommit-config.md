# Pre-commit 3.6+ Configuration Best Practices (2026)

**Date:** 2026-02-10
**Researcher:** best-practices-research agent
**Task:** Research current Pre-commit configuration standards for migration and optimization

---

## 1. default_stages Migration (commit → pre-commit)

**Deprecation Status:**
- Pre-commit 3.2.0+ changed stages naming to match hook names
- Old values: `commit`, `push`, `merge-commit`
- New values: `pre-commit`, `pre-push`, `pre-merge-commit`
- `pre-commit migrate-config` command handles automatic migration

**Best Practice:**
```yaml
default_stages: [pre-commit]  # NOT [commit]
```

**Source:** [Pre-commit advanced docs](https://github.com/pre-commit/pre-commit.com/blob/main/sections/advanced.md)

---

## 2. Ruff Integration (2026 Standard)

**Hook Order (CRITICAL):**
```yaml
- repo: https://github.com/astral-sh/ruff-pre-commit
  rev: v0.15.0+
  hooks:
    - id: ruff
      args: [--fix]  # Must run BEFORE formatter
    - id: ruff-format
```

**Why:** Ruff's linter with `--fix` must precede formatter to avoid conflicts.

**Exclude Jupyter Notebooks:**
```yaml
types_or: [python, pyi]  # Removes jupyter from defaults
```

**Source:** [Ruff pre-commit repo](https://github.com/astral-sh/ruff-pre-commit)

---

## 3. Performance Optimization

**CI Skip (pre-commit.ci):**
```yaml
ci:
  autoupdate_schedule: weekly  # Default: 16:00 UTC Monday
  skip: [mypy, pylint]  # Skip slow hooks in CI only
```

**Local SKIP:**
```bash
SKIP=mypy,pylint git commit -m "message"
```

**Source:** [Pre-commit.ci docs](https://pre-commit.ci/)

---

## 4. Version Drift Prevention

**Problem:** Updating `pyproject.toml` doesn't sync `.pre-commit-config.yaml`

**Solution:** Manual sync required until tooling improves
```bash
pre-commit autoupdate  # Run after dependency updates
```

**Source:** [Python Developer Tooling Handbook](https://pydevtools.com/blog/sync-with-uv-eliminate-pre-commit-version-drift/)

---

## 5. 2026 Recommendations

**Hook ordering:**
1. Auto-fixers first (ruff --fix, isort)
2. Formatters second (ruff-format, black)
3. Validators last (mypy, type checkers)

**fail_fast:** Set `false` for full feedback loop (see all errors at once)

**Sources:**
- [Pre-commit hooks guide 2025](https://gatlenculp.medium.com/effortless-code-quality-the-ultimate-pre-commit-hooks-guide-for-2025-57ca501d9835)
- [Medium: Automate Python formatting](https://medium.com/@kutayeroglu/automate-python-formatting-with-ruff-and-pre-commit-b6cd904b727e)
