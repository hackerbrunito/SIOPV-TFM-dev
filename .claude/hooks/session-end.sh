#!/usr/bin/env bash
# session-end.sh — Timestamp update + log entry on session exit
# Hard limit: 1.5 second timeout — keep this minimal
trap 'exit 0' ERR

BRIEFING="${CLAUDE_PROJECT_DIR:-.}/.claude/workflow/briefing.md"
COMPACT_LOG="${CLAUDE_PROJECT_DIR:-.}/.claude/workflow/compaction-log.md"
TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

if [[ -f "$BRIEFING" ]] && grep -q "^> Last updated:" "$BRIEFING"; then
  perl -i -pe "s|^> Last updated:.*|> Last updated: ${TIMESTAMP}|" "$BRIEFING"
fi

[[ ! -f "$COMPACT_LOG" ]] && echo "# SIOPV Compaction Log" > "$COMPACT_LOG"
echo "- ${TIMESTAMP} — SessionEnd fired (normal exit)" >> "$COMPACT_LOG"
exit 0
