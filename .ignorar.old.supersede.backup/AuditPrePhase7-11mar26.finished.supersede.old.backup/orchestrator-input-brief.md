# SIOPV Remediation-Hardening — Orchestrator Input Brief

**Prepared by:** claude-main (plan mode session, 2026-03-15)
**For:** Opus orchestrator review → produce final execution guidelines
**Project root:** `/Users/bruno/siopv/`

---

## 1. Context

Phases 0–6 of SIOPV are complete. Before Phase 7 (Streamlit Human-in-the-Loop) begins,
a set of CRITICAL and HIGH issues must be fixed across the codebase. These were identified
across 4 audit stages (Stages 1–4.2, March 11–15 2026). The briefing.md contains the
consolidated issue list. This document adds planning-session findings that update and
refine that list.

**Orchestrator's deliverable:** A file named
`remediation-hardening-orchestrator-guidelines.md` saved to
`/Users/bruno/siopv/AuditPrePhase7-11mar26/`
containing the complete execution plan for worker agents.

---

## 2. Scope Decisions (closed — do not re-open)

| Item | Decision | Reason |
|------|----------|--------|
| LLM confidence stub (`adapters/llm/__init__.py` empty) | **DEFER to Phase 7** | Requires real Claude Sonnet adapter — Phase 7/8 builders own this |
| Phase 2 adapter tests (NVD, EPSS, GitHub, Tavily, ChromaDB at 0–20%) | **INCLUDE** in Round 5 | Adapters are frozen; Phase 7/8 builders shouldn't inherit this gap |
| `SanitizeVulnerabilityUseCase` | **DELETE** (confirmed orphaned) | Never imported or called anywhere; `dlp_node` is the real path |
| Phase 7/8 features | **NOT touched** | Phase 7/8 builders own all new feature work |

---

## 3. Stale Briefing Items — Verify Before Acting

Two items in briefing.md Section 5 appear to be stale based on Explore-agent codebase scan:

### Known #7: "asyncio.run() in sync nodes"
**Briefing claims:** `asyncio.run()` in `dlp_node`, `enrich_node`, `authorization_node`.
**Actual finding:** Zero `asyncio.run()` calls in any node. All three nodes are correctly
`async def` using `await`. Only `cli/main.py:87` uses `asyncio.run()` — which is correct
(CLI sync→async boundary).
**Worker instruction:** Verify current state first. If confirmed correct → no-op. Report
finding. Only act if an actual misuse is found.

### Known #4: "run_pipeline() drops enrichment clients (graph.py:439-444)"
**Briefing claims:** Clients dropped at lines 439-444.
**Actual finding:** Clients ARE passed to `PipelineGraphBuilder` at lines 456-466.
Whether the builder correctly wires them into `enrich_node` is unverified.
**Worker instruction:** Read `graph.py` AND `PipelineGraphBuilder._add_enrich_node()`
(or equivalent). Confirm whether clients reach the node. If wiring is correct → no-op.
If gap found → fix it. Report either way.

---

## 4. Core Design Rules for All Workers

### Rule 1 — One file, one worker, one pass
Every file in the codebase is assigned to exactly one worker for the entire remediation.
No file appears in two worker assignments. If a file has multiple issues, all are fixed
in a single read-fix-verify pass by the same worker.

### Rule 2 — Universal worker protocol (applies to every worker, every round)
1. Read the assigned briefing section (issues for their files)
2. Read the complete content of each assigned file
3. Compare: confirm each issue exists as described
4. If issue confirmed → implement fix
5. If issue NOT found (stale/already fixed) → stop, report to orchestrator, do not touch
6. Run: `ruff format`, `ruff check`, `mypy src` on modified files
7. Run affected tests: `pytest tests/ -x -q --tb=short`
8. Save report to `.ignorar/production-reports/remediation/{TIMESTAMP}-{slug}.md`
9. Report pass/fail to orchestrator

### Rule 3 — Escalate ambiguity, never guess
If the correct fix approach is unclear after reading the file → stop → report to
orchestrator → wait for guidance. Never infer. Never guess.

