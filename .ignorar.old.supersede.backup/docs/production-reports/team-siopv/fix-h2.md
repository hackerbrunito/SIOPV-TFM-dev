# Fix H2: Export DLP DI functions from __init__.py

**Task:** #8 — DLP DI not exported
**Agent:** h2-fixer
**Date:** 2026-03-05

## Problem

`get_dlp_port()` and `get_dual_layer_dlp_port()` were implemented in
`src/siopv/infrastructure/di/dlp.py` but not re-exported from
`src/siopv/infrastructure/di/__init__.py`. Any consumer doing
`from siopv.infrastructure.di import get_dlp_port` would get an `ImportError`.

## Fix Applied

**File:** `src/siopv/infrastructure/di/__init__.py`

1. Added import block:
   ```python
   from siopv.infrastructure.di.dlp import (
       get_dlp_port,
       get_dual_layer_dlp_port,
   )
   ```
2. Added both names to `__all__` list (alphabetically sorted).

## Verification

- `uv run pytest tests/ -q --tb=short` — **1,404 passed, 12 skipped, 5 warnings** (68.76s)
- No regressions introduced.

## Status: COMPLETE
