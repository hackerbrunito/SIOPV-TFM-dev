🇪🇸 Español (actual) | 🇬🇧 [Read in English](README.md)

# SIOPV

**Sistema Inteligente de Orquestación y Priorización de Vulnerabilidades**

SIOPV es un sistema de análisis de vulnerabilidades totalmente automatizado e inteligente, diseñado para operar como la siguiente etapa después del escaneo de seguridad CI/CD en el Ciclo de Vida de Desarrollo de Software (SDLC). Cuando un pipeline CI/CD completa un escaneo de vulnerabilidades (por ejemplo, Trivy), SIOPV recibe automáticamente los resultados vía webhook, los enriquece con inteligencia de amenazas de múltiples fuentes (NVD, EPSS, GitHub Security Advisories) utilizando un patrón Corrective RAG (CRAG) — donde un LLM juez evalúa la relevancia de la información recuperada y activa un fallback OSINT si la calidad es insuficiente — clasifica el riesgo mediante modelos ML XGBoost con evaluación de confianza LLM, y entrega resultados priorizados y accionables como tickets de Jira e informes PDF de auditoría, sin intervención manual.

---

## Integración en el SDLC

SIOPV opera como la capa de análisis automatizado entre el escaneo CI/CD y la acción del desarrollador:

```
Pipeline CI/CD
  │
  ▼
Escáner Trivy ──▶ Informe JSON
  │
  ▼
Webhook SIOPV (verificación HMAC-SHA256)
  │
  ▼
┌─ Autorizar ──▶ Ingestar ──▶ DLP ──▶ Enriquecer ──▶ Clasificar ──▶ [Escalar] ──▶ Salida ─┐
│  (OpenFGA)     (Parser)   (Presidio) (CRAG +       (XGBoost +    (HITL si       (Generar)  │
│                                       LLM Juez)     conf. LLM)   incierto)                 │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
  │                    │                    │
  ▼                    ▼                    ▼
Tickets Jira       Informe PDF         Métricas CSV/JSON
(priorizados)      (auditoría)         (analítica)
```

---

## Detalle del Pipeline

```
                         Pipeline de Procesamiento SIOPV

    Webhook :8080
    POST /api/v1/webhook/trivy
    (HMAC-SHA256 verificado)
         │
         │  Informe JSON de Trivy
         ▼
    ┌──────────┐
    │ Recibir  │ ── 202 Aceptado (procesamiento asíncrono)
    └────┬─────┘
         │
         ▼
    Paso 1: AUTORIZAR
    └─ Verificación ReBAC con OpenFGA (usuario + rol + proyecto)
         │
         ▼
    Paso 2: INGESTAR
    └─ Parsear JSON de Trivy (extraer CVEs, paquetes, versiones, severidades)
         │
         ▼
    Paso 3: DLP
    └─ Detección de PII con Presidio (anonimizar datos sensibles)
         │
         ▼
    Paso 4: ENRIQUECER
    └─ Consultar NVD, EPSS, GitHub Security Advisories
    └─ CRAG: LLM juez evalúa la relevancia de los datos recuperados
    └─ Fallback OSINT si la puntuación de relevancia < umbral
         │
         ▼
    Paso 5: CLASIFICAR
    └─ Puntuación de riesgo ML con XGBoost
    └─ Evaluación de confianza LLM
    └─ Explicabilidad SHAP/LIME
         │
         ▼
    Paso 6: ESCALAR (condicional)
    └─ Si la discrepancia ML vs LLM supera el umbral →
       Revisión Human-in-the-Loop (dashboard Streamlit)
         │
         ▼
    Paso 7: SALIDA
    └─ Tickets Jira (priorizados, con datos de enriquecimiento completos)
    └─ Informe PDF de auditoría
    └─ Métricas CSV + JSON
```

---

## Arquitectura

SIOPV sigue una arquitectura hexagonal (puertos y adaptadores) con un pipeline LangGraph de 7 nodos:

```
INICIO → autorizar → ingestar → dlp → enriquecer → clasificar → [escalar] → salida → FIN
```

| Fase | Nodo | Descripción |
|------|------|-------------|
| 1 | **autorizar** | Control de acceso basado en relaciones con OpenFGA — verifica que el usuario tiene permisos en el proyecto |
| 2 | **ingestar** | Parsea el informe JSON de Trivy en registros estructurados de vulnerabilidades |
| 3 | **dlp** | Detección y anonimización de PII basada en Presidio |
| 4 | **enriquecer** | Patrón CRAG — consulta NVD, EPSS, GitHub Advisories, con fallback OSINT |
| 5 | **clasificar** | Clasificación de riesgo ML (XGBoost) con evaluación de confianza LLM |
| 6 | **escalar** | Revisión human-in-the-loop para clasificaciones de alta incertidumbre |
| 7 | **salida** | Genera tickets Jira, informes PDF de auditoría, exportaciones JSON/CSV |

