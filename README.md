# SIOPV

**Sistema Inteligente de Orquestación y Priorización de Vulnerabilidades**

SIOPV is an automated vulnerability analysis pipeline that receives Trivy scan reports, enriches them with threat intelligence from multiple sources (NVD, EPSS, GitHub Security Advisories), classifies risk using ML models, and delivers prioritized results as Jira tickets and PDF audit reports. It is designed to operate as a downstream component in CI/CD pipelines, processing vulnerability data automatically with built-in authorization, privacy controls, and human-in-the-loop escalation.

---

## Architecture

SIOPV follows a hexagonal (ports & adapters) architecture with an 8-phase LangGraph pipeline:

```
Trivy Scan → Webhook/CLI → SIOPV Pipeline → Jira Tickets + PDF Report
```

### Pipeline Flow

```
START → authorize → ingest → dlp → enrich → classify → [escalate] → output → END
```

| Phase | Node | Description |
|-------|------|-------------|
| 1 | **authorize** | OpenFGA role-based access control — verifies user has permission on the project |
| 2 | **ingest** | Parses Trivy JSON report into structured vulnerability records |
| 3 | **dlp** | Presidio-based PII detection and anonymization of sensitive data |
| 4 | **enrich** | CRAG pattern — queries NVD, EPSS, GitHub Advisories, with OSINT fallback |
| 5 | **classify** | ML risk classification (XGBoost) with LLM confidence evaluation |
| 6 | **escalate** | Human-in-the-loop review for high-uncertainty classifications |
| 7 | **output** | Generates Jira tickets, PDF audit reports, JSON/CSV metrics exports |

### Hexagonal Layers

```
domain/          — entities, value objects, ports (interfaces), constants
application/     — use cases, orchestration (LangGraph graph + nodes + state)
adapters/        — inbound (webhook, CLI) + outbound (NVD, EPSS, Jira, ChromaDB, etc.)
infrastructure/  — DI container, config/settings, logging, persistence
interfaces/      — CLI entry point, Streamlit dashboard
```

---

## Prerequisites

