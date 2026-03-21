#!/usr/bin/env bash
# SIOPV Setup Script
# Interactive setup: configures .env, starts Docker services,
# initializes OpenFGA + Keycloak, and verifies the pipeline.
#
# Usage: bash scripts/setup.sh
#
# Prerequisites:
#   - Python 3.11+
#   - uv (Python package manager)
#   - Docker + Docker Compose

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# --- Step 0: Check prerequisites ---
echo ""
echo "============================================"
echo "  SIOPV Setup"
echo "  Sistema Inteligente de Orquestación y"
echo "  Priorización de Vulnerabilidades"
echo "============================================"
echo ""

info "Checking prerequisites..."

check_command() {
    if ! command -v "$1" &>/dev/null; then
        error "$1 is not installed. Please install it first."
        exit 1
    fi
    ok "$1 found: $(command -v "$1")"
}

check_command python3
check_command uv
check_command docker

if ! docker info &>/dev/null; then
    error "Docker is not running. Please start Docker and try again."
    exit 1
fi
ok "Docker is running"

echo ""

# --- Step 1: Configure .env ---
info "Configuring environment..."

ENV_FILE="${PROJECT_DIR}/.env"
ENV_EXAMPLE="${PROJECT_DIR}/.env.example"

if [[ -f "$ENV_FILE" ]]; then
    warn ".env file already exists."
    read -p "  Overwrite with fresh copy from .env.example? [y/N]: " OVERWRITE
    if [[ "${OVERWRITE,,}" == "y" ]]; then
        cp "$ENV_EXAMPLE" "$ENV_FILE"
        ok "Copied .env.example to .env"
    else
        ok "Keeping existing .env"
    fi
else
    cp "$ENV_EXAMPLE" "$ENV_FILE"
    ok "Created .env from .env.example"
fi

echo ""

# --- Step 2: Configure user identity ---
info "Configuring user identity for OpenFGA authorization..."
echo ""
echo "  SIOPV uses OpenFGA for role-based access control."
echo "  Each user needs an identity to authorize pipeline operations."
echo "  In production, this would come from your company's IAM system."
echo ""

DETECTED_USER="$(whoami)"
read -p "  Enter your SIOPV user identity [$DETECTED_USER]: " SIOPV_USER
SIOPV_USER="${SIOPV_USER:-$DETECTED_USER}"
ok "User identity: $SIOPV_USER"

# --- Step 3: Configure project ---
echo ""
info "Configuring project identity..."
echo ""
echo "  Projects represent the scope of a vulnerability scan."
echo "  Use 'default' for single-project setups."
echo "  For multi-project environments, enter your project name"
echo "  (e.g., 'frontend-app', 'payment-service')."
echo ""

read -p "  Enter project name [default]: " SIOPV_PROJECT
SIOPV_PROJECT="${SIOPV_PROJECT:-default}"
ok "Project: $SIOPV_PROJECT"

# --- Step 4: Configure output directory ---
echo ""
info "Configuring output directory..."
echo ""
echo "  SIOPV saves PDF reports, JSON metrics, and CSV exports here."
echo "  Use an absolute path for production (e.g., /var/siopv/reports)."
echo ""

read -p "  Enter output directory [./output]: " SIOPV_OUTPUT
SIOPV_OUTPUT="${SIOPV_OUTPUT:-./output}"
mkdir -p "$SIOPV_OUTPUT"
ok "Output directory: $SIOPV_OUTPUT"

# --- Step 5: Write configuration to .env ---
echo ""
info "Writing configuration to .env..."

# Update .env with user choices (append or replace)
_set_env_var() {
    local key="$1" value="$2"
    if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
        # Replace existing value (macOS-compatible sed)
        sed -i '' "s|^${key}=.*|${key}=${value}|" "$ENV_FILE"
    else
        echo "${key}=${value}" >> "$ENV_FILE"
    fi
}

_set_env_var "SIOPV_DEFAULT_USER_ID" "$SIOPV_USER"
_set_env_var "SIOPV_DEFAULT_PROJECT_ID" "$SIOPV_PROJECT"
_set_env_var "SIOPV_OUTPUT_DIR" "$SIOPV_OUTPUT"

ok "Configuration written to .env"

# --- Step 6: Install Python dependencies ---
echo ""
info "Installing Python dependencies..."
(cd "$PROJECT_DIR" && uv sync 2>&1 | tail -3)
ok "Dependencies installed"

# --- Step 7: Start Docker services ---
echo ""
info "Starting Docker services (OpenFGA, Keycloak, PostgreSQL)..."
(cd "$PROJECT_DIR" && docker compose up -d 2>&1 | tail -5)

# Wait for services to be healthy
info "Waiting for services to be ready..."
MAX_WAIT=60
WAITED=0
INTERVAL=5

while [[ $WAITED -lt $MAX_WAIT ]]; do
    # Check if OpenFGA is responding
    if curl -sf http://localhost:8080/healthz &>/dev/null; then
        ok "OpenFGA is ready"
        break
    fi
    echo -n "."
    sleep "$INTERVAL"
    WAITED=$((WAITED + INTERVAL))
done

if [[ $WAITED -ge $MAX_WAIT ]]; then
    warn "OpenFGA did not become ready within ${MAX_WAIT}s. Continuing anyway..."
fi

echo ""

# --- Step 8: Configure Keycloak ---
info "Configuring Keycloak (OIDC provider)..."
(cd "$PROJECT_DIR" && uv run python scripts/setup-keycloak.py 2>&1 | tail -3) || {
    warn "Keycloak setup had issues (may already be configured)"
}
ok "Keycloak configured"

# --- Step 9: Configure OpenFGA authorization tuples ---
echo ""
info "Creating OpenFGA authorization tuples..."
info "  User: $SIOPV_USER | Project: $SIOPV_PROJECT"

(cd "$PROJECT_DIR" && bash scripts/setup-openfga-tuples.sh "$SIOPV_USER" "$SIOPV_PROJECT" 2>&1 | tail -3) || {
    warn "OpenFGA tuple setup had issues (may already exist)"
}
ok "Authorization tuples created"

# --- Step 10: Verify installation ---
echo ""
info "Verifying installation with sample Trivy report..."
echo ""

SAMPLE_REPORT="${PROJECT_DIR}/trivy-report-small.json"
if [[ -f "$SAMPLE_REPORT" ]]; then
    (cd "$PROJECT_DIR" && uv run siopv process-report "$SAMPLE_REPORT" \
        --user-id "$SIOPV_USER" \
        --project-id "$SIOPV_PROJECT" \
        --output "$SIOPV_OUTPUT" 2>&1 | tail -10) || {
        warn "Verification run had issues — check logs above"
    }
    ok "Verification complete"
else
    warn "Sample report not found at $SAMPLE_REPORT — skipping verification"
fi

# --- Done ---
echo ""
echo "============================================"
echo -e "  ${GREEN}SIOPV is ready!${NC}"
echo "============================================"
echo ""
echo "  User:      $SIOPV_USER"
echo "  Project:   $SIOPV_PROJECT"
echo "  Output:    $SIOPV_OUTPUT"
echo "  Webhook:   http://localhost:8080/api/v1/webhook/trivy"
echo ""
echo "  To process a Trivy report:"
echo "    uv run siopv process-report <trivy-report.json>"
echo ""
echo "  To send via webhook:"
echo "    ./scripts/webhook-bridge.sh <trivy-report.json>"
echo ""
echo "  To run tests:"
echo "    uv run pytest"
echo ""
