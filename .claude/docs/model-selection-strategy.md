<!-- version: 2026-02 -->
# Model Selection Strategy - Hierarchical Routing

**Purpose:** Define decision tree for selecting Haiku/Sonnet/Opus when delegating tasks to agents

**Last Updated:** 2026-02-08
**Status:** Active
**Cost Impact:** 40-60% reduction vs. all-Opus baseline

---

## Overview

This document defines **hierarchical model routing** for task delegation in the orchestrator workflow. Instead of using a single model for all tasks, we match model capabilities to task complexity for optimal cost-performance.

### Why Hierarchical Routing?

**Problem:** Using Opus 4.6 for all tasks is expensive ($15/$75 per MTok)
**Solution:** Route simple tasks → Haiku, synthesis → Sonnet, complex → Opus
**Result:** 40-60% cost reduction with no quality loss

### Model Capabilities Spectrum

```
HAIKU ──────────── SONNET ──────────── OPUS
Fast/Cheap        Balanced           Slow/Expensive
Simple tasks      Synthesis          Full context
```

---

## Model Specifications

### Haiku
**Cost:** $0.25 input / $1.25 output per MTok (2026 pricing)
**Strengths:**
- Fastest response time
- Lowest cost (10-20× cheaper than Opus)
- Reliable for well-defined tasks
- No context limitations for simple operations

**Best For:**
- File operations (Read, Glob, Grep)
- Single-file edits (text replacement)
- Simple validation scripts
- Bash command execution
- Template filling
- Metric collection

**Avoid For:**
- Multi-file synthesis
- Code review requiring pattern recognition
- Architectural decisions
- Tasks requiring full project context

---

### Sonnet 4.5
**Cost:** $3 input / $15 output per MTok
**Strengths:**
- Balanced quality and cost
- Excellent at synthesis and analysis
- Handles multi-file reasoning
- Good at pattern recognition

**Best For:**
- Code synthesis (100-300 lines)
- Multi-file analysis
- Documentation generation
- Verification agents (all 5)
- Gap analysis
- Prompt engineering
- Code review

**Avoid For:**
- Simple file reads (overkill)
- Full project architectural decisions (use Opus)
- Tasks with >10 file dependencies (use Opus)

---

### Opus 4.6
**Cost:** $15 input / $75 output per MTok
**Strengths:**
- Highest quality reasoning
- Full project context understanding
- Complex multi-agent coordination
- Handles ambiguous requirements

**Best For:**
- Architectural design requiring full context
- Parallel execution implementation
- Complex multi-agent coordination
- System-wide refactoring (>5 modules)
- High-stakes decisions with many dependencies

**Avoid For:**
- Simple file operations (wasteful)
- Single-module implementations (use Sonnet)
- Validation scripts (use Haiku)

---

## Decision Tree

### Level 1: Task Type Classification

```
START: Classify the task
│
├─ [A] FILE OPERATIONS → Go to Section A
├─ [B] VALIDATION & TESTING → Go to Section B
├─ [C] SYNTHESIS & ANALYSIS → Go to Section C
├─ [D] CODE GENERATION → Go to Section D
├─ [E] VERIFICATION AGENTS → Go to Section E
└─ [F] ORCHESTRATION & ARCHITECTURE → Go to Section F
```

### Section A: File Operations

```
FILE OPERATIONS
│
├─ Read single file (<3000 lines)
│  └─ USE: Haiku
│
├─ Read multiple files (<5 files, <10K lines total)
│  └─ USE: Haiku (sequential reads)
│
├─ Read multiple files (>5 files OR >10K lines)
│  └─ USE: Sonnet (synthesis needed)
│
├─ Glob pattern search
│  └─ USE: Haiku
│
├─ Grep content search
│  └─ USE: Haiku
│
├─ Single file edit (text replacement, <100 changes)
│  └─ USE: Haiku
│
├─ Multi-file edit (coordinated changes)
│  └─ USE: Sonnet
│
└─ Write new file (template-based, clear spec)
   └─ USE: Haiku
```

