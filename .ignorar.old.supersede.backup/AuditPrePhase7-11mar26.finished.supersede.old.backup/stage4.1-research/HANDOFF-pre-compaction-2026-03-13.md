# HANDOFF FILE — Pre-Compaction 2026-03-13
# Stage 4.1 Research — SIOPV Audit Pre-Phase 7

> **Purpose:** Full session recovery document. The next session must read this file completely before taking any action.
> **Created:** 2026-03-13
> **Status:** Stage 4.1 is ⏳ PENDING — NOT yet started

---

## OPENING PROMPT FOR NEXT SESSION

"Read the handoff file at `/Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.1-research/HANDOFF-pre-compaction-2026-03-13.md` completely before doing anything. Then complete Tasks A, B, C, and D in that order. Do not start Stage 4.1 until all four tasks are done and you have confirmed with me."

---

## PROJECT CONTEXT

### Working Directories
- Meta-project: `/Users/bruno/sec-llm-workbench/`
- SIOPV project: `/Users/bruno/siopv/`
- Stage 4.1 research dir: `/Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.1-research/`

### What Stage 4.1 Is
Stage 4.1 is a multi-round online research phase that precedes Stage 4.2 (the actual implementation of Phase 7 and Phase 8 of SIOPV). Its purpose is to:
1. Research current (2026) best practices for all libraries used in Phase 7/8
2. Scan the meta-project for reusable agents, hooks, and patterns
3. Perform gap analysis between what exists and what is needed
4. Produce a "truth document" (set of baseline files) that Stage 4.2 will use as authoritative implementation references

Stage 4.1 was previously attempted (the old directory was backed up this session). It is being re-run from scratch.

---

## ACTIONS COMPLETED THIS SESSION

### 1. Renamed old Stage 4.1 directory
- Old: `/Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.1-research/`
- New: `/Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.1-research.old.backup/`

### 2. Updated briefing.md
- File: `/Users/bruno/sec-llm-workbench/.claude/workflow/briefing.md`
- Change: STAGE-4.1 changed from ✅ Complete to ⏳ PENDING
- Change: Removed the truth document path reference

### 3. Updated MEMORY.md
- File: `/Users/bruno/.claude/projects/-Users-bruno-sec-llm-workbench/memory/MEMORY.md`
- Change: STAGE-4.1 changed from ✅ COMPLETE (2026-03-12) to ⏳ PENDING

### 4. Created new empty Stage 4.1 directory structure
```
/Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.1-research/          ← empty, fresh
/Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.1-research/round1-online-research/
/Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.1-research/round2-metaproject-scan/
/Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.1-research/round3-gap-analysis/
/Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.1-research/round4-truth-document/
```

### 5. Created orchestrator guidelines file (INCOMPLETE — needs updates per Task C below)
- File: `/Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.1-research/stage4.1-orchestrator-guidelines.md`
- Status: Created but needs updates from this session's findings before Stage 4.1 spawns

---

## TASKS FOR NEXT SESSION (complete in order before starting Stage 4.1)

### Task A: Create Team Management Best Practices File

**Path:** `/Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.1-research/team-management-best-practices.md`

This is a reusable template for future projects. It must be referenced FROM the orchestrator guidelines, not embedded in them. Contents must include all findings below.

**Content to include:**

#### Hard Architectural Constraint
Teammates in a Claude Code team CANNOT spawn other agents or sub-teams. The `Agent`, `TeamCreate`, `TeamDelete` tools are stripped from teammates at spawn time. Only the team lead (main session) can spawn. Teammates have 20 tools vs 25 for standalone subagents.

#### Orchestrator Role
The orchestrator is a PLANNER and COORDINATOR only. It:
- Reads all input files
- Writes its plan to a file
- Sends SendMessage to the team lead specifying exactly what agents to spawn (names, prompts, output paths)
- Waits for agents to complete
- Reads their output files
- Aggregates and sends next round specs to team lead
- Does NOT spawn agents itself — requests spawning from the team lead

