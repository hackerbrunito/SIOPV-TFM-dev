#!/usr/bin/env bash
# Pre-Git-Commit Hook - Bloquea commit si hay archivos sin verificar
# Este hook se ejecuta ANTES de cualquier comando Bash
# Solo actua si el comando es "git commit"
# Output format: hookSpecificOutput (verified via Context7 2026-01-27)
# Reference: .claude/docs/verification-thresholds.md

set -euo pipefail

# Leer JSON de stdin
INPUT=$(cat)

# =============================================================================
# SISTEMA DE TRAZABILIDAD - Log de decisiones de commit
# =============================================================================

log_commit_decision() {
    local decision="$1"  # allowed o blocked
    local reason="$2"

    LOGS_DIR="${CLAUDE_PROJECT_DIR:-.}/.build/logs/decisions"
    mkdir -p "$LOGS_DIR"

    DATE=$(date +%Y-%m-%d)
    LOG_FILE="$LOGS_DIR/${DATE}.jsonl"
    SESSION_ID="${CLAUDE_SESSION_ID:-unknown}"

    # Generar UUID simple
    DECISION_ID=$(uuidgen 2>/dev/null || echo "$(date +%s)-$$")

    echo "{\"id\":\"$DECISION_ID\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"session_id\":\"$SESSION_ID\",\"type\":\"commit\",\"outcome\":\"$decision\",\"reason\":\"$reason\"}" >> "$LOG_FILE"
}

# Extraer el comando del JSON
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)

# Si no es un comando git commit, permitir (sin loggear)
if [[ "$COMMAND" != *"git commit"* ]]; then
    cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow"
  }
}
EOF
    exit 0
fi

# Es un git commit - verificar markers pendientes
# Check the active project's pending dir (post-code.sh writes markers there)
ACTIVE_PROJECT=$(cat "${CLAUDE_PROJECT_DIR:-.}/.build/active-project" 2>/dev/null || echo "")
ACTIVE_PROJECT="${ACTIVE_PROJECT/#\~/$HOME}"  # expand ~ to absolute path
if [ -n "$ACTIVE_PROJECT" ] && [ -d "$ACTIVE_PROJECT" ]; then
    VERIFICATION_DIR="$ACTIVE_PROJECT/.build/checkpoints/pending"
else
    VERIFICATION_DIR="${CLAUDE_PROJECT_DIR:-.}/.build/checkpoints/pending"
fi

# Si no existe el directorio, no hay nada pendiente
if [ ! -d "$VERIFICATION_DIR" ]; then
    log_commit_decision "allowed" "no_pending_dir"
    cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow"
  }
}
EOF
    exit 0
fi

# Contar archivos pendientes de verificacion
PENDING_COUNT=$(find "$VERIFICATION_DIR" -type f 2>/dev/null | wc -l | tr -d ' ')

if [ "$PENDING_COUNT" -gt 0 ]; then
    # Obtener lista de archivos pendientes
    PENDING_FILES=""
    for marker in "$VERIFICATION_DIR"/*; do
        if [ -f "$marker" ]; then
            FILE_PATH=$(jq -r '.file' "$marker" 2>/dev/null || echo "unknown")
            PENDING_FILES="${PENDING_FILES}- ${FILE_PATH}\n"
        fi
    done

    # Loggear decisión de bloqueo
    log_commit_decision "blocked" "pending_verification:${PENDING_COUNT}"

    # Bloquear commit
    cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "COMMIT BLOQUEADO: Hay ${PENDING_COUNT} archivo(s) Python sin verificar por agentes. Archivos pendientes: ${PENDING_FILES}ACCION REQUERIDA: Ejecuta /verify para correr los agentes de verificacion, despues intenta commit de nuevo."
  }
}
EOF
    exit 0
fi

# Verificar code-reviewer score threshold (>= 9.0/10)
SCORE_CHECK_SCRIPT="${CLAUDE_PROJECT_DIR:-.}/.claude/scripts/check-reviewer-score.sh"

if [ -f "$SCORE_CHECK_SCRIPT" ]; then
    # Ejecutar verificación de score y capturar output
    SCORE_OUTPUT=$(bash "$SCORE_CHECK_SCRIPT" 2>&1)
    SCORE_EXIT_CODE=$?

    if [ $SCORE_EXIT_CODE -ne 0 ]; then
        # Score check FAILED (< 9.0/10)
        log_commit_decision "blocked" "code_reviewer_score_below_threshold"

        cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "COMMIT BLOQUEADO: Code reviewer score no cumple con threshold >= 9.0/10.\n\n${SCORE_OUTPUT}\n\nACCION REQUERIDA: Corrige los problemas de calidad identificados y ejecuta /verify nuevamente."
  }
}
EOF
        exit 0
    else
        # Score check PASSED or WARNING (graceful degradation)
        # Si el output contiene WARNING, loggear pero permitir
        if echo "$SCORE_OUTPUT" | grep -q "WARNING"; then
            log_commit_decision "allowed" "code_reviewer_score_warning:first_time_or_parse_failed"
        else
            log_commit_decision "allowed" "code_reviewer_score_passed"
        fi
    fi
fi

# Loggear decisión de permitir
log_commit_decision "allowed" "all_verified"

# Todo verificado, permitir commit
cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow"
  }
}
EOF
exit 0
