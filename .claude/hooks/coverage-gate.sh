#!/usr/bin/env bash
# coverage-gate.sh — PostToolUse: check pytest coverage >= 83%
# Non-blocking hook; writes pending marker to block commit if coverage regresses.

trap 'exit 0' ERR

INPUT=$(cat)

COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)
if [[ "$COMMAND" != *"pytest"* ]] || [[ "$COMMAND" != *"--cov"* ]]; then
    exit 0
fi

OUTPUT=$(echo "$INPUT" | jq -r '.tool_response // empty' 2>/dev/null)
COVERAGE=$(echo "$OUTPUT" | grep -oE 'TOTAL[[:space:]]+[0-9]+[[:space:]]+[0-9]+[[:space:]]+([0-9]+)%' \
    | grep -oE '[0-9]+%$' | tr -d '%' | tail -1)

if [[ -z "$COVERAGE" ]]; then
    exit 0
fi

THRESHOLD=83
if [[ "$COVERAGE" -lt "$THRESHOLD" ]]; then
    VERIFICATION_DIR="${CLAUDE_PROJECT_DIR:-.}/.build/checkpoints/pending"
    mkdir -p "$VERIFICATION_DIR"
    cat > "$VERIFICATION_DIR/coverage-below-threshold" << EOF
{
  "file": "coverage-check",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "verified": false,
  "reason": "Coverage ${COVERAGE}% below threshold ${THRESHOLD}%"
}
EOF
    echo "COVERAGE GATE: ${COVERAGE}% < ${THRESHOLD}% threshold. Commit blocked until coverage is restored." >&2
fi

exit 0