### Capas Hexagonales

```
domain/          — entidades, objetos de valor, puertos (interfaces), constantes
application/     — casos de uso, orquestación (grafo LangGraph + nodos + estado)
adapters/        — inbound (webhook, CLI) + outbound (NVD, EPSS, Jira, ChromaDB, etc.)
infrastructure/  — contenedor DI, configuración/settings, logging, persistencia
interfaces/      — punto de entrada CLI, dashboard Streamlit
```

---

## Prerrequisitos

- **Python 3.11+**
- **[uv](https://docs.astral.sh/uv/)** — gestor de paquetes Python
- **Docker + Docker Compose** — para OpenFGA, Keycloak y PostgreSQL

---

## Instalación y Configuración

### 1. Clonar el repositorio

```bash
git clone https://github.com/hackerbrunito/SIOPV-TFM.git
cd SIOPV-TFM
```

### 2. Ejecutar el script de instalación

```bash
bash scripts/setup.sh
```

El script de instalación:
1. Verifica prerrequisitos (Python, uv, Docker)
2. Crea `.env` a partir de `.env.example`
3. Solicita tu **identidad de usuario** para la autorización OpenFGA (detecta tu nombre de usuario del sistema)
4. Solicita un **nombre de proyecto** (por defecto: `default` para configuraciones de un solo proyecto)
5. Solicita un **directorio de salida** para informes (por defecto: `./output`)
6. Instala dependencias Python con `uv sync`
7. Inicia servicios Docker (OpenFGA, Keycloak, PostgreSQL)
8. Configura el proveedor OIDC de Keycloak
9. Crea las tuplas de autorización OpenFGA para tu usuario y proyecto
10. Verifica la instalación procesando un informe de ejemplo de Trivy (25 CVEs)

### 3. Configurar claves API

Edita `.env` y añade tus claves API:

```bash
# Requerido para enriquecimiento completo
SIOPV_ANTHROPIC_API_KEY=sk-ant-...    # Evaluación de confianza LLM
SIOPV_NVD_API_KEY=...                 # Enriquecimiento NVD (mayores límites de tasa)

# Requerido para creación de tickets Jira
SIOPV_JIRA_URL=https://tu-dominio.atlassian.net
SIOPV_JIRA_EMAIL=tu-email@ejemplo.com
SIOPV_JIRA_API_TOKEN=...
SIOPV_JIRA_PROJECT_KEY=...

# Opcional
SIOPV_GITHUB_TOKEN=ghp_...            # GitHub Security Advisories
SIOPV_TAVILY_API_KEY=tvly-...         # Búsqueda OSINT de respaldo
```

El pipeline funciona sin estas claves pero con funcionalidad reducida:
- Sin `ANTHROPIC_API_KEY`: La confianza LLM usa un respaldo heurístico
- Sin `NVD_API_KEY`: Las consultas NVD usan límites de tasa más bajos
- Sin `JIRA_*`: No se crean tickets Jira (PDF y CSV se generan igualmente)

---

## Uso

### Modo Webhook (Producción)

SIOPV escucha en un endpoint webhook para recibir informes de escaneo Trivy desde pipelines CI/CD. Este es el modo principal de producción.

**Endpoint:** `POST /api/v1/webhook/trivy`

Cuando un pipeline CI/CD completa un escaneo Trivy, envía el informe JSON al webhook de SIOPV con una firma HMAC-SHA256. SIOPV verifica la firma, devuelve `202 Accepted`, y procesa el informe de forma asíncrona a través del pipeline completo.

#### Integración CI/CD

Añade estas líneas a tu pipeline CI/CD después del paso de escaneo Trivy:

```bash
# Generar firma HMAC-SHA256
PAYLOAD=$(cat trivy-report.json)
SIGNATURE=$(printf '%s' "$PAYLOAD" | openssl dgst -sha256 -hmac "$SIOPV_WEBHOOK_SECRET" | sed 's/^.* //')

# Enviar a SIOPV
curl -sf -X POST \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Signature-256: sha256=${SIGNATURE}" \
  -d "$PAYLOAD" \
  http://tu-host-siopv:8080/api/v1/webhook/trivy
```

Esto funciona en **GitHub Actions**, **Jenkins**, **GitLab CI**, o cualquier sistema CI/CD que pueda ejecutar comandos shell.

<details>
<summary>Ejemplo de GitHub Actions</summary>

```yaml
- name: Ejecutar escaneo Trivy
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: ${{ env.IMAGE }}
    format: json
    output: trivy-report.json

- name: Enviar a SIOPV
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

#### Script Puente

Para sistemas CI/CD que no pueden generar firmas HMAC en línea, o para pruebas manuales del webhook:

```bash
# Con secreto desde variable de entorno
export SIOPV_WEBHOOK_SECRET=tu-secreto-compartido
./scripts/webhook-bridge.sh trivy-report.json

# Con URL y secreto explícitos
./scripts/webhook-bridge.sh trivy-report.json http://host-siopv:8080/api/v1/webhook/trivy tu-secreto
```

#### Configuración del Webhook

| Variable de Entorno | Por defecto | Descripción |
|---------------------|-------------|-------------|
| `SIOPV_WEBHOOK_ENABLED` | `false` | Habilitar el servidor webhook |
| `SIOPV_WEBHOOK_SECRET` | *(ninguno)* | Secreto compartido HMAC-SHA256 para verificación de firma |
| `SIOPV_WEBHOOK_HOST` | `0.0.0.0` | Host donde escucha el servidor webhook |
| `SIOPV_WEBHOOK_PORT` | `8080` | Puerto del servidor webhook |

Cuando `SIOPV_WEBHOOK_SECRET` está configurado, todas las peticiones deben incluir un header `X-Webhook-Signature-256` válido. Si no está configurado, la verificación de firma se omite (solo para desarrollo — no recomendado para producción).

**Respuestas del webhook:**

| Código | Significado |
|--------|------------|
| `202 Accepted` | Informe recibido, procesamiento del pipeline encolado |
| `400 Bad Request` | Payload JSON malformado |
| `401 Unauthorized` | Firma HMAC faltante o inválida |
| `503 Service Unavailable` | Webhook no configurado |

### Modo CLI (Verificación y Pruebas)

El CLI se utiliza para verificar la instalación y para pruebas manuales:

```bash
uv run siopv process-report <informe-trivy.json> [opciones]
```

**Subcomando:** `process-report` — ejecuta el pipeline completo de SIOPV sobre un archivo de informe JSON de Trivy.

**Argumentos y flags:**

| Flag | Corto | Por defecto | Descripción |
|------|-------|-------------|-------------|
| `<report_path>` | *(posicional)* | *(requerido)* | Ruta al archivo de informe JSON de Trivy |
| `--output` | `-o` | `./output` | Directorio para informes PDF, métricas JSON, exportaciones CSV. Usar ruta absoluta en producción (ej., `/var/siopv/reports` o un recurso de red compartido). |
| `--batch-size` | `-b` | `50` | Número de CVEs a procesar en lotes paralelos |
| `--user-id` | `-u` | desde `.env` | Identidad de usuario OpenFGA (sobreescribe `SIOPV_DEFAULT_USER_ID`) |
| `--project-id` | `-p` | desde `.env` | Ámbito del proyecto para autorización (sobreescribe `SIOPV_DEFAULT_PROJECT_ID`) |

**Ejemplos:**

```bash
# Básico — usa valores por defecto de .env
uv run siopv process-report trivy-report.json

# Directorio de salida personalizado
uv run siopv process-report trivy-report.json --output /var/siopv/informes

# Sobreescribir usuario y proyecto
uv run siopv process-report trivy-report.json -u juan_perez -p servicio-pagos

# Verificar instalación con datos de ejemplo
uv run siopv process-report trivy-report-small.json
```

---

## Modelo de Autorización

SIOPV utiliza [OpenFGA](https://openfga.dev/) para control de acceso granular basado en relaciones (ReBAC). Cada ejecución del pipeline es autorizada antes de comenzar el procesamiento.

### Usuario → Rol → Proyecto

El modelo de autorización define quién puede hacer qué en cada proyecto:

```
user:juan_perez  →  analyst  →  project:app-frontend
user:juan_perez  →  viewer   →  project:servicio-pagos
user:admin       →  owner    →  project:app-frontend
```

**Roles disponibles:**

| Rol | Permisos |
|-----|----------|
| `owner` | Acceso completo — ver, analizar, escalar, eliminar |
| `analyst` | Ver y analizar vulnerabilidades, crear tickets Jira |
| `viewer` | Acceso de solo lectura a resultados de escaneo |
| `auditor` | Acceso de solo lectura con visibilidad de traza de auditoría |

### Añadir Usuarios y Proyectos

Para añadir un nuevo usuario o proyecto, crear tuplas OpenFGA:

```bash
# Añadir usuario a un proyecto con rol analyst
bash scripts/setup-openfga-tuples.sh nuevo_usuario nombre_proyecto
```

O crear tuplas directamente vía la API de OpenFGA:

```bash
curl -X POST http://localhost:8080/stores/${STORE_ID}/write \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "writes": {
      "tuple_keys": [
        {"user": "user:nuevo_usuario", "relation": "analyst", "object": "project:nombre_proyecto"}
      ]
    },
    "authorization_model_id": "'${MODEL_ID}'"
  }'