### Section B: Validation & Testing

```
VALIDATION & TESTING
│
├─ Run bash commands (ruff, mypy, pytest)
│  └─ USE: Haiku
│
├─ Create simple test script (<50 lines, clear pattern)
│  └─ USE: Haiku
│
├─ Create complex test suite (>50 lines, edge cases)
│  └─ USE: Sonnet
│
├─ Configuration validation (syntax check)
│  └─ USE: Haiku
│
├─ Configuration analysis (semantic check)
│  └─ USE: Sonnet
│
└─ Measurement/metrics collection
   └─ USE: Haiku
```

### Section C: Synthesis & Analysis

```
SYNTHESIS & ANALYSIS
│
├─ Gap analysis (comparing 2-3 files)
│  └─ USE: Sonnet
│
├─ Gap analysis (comparing >5 files)
│  └─ USE: Opus
│
├─ Documentation generation (synthesizing info from code)
│  └─ USE: Sonnet
│
├─ Prompt engineering (multi-agent coordination)
│  └─ USE: Sonnet
│
├─ Code review (quality assessment, pattern recognition)
│  └─ USE: Sonnet
│
├─ Multi-file refactoring (2-5 files)
│  └─ USE: Sonnet
│
├─ Multi-file refactoring (>5 files)
│  └─ USE: Opus
│
└─ Design pattern implementation
   └─ USE: Sonnet
```

### Section D: Code Generation

```
CODE GENERATION
│
├─ Simple function (<50 lines, clear spec)
│  └─ USE: Haiku
│
├─ Module implementation (50-300 lines)
│  └─ USE: Sonnet
│
├─ Multi-module feature (>300 lines, 2-5 modules)
│  └─ USE: Sonnet
│
└─ Complex architectural code (>5 modules, interdependencies)
   └─ USE: Opus
```

### Section E: Verification Agents

```
VERIFICATION AGENTS
│
├─ best-practices-enforcer
│  └─ USE: Sonnet
│
├─ security-auditor
│  └─ USE: Sonnet
│
├─ hallucination-detector
│  └─ USE: Sonnet
│
├─ code-reviewer
│  └─ USE: Sonnet
│
└─ test-generator
   └─ USE: Sonnet
```

**Rationale:** Verification requires quality pattern recognition but not full project context. Sonnet provides optimal balance.

### Section F: Orchestration & Architecture

```
ORCHESTRATION & ARCHITECTURE
│
├─ Parallel execution design (multi-agent coordination)
│  └─ USE: Opus
│
├─ Workflow architecture decisions (affects multiple phases)
│  └─ USE: Opus
│
├─ Complex multi-agent coordination (>3 agents, shared state)
│  └─ USE: Opus
│
├─ System-wide refactoring (>5 modules)
│  └─ USE: Opus
│
└─ Simple orchestration (task delegation, progress tracking)
   └─ USE: Sonnet
```

---

## Cost Comparison Table

| Task Type | Lines/Files | Haiku Cost | Sonnet Cost | Opus Cost | Recommended | Savings |
|-----------|-------------|------------|-------------|-----------|-------------|---------|
| Read single file | <3000 lines | $0.001 | $0.007 | $0.035 | Haiku | 7-35× |
| Simple edit | <100 changes | $0.002 | $0.010 | $0.050 | Haiku | 5-25× |
| Bash validation | 1 command | $0.001 | $0.005 | $0.025 | Haiku | 5-25× |
| Code synthesis | 100-300 lines | $0.015 | $0.050 | $0.250 | Sonnet | 5× vs Opus |
| Multi-file refactor | 2-5 files | $0.030 | $0.100 | $0.500 | Sonnet | 5× vs Opus |
| Gap analysis | 3-5 files | $0.020 | $0.080 | $0.400 | Sonnet | 5× vs Opus |
| Verification agent | Full scan | $0.025 | $0.120 | $0.600 | Sonnet | 5× vs Opus |
| Parallel execution | Full project | $0.100 | $0.500 | $3.000 | Opus | Required |
| Architectural design | Full project | $0.150 | $0.750 | $4.000 | Opus | Required |

