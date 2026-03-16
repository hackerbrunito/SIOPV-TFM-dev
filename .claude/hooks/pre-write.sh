#!/usr/bin/env bash
# Pre-write hook: Middleware pattern con additionalContext
# Requiere Claude Code 2.1.9+
# Sistema 2026 - Reemplaza Anti-Autopilot
# Output format: hookSpecificOutput (verified via Context7 2026-01-27)

set -euo pipefail

TODAY=$(date +%Y%m%d)

# Verificar checkpoints diarios (opcionales, solo recordatorio)
MISSING_DOCS=()

if [[ ! -f "${CLAUDE_PROJECT_DIR:-.}/.build/checkpoints/daily/orchestrator-read-${TODAY}" ]]; then
    MISSING_DOCS+=("workflow docs")
fi

if [[ ! -f "${CLAUDE_PROJECT_DIR:-.}/.build/checkpoints/daily/spec-read-${TODAY}" ]]; then
    MISSING_DOCS+=("project specification")
fi

if [[ ! -f "${CLAUDE_PROJECT_DIR:-.}/.build/checkpoints/daily/errors-read-${TODAY}" ]]; then
    MISSING_DOCS+=("errors-to-rules.md")
fi

# Si faltan documentos, inyectar contexto como recordatorio (no bloquear)
if [[ ${#MISSING_DOCS[@]} -gt 0 ]]; then
    DOCS_LIST=$(printf '%s' "${MISSING_DOCS[0]}"; for doc in "${MISSING_DOCS[@]:1}"; do printf ', %s' "$doc"; done)

    cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "ask",
    "permissionDecisionReason": "Faltan checkpoints de lectura de documentacion. Ejecuta /init-session para crearlos.",
    "additionalContext": "RECORDATORIO: Antes de Write/Edit, verifica que hayas consultado: ${DOCS_LIST}. Esto previene errores de piloto automatico. Para crear checkpoints ejecuta: /init-session"
  }
}
EOF
    exit 0
fi

# Si todos los checkpoints existen, permitir sin preguntar
cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow"
  }
}
EOF
exit 0