```

### Despliegue en Producción

En un entorno de producción:

- **OpenFGA existente:** Apuntar `SIOPV_OPENFGA_API_URL` a la instancia OpenFGA de tu empresa. SIOPV solo lee decisiones de autorización — nunca gestiona usuarios ni tuplas. Tu equipo de IAM gestiona el acceso a través de las herramientas de administración OpenFGA existentes.
- **Keycloak/OIDC existente:** Apuntar la configuración `SIOPV_OIDC_*` a tu proveedor de identidad. SIOPV soporta cualquier proveedor compatible con OIDC (Keycloak, Okta, Auth0, Azure AD).
- **Multi-proyecto:** Crear tuplas OpenFGA separadas para cada proyecto. Diferentes equipos obtienen diferentes roles en diferentes proyectos. Los tickets Jira se crean en el proyecto especificado por `--project-id` o `SIOPV_DEFAULT_PROJECT_ID`.

---

## Referencia de Configuración

Todos los ajustes se configuran mediante variables de entorno con el prefijo `SIOPV_`. Consulta `.env.example` para la lista completa con descripciones.

| Categoría | Variables Clave |
|-----------|----------------|
| **Anthropic (LLM)** | `SIOPV_ANTHROPIC_API_KEY`, `SIOPV_ANTHROPIC_MODEL` |
| **NVD** | `SIOPV_NVD_API_KEY`, `SIOPV_NVD_BASE_URL` |
| **EPSS** | `SIOPV_EPSS_BASE_URL` |
| **GitHub** | `SIOPV_GITHUB_TOKEN` |
| **Jira** | `SIOPV_JIRA_URL`, `SIOPV_JIRA_EMAIL`, `SIOPV_JIRA_API_TOKEN`, `SIOPV_JIRA_PROJECT_KEY` |
| **OpenFGA** | `SIOPV_OPENFGA_API_URL`, `SIOPV_OPENFGA_STORE_ID`, `SIOPV_OPENFGA_AUTH_METHOD` |
| **OIDC** | `SIOPV_OIDC_ISSUER_URL`, `SIOPV_OIDC_CLIENT_ID` |
| **Webhook** | `SIOPV_WEBHOOK_ENABLED`, `SIOPV_WEBHOOK_SECRET`, `SIOPV_WEBHOOK_PORT` |
| **Salida** | `SIOPV_OUTPUT_DIR`, `SIOPV_DEFAULT_USER_ID`, `SIOPV_DEFAULT_PROJECT_ID` |
| **ML/Clasificación** | `SIOPV_UNCERTAINTY_THRESHOLD`, `SIOPV_CONFIDENCE_FLOOR` |
| **Escalación HITL** | `SIOPV_HITL_TIMEOUT_LEVEL1_HOURS`, `SIOPV_HITL_TIMEOUT_LEVEL2_HOURS` |

---

## Compatibilidad con Trivy

SIOPV procesa informes de vulnerabilidades en **formato JSON de Trivy**. [Trivy](https://trivy.dev/) es un escáner de vulnerabilidades open source mantenido activamente por Aqua Security, ampliamente adoptado en la industria.

Para generar un informe Trivy:

```bash
# Escanear una imagen Docker
trivy image --format json -o trivy-report.json tu-imagen:latest

