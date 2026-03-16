# Task #7: Fix CLI Stubs — h1-fixer Report

**Date:** 2026-03-05
**File:** `src/siopv/interfaces/cli/main.py`
**Status:** COMPLETE

## Changes Made

### 1. `process_report()` — Wired to `run_pipeline()`
- Lazy-imports `run_pipeline` from `siopv.application.orchestration.graph`
- Added `--user-id` and `--project-id` CLI options for Phase 5 authorization
- Calls `run_pipeline(report_path=..., user_id=..., project_id=...)`
- Creates output directory, writes `pipeline_summary.json` with results
- Proper error handling with `log.exception` and `typer.Exit(code=1)`

### 2. `dashboard()` — Wired to Streamlit launcher
- Defined `STREAMLIT_APP_PATH` pointing to `interfaces/dashboard/app.py`
- Checks if file exists; if not, prints clear message about Phase 7 and exits
- Uses `subprocess.run([sys.executable, "-m", "streamlit", "run", ...])` to launch
- Handles `CalledProcessError` and `KeyboardInterrupt` gracefully

### 3. `train_model()` — Wired to `XGBoostClassifier.train()`
- Lazy-imports `csv`, `XGBoostClassifier`, `MLFeatureVector`
- Added `--no-optimize` and `--n-trials` CLI options
- Reads CSV via `csv.DictReader` with header columns matching `MLFeatureVector` fields
- Last column treated as label (1=exploited, 0=not)
- Constructs `MLFeatureVector` with all 14 features + cve_id per row
- Calls `classifier.train(features, labels, optimize_hyperparams=..., n_trials=...)`
- Calls `classifier.save_model(str(output_path))` after training
- Prints metrics summary

## Design Decisions

- **Lazy imports** (`# noqa: PLC0415`): Heavy modules (`graph`, `xgboost_classifier`, `ml_feature_vector`) are imported inside functions to avoid side effects at module load time. Importing `graph.py` at top level pulls in LangGraph, SQLite, and all node dependencies, which broke graph tests when imported eagerly.
- **STREAMLIT_APP_PATH**: Uses `Path(__file__).resolve().parent.parent / "dashboard" / "app.py"` — the `interfaces/dashboard/` directory exists but has no `app.py` yet (Phase 7 pending). The command exits cleanly with a message.

## Verification

- **ruff check:** 0 errors
- **ruff format:** No changes needed
- **pytest:** 1400 passed, 4 failed, 12 skipped
  - The 4 failures are in `test_graph.py` caused by another task's async changes to `graph.py` (not related to CLI)
  - No new test failures introduced by this task
