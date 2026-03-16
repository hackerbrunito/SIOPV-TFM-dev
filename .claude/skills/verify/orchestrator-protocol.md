# Orchestrator Protocol

This document is read and executed by the orchestrator agent.

## Orchestrator Responsibilities

- Drive the full pipeline from pre-wave through Wave 9
- For each wave: send spawn request -> wait for confirmation -> wait for agents -> collect results -> send wave report -> wait for approval
- **Never spawn agents directly** — only team-lead can spawn
- **Never communicate with human directly** — only through team-lead
- Compute file batch assignments before each spawn request
- Compute fixer count formula at runtime (not hardcoded)

## Communication Protocols

**Spawn request (orchestrator -> team-lead):**
```
SendMessage(to="team-lead", message="SPAWN REQUEST — {Wave name}:
Agent 1: name={name}, assigned_files=[{list}], prompt={full prompt}")
```

**Agent completion (agent -> orchestrator):**
```
SendMessage(to="orchestrator", message="{WAVE} AGENT {name} COMPLETE: {PASS|FAIL} — {summary}")
```

**Wave report (orchestrator -> team-lead):**
```
SendMessage(to="team-lead", message="{WAVE} REPORT:
{agent}: PASS/FAIL — {summary}
...
Overall: PASS/FAIL
Awaiting human approval to proceed.")
```

**If wave FAILS:**
- Send wave report with FAIL status and proposed fixes (with confidence levels)
- STOP. Wait for team-lead to relay human decision.
- Do NOT fix anything autonomously.

---

## PRE-CHECKS (before pre-wave)

```bash
TARGET="/Users/bruno/siopv"
VERIFY_DIR="${TARGET}/.verify-$(date +%d-%m-%Y)"

# Secrets scan (non-blocking)
bash .claude/scripts/scan-git-history-for-secrets.sh "$TARGET" 2>/dev/null || true

# Identify pending files
PENDING_FILES=$(ls "$TARGET/.build/checkpoints/pending/" 2>/dev/null)
if [ -z "$PENDING_FILES" ]; then
  echo "No pending files to verify — pipeline complete."
  exit 0
fi

# Validate project
[ ! -f "$TARGET/pyproject.toml" ] && echo "ERROR: not a valid Python project" && exit 1
echo "Validated: $TARGET — pending files found"
```

**File batch computation (orchestrator does this before each spawn request):**

```bash
# List pending marker files — each marker filename is the source file path (encoded)
ls "$TARGET/.build/checkpoints/pending/" | while read marker; do
  echo "$TARGET/src/siopv/$(echo $marker | sed 's/__/\//g' | sed 's/.marker//')"
done
```

Split the resulting list into batches of 5 files. Each scanner agent gets exactly one batch.
If 31 files: 7 batches (6 x 5 files + 1 x 1 file). Spawn one agent per batch per domain.

---

## Post-Wave Actions (orchestrator runs after ALL waves pass)

```bash
TARGET="/Users/bruno/siopv"

# Final ruff + mypy pass
uv run ruff format src tests --check
uv run ruff check src tests
uv run mypy src

# Full test suite with coverage
uv run pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=xml --cov-fail-under=83

# Per-module coverage floor (90% per module)
python3 /Users/bruno/siopv/.claude/scripts/check-module-coverage.py "$TARGET"
```

With `--fix`:
```bash
uv run ruff format src tests
uv run ruff check src tests --fix
```

Notify team-lead when complete:
```
SendMessage(to="team-lead", message="ALL WAVES PASSED. Marker cleanup complete. Verifications passed. Ready for TeamDelete.")
```

---

## JSONL Logging (orchestrator responsibility)

After each wave, log to `.build/logs/agents/YYYY-MM-DD.jsonl`:

```json
{
  "id": "<uuid>",
  "timestamp": "<ISO8601>",
  "session_id": "<session_id>",
  "agent": "<agent_name>",
  "wave": "<wave_name>",
  "files": ["<file1>", "<file2>"],
  "status": "PASSED|FAILED",
  "findings": [],
  "duration_ms": 0
}
```

If agents report findings, also log to `.build/logs/decisions/YYYY-MM-DD.jsonl`:

```json
{
  "id": "<uuid>",
  "timestamp": "<ISO8601>",
  "session_id": "<session_id>",
  "agent": "<agent_name>",
  "type": "finding",
  "severity": "CRITICAL|HIGH|MEDIUM|LOW",
  "finding": "<description>",
  "file": "<file>",
  "outcome": "flagged|fixed"
}
```
