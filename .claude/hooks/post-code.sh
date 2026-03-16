#!/usr/bin/env bash
# =============================================================================
# Post-Code Hook - META-PROYECTO
# =============================================================================
# Ejecutado automáticamente después de Write/Edit
# 1. Formatea código con ruff
# 2. Marca archivo como "pendiente de verificación por agentes"
# 3. Registra decisión en sistema de trazabilidad
# =============================================================================

set -euo pipefail

# Leer JSON de stdin
INPUT=$(cat)

# =============================================================================
# SISTEMA DE TRAZABILIDAD - Log de decisiones
# =============================================================================

log_decision() {
    local file_path="$1"
    local tool_name="$2"

    LOGS_DIR="${CLAUDE_PROJECT_DIR:-.}/.build/logs/decisions"
    mkdir -p "$LOGS_DIR"

    DATE=$(date +%Y-%m-%d)
    LOG_FILE="$LOGS_DIR/${DATE}.jsonl"
    SESSION_ID="${CLAUDE_SESSION_ID:-unknown}"

    # Generar UUID simple
    DECISION_ID=$(uuidgen 2>/dev/null || echo "$(date +%s)-$$")

    echo "{\"id\":\"$DECISION_ID\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"session_id\":\"$SESSION_ID\",\"type\":\"code_change\",\"tool\":\"$tool_name\",\"file\":\"$file_path\",\"outcome\":\"written\"}" >> "$LOG_FILE"
}

# Extraer file_path y tool_name del JSON
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // "unknown"' 2>/dev/null)

# Si no hay file_path, salir
if [ -z "$FILE_PATH" ]; then
    exit 0
fi

# Registrar decisión de cambio de código
log_decision "$FILE_PATH" "$TOOL_NAME"

# Solo procesar archivos Python
if [[ "$FILE_PATH" != *.py ]]; then
    exit 0
fi

# Verificar que el archivo existe
if [ ! -f "$FILE_PATH" ]; then
    exit 0
fi

# Obtener directorio del proyecto (buscar pyproject.toml hacia arriba)
PROJECT_DIR=$(dirname "$FILE_PATH")
while [ "$PROJECT_DIR" != "/" ]; do
    if [ -f "$PROJECT_DIR/pyproject.toml" ]; then
        break
    fi
    PROJECT_DIR=$(dirname "$PROJECT_DIR")
done

# Si encontramos pyproject.toml, formatear
if [ -f "$PROJECT_DIR/pyproject.toml" ]; then
    cd "$PROJECT_DIR"
    uv run ruff format "$FILE_PATH" 2>/dev/null || true
    uv run ruff check "$FILE_PATH" --fix 2>/dev/null || true
fi

# =============================================================================
# SISTEMA DE VERIFICACIÓN PENDIENTE
# =============================================================================
# Marcar que este archivo necesita verificación por agentes antes de commit

# Store markers in the TARGET project's .build/, not the meta-project's
if [ -f "$PROJECT_DIR/pyproject.toml" ]; then
    VERIFICATION_DIR="$PROJECT_DIR/.build/checkpoints/pending"
else
    VERIFICATION_DIR="${CLAUDE_PROJECT_DIR:-.}/.build/checkpoints/pending"
fi
mkdir -p "$VERIFICATION_DIR"

# Crear marker con hash del archivo para tracking
FILE_HASH=$(echo "$FILE_PATH" | if command -v md5sum &>/dev/null; then md5sum; else md5; fi | cut -c1-8)
MARKER_FILE="$VERIFICATION_DIR/$FILE_HASH"

# Guardar info del archivo pendiente
cat > "$MARKER_FILE" << EOF
{
  "file": "$FILE_PATH",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "verified": false
}
EOF

exit 0