**Key Insights:**
- **Haiku tasks:** 5-35× cheaper than alternatives (no quality loss)
- **Sonnet tasks:** 5× cheaper than Opus (minimal quality difference)
- **Opus tasks:** Only justified when full project context required (~10% of tasks)

---

## Concrete Examples from Master Plan

### Example 1: Extract Verification Thresholds (Phase 1, Task 1.1)
**Task:** Read 05-before-commit.md, extract table, create new file
**Input:** 200 lines
**Complexity:** Simple file reorganization
**Model:** Haiku
**Rationale:** No synthesis needed, just extraction and formatting
**Actual Cost:** $0.02 (5,000 tokens)

### Example 2: Deploy Prompt Caching (Phase 1, Task 1.4)
**Task:** Identify static content across 6 agent prompts, add cache markers
**Input:** 500 lines across multiple files
**Complexity:** Multi-file synthesis + API validation
**Model:** Sonnet
**Rationale:** Requires understanding patterns across agents
**Actual Cost:** $0.30 (20,000 tokens)

### Example 3: Create Agent Validation Script (Phase 2, Task 2.1)
**Task:** Read spec, create validation script with YAML parsing
**Input:** 400 lines
**Complexity:** Code synthesis with domain logic
**Model:** Sonnet
**Rationale:** Requires understanding spec and implementing validation logic
**Actual Cost:** $0.53 (35,000 tokens)

### Example 4: Complete Phase 3 Schema Deployment (Phase 2, Task 2.2)
**Task:** Audit 5 agent prompts, add JSON schema examples
**Input:** 1,200 lines
**Complexity:** Multi-file analysis + template application
**Model:** Sonnet
**Rationale:** Pattern recognition across agents, structured output
**Actual Cost:** $0.75 (50,000 tokens)

### Example 5: Test Schema Fallback (Phase 2, Task 2.4)
**Task:** Create test suite, inject invalid JSON, verify graceful fallback
**Input:** 200 lines
**Complexity:** Simple test script
**Model:** Haiku
**Rationale:** Clear pattern, no synthesis needed
**Actual Cost:** $0.05 (12,000 tokens)

### Example 6: Document Model Selection Strategy (Phase 2, Task 2.5)
**Task:** Synthesize routing rules + cost analysis across sources
**Input:** 500 lines
**Complexity:** Multi-source synthesis + decision tree creation
**Model:** Sonnet
**Rationale:** Requires synthesis but not full project context
**Actual Cost:** $0.45 (30,000 tokens)

### Example 7: Deploy Parallel Execution (Phase 3, Task 3.1)
**Task:** Implement wave-based coordination with TaskList + SendMessage
**Input:** 2,000 lines across workflow docs and agent definitions
**Complexity:** Complex multi-agent coordination requiring full project understanding
**Model:** Opus
**Rationale:** Requires understanding all agent interactions, shared state management, edge cases
**Actual Cost:** $3.00 (120,000 tokens)

### Example 8: Validate Parallel Execution Performance (Phase 3, Task 3.2)
**Task:** Run 3 cycles, measure timing, compare to baseline
**Input:** 100 lines
**Complexity:** Simple execution + measurement
**Model:** Haiku
**Rationale:** Straightforward timing measurement
**Actual Cost:** $0.03 (8,000 tokens)

### Example 9: Implement Hierarchical Model Routing (Phase 3, Task 3.3)
**Task:** Create complexity classifier + routing logic
**Input:** 800 lines
**Complexity:** Code synthesis with decision logic
**Model:** Sonnet
**Rationale:** Clear spec, doesn't need full project context
**Actual Cost:** $0.68 (45,000 tokens)