#### Team Lead Role (the main Claude Code session)
- Creates team with TeamCreate
- Spawns orchestrator
- Receives agent specifications from orchestrator via SendMessage
- Spawns all agents round by round
- Uses delegate mode (Shift+Tab) to restrict itself to coordination only
- Does NOT use /compact mid-run — use /rewind → Summarize from here instead
- Human approves between rounds

#### Model Assignment
- Orchestrator: `claude-opus-4-6` (Opus — planning, synthesizing)
- All worker agents: `claude-sonnet-4-6` (Sonnet — execution)
- Rationale: Anthropic's own production pattern — Opus for orchestration, Sonnet for execution

#### Communication Pattern
- All communication via SendMessage
- Team lead name in the team = "team-lead" (not claude-main)
- Teammates discover each other via `~/.claude/teams/{team-name}/config.json`
- Direct messages (one-to-one) preferred over broadcast
- Broadcast costs scale linearly — avoid unless all teammates truly need the message

#### File-Based Results Pattern (confirmed best practice)
- Every agent saves full report to a timestamped file
- Agent sends only a 3-5 line summary via SendMessage
- Team lead reads files on demand only when depth is needed
- Naming convention: `{TIMESTAMP}-{round}-{agent-slug}.md`
- Example: `2026-03-13-143022-round1-streamlit-researcher.md`

#### Team Size Limits
- Max 3-5 active teammates at a time
- Use waves for larger rounds (Wave A → Wave B → Wave C)
- Each wave completes before next wave spawns

#### TeammateIdle + TaskCompleted Hooks (released Feb 6, 2026)
- Quality gates that fire when a teammate finishes
- Can auto-run linting/tests
- Exit code 2 blocks task completion
- Register in settings.json
- Claude Code v2.1.32+ required

