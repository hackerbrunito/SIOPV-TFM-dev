## Batch 4 of 4 — Infrastructure + Orchestration Integration

**Timestamp:** 2026-02-20-164911
**Files analyzed:**
- /Users/bruno/siopv/src/siopv/infrastructure/di/dlp.py
- /Users/bruno/siopv/src/siopv/application/orchestration/nodes/__init__.py
- /Users/bruno/siopv/src/siopv/application/orchestration/state.py
- /Users/bruno/siopv/src/siopv/application/orchestration/graph.py

---

## Findings

### 1. DLP node is optional — pipeline proceeds to enrichment without sanitization when not configured
- **File:** /Users/bruno/siopv/src/siopv/application/orchestration/graph.py:186-189, 239
- **Severity:** MEDIUM
- **CWE:** CWE-636 (Not Failing Securely)
- **Description:** The DLP node is wired into the graph unconditionally (`ingest -> dlp -> enrich`), but `dlp_port=None` is accepted silently at both `PipelineGraphBuilder.__init__()` and `create_pipeline_graph()`. When `dlp_port` is None, `dlp_node` logs a warning and returns immediately (per Batch 3 analysis), and the pipeline continues to enrichment and classification with raw, unsanitized vulnerability descriptions. There is no circuit-breaker, no state flag that downstream nodes check, and no way for an operator to enforce that DLP must be configured. A misconfigured deployment (e.g., missing `ANTHROPIC_API_KEY`) silently loses the entire privacy guardrail layer. The `run_pipeline()` convenience function accepts `dlp_port=None` as a default, making this the path of least resistance.
- **Fix:** Add a `require_dlp: bool = False` parameter to `PipelineGraphBuilder` and `create_pipeline_graph`. When `True`, raise `ValueError` at build time if `dlp_port is None`. Set this flag to `True` in production deployment configuration. At minimum, document that omitting `dlp_port` disables all PII sanitization.

### 2. SQLite checkpoint database path traversal — insufficient validation
- **File:** /Users/bruno/siopv/src/siopv/application/orchestration/graph.py:275-281
- **Severity:** MEDIUM
- **CWE:** CWE-22 (Path Traversal)
- **Description:** `_validate_path()` calls `path.resolve()` to canonicalize the path and checks the file extension. However, it does not restrict the resolved path to any allowed base directory. A caller who controls `checkpoint_db_path` (e.g., via a user-supplied parameter passed to `run_pipeline()`) could supply a path such as `../../etc/passwd.db` or `/tmp/attacker.db`. While the SQLite write operation would likely fail on system files, the check allows the database to be created anywhere on the filesystem where the process has write permission. The `must_exist` check only validates the parent directory exists, not that it is within any expected location.
- **Fix:** Restrict the resolved path to a configured allowed base directory (e.g., the application data directory). Reject paths that resolve outside of it: `if not resolved.is_relative_to(allowed_base): raise ValueError(...)`.

### 3. `run_pipeline()` logs `user_id` and `project_id` in plaintext
- **File:** /Users/bruno/siopv/src/siopv/application/orchestration/graph.py:450-456
- **Severity:** LOW
- **CWE:** CWE-532 (Insertion of Sensitive Information into Log File)
- **Description:** `pipeline_execution_started` log event emits `user_id` and `project_id` verbatim. Depending on the system design, `user_id` may be a PII-sensitive identifier (e.g., email address, national ID, internal employee number). Logging it at INFO level without masking means it will appear in any log aggregation system, potentially violating data minimization principles.
- **Fix:** Log only a truncated or hashed form of `user_id` (e.g., first 8 chars of a hash), or omit it from the log and rely on the thread_id for correlation.

### 4. `lru_cache` on `get_dlp_port` / `get_dual_layer_dlp_port` retains API key in memory indefinitely
- **File:** /Users/bruno/siopv/src/siopv/infrastructure/di/dlp.py:55-71, 104-120
- **Severity:** LOW
- **CWE:** CWE-316 (Cleartext Storage of Sensitive Information in Memory)
- **Description:** `@lru_cache(maxsize=1)` caches the adapter instance for the lifetime of the process. The adapter holds an `anthropic.Anthropic` client that internally retains the API key. While this is standard practice for singleton service objects, it means the API key remains in memory (reachable via the cached adapter) for the entire process lifetime with no mechanism to rotate or clear it without restarting. Combined with the `Settings` object being the cache key, any debug heap dump would expose the API key through the cached object graph.
- **Fix:** This is a low-risk accepted pattern for long-running services. Document the behavior explicitly. If key rotation is a requirement, add a `clear_dlp_cache()` function that calls `get_dlp_port.cache_clear()` and `get_dual_layer_dlp_port.cache_clear()`.

### 5. `dlp_result` in `PipelineState` is untyped `dict[str, object] | None`
- **File:** /Users/bruno/siopv/src/siopv/application/orchestration/state.py:70
- **Severity:** LOW
- **Description:** `dlp_result: dict[str, object] | None` stores DLP audit results in an untyped dictionary. Downstream nodes that inspect `dlp_result` (e.g., for audit or gating decisions) must rely on string key lookups with no type safety. This is not a direct security vulnerability but reduces the ability to enforce that security-relevant fields (e.g., `skipped`, `total_redactions`) are present and correctly typed, making it easier to accidentally bypass DLP checks in future node implementations.
- **Fix:** Define a typed `DLPNodeResult` TypedDict and use it for `dlp_result`. This is a design improvement that hardens the pipeline against future coding errors in downstream nodes.

### 6. `_validate_path` does not prevent symlink attacks
- **File:** /Users/bruno/siopv/src/siopv/application/orchestration/graph.py:57-86
- **Severity:** LOW
- **CWE:** CWE-61 (UNIX Symbolic Link Following)
- **Description:** `path.resolve()` follows symlinks before returning the canonical path. A symlink at the expected checkpoint path location could redirect writes to an arbitrary target. Given that the checkpoint database stores pipeline execution state (including vulnerability data and auth results), this could result in sensitive data being written to an attacker-controlled location.
- **Fix:** After resolving, check whether the path itself (not just its parent) was a symlink: `if path.is_symlink(): raise ValueError("Symlinks not permitted for checkpoint database path")`. This applies before the extension check.

---

## Summary
- Total: 6
- CRITICAL: 0
- HIGH: 0
- MEDIUM: 2 (non-blocking per thresholds)
- LOW: 4
- **Threshold status: PASS** (0 CRITICAL/HIGH found)

**Notes:** The infrastructure and orchestration layers are relatively clean from a security perspective. The two MEDIUM findings are architectural — optional DLP with no enforcement mode, and insufficient path containment for the checkpoint database. The `_validate_path` function shows security awareness (extension allowlist, parent directory existence check) but stops short of full containment. The DI module correctly uses `settings.anthropic_api_key.get_secret_value()` (SecretStr), which is the right pattern and a positive finding in contrast to the raw `str` handling observed in Batches 2 and 3.
