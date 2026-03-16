# R2 — Gap Analysis: Phase 5 & Phase 6

> Analyst: gap-analyzer-phases-5-6 | Date: 2026-03-11
> Sources: R1 requirements matrix, adapter code, node code, DI module, domain layer

---

## Phase 5: Control de Acceso (Zero Trust)

### REQ-P5-001 — Module name: `Authorization_Gatekeeper`
- **Status:** IMPLEMENTED
- **Evidence:** `authorization_node.py:290` — function named `authorization_node`, docstring references "Authorization_Gatekeeper from spec section 3.5"
- **Notes:** Implemented as a LangGraph node function, not a class named `Authorization_Gatekeeper`. Functionally equivalent.

### REQ-P5-002 — Technology: OpenFGA for fine-grained authorization
- **Status:** IMPLEMENTED
- **Evidence:** `adapters/authorization/openfga_adapter.py:76` — `OpenFGAAdapter` uses `openfga_sdk` (ClientCheckRequest, ClientBatchCheckRequest, etc.)
- **Notes:** Full OpenFGA SDK integration with async client, circuit breaker, retry logic.

### REQ-P5-003 — Methodology: ReBAC (not RBAC)
- **Status:** IMPLEMENTED
- **Evidence:** `domain/authorization/value_objects.py:39-55` — `Relation` enum with `OWNER`, `VIEWER`, `ANALYST`, `AUDITOR`. `RelationshipTuple` entity at `entities.py:31` models user→relation→resource triples.
- **Notes:** True ReBAC: relationships stored as tuples in OpenFGA, not role assignments.

### REQ-P5-004 — Policies: owner→view, analyst→remediate, auditor→export
- **Status:** IMPLEMENTED
- **Evidence:** `domain/authorization/value_objects.py:294-301` — `ActionPermissionMapping.default_mappings()` defines:
  - VIEW: viewer, analyst, auditor, owner
  - REMEDIATE: analyst, owner
  - EXPORT: auditor, owner
  - Plus additional: EDIT, DELETE, CLASSIFY, ESCALATE, APPROVE
- **Notes:** Exceeds spec — more granular than required.

### REQ-P5-005 — Authorization query format: `check(user:X, relation:R, object:O)`
- **Status:** IMPLEMENTED
- **Evidence:** `openfga_adapter.py:322-336` — `_execute_check()` builds `ClientCheckRequest(user=user, relation=relation, object=obj)` matching the spec format exactly.
- **Notes:** Also supports batch checks via `ClientBatchCheckRequest`.

### REQ-P5-006 — Intercept every request before sensitive operations
- **Status:** IMPLEMENTED
- **Evidence:** `authorization_node.py:290-354` — `authorization_node()` runs as the FIRST node in the LangGraph pipeline (START → authorize → ingest → ...). `route_after_authorization()` at line 357 gates progression.
- **Notes:** Fail-secure design: if no port configured, access DENIED (line 152-170).

### REQ-P5-007 — Return 403 Forbidden with audit log on denied access
- **Status:** PARTIAL
- **Evidence:**
  - Audit log: YES — `authorization_node.py:239-256` logs `DENIED` event with `user_id_hash`, `project_id`, `action`, `decision_id` via structlog.
  - 403 Forbidden: NOT DIRECTLY — the node returns `authorization_allowed=False` in pipeline state and halts the pipeline (routes to "end"). There is no HTTP 403 response because the authorization node operates within the LangGraph pipeline, not at the HTTP layer.
- **Notes:** The spec says "return 403 Forbidden" which implies an HTTP response. This is only meaningful when exposed via FastAPI (Phase 7/8). The pipeline-level denial is the correct internal behavior, but no FastAPI middleware/endpoint currently translates this to HTTP 403.

---

### Phase 5 Summary

| Status | Count | IDs |
|--------|-------|-----|
| IMPLEMENTED | 6 | P5-001, P5-002, P5-003, P5-004, P5-005, P5-006 |
| PARTIAL | 1 | P5-007 |
| MISSING | 0 | — |

---

## Phase 6: Privacidad y DLP

### REQ-P6-001 — Module name: `Data_Privacy_Guardrail`
- **Status:** IMPLEMENTED
- **Evidence:** `nodes/dlp_node.py:67` — `dlp_node()` function. `adapters/dlp/presidio_adapter.py:219` — `PresidioAdapter`. `adapters/dlp/dual_layer_adapter.py:204` — `DualLayerDLPAdapter`.
- **Notes:** Not a single class named `Data_Privacy_Guardrail` but the functionality is split across adapter + node following hexagonal architecture.

### REQ-P6-002 — Layer 1 (deterministic): Microsoft Presidio (Regex + NLP)
- **Status:** IMPLEMENTED
- **Evidence:** `presidio_adapter.py:56-87` — `_build_analyzer()` creates `AnalyzerEngine` with custom `PatternRecognizer` for API keys. `presidio_adapter.py:90-104` — `_build_anonymizer()` creates `AnonymizerEngine`. Runs synchronously in thread-pool executor (line 282-287).
- **Notes:** Full Presidio integration with analyze + anonymize pipeline.