#### Requires
- `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in settings.json or environment
- Claude Code v2.1.32+

#### Anti-Patterns to Avoid
| Anti-Pattern | Consequence |
|-------------|-------------|
| Two agents editing the same file | Overwrites — one agent's work is lost |
| Vague task specs | Conflicting output formats, incomplete results |
| No plan approval before spawning workers | Inconsistent results across rounds |
| Broadcast instead of direct messages | Token cost multiplies by team size |
| Full /compact mid-run | Breaks teammate communication state |
| Overly large teams | Coordination overhead exceeds gains |
| Orchestrator spawning agents directly | Architecture violation — tools stripped |

---

### Task B: Create Compaction-Proof Handoff Best Practices File

**Path:** `/Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.1-research/compaction-proof-handoff-best-practices.md`

This file must be referenced FROM the orchestrator guidelines. It covers how Stage 4.2 must implement compaction-proof session continuity for SIOPV.

**What we know so far (include this in the file):**
- PreCompact hook fires before every compaction — use it to write a handoff file
- SessionStart hook fires on every session start and post-compaction resume — use it to load the handoff file
- SessionEnd hook fires on normal exit — use it to update the handoff file
- The meta-project already implements this pattern: `briefing.md` is the handoff file, hooks update timestamps and log events
- The handoff file must contain MORE than the compaction summary — it must be a full context recovery document
- Current meta-project example: `/Users/bruno/sec-llm-workbench/.claude/workflow/briefing.md` (the master briefing loaded by session-start.sh)
- Key insight: compaction summary alone is NOT enough — a real handoff file must be maintained separately

**What needs additional research (Task D will fill this in):**
- Best practices for the handoff file format and contents
- What the PreCompact hook should write to the handoff file
- How the SessionStart hook should load the handoff file
- Any new Claude Code 2026 patterns for session continuity beyond what the meta-project already does

> NOTE: This file will be INCOMPLETE until Task D (compaction-proof research sub-agent) is done. Create the file with the known content above and a clear "PENDING RESEARCH" section placeholder.

---

### Task C: Update the Orchestrator Guidelines File

**Path:** `/Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.1-research/stage4.1-orchestrator-guidelines.md`

Read the current file first, then make these specific changes:

1. **Model rule (Section 9 — Absolute Rules):** Replace "All agents use `model: sonnet`" with: "Orchestrator uses `claude-opus-4-6`. All worker agents use `claude-sonnet-4-6`."

2. **Input Files (Section 2):** Add references to:
   - `team-management-best-practices.md` — orchestrator must read it
   - `compaction-proof-handoff-best-practices.md` — orchestrator must read it

3. **Spawning language (Section 7):** Replace current orchestrator-spawning language to reflect the correct architecture: orchestrator requests spawning via SendMessage → team lead spawns. The orchestrator does NOT spawn agents itself.

4. **Delegate mode instruction:** Add instruction that team lead activates delegate mode (Shift+Tab) after spawning orchestrator.

5. **No /compact rule:** Add rule: no /compact mid-run; use /rewind → Summarize from here between rounds only.

6. **Truth document addition (Section 7 — Round 4):** Add `truth-11-compaction-proof-session-continuity.md` to the baseline file list. This is a new truth document that Stage 4.2 must implement session continuity for SIOPV.

---

### Task D: Spawn Sub-Agent for Compaction-Proof Research

Before finalizing `compaction-proof-handoff-best-practices.md` with full content, spawn a sub-agent to research:
- Current best practices (March 2026) for PreCompact/SessionStart/SessionEnd hook patterns
- What a compaction-proof handoff file should contain (format, required sections, update frequency)
- How the meta-project's current implementation compares to March 2026 best practices
- Any new patterns for session continuity in Claude Code 2026
- Whether there are community-established templates or schemas for handoff files

After Task D completes, update the `compaction-proof-handoff-best-practices.md` file with the research findings (replacing the "PENDING RESEARCH" placeholder).

**Do Task D BEFORE finalizing Task B content and BEFORE updating Task C's guidelines file.**

**Correct task order:** D → B (finalize) → C

---

## KEY DECISIONS MADE THIS SESSION

| Decision | Details |
|----------|---------|
| Stage 4.1 re-run from scratch | Old directory backed up as `.old.backup`, new empty directory created |
| Truth document structure | 11 baseline files + additional as needed — numbered truth-00 through truth-10, plus truth-11+ for new findings |
| File action tags | COPY / ADAPT / NEW / DO NOT INCLUDE (no DELETE — meta-project is never touched) |
| Team management = separate file | Reusable template for future projects, referenced from orchestrator guidelines |
| Compaction-proof session continuity = truth-11 | Stage 4.2 must implement this for SIOPV |
| Orchestrator = Opus, workers = Sonnet | Anthropic's own production pattern |
| No /compact mid-run | /rewind → Summarize from here between rounds only |
| Max 3-5 teammates per wave | Round 4 uses Wave A/B/C structure |

---

## STAGE STATUS AT END OF THIS SESSION

| Stage | Status |
|-------|--------|
| STAGE-1 | ✅ COMPLETE (2026-03-11) |
| STAGE-2 | ✅ COMPLETE (2026-03-11) |
| STAGE-3 | ✅ COMPLETE (2026-03-11) |
| STAGE-3.5 | ✅ COMPLETE (2026-03-12) |
| STAGE-4.1 | ⏳ PENDING (re-run from scratch) |
| STAGE-4.2 | ⏳ PENDING |

---

## RELEVANT FILE PATHS

| File | Status | Purpose |
|------|--------|---------|
| `/Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.1-research/stage4.1-orchestrator-guidelines.md` | EXISTS — incomplete | Orchestrator instructions for Stage 4.1 run |
| `/Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.1-research/team-management-best-practices.md` | DOES NOT EXIST — Task A | Reusable team management guide |
| `/Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.1-research/compaction-proof-handoff-best-practices.md` | DOES NOT EXIST — Task B/D | Compaction-proof session continuity guide |
| `/Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.1-research.old.backup/` | EXISTS — do not touch | Backup of previous Stage 4.1 attempt |
| `/Users/bruno/sec-llm-workbench/.claude/workflow/briefing.md` | EXISTS | Master project briefing |
| `/Users/bruno/.claude/projects/-Users-bruno-sec-llm-workbench/memory/MEMORY.md` | EXISTS | Project memory (STAGE-4.1 shows ⏳ PENDING) |
| `/Users/bruno/siopv/AuditPrePhase7-11mar26/stage3.5/stage3.5-final-reports-summarizer-n-aggregator-for-stage4-input-brief.md` | EXISTS | Stage 3.5 aggregated brief — primary input for Stage 4.1 |

---

## SIOPV PROJECT SUMMARY (for context)

**What SIOPV is:** A security vulnerability processing pipeline built with hexagonal architecture.

**Graph flow:** START → authorize → ingest → dlp → enrich → classify → [escalate] → END

**Phase status:**
- Phases 0–6: Complete
- Phase 7 (Human-in-the-Loop — Streamlit): PENDING
- Phase 8 (Output — Jira + PDF): PENDING

**Key metrics (2026-03-05 audit):**
- Tests: 1,404 passed, 12 skipped
- Coverage: 83% overall
- mypy: 0 errors
- ruff: 0 errors

**Key paths in SIOPV:**
| Component | Path |
|-----------|------|
| Graph | `src/siopv/application/orchestration/graph.py` |
| State | `src/siopv/application/orchestration/state.py` |
| CLI | `src/siopv/interfaces/cli/main.py` |
| Settings | `src/siopv/infrastructure/config/settings.py` |
| DI container | `src/siopv/infrastructure/di/__init__.py` |

---

## STAGE-3 KEY VERIFIED FACTS (for Stage 4.1 researchers to cross-check)

| Library | Critical Verified Fact |
|---------|----------------------|
| Streamlit | `@st.fragment(run_every="15s")` — not sleep+rerun |
| Jira v3 | Description requires ADF format — plain strings rejected |
| Jira client | Use `httpx.AsyncClient` — sync libs block event loop |
| fpdf2 | `fname` required in `add_font()` since 2.7 (breaking change) |
| LangGraph | `interrupt()` requires checkpointer at compile time |
| Redis | Use `redis.asyncio` — aioredis merged into redis-py ≥4.2 |
| OTel | `HTTPXClientInstrumentor` does NOT cover module-level `httpx.get()` |
| LIME | Always `plt.close(fig)` after `st.pyplot()` — memory leak prevention |
| Streamlit | Port via `STREAMLIT_SERVER_PORT` env var |

---

## STAGE-3.5 OPEN QUESTIONS (Stage 4.1 must resolve)

These 9 questions were left unresolved at end of Stage 3.5:
1. LangSmith integration specifics for SIOPV
2. Phase 7/8 state field additions — exact TypedDict changes needed
3. Phase 8 exact topology steps in `graph.py._add_edges()`
4. Full fpdf2 API patterns for SIOPV PDF output
5. LangGraph threading constraint details
6. Redis key convention for SIOPV + `aclose()` pattern
7. OTel ordering constraint specifics
8. LIME memory leak — complete mitigation pattern
9. Jira ADF silent failure — validation approach

**Context7 coverage gaps (Stage 4.1 must use official docs directly):**
- LIME: no Context7 coverage
- Jira v3: no Context7 coverage
- Redis (asyncio patterns): no Context7 coverage

---

## DO NOT DO IN NEXT SESSION

- Do NOT start Stage 4.1 before completing Tasks A, B, C, D
- Do NOT touch the old backup directory (`stage4.1-research.old.backup/`)
- Do NOT modify the meta-project files (CLAUDE.md, workflow files, hooks) — reference only
- Do NOT commit anything until Stage 4.1 is complete and verified
- Do NOT use /compact during a Stage 4.1 run once it starts

---

*End of handoff file. This document is self-contained and sufficient to resume the session.*
