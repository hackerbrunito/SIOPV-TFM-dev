# SPAWN REQUEST — WAVE 1.2a (BPE Scanners, batches 8–12)

**Number of agents:** 5
**VERIFY_DIR:** `/Users/bruno/siopv/.verify-16-03-2026`
**All 5 agents run in parallel.**

---

## Agent 1: scanner-bpe-8

**Files:**
- /Users/bruno/siopv/src/siopv/application/use_cases/classify_risk.py
- /Users/bruno/siopv/src/siopv/application/use_cases/enrich_context.py
- /Users/bruno/siopv/src/siopv/application/use_cases/ingest_trivy.py
- /Users/bruno/siopv/src/siopv/domain/authorization/entities.py
- /Users/bruno/siopv/src/siopv/domain/authorization/exceptions.py

**Prompt:**

You are scanner-bpe-8 (best-practices-enforcer) for SIOPV /verify Wave 1.

VERIFY_DIR: /Users/bruno/siopv/.verify-16-03-2026

HANDOFF: Write to /Users/bruno/siopv/.verify-16-03-2026/handoffs/handoff-scanner-bpe-8.md NOW.

CONTEXT7 CACHE: Read /Users/bruno/siopv/.verify-16-03-2026/context7-cache/BRIEFING.md first. Do NOT call mcp__context7__ tools.

YOUR ASSIGNED FILES (process ONLY these):
- /Users/bruno/siopv/src/siopv/application/use_cases/classify_risk.py
- /Users/bruno/siopv/src/siopv/application/use_cases/enrich_context.py
- /Users/bruno/siopv/src/siopv/application/use_cases/ingest_trivy.py
- /Users/bruno/siopv/src/siopv/domain/authorization/entities.py
- /Users/bruno/siopv/src/siopv/domain/authorization/exceptions.py

AUDIT CHECKS:
- Type hints: list[str] not List[str], dict[str,Any] not Dict, X | None not Optional[X]
- Pydantic v2: ConfigDict not class Config, model_validator not root_validator
- httpx not requests, structlog not print()/logging, pathlib.Path not os.path
- Missing type hints on function parameters/returns

OUTPUT: Write findings JSON to /Users/bruno/siopv/.verify-16-03-2026/scans/scan-bpe-8.json
When done: SendMessage(to="orchestrator", message="WAVE 1.2 AGENT scanner-bpe-8 COMPLETE: {PASS|FAIL} — {N} violations")

---

## Agent 2: scanner-bpe-9

**Files:**
- /Users/bruno/siopv/src/siopv/domain/authorization/value_objects.py
- /Users/bruno/siopv/src/siopv/domain/constants.py
- /Users/bruno/siopv/src/siopv/domain/entities/ml_feature_vector.py
- /Users/bruno/siopv/src/siopv/domain/exceptions.py
- /Users/bruno/siopv/src/siopv/domain/oidc/exceptions.py

**Prompt:**

You are scanner-bpe-9 (best-practices-enforcer) for SIOPV /verify Wave 1.

VERIFY_DIR: /Users/bruno/siopv/.verify-16-03-2026

HANDOFF: Write to /Users/bruno/siopv/.verify-16-03-2026/handoffs/handoff-scanner-bpe-9.md NOW.

CONTEXT7 CACHE: Read /Users/bruno/siopv/.verify-16-03-2026/context7-cache/BRIEFING.md first. Do NOT call mcp__context7__ tools.

YOUR ASSIGNED FILES (process ONLY these):
- /Users/bruno/siopv/src/siopv/domain/authorization/value_objects.py
- /Users/bruno/siopv/src/siopv/domain/constants.py
- /Users/bruno/siopv/src/siopv/domain/entities/ml_feature_vector.py
- /Users/bruno/siopv/src/siopv/domain/exceptions.py
- /Users/bruno/siopv/src/siopv/domain/oidc/exceptions.py

AUDIT CHECKS:
- Type hints: list[str] not List[str], dict[str,Any] not Dict, X | None not Optional[X]
- Pydantic v2: ConfigDict not class Config, model_validator not root_validator
- httpx not requests, structlog not print()/logging, pathlib.Path not os.path
- Missing type hints on function parameters/returns

OUTPUT: Write findings JSON to /Users/bruno/siopv/.verify-16-03-2026/scans/scan-bpe-9.json
When done: SendMessage(to="orchestrator", message="WAVE 1.2 AGENT scanner-bpe-9 COMPLETE: {PASS|FAIL} — {N} violations")

---

## Agent 3: scanner-bpe-10

**Files:**
- /Users/bruno/siopv/src/siopv/domain/oidc/value_objects.py
- /Users/bruno/siopv/src/siopv/domain/privacy/entities.py
- /Users/bruno/siopv/src/siopv/domain/privacy/exceptions.py
- /Users/bruno/siopv/src/siopv/domain/privacy/value_objects.py
- /Users/bruno/siopv/src/siopv/domain/services/discrepancy.py

**Prompt:**

You are scanner-bpe-10 (best-practices-enforcer) for SIOPV /verify Wave 1.

VERIFY_DIR: /Users/bruno/siopv/.verify-16-03-2026

HANDOFF: Write to /Users/bruno/siopv/.verify-16-03-2026/handoffs/handoff-scanner-bpe-10.md NOW.

CONTEXT7 CACHE: Read /Users/bruno/siopv/.verify-16-03-2026/context7-cache/BRIEFING.md first. Do NOT call mcp__context7__ tools.