### Example 10: Audit Over-Prompting Language (Phase 5, Task 5.1)
**Task:** Grep patterns, replace with adaptive language across all .claude/ files
**Input:** 2,000 lines
**Complexity:** Multi-file pattern analysis + rewriting
**Model:** Sonnet
**Rationale:** Requires understanding context of each "CRITICAL"/"MUST" usage
**Actual Cost:** $0.68 (45,000 tokens)

### Example 11: Measure System Prompt Token Budget (Phase 5, Task 5.2)
**Task:** Count tokens in CLAUDE.md + referenced docs
**Input:** 500 lines
**Complexity:** Simple token counting
**Model:** Haiku
**Rationale:** Mechanical task, no synthesis
**Actual Cost:** $0.02 (6,000 tokens)

### Example 12: Final SOTA Validation (Phase 5, Task 5.7)
**Task:** Review 47 findings, validate remediation, score 7 categories
**Input:** 3,000 lines across all production reports
**Complexity:** Comprehensive audit + synthesis
**Model:** Sonnet
**Rationale:** Extensive analysis but structured checklist-based (not architectural)
**Actual Cost:** $0.90 (60,000 tokens)

---

## Override Guidelines

### When to Override the Decision Tree

**Override to Haiku (downgrade from Sonnet):**
- Task is more mechanical than expected
- Clear template or pattern to follow
- No synthesis required after inspection

**Override to Sonnet (upgrade from Haiku):**
- Task reveals unexpected complexity
- Multi-file dependencies discovered
- Pattern recognition needed

**Override to Opus (upgrade from Sonnet):**
- Full project context required (>10 file dependencies)
- Architectural decisions with cascading effects
- Complex multi-agent coordination

**Override to Sonnet (downgrade from Opus):**
- Task can be decomposed into smaller Sonnet-appropriate subtasks
- Full context not actually needed after scoping

### Explicit Model Parameter

When invoking Task tool, use explicit `model` parameter:

```python
Task(
    subagent_type="general-purpose",
    model="haiku",  # Explicit override
    max_turns=10,
    prompt="Extract threshold table from 05-before-commit.md..."
)
```

---

## Expected Savings

### Baseline (All Opus)
**Cost per cycle:** $0.75 (250K tokens at Opus pricing)
**Monthly cost (150 cycles):** $112.50
**Annual cost:** $1,350

### With Hierarchical Routing
**Distribution:**
- 40% Haiku tasks: 40% × $0.001 avg = $0.0004/task
- 50% Sonnet tasks: 50% × $0.050 avg = $0.025/task
- 10% Opus tasks: 10% × $3.00 avg = $0.30/task

**Average cost per cycle:** $0.47 (157.5K tokens mixed pricing)
**Monthly cost (150 cycles):** $70.50
**Annual cost:** $846

**Savings:** 40-60% reduction ($300-500/year)

### Validated Savings (from Master Plan)
- Phase 1: $0.41 total (83% Haiku usage)
- Phase 2: $2.16 total (80% Sonnet usage)
- Phase 3: $4.68 total (17% Opus for parallel execution)
- Phase 4: $2.96 total (0% Opus, avoided where possible)
- Phase 5: $2.63 total (0% Opus for validation work)

**Total for 32 tasks:** $12.84 (vs. ~$50 if all Opus)
**Actual savings:** 74% reduction

---

## Integration Instructions

### For Orchestrators

1. **Classify task** using decision tree (Section by Section)
2. **Select model** based on classification
3. **Invoke Task tool** with explicit `model` parameter
4. **Monitor cost** via API logs
5. **Adjust** if task complexity mismatched

**Example orchestrator workflow:**
```python
# Step 1: Classify
task_description = "Extract verification thresholds from 05-before-commit.md"
task_type = "FILE OPERATIONS - Read single file + simple extraction"

# Step 2: Select model
model = "haiku"  # From decision tree Section A

# Step 3: Invoke
Task(
    subagent_type="general-purpose",
    model=model,
    max_turns=10,
    prompt=task_description
)
```