# Escanear un sistema de archivos/repositorio
trivy fs --format json -o trivy-report.json /ruta/al/proyecto
```

Otros escáneres de vulnerabilidades (Grype, Snyk, Qualys, etc.) usan formatos de salida diferentes. La arquitectura hexagonal permite añadir adaptadores de parser para otros formatos sin modificar el pipeline principal. Ver `src/siopv/application/ports/parsing.py` para la interfaz del puerto parser.

---

## Ejecución de Tests

```bash
# Suite completa de tests (1.829 tests, ~2 min)
uv run pytest

# Ejecución rápida
uv run pytest -x -q

# Tests de pre-producción (requiere servicios Docker activos)
uv run python scripts/smoke-tests.py
```

### Tests de Pre-Producción

La suite de smoke tests valida la robustez operativa:

| Test | Qué valida |
|------|-----------|
| **Flujo de datos** | Todos los CVEs atraviesan cada nodo del pipeline con datos completos |
| **Ruta de error** | Degradación elegante con entrada malformada (sin crashes) |
| **Sensibilidad de configuración** | Los cambios de configuración producen comportamiento diferente en el pipeline |
| **Aislamiento** | Los contratos entre nodos se mantienen — la salida de cada nodo es entrada válida para el siguiente |
| **Idempotencia** | La misma entrada dos veces produce las mismas clasificaciones y decisiones |

---

## Licencia

Copyright 2026 Carlos Val Souto

Licenciado bajo la Licencia Apache, Versión 2.0. Ver [LICENSE](LICENSE) para más detalles.