- **Python 3.11+**
- **[uv](https://docs.astral.sh/uv/)** — Python package manager
- **Docker + Docker Compose** — for OpenFGA, Keycloak, and PostgreSQL

---

## Installation & Setup

### 1. Clone the repository

```bash
git clone https://github.com/hackerbrunito/SIOPV-TFM.git
cd SIOPV-TFM
```

### 2. Run the setup script

```bash
bash scripts/setup.sh
```

The setup script will:
1. Check prerequisites (Python, uv, Docker)
2. Create `.env` from `.env.example`
3. Ask for your **user identity** for OpenFGA authorization (detects your system username)
4. Ask for a **project name** (default: `default` for single-project setups)
5. Ask for an **output directory** for reports (default: `./output`)
6. Install Python dependencies via `uv sync`
7. Start Docker services (OpenFGA, Keycloak, PostgreSQL)
8. Configure Keycloak OIDC provider
9. Create OpenFGA authorization tuples for your user and project
10. Verify the installation by processing a sample Trivy report (25 CVEs)

### 3. Configure API keys

Edit `.env` and add your API keys:

```bash
# Required for full enrichment
SIOPV_ANTHROPIC_API_KEY=sk-ant-...    # LLM confidence evaluation
SIOPV_NVD_API_KEY=...                 # NVD enrichment (higher rate limits)

# Required for Jira ticket creation
SIOPV_JIRA_URL=https://your-domain.atlassian.net
SIOPV_JIRA_EMAIL=your-email@example.com
SIOPV_JIRA_API_TOKEN=...
SIOPV_JIRA_PROJECT_KEY=...

# Optional
SIOPV_GITHUB_TOKEN=ghp_...            # GitHub Security Advisories
SIOPV_TAVILY_API_KEY=tvly-...         # OSINT fallback search
```

The pipeline runs without these keys but with reduced functionality:
- Without `ANTHROPIC_API_KEY`: LLM confidence uses heuristic fallback
- Without `NVD_API_KEY`: NVD queries use lower rate limits
- Without `JIRA_*`: No Jira tickets created (PDF and CSV still generated)

---

## Usage

### Webhook Mode (Production)

SIOPV listens on a webhook endpoint for Trivy scan reports from CI/CD pipelines. This is the primary production mode.

**Endpoint:** `POST /api/v1/webhook/trivy`

When a CI/CD pipeline completes a Trivy scan, it sends the JSON report to SIOPV's webhook with an HMAC-SHA256 signature. SIOPV verifies the signature, returns `202 Accepted`, and processes the report asynchronously through the full pipeline.

#### CI/CD Integration

Add these lines to your CI/CD pipeline after the Trivy scan step:

```bash
# Generate HMAC-SHA256 signature
PAYLOAD=$(cat trivy-report.json)
SIGNATURE=$(printf '%s' "$PAYLOAD" | openssl dgst -sha256 -hmac "$SIOPV_WEBHOOK_SECRET" | sed 's/^.* //')

# Send to SIOPV
curl -sf -X POST \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Signature-256: sha256=${SIGNATURE}" \
  -d "$PAYLOAD" \
  http://your-siopv-host:8080/api/v1/webhook/trivy
```

This works in **GitHub Actions**, **Jenkins**, **GitLab CI**, or any CI/CD system that can run shell commands.

<details>
<summary>GitHub Actions example</summary>

```yaml
- name: Run Trivy scan
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: ${{ env.IMAGE }}
    format: json
    output: trivy-report.json

- name: Send to SIOPV
  run: |
    PAYLOAD=$(cat trivy-report.json)
    SIGNATURE=$(printf '%s' "$PAYLOAD" | openssl dgst -sha256 -hmac "${{ secrets.SIOPV_WEBHOOK_SECRET }}" | sed 's/^.* //')
    curl -sf -X POST \
      -H "Content-Type: application/json" \
      -H "X-Webhook-Signature-256: sha256=${SIGNATURE}" \
      -d "$PAYLOAD" \
      "${{ vars.SIOPV_WEBHOOK_URL }}"
```

</details>

#### Bridge Script

For CI/CD systems that cannot generate HMAC signatures inline, or for manual webhook testing:

```bash
# With secret from environment variable
export SIOPV_WEBHOOK_SECRET=your-shared-secret
./scripts/webhook-bridge.sh trivy-report.json

# With explicit URL and secret
./scripts/webhook-bridge.sh trivy-report.json http://siopv-host:8080/api/v1/webhook/trivy your-secret
```

#### Webhook Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `SIOPV_WEBHOOK_ENABLED` | `false` | Enable the webhook server |
| `SIOPV_WEBHOOK_SECRET` | *(none)* | HMAC-SHA256 shared secret for signature verification |
| `SIOPV_WEBHOOK_HOST` | `0.0.0.0` | Host to bind the webhook server |
| `SIOPV_WEBHOOK_PORT` | `8080` | Port for the webhook server |

When `SIOPV_WEBHOOK_SECRET` is set, all requests must include a valid `X-Webhook-Signature-256` header. When unset, signature verification is skipped (development only — not recommended for production).

**Webhook responses:**

| Code | Meaning |
|------|---------|
| `202 Accepted` | Report received, pipeline processing enqueued |
| `400 Bad Request` | Malformed JSON payload |
| `401 Unauthorized` | Missing or invalid HMAC signature |
| `503 Service Unavailable` | Webhook not configured |

### CLI Mode (Verification & Testing)

The CLI is used to verify the installation and for manual testing:

```bash
uv run siopv process-report <trivy-report.json> [options]
```

**Subcommand:** `process-report` — runs the full SIOPV pipeline on a Trivy JSON report file.

**Arguments and flags:**

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `<report_path>` | *(positional)* | *(required)* | Path to the Trivy JSON report file |
| `--output` | `-o` | `./output` | Directory for PDF reports, JSON metrics, CSV exports. Use an absolute path for production (e.g., `/var/siopv/reports` or a network share). |
| `--batch-size` | `-b` | `50` | Number of CVEs to process in parallel batches |
| `--user-id` | `-u` | from `.env` | OpenFGA user identity (overrides `SIOPV_DEFAULT_USER_ID`) |
| `--project-id` | `-p` | from `.env` | Project scope for authorization (overrides `SIOPV_DEFAULT_PROJECT_ID`) |

**Examples:**

```bash
# Basic — uses defaults from .env
uv run siopv process-report trivy-report.json

# Custom output directory
uv run siopv process-report trivy-report.json --output /var/siopv/reports

# Override user and project
uv run siopv process-report trivy-report.json -u john_smith -p payment-service

# Verify installation with sample data
uv run siopv process-report trivy-report-small.json
```

---

## Authorization Model

SIOPV uses [OpenFGA](https://openfga.dev/) for fine-grained, relationship-based access control (ReBAC). Every pipeline run is authorized before processing begins.

### User → Role → Project

The authorization model defines who can do what on which project:

```
user:john_smith  →  analyst  →  project:frontend-app
user:john_smith  →  viewer   →  project:payment-service
user:admin       →  owner    →  project:frontend-app
```

**Available roles:**

| Role | Permissions |
|------|------------|
| `owner` | Full access — view, analyze, escalate, delete |
| `analyst` | View and analyze vulnerabilities, create Jira tickets |
| `viewer` | Read-only access to scan results |
| `auditor` | Read-only access with audit trail visibility |

### Adding Users and Projects

To add a new user or project, create OpenFGA tuples:

```bash
# Add user to a project with analyst role
bash scripts/setup-openfga-tuples.sh new_user project_name
```

Or create tuples directly via the OpenFGA API:

```bash
curl -X POST http://localhost:8080/stores/${STORE_ID}/write \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "writes": {
      "tuple_keys": [
        {"user": "user:new_user", "relation": "analyst", "object": "project:project_name"}
      ]
    },
    "authorization_model_id": "'${MODEL_ID}'"
  }'
```

### Production Deployment

In a production environment:

- **Existing OpenFGA:** Point `SIOPV_OPENFGA_API_URL` to your company's OpenFGA instance. SIOPV only reads authorization decisions — it never manages users or tuples. Your IAM team manages access through existing OpenFGA administration tools.
- **Existing Keycloak/OIDC:** Point `SIOPV_OIDC_*` settings to your identity provider. SIOPV supports any OIDC-compliant provider (Keycloak, Okta, Auth0, Azure AD).
- **Multi-project:** Create separate OpenFGA tuples for each project. Different teams get different roles on different projects. The Jira tickets are created in the project specified by `--project-id` or `SIOPV_DEFAULT_PROJECT_ID`.

---

## Configuration Reference

All settings are configured via environment variables with the `SIOPV_` prefix. See `.env.example` for the complete list with descriptions.

| Category | Key Variables |
|----------|--------------|
| **Anthropic (LLM)** | `SIOPV_ANTHROPIC_API_KEY`, `SIOPV_ANTHROPIC_MODEL` |
| **NVD** | `SIOPV_NVD_API_KEY`, `SIOPV_NVD_BASE_URL` |
| **EPSS** | `SIOPV_EPSS_BASE_URL` |
| **GitHub** | `SIOPV_GITHUB_TOKEN` |
| **Jira** | `SIOPV_JIRA_URL`, `SIOPV_JIRA_EMAIL`, `SIOPV_JIRA_API_TOKEN`, `SIOPV_JIRA_PROJECT_KEY` |
| **OpenFGA** | `SIOPV_OPENFGA_API_URL`, `SIOPV_OPENFGA_STORE_ID`, `SIOPV_OPENFGA_AUTH_METHOD` |
| **OIDC** | `SIOPV_OIDC_ISSUER_URL`, `SIOPV_OIDC_CLIENT_ID` |
| **Webhook** | `SIOPV_WEBHOOK_ENABLED`, `SIOPV_WEBHOOK_SECRET`, `SIOPV_WEBHOOK_PORT` |
| **Output** | `SIOPV_OUTPUT_DIR`, `SIOPV_DEFAULT_USER_ID`, `SIOPV_DEFAULT_PROJECT_ID` |
| **ML/Classification** | `SIOPV_UNCERTAINTY_THRESHOLD`, `SIOPV_CONFIDENCE_FLOOR` |
| **HITL Escalation** | `SIOPV_HITL_TIMEOUT_LEVEL1_HOURS`, `SIOPV_HITL_TIMEOUT_LEVEL2_HOURS` |

---

## Trivy Compatibility

SIOPV processes vulnerability reports in **Trivy JSON format**. [Trivy](https://trivy.dev/) is an open-source vulnerability scanner actively maintained by Aqua Security, widely adopted across the industry.

To generate a Trivy report:

```bash
# Scan a Docker image
trivy image --format json -o trivy-report.json your-image:latest

# Scan a filesystem/repository
trivy fs --format json -o trivy-report.json /path/to/project
```

Other vulnerability scanners (Grype, Snyk, Qualys, etc.) use different output formats. The hexagonal architecture allows adding parser adapters for other formats without modifying the core pipeline. See `src/siopv/application/ports/parsing.py` for the parser port interface.

---

## Running Tests

```bash
# Full test suite (1,829 tests, ~2 min)
uv run pytest

# Quick run
uv run pytest -x -q

# Pre-production smoke tests (requires Docker services running)
uv run python scripts/smoke-tests.py
```

### Pre-Production Smoke Tests

The smoke test suite validates operational robustness:

| Test | What it validates |
|------|-------------------|
| **Data-flow** | All CVEs traverse every pipeline node with complete data |
| **Error-path** | Graceful degradation with malformed input (no crashes) |
| **Config sensitivity** | Settings changes produce different pipeline behavior |
| **Isolation** | Node contracts hold — each node's output is valid input for the next |
| **Idempotency** | Same input twice produces same classifications and decisions |

---

## License

MIT