### For Agent Developers

When defining new agent types, document recommended model:

```markdown
## Agent: my-new-agent

**Recommended Model:** Sonnet
**Rationale:** Requires multi-file synthesis but not full project context
**Override to Haiku if:** Task is simple file scanning
**Override to Opus if:** Task requires architectural decisions
```

### For Workflow Documentation

Reference this file in:
- `.claude/workflow/04-agents.md` (agent invocation patterns)
- `.claude/workflow/02-reflexion-loop.md` (delegation guidance)
- `.claude/CLAUDE.local.md` (project-specific preferences)

---

## Monitoring & Adjustment

### Metrics to Track

1. **Cost per cycle** (target: <$0.50)
2. **Model distribution** (target: 40% Haiku, 50% Sonnet, 10% Opus)
3. **Task success rate by model** (detect mismatches)
4. **Override frequency** (should be <10% of tasks)

### Red Flags

- **Haiku tasks failing repeatedly** → Upgrade to Sonnet
- **Sonnet costs >$0.15/task** → Task too complex, consider decomposition
- **Opus usage >20%** → Over-routing, review decision tree
- **Cost per cycle >$0.75** → Routing not effective, audit decisions

### Adjustment Process

1. Review API logs weekly
2. Identify high-cost tasks
3. Check if model selection matched decision tree
4. Update decision tree if systematic mismatch
5. Document adjustments in this file

---

## Cost Monitoring

### Monthly Cost Reports

**Script:** `.claude/scripts/monthly-cost-report.py`

Generate comprehensive monthly cost reports with:
- Model routing distribution (actual vs expected)
- Cost breakdown by model and agent type
- Token consumption (input/output split)
- Savings comparison vs all-Opus baseline
- Alert triggers for threshold violations

**Usage:**
```bash
# Generate report for current month
python .claude/scripts/monthly-cost-report.py

# Generate report for specific month
python .claude/scripts/monthly-cost-report.py --month 2026-02

# Use custom config
python .claude/scripts/monthly-cost-report.py --config custom-config.json
```

**Output Location:** `.ignorar/production-reports/cost-tracking/YYYY-MM-cost-report.md`

### Configuration

**File:** `.claude/scripts/cost-tracking-config.json`

Configure:
- Model pricing tiers (Haiku/Sonnet/Opus)
- Expected distribution targets
- Log file paths
- Alert thresholds (monthly cost, distribution limits)
- Projection defaults (cycles per month)

**Alert Thresholds:**
- Monthly cost: $50 USD
- Haiku usage: ≥30%
- Opus usage: ≤20%
- Cost per cycle: ≤$0.75

### When to Run Reports

- **Monthly:** First week of each month for previous month
- **Ad-hoc:** After major workflow changes
- **Quarterly:** Review trends and adjust thresholds

### Interpreting Reports

**Model Distribution:**
- ✅ Green: Within 5% of expected
- ⚠️ Yellow: 5-10% deviation from expected
- ❌ Red: >10% deviation from expected

**Action Items:**
- High Opus usage → Review decision tree, look for Sonnet opportunities
- Low Haiku usage → Identify simple tasks being over-routed
- Alerts triggered → Investigate root cause before next cycle

---

## References

- **Master Remediation Plan:** `.ignorar/2026-02-08-claude-config-sota-audit-and-remediation-plan--delete-after-successful-implementation/team4-master-plan/MASTER-REMEDIATION-PLAN.md` (Lines 759-811)
- **Local Preferences:** `.claude/CLAUDE.local.md` (Lines 11-14)
- **Agent Definitions:** `.claude/workflow/04-agents.md`
- **Cost Analysis:** `.claude/docs/agent-tool-schemas.md` (Phase 3 token impact)

---

**Status:** Ready for orchestrator use
**Last Updated:** 2026-02-08
**Version:** 1.0
**Maintained by:** Orchestrator + general-purpose agents