### REQ-P6-003 — Layer 2 (semantic): Claude Haiku 4.5 for contextual validation
- **Status:** IMPLEMENTED
- **Evidence:** Two implementations:
  1. `haiku_validator.py:52` — `HaikuSemanticValidatorAdapter` (SAFE/UNSAFE binary check, used inside `PresidioAdapter`)
  2. `dual_layer_adapter.py:65` — `_HaikuDLPAdapter` (JSON-structured DLP check with sanitized_text, used in `DualLayerDLPAdapter`)
- **Notes:** Model ID hardcoded as `"claude-haiku-4-5-20251001"` in default params (presidio_adapter.py:232, dual_layer_adapter.py:79, haiku_validator.py:63). DI module (`dlp.py:37`) reads from `settings.claude_haiku_model` — but the adapters' default values remain hardcoded. Known HIGH finding (#6 in MEMORY.md audit).

### REQ-P6-004 — Presidio detects: IPs, emails, API tokens, PII, internal URLs, filesystem paths
- **Status:** PARTIAL
- **Evidence:**
  - IPs, emails, phone, SSN, CC: YES — Presidio built-in recognizers handle these by default.
  - API tokens: YES — custom `PatternRecognizer` at `presidio_adapter.py:50-84` with regex `_API_KEY_REGEX`.
  - Internal URLs: NOT EXPLICITLY — no custom recognizer for internal URL patterns (e.g., `*.internal.corp`, `10.x.x.x/path`). Presidio's default `URL` entity may catch some but not domain-specific internal URLs.
  - Filesystem paths: NOT EXPLICITLY — no custom recognizer for filesystem paths (e.g., `/etc/passwd`, `C:\Users\...`). Not a default Presidio entity.
- **Notes:** Two entity types from the spec (internal URLs, filesystem paths) lack dedicated recognizers. Presidio's defaults may catch some via URL/IP entities, but there's no targeted detection.

### REQ-P6-005 — Haiku detects: internal project names, client names, trade secrets, internal architecture info
- **Status:** PARTIAL
- **Evidence:**
  - `haiku_validator.py:37-49` — validation prompt asks for "PII, secrets, API keys, passwords, or other sensitive data" — does NOT mention project names, client names, trade secrets, or architecture info.
  - `dual_layer_adapter.py:46-60` — DLP prompt asks for "Credentials, passwords, API keys, tokens / Internal hostnames, IP addresses, private URLs / Personal information" — mentions internal hostnames but NOT project names, client names, trade secrets, or architecture info.
- **Notes:** The Haiku prompts are generic security-focused but do NOT specifically target the four categories the spec calls out: (1) internal project names, (2) client names, (3) trade secrets, (4) internal architecture info. The LLM might catch some by inference, but there's no explicit instruction.

### REQ-P6-006 — All pipeline output passes through DLP BEFORE any logging operation
- **Status:** PARTIAL
- **Evidence:** `dlp_node.py:67-107` — `dlp_node` runs in the pipeline (after authorize, before enrich per graph topology). It processes vulnerability descriptions through DLP.
- **Notes:** The DLP node sanitizes vulnerability descriptions but does NOT modify the actual vulnerability records in state (line 77: "Does NOT modify the vulnerability records themselves"). Subsequent nodes (enrich, classify) work with unsanitized data. The spec says "ALL pipeline output passes through DLP BEFORE any logging" — but structlog calls throughout the pipeline log unsanitized data. DLP is an audit pass, not a pre-logging filter.

### REQ-P6-007 — LangSmith logs contain only sanitized data
- **Status:** MISSING
- **Evidence:** Grep for "LangSmith" or "langsmith" across the entire `src/siopv/` directory returned 0 results.
- **Notes:** LangSmith integration does not exist yet. No tracing, no sanitized log routing.

### REQ-P6-008 — Optional local logging for unsanitized traces with restricted access
- **Status:** MISSING
- **Evidence:** No separate logging configuration for unsanitized traces. `infrastructure/logging/setup.py` configures a single structlog pipeline with no access-restricted output channel.
- **Notes:** No dual-channel logging (sanitized public + unsanitized restricted).

---

### Phase 6 Summary

| Status | Count | IDs |
|--------|-------|-----|
| IMPLEMENTED | 3 | P6-001, P6-002, P6-003 |
| PARTIAL | 3 | P6-004, P6-005, P6-006 |
| MISSING | 2 | P6-007, P6-008 |

---

## Combined Summary

| Phase | IMPLEMENTED | PARTIAL | MISSING | Total |
|-------|-------------|---------|---------|-------|
| Phase 5 | 6 | 1 | 0 | 7 |
| Phase 6 | 3 | 3 | 2 | 8 |
| **Total** | **9** | **4** | **2** | **15** |

### Top Gaps to Address

1. **REQ-P6-007 (MISSING):** LangSmith integration absent — no tracing at all.
2. **REQ-P6-008 (MISSING):** No dual-channel logging (sanitized vs unsanitized).
3. **REQ-P6-005 (PARTIAL):** Haiku prompts miss spec-required detection categories (project names, client names, trade secrets, architecture info).
4. **REQ-P6-004 (PARTIAL):** No Presidio recognizers for internal URLs or filesystem paths.
5. **REQ-P6-006 (PARTIAL):** DLP node is audit-only; does not filter data before logging in downstream nodes.
6. **REQ-P5-007 (PARTIAL):** No HTTP 403 response — pipeline-level denial only (acceptable until FastAPI layer exists).

---

*End of report — 15 requirements assessed (9 IMPLEMENTED, 4 PARTIAL, 2 MISSING)*
