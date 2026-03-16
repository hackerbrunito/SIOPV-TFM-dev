#!/usr/bin/env bash
# session-start.sh — Inject SIOPV briefing at every session start/resume/compact
trap 'exit 0' ERR

BRIEFING="${CLAUDE_PROJECT_DIR:-.}/.claude/workflow/briefing.md"
COMPACT_LOG="${CLAUDE_PROJECT_DIR:-.}/.claude/workflow/compaction-log.md"

# Idempotency guard: --continue fires both startup AND resume (bug workaround)
SESSION_ID="${CLAUDE_SESSION_ID:-default}"
LOCK="/tmp/siopv-session-start-${SESSION_ID}.lock"
if [[ -f "$LOCK" ]]; then exit 0; fi
touch "$LOCK"

if [[ -f "$BRIEFING" ]]; then
  echo "========================================================"
  echo "  SIOPV SESSION START — Loading master briefing"
  echo "========================================================"
  cat "$BRIEFING"
  echo ""
fi

if [[ -f "$COMPACT_LOG" ]]; then
  echo "========================================================"
  echo "  COMPACTION LOG — Last 5 entries"
  echo "========================================================"
  tail -n 5 "$COMPACT_LOG"
  echo ""
fi

exit 0
