## Batch 1 of 4 — Domain Privacy Layer

**Timestamp:** 2026-02-20-164428
**Files analyzed:**
- /Users/bruno/siopv/src/siopv/domain/privacy/__init__.py
- /Users/bruno/siopv/src/siopv/domain/privacy/entities.py
- /Users/bruno/siopv/src/siopv/domain/privacy/exceptions.py
- /Users/bruno/siopv/src/siopv/domain/privacy/value_objects.py

---

## Findings

### 1. DLPResult stores original PII text in-memory indefinitely
- **File:** /Users/bruno/siopv/src/siopv/domain/privacy/entities.py:53
- **Severity:** MEDIUM
- **CWE:** CWE-312 (Cleartext Storage of Sensitive Information)
- **Description:** `DLPResult` is a frozen Pydantic model that stores `original_text` (the raw, unsanitized PII-containing text) alongside `sanitized_text`. This object is the return value of all DLP operations and may be retained in memory, logged, or serialized downstream. Any inadvertent serialization (e.g., JSON response, log sink) of a `DLPResult` instance will leak the raw PII that the DLP layer was designed to redact. There is no mechanism to prevent access to `original_text` after the sanitization is complete.
- **Fix:** Consider removing `original_text` from `DLPResult` entirely, or marking it as excluded from serialization (`Field(exclude=True)`) if it is only needed transiently for internal diff-comparison. If it must be retained for audit purposes, ensure access is restricted to privileged callers and that serialization is explicitly controlled.

### 2. PIIDetection stores raw detected PII text
- **File:** /Users/bruno/siopv/src/siopv/domain/privacy/value_objects.py:61-64
- **Severity:** MEDIUM
- **CWE:** CWE-312 (Cleartext Storage of Sensitive Information)
- **Description:** `PIIDetection.text` stores the verbatim PII string (e.g., the actual credit card number, SSN, or password) that was detected. This is embedded in every `PIIDetection` in `DLPResult.detections`. If any part of the `DLPResult` (including the detections list) is serialized, logged, or returned to an API consumer, the raw PII values will be exposed. The field carries no protection, exclusion flag, or masking.
- **Fix:** Either omit `text` from the detection record and rely on `start`/`end` offsets to reconstruct it from the sanitized context only when needed, or mark `text` as `Field(exclude=True)` and document that it is in-memory only for internal processing.

### 3. Incomplete entity type mapping — silent lossy fallback to SECRET_TOKEN
- **File:** /Users/bruno/siopv/src/siopv/domain/privacy/value_objects.py:118
- **Severity:** LOW
- **CWE:** CWE-20 (Improper Input Validation)
- **Description:** When `from_presidio()` receives an entity type not in `type_map`, it silently falls back to `PIIEntityType.SECRET_TOKEN`. This means new Presidio entity types added in future versions of the library, or custom recognizers, will be silently misclassified. Downstream code filtering or routing based on `entity_type` will silently misbehave. There is no warning or log emitted.
- **Fix:** Log a warning when an unmapped entity type is encountered before falling back to `SECRET_TOKEN`. This provides observability without breaking behavior.

### 4. No input length validation on SanitizationContext.text
- **File:** /Users/bruno/siopv/src/siopv/domain/privacy/entities.py:23-26
- **Severity:** LOW
- **CWE:** CWE-400 (Uncontrolled Resource Consumption)
- **Description:** `SanitizationContext.text` has no maximum length constraint. Submitting extremely large texts (e.g., multi-MB strings) to the DLP pipeline could exhaust memory in Presidio's NLP pipeline, trigger excessive API token usage in the Haiku validator, or cause denial-of-service conditions. The `score_threshold` field correctly uses `ge`/`le` bounds, but `text` has none.
- **Fix:** Add `max_length` constraint (e.g., `Field(..., max_length=50_000)`) appropriate to the expected workload, and document the limit.

### 5. semantic_passed defaults to True — optimistic failure mode
- **File:** /Users/bruno/siopv/src/siopv/domain/privacy/entities.py:69-72
- **Severity:** LOW
- **Description:** `DLPResult.semantic_passed` defaults to `True`. If the Haiku semantic validator is skipped (not configured, or an exception is silently swallowed upstream), the result will appear as semantically validated when it was not. This creates a false sense of security in the dual-layer design.
- **Fix:** There is no ideal fix at the entity level alone — this depends on how callers construct `DLPResult`. The concern is flagged here as a design note. The actual risk depends on whether the adapter always explicitly sets this field. If the Haiku layer is optional by design, document clearly that `semantic_passed=True` with no detections does not mean Haiku ran.

---

## Summary
- Total: 5
- CRITICAL: 0
- HIGH: 0
- MEDIUM: 2 (non-blocking)
- LOW: 3
- **Threshold status: PASS** (0 CRITICAL/HIGH found)

**Notes:** The domain layer itself contains no hardcoded secrets, no SQL, no command injection, and no authentication logic. The two MEDIUM findings relate to PII data retention in memory/serialization paths and are architectural concerns that should be reviewed when defining the API surface and logging strategy.
