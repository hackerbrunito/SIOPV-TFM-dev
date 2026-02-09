# GitHub Actions CI Best Practices (Python + uv) - February 2026

**Date:** 2026-02-10
**Researcher:** best-practices-researcher
**Task:** Research current best practices for GitHub Actions with Python + uv

---

## Current Implementation Analysis

**Status:** ✅ EXCELLENT - Follows 95% of 2026 best practices

**Existing CI (~/siopv/.github/workflows/ci.yml):**
- ✅ astral-sh/setup-uv@v4 with enable-cache: true
- ✅ Python matrix (3.11, 3.12) with proper quoting
- ✅ Separate jobs (lint, typecheck, test) for fast feedback
- ✅ Concurrency with cancel-in-progress for PRs
- ✅ uv sync --frozen --all-extras (reproducible builds)
- ✅ Codecov integration (Python 3.11 only to avoid duplication)
- ✅ Pinned actions (@v4, @v5)

**Minor Gaps (non-critical):**
- ⚠️  Missing explicit timeout-minutes (defaults to 360 min)
- ⚠️  Missing explicit permissions declaration (security hardening)
- ⚠️  Missing fail-fast: false (stops on first failure)
- ⚠️  Missing uv cache prune --ci optimization

---

## 2026 Best Practices Summary

### 1. astral-sh/setup-uv Configuration
- **Use v4 (latest)** with enable-cache: true ✅
- **Pin version if needed** (avoid version="latest" on self-hosted runners)
- **Default GITHUB_TOKEN** for API rate limiting ✅
- **Cache pruning:** Add `uv cache prune --ci` post-job to remove pre-built wheels

### 2. Python Matrix Strategy
- **Quote versions:** "3.11", "3.12" (YAML interprets 3.10 as 3.1 float) ✅
- **Test current + next:** Python 3.11 (stable) + 3.12 (latest) ✅
- **Avoid over-testing:** Don't test all minor versions (3.11.0, 3.11.1...)

### 3. Job Separation vs Single Job
- **Best: Separate jobs** (lint → typecheck → test) ✅
- **Fast feedback:** Lint fails in ~30s vs waiting for full test suite
- **Runner minutes:** Early exit on lint failure saves costs
- **Parallelization:** Jobs run concurrently (matrix expansion)

### 4. Concurrency Settings
- **cancel-in-progress: true for PRs** ✅
- **Keep false for main/develop** (allow parallel deployments) ✅

### 5. Caching Strategies
- **enable-cache: true** (automatic uv cache) ✅
- **Cache directories:** ~/.cache/uv, ~/.local/share/uv, .venv
- **Cache key:** Based on uv.lock hash (automatic)
- **Post-job optimization:** `uv cache prune --ci` to reduce cache size

### 6. Coverage Reporting
- **Codecov v4 with token** ✅
- **Upload once:** if: matrix.python-version == '3.11' ✅
- **fail_ci_if_error: false** (advisory, not blocking) ✅

### 7. Security Best Practices
- **Pin action versions:** @v4, @v5 (not @latest) ✅
- **Minimal permissions:** Declare permissions: read/write explicitly
- **Dependabot:** Auto-update action versions (setup separately)

### 8. Timeout Settings
- **Add timeout-minutes: 10** per job (prevent hanging)
- **Default 360 min** is excessive for Python CI

---

## Recommended Changes (Priority Order)

### HIGH Priority (Security/Performance)
1. **Add explicit permissions** (security hardening):
   ```yaml
   permissions:
     contents: read
   ```

2. **Add timeout-minutes** (prevent hanging jobs):
   ```yaml
   jobs:
     lint:
       timeout-minutes: 10
   ```

### MEDIUM Priority (Optimization)
3. **Add uv cache pruning** (reduce cache size):
   ```yaml
   - name: Prune uv cache
     run: uv cache prune --ci
   ```

4. **Add fail-fast: false** (see all failures):
   ```yaml
   strategy:
     fail-fast: false
     matrix:
       python-version: ["3.11", "3.12"]
   ```

### LOW Priority (Nice-to-have)
5. **Parallel pytest execution** (faster tests):
   ```yaml
   run: uv run pytest tests/ -n auto --cov=src/siopv
   ```

---

## Sources

- [Using uv in GitHub Actions - Astral Docs](https://docs.astral.sh/uv/guides/integration/github/)
- [astral-sh/setup-uv GitHub Action](https://github.com/astral-sh/setup-uv)
- [Optimizing uv in GitHub Actions (Medium)](https://szeyusim.medium.com/optimizing-uv-in-github-actions-one-global-cache-to-rule-them-all-9c64b42aee7f)
- [GitHub Actions Matrix Strategy Best Practices](https://codefresh.io/learn/github-actions/github-actions-matrix/)
- [How to Optimize GitHub Actions Performance (2026)](https://oneuptime.com/blog/post/2026-02-02-github-actions-performance-optimization/view)
- [uv Caching Concepts](https://docs.astral.sh/uv/concepts/cache/)