### Rule 4 — No scope creep
Workers fix only their assigned issues. If they notice other problems → document in
report → do not fix unless explicitly assigned.

---

## 5. File Ownership Map (authoritative — one file = one worker)

Every source file with an issue is listed below, consolidated by worker assignment.
The orchestrator assigns workers based on this map. No file appears twice.

| Worker slug | Files owned | Issues to fix | Round |
|-------------|-------------|---------------|-------|
| `fix-di-auth` | `infrastructure/di/authorization.py` | Hex #5: add `@lru_cache` to OpenFGA factory | 1 |
| `fix-logging` | `infrastructure/logging/setup.py` | Known #9: fix `format_exc_info` deprecation | 1 |
| `fix-sanitize` | `application/use_cases/sanitize_vulnerability.py` + `tests/unit/application/test_sanitize_vulnerability.py` | Known #2: delete both files (confirmed orphaned) | 1 |
| `fix-haiku-dlp` | `adapters/dlp/haiku_validator.py` + `adapters/dlp/_haiku_utils.py` + `adapters/dlp/presidio_adapter.py` | Known #6 (partial): replace hardcoded Haiku model IDs with settings constant | 1 |
| `fix-ports-ingest` | `application/use_cases/ingest_trivy.py` + domain port file (create or extend) | Hex #1: remove `TrivyParser` adapter import; inject via domain port | 2 |
| `fix-ports-classify` | `application/use_cases/classify_risk.py` + domain port file (create or extend) | Hex #2: remove `FeatureEngineer` adapter import; inject via domain port | 2 |
| `fix-dlp-port` | `adapters/dlp/dual_layer_adapter.py` | Hex #4: add explicit `DLPPort` inheritance + Known #6 (this file's Haiku ID) | 2 |
| `fix-di-exports` | `infrastructure/di/__init__.py` | Known #5: export `get_dlp_port`, `get_dual_layer_dlp_port` | 2 |
| `fix-edges` | `application/orchestration/edges.py` + target domain file | Hex #7: move `calculate_batch_discrepancies()` logic to domain layer | 2 |
| `fix-ingest-node` | `application/orchestration/nodes/ingest_node.py` | Hex #6: remove direct use-case instantiation; wire via DI | 3 |
| `fix-enrich-node` | `application/orchestration/nodes/enrich_node.py` | Remove dead `enrich_node_async`; verify asyncio pattern (Known #7 stale — may be no-op) | 3 |
| `fix-async-nodes` | `application/orchestration/nodes/dlp_node.py` + `application/orchestration/nodes/authorization_node.py` | Verify asyncio pattern (Known #7 stale — likely no-op); report findings | 3 |
| `fix-graph` | `application/orchestration/graph.py` | Known #4: verify enrichment client wiring into nodes (stale — may be no-op) | 3 |
| `fix-cli` | `interfaces/cli/main.py` | Hex #3 + Known #1: wire all 8 adapter ports via DI; fix 3 TODO stubs | 4 |
| `fix-adapter-tests` | `adapters/outbound/nvd/`, `adapters/outbound/epss/`, `adapters/outbound/github/`, `adapters/outbound/tavily/`, `adapters/vector/chroma/` (test files only) | Known #8: write unit tests for all 5 Phase 2 adapters; target 80%+ per adapter | 5 |

---

## 6. Round Structure and Dependencies

```
Round 1 (parallel — no dependencies)
├── fix-di-auth        → di/authorization.py
├── fix-logging        → logging/setup.py
├── fix-sanitize       → sanitize_vulnerability.py + test
└── fix-haiku-dlp      → 3 DLP adapter files

Round 2 (parallel — depends on Round 1 complete)
├── fix-ports-ingest   → ingest_trivy.py + new domain port
├── fix-ports-classify → classify_risk.py + new domain port
├── fix-dlp-port       → dual_layer_adapter.py
├── fix-di-exports     → di/__init__.py
└── fix-edges          → edges.py + domain target

Round 3 (parallel — depends on Round 2 complete)
├── fix-ingest-node    → ingest_node.py (needs di/__init__.py exports from R2)
├── fix-enrich-node    → enrich_node.py (verify + dead code removal)
├── fix-async-nodes    → dlp_node.py + authorization_node.py (verify)
└── fix-graph          → graph.py (verify enrichment wiring)

Round 4 (single — depends on Round 3 complete)
└── fix-cli            → cli/main.py (needs ALL DI correct)

Round 5 (parallel — independent, after Round 4)
└── fix-adapter-tests  → 5 Phase 2 adapter test campaigns
    (can split into 5 sub-workers, one per adapter)

Round 6 — Verification
└── Run full /verify skill (14 agents, 83% coverage floor)
    ruff format && ruff check && mypy src
    pytest --cov=src --cov-fail-under=83
```

**Key dependency rationale:**
- Round 1 before Round 2: DI authorization cache must exist before nodes use it;
  DLP files must be clean before DLPPort inheritance is added
- Round 2 before Round 3: domain ports must exist before nodes wire via DI;
  `di/__init__.py` exports must exist before `ingest_node` wires via them
- Round 3 before Round 4: all DI must be correct before CLI wires all 8 ports
- Round 5 after Round 4: adapter tests are independent but run last to keep focus
  on blocking fixes first

---

## 7. Known Complexity Flags (orchestrator must address in guidelines)

### Hex #1 and #2 (ingest_trivy + classify_risk port introduction)
These require creating or extending domain port files. The worker must:
1. Check if a suitable port/protocol already exists in `domain/ports/`
2. If yes → reference it in the use case
3. If no → create a minimal abstract port in `domain/ports/` first, then reference it
This means `fix-ports-ingest` and `fix-ports-classify` may each create a new domain file.
The orchestrator guidelines must explicitly allow this.

### Hex #7 (edges.py domain logic)
Moving `calculate_batch_discrepancies()` to domain means creating or extending a domain
entity/service. The worker must identify the correct domain home (likely an existing
entity or a new domain service). The domain target file is unspecified — worker must
decide and report before committing.

### CLI wiring (fix-cli) — HIGH complexity
`cli/main.py` has 8 adapter ports all set to `None`. The worker must:
1. Read `infrastructure/di/__init__.py` (after Round 3) to see all available DI functions
2. Map each port to its DI function
3. Wire all 8 correctly
4. Fix 3 TODO stubs (need to understand what each stub should do)
This is the highest-risk worker task. The orchestrator guidelines should specify that
`fix-cli` worker must read BOTH `cli/main.py` AND `di/__init__.py` before acting.

---

## 8. Orchestrator Instructions

The Opus orchestrator reading this brief should:

1. **Validate** the round structure — check for dependency gaps or ordering errors
2. **Challenge** any worker assignment where the fix approach is unclear or risky
3. **Improve** the plan if better groupings or sequencing exist
4. **Specify** the exact worker prompts for each slug (what to read, what to fix, what to verify)
5. **Produce** `remediation-hardening-orchestrator-guidelines.md` as the final artifact

The guidelines document must include:
- Section 1: Scope (closed decisions, out-of-scope items)
- Section 2: Core rules (the 4 rules from Section 4 above)
- Section 3: File ownership map (final version)
- Section 4: Round structure with dependency rationale
- Section 5: Per-worker specs (exact prompt, files to read, fix description, verification steps)
- Section 6: Verification round (full /verify + coverage gate)
- Section 7: Escalation protocol (what to do when stale items confirmed or fix is ambiguous)

**Model assignments:**
- Orchestrator: `claude-opus-4-6`
- All workers: `claude-sonnet-4-6`, `mode: acceptEdits`

**Report path convention:**
`.ignorar/production-reports/remediation/{TIMESTAMP}-{worker-slug}.md`

---

## 9. What the Orchestrator Should NOT Do

- Re-open scope decisions from Section 2
- Read Stage 1–4.2 audit files (this brief already distills them)
- Assign workers to Phase 7/8 features
- Allow two workers to share a file
- Allow a worker to fix issues not in their assigned list
