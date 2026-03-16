# Output Directory Structure

All verify output goes to a dated directory created at runtime:

```bash
VERIFY_DIR="/Users/bruno/siopv/.verify-$(date +%d-%m-%Y)"
mkdir -p "$VERIFY_DIR"/{context7-cache,scans,fixes,reports,handoffs}
```

Structure:
```
.verify-{DD}-{MM}-{YYYY}/
├── context7-cache/
│   ├── BRIEFING.md              <- library facts summary (written by pre-wave researcher)
│   └── {library}.md             <- one file per library (pydantic, httpx, etc.)
├── scans/
│   ├── scan-bpe-{ts}.json
│   ├── scan-security-{ts}.json
│   ├── scan-hallucination-{ts}.json
│   └── findings-consolidated-{ts}.json
├── fixes/
│   ├── fixed-batch-{N}-{ts}.json
│   └── fix-validation-{ts}.json
├── reports/
│   └── {wave}-{agent}-{ts}.md
└── handoffs/
    └── handoff-{agent-name}.md
```

---

## Marker System

- `post-code.sh` creates markers in `.build/checkpoints/pending/` after Write/Edit on .py files
- `pre-git-commit.sh` blocks commits if pending markers exist
- `/verify` runs agents and clears markers when Wave 3B validator confirms all checks pass

## Traceability System

- Agent logs: `.build/logs/agents/YYYY-MM-DD.jsonl`
- Decision logs: `.build/logs/decisions/YYYY-MM-DD.jsonl`
- Verify output: `/Users/bruno/siopv/.verify-{DD}-{MM}-{YYYY}/`
