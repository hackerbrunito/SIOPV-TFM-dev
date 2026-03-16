#!/usr/bin/env bash
# pre-compact.sh — Fires before compaction; updates timestamp, generates brief
trap 'exit 0' ERR

INPUT=$(cat)
TRANSCRIPT=$(echo "$INPUT" | jq -r '.transcript_path // empty')
BRIEFING="${CLAUDE_PROJECT_DIR:-.}/.claude/workflow/briefing.md"
COMPACT_LOG="${CLAUDE_PROJECT_DIR:-.}/.claude/workflow/compaction-log.md"
TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# Bug #13668: transcript_path can be null/empty — fallback to most recent JSONL
if [[ -z "$TRANSCRIPT" || "$TRANSCRIPT" == "null" ]]; then
  TRANSCRIPT=$(ls -t ~/.claude/projects/*/*.jsonl 2>/dev/null | head -1)
fi

# Generate recovery brief from transcript tail (async: true in settings.json)
if [[ -f "$TRANSCRIPT" ]]; then
  BRIEF_PATH="${CLAUDE_PROJECT_DIR:-.}/.claude/workflow/pre-compact-brief-${TIMESTAMP}.md"
  tail -100 "$TRANSCRIPT" | claude -p \
    "Generate compact SIOPV recovery brief: current task, key decisions, next action, files modified. Max 30 lines." \
    --print > "$BRIEF_PATH" 2>/dev/null &
fi

# Update timestamp in briefing.md
if [[ -f "$BRIEFING" ]] && grep -q "^> Last updated:" "$BRIEFING"; then
  perl -i -pe "s|^> Last updated:.*|> Last updated: ${TIMESTAMP}|" "$BRIEFING"
fi

# Append to compaction log
[[ ! -f "$COMPACT_LOG" ]] && echo "# SIOPV Compaction Log" > "$COMPACT_LOG"
echo "- ${TIMESTAMP} — PreCompact fired" >> "$COMPACT_LOG"

# Prune compaction log to last 30 entries (keep header lines + last 30 data lines)
HEADER_LINES=$(grep -c "^#\|^$\|^Entries" "$COMPACT_LOG" 2>/dev/null || echo 5)
TOTAL_LINES=$(wc -l < "$COMPACT_LOG")
DATA_LINES=$((TOTAL_LINES - HEADER_LINES))
if [ "$DATA_LINES" -gt 30 ]; then
    HEAD_CONTENT=$(head -n "$HEADER_LINES" "$COMPACT_LOG")
    TAIL_CONTENT=$(tail -n 30 "$COMPACT_LOG")
    printf '%s\n%s\n' "$HEAD_CONTENT" "$TAIL_CONTENT" > "$COMPACT_LOG"
fi

echo "PreCompact: timestamp updated, brief spawned" >&2
exit 0