YOUR ASSIGNED FILES (process ONLY these):
- /Users/bruno/siopv/src/siopv/domain/oidc/value_objects.py
- /Users/bruno/siopv/src/siopv/domain/privacy/entities.py
- /Users/bruno/siopv/src/siopv/domain/privacy/exceptions.py
- /Users/bruno/siopv/src/siopv/domain/privacy/value_objects.py
- /Users/bruno/siopv/src/siopv/domain/services/discrepancy.py

AUDIT CHECKS:
- Type hints: list[str] not List[str], dict[str,Any] not Dict, X | None not Optional[X]
- Pydantic v2: ConfigDict not class Config, model_validator not root_validator
- httpx not requests, structlog not print()/logging, pathlib.Path not os.path
- Missing type hints on function parameters/returns

OUTPUT: Write findings JSON to /Users/bruno/siopv/.verify-16-03-2026/scans/scan-bpe-10.json
When done: SendMessage(to="orchestrator", message="WAVE 1.2 AGENT scanner-bpe-10 COMPLETE: {PASS|FAIL} — {N} violations")

---

## Agent 4: scanner-bpe-11

**Files:**
- /Users/bruno/siopv/src/siopv/domain/value_objects/enrichment.py
- /Users/bruno/siopv/src/siopv/domain/value_objects/risk_score.py
- /Users/bruno/siopv/src/siopv/infrastructure/config/settings.py
- /Users/bruno/siopv/src/siopv/infrastructure/di/authentication.py
- /Users/bruno/siopv/src/siopv/infrastructure/di/authorization.py

**Prompt:**

You are scanner-bpe-11 (best-practices-enforcer) for SIOPV /verify Wave 1.

VERIFY_DIR: /Users/bruno/siopv/.verify-16-03-2026

HANDOFF: Write to /Users/bruno/siopv/.verify-16-03-2026/handoffs/handoff-scanner-bpe-11.md NOW.

CONTEXT7 CACHE: Read /Users/bruno/siopv/.verify-16-03-2026/context7-cache/BRIEFING.md first. Do NOT call mcp__context7__ tools.

YOUR ASSIGNED FILES (process ONLY these):
- /Users/bruno/siopv/src/siopv/domain/value_objects/enrichment.py
- /Users/bruno/siopv/src/siopv/domain/value_objects/risk_score.py
- /Users/bruno/siopv/src/siopv/infrastructure/config/settings.py
- /Users/bruno/siopv/src/siopv/infrastructure/di/authentication.py
- /Users/bruno/siopv/src/siopv/infrastructure/di/authorization.py

AUDIT CHECKS:
- Type hints: list[str] not List[str], dict[str,Any] not Dict, X | None not Optional[X]
- Pydantic v2: ConfigDict not class Config, model_validator not root_validator
- httpx not requests, structlog not print()/logging, pathlib.Path not os.path
- Missing type hints on function parameters/returns

OUTPUT: Write findings JSON to /Users/bruno/siopv/.verify-16-03-2026/scans/scan-bpe-11.json
When done: SendMessage(to="orchestrator", message="WAVE 1.2 AGENT scanner-bpe-11 COMPLETE: {PASS|FAIL} — {N} violations")

---

## Agent 5: scanner-bpe-12

**Files:**
- /Users/bruno/siopv/src/siopv/infrastructure/di/dlp.py
- /Users/bruno/siopv/src/siopv/infrastructure/logging/setup.py
- /Users/bruno/siopv/src/siopv/infrastructure/middleware/oidc_middleware.py
- /Users/bruno/siopv/src/siopv/infrastructure/ml/dataset_loader.py
- /Users/bruno/siopv/src/siopv/infrastructure/ml/model_persistence.py

**Prompt:**

You are scanner-bpe-12 (best-practices-enforcer) for SIOPV /verify Wave 1.

VERIFY_DIR: /Users/bruno/siopv/.verify-16-03-2026

HANDOFF: Write to /Users/bruno/siopv/.verify-16-03-2026/handoffs/handoff-scanner-bpe-12.md NOW.

CONTEXT7 CACHE: Read /Users/bruno/siopv/.verify-16-03-2026/context7-cache/BRIEFING.md first. Do NOT call mcp__context7__ tools.

YOUR ASSIGNED FILES (process ONLY these):
- /Users/bruno/siopv/src/siopv/infrastructure/di/dlp.py
- /Users/bruno/siopv/src/siopv/infrastructure/logging/setup.py
- /Users/bruno/siopv/src/siopv/infrastructure/middleware/oidc_middleware.py
- /Users/bruno/siopv/src/siopv/infrastructure/ml/dataset_loader.py
- /Users/bruno/siopv/src/siopv/infrastructure/ml/model_persistence.py

AUDIT CHECKS:
- Type hints: list[str] not List[str], dict[str,Any] not Dict, X | None not Optional[X]
- Pydantic v2: ConfigDict not class Config, model_validator not root_validator
- httpx not requests, structlog not print()/logging, pathlib.Path not os.path
- Missing type hints on function parameters/returns

OUTPUT: Write findings JSON to /Users/bruno/siopv/.verify-16-03-2026/scans/scan-bpe-12.json
When done: SendMessage(to="orchestrator", message="WAVE 1.2 AGENT scanner-bpe-12 COMPLETE: {PASS|FAIL} — {N} violations")

---

**Awaiting confirmation to spawn these 5 agents.**
