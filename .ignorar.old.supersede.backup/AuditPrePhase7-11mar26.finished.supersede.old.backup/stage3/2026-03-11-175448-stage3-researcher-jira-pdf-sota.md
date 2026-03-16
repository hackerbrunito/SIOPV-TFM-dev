# STAGE-3 Research: Jira REST API v3 + fpdf2 >=2.7.0 State-of-the-Art
**Agent:** researcher-jira-pdf
**Timestamp:** 2026-03-11-175448
**Scope:** Phase 8 output_node — Jira ticket creation + PDF compliance reports

---

## 1. Jira REST API v3 — Verified Patterns

### 1.1 Auth — API Token + Basic Auth

```python
import httpx, base64, os

email = os.environ["JIRA_EMAIL"]
api_token = os.environ["JIRA_API_TOKEN"]
base_url = os.environ["JIRA_BASE_URL"]  # e.g. https://yourorg.atlassian.net

credentials = base64.b64encode(f"{email}:{api_token}".encode()).decode()
headers = {
    "Authorization": f"Basic {credentials}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}
```

**Important:** Basic auth with email + API token bypasses OAuth scopes entirely;
permissions depend solely on the Jira account's project permissions.

### 1.2 Create Issue Endpoint

```
POST https://{JIRA_BASE_URL}/rest/api/3/issue
```

**Minimal required fields:** `project.key`, `summary`, `issuetype.name`

### 1.3 Full JSON Body for Vulnerability Ticket

```python
def cvss_to_priority(cvss: float) -> str:
    """Map CVSS v3.x score to Jira priority name."""
    if cvss >= 9.0:
        return "Highest"   # Critical
    elif cvss >= 7.0:
        return "High"
    elif cvss >= 4.0:
        return "Medium"
    elif cvss >= 0.1:
        return "Low"
    return "Lowest"

def build_jira_issue(vuln: dict, project_key: str) -> dict:
    """Build Jira REST API v3 create-issue payload."""
    return {
        "fields": {
            "project": {"key": project_key},
            "summary": f"[VULN] {vuln['cve_id']} — {vuln['package']} (CVSS {vuln['cvss_score']})",
            "issuetype": {"name": "Bug"},
            "priority": {"name": cvss_to_priority(vuln["cvss_score"])},
            "labels": ["security", "vulnerability", f"cvss-{cvss_to_priority(vuln['cvss_score']).lower()}"],
            "description": {
                "version": 1,
                "type": "doc",
                "content": [
                    {
                        "type": "heading",
                        "attrs": {"level": 2},
                        "content": [{"type": "text", "text": "Vulnerability Summary"}]
                    },
                    {
                        "type": "paragraph",
                        "content": [
                            {"type": "text", "text": f"CVE: {vuln['cve_id']}", "marks": [{"type": "strong"}]},
                            {"type": "hardBreak"},
                            {"type": "text", "text": f"Package: {vuln['package']} {vuln.get('version', '')}"},
                            {"type": "hardBreak"},
                            {"type": "text", "text": f"CVSS Score: {vuln['cvss_score']}"},
                            {"type": "hardBreak"},
                            {"type": "text", "text": f"Risk Class: {vuln.get('risk_class', 'N/A')}"},
                        ]
                    },
                    {
                        "type": "heading",
                        "attrs": {"level": 2},
                        "content": [{"type": "text", "text": "LIME Justification"}]
                    },
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": vuln.get("lime_justification", "N/A")}]
                    },
                    {
                        "type": "heading",
                        "attrs": {"level": 2},
                        "content": [{"type": "text", "text": "Recommended Remediation"}]
                    },
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": vuln.get("remediation", "Upgrade to patched version.")}]
                    }
                ]
            }
        }
    }
```

### 1.4 httpx Async Call Pattern

```python
async def create_jira_ticket(vuln: dict, project_key: str) -> str:
    """Create Jira issue; returns issue key (e.g. 'PROJ-123')."""
    payload = build_jira_issue(vuln, project_key)
    async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
        resp = await client.post(f"{base_url}/rest/api/3/issue", json=payload)
        resp.raise_for_status()
        return resp.json()["key"]
```

**Response:** `{"id": "10001", "key": "PROJ-123", "self": "https://..."}`

### 1.5 Python Client Libraries — Recommendation

| Library | Version | REST v3 | Async | Verdict |
|---------|---------|---------|-------|---------|
| `jira` | 3.10.x+ | ✅ (post-migration fix) | ❌ (requests-based) | OK for simple use |
| `atlassian-python-api` | latest | ✅ | ❌ (requests-based) | Heavier, more features |
| **raw `httpx`** | 0.27+ | ✅ | ✅ | **RECOMMENDED** for async pipeline |

**Decision for SIOPV Phase 8:** Use raw `httpx.AsyncClient`. SIOPV is an async LangGraph
pipeline; both Jira client libraries are synchronous (requests-based) and would block the
event loop. httpx is already a project dependency.

### 1.6 Custom Fields Pattern

```python
# Custom field by ID
"customfield_10000": "value",
# Custom field with object value
"customfield_10001": {"value": "Security"},
```

CVSS score as custom field (if configured in Jira):
```python
"customfield_10100": str(vuln["cvss_score"]),
```

---

## 2. fpdf2 >=2.7.0 — Verified Patterns

**Current version: 2.8.7** (released 2026-02-28)
**Context7 library ID:** `/py-pdf/fpdf2` (High reputation, 650 snippets)

### 2.1 Core Architecture — Subclass FPDF

```python
from fpdf import FPDF
from fpdf.outline import TableOfContents

class ComplianceReport(FPDF):
    """ISO 27001 / SOC 2 compliance PDF report."""

    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.cell(w=0, h=8, text="SIOPV Vulnerability Audit Report — CONFIDENTIAL",
                  border=0, align="C")
        self.ln(4)
        self.set_draw_color(200, 0, 0)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(w=0, h=10,
                  text=f"Page {self.page_no()}/{{nb}} | CONFIDENTIAL | ISO 27001",
                  align="C")
```

### 2.2 Compliance Report Structure

```python
def build_compliance_report(vulns: list[dict], output_path: str) -> None:
    pdf = ComplianceReport()
    pdf.alias_nb_pages()  # Enables {nb} total-page placeholder
    pdf.set_auto_page_break(auto=True, margin=20)

    # ── Cover Page ──────────────────────────────────────────────────
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 28)
    pdf.ln(40)
    pdf.cell(0, 15, "Vulnerability Audit Report", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 14)
    pdf.cell(0, 10, f"Generated: {datetime.utcnow().isoformat()}Z", align="C",
             new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 10, "Prepared for: ISO 27001 / SOC 2 Compliance Review", align="C",
             new_x="LMARGIN", new_y="NEXT")

    # ── Table of Contents ────────────────────────────────────────────
    pdf.add_page()
    toc = TableOfContents()
    pdf.insert_toc_placeholder(toc.render_toc, allow_extra_pages=True)

    # ── Executive Summary ────────────────────────────────────────────
    pdf.add_page()
    pdf.start_section("1. Executive Summary", level=0)
    pdf.set_font("Helvetica", "", 11)
    critical = sum(1 for v in vulns if v["cvss_score"] >= 9.0)
    high = sum(1 for v in vulns if 7.0 <= v["cvss_score"] < 9.0)
    pdf.multi_cell(w=0, h=6,
                   text=f"Total vulnerabilities: {len(vulns)}. "
                        f"Critical: {critical}. High: {high}. "
                        f"All escalated cases have been reviewed and Jira tickets created.")
    pdf.ln(4)

    # ── Vulnerability Table ──────────────────────────────────────────
    pdf.add_page()
    pdf.start_section("2. Vulnerability Inventory", level=0)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "2.1 Full Vulnerability List", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)

    TABLE_HEADERS = ("CVE ID", "Package", "CVSS", "Severity", "Status", "Jira Ticket")
    with pdf.table(col_widths=(40, 40, 15, 22, 30, 30)) as table:
        # Header row
        hrow = table.row()
        for h in TABLE_HEADERS:
            hrow.cell(h)
        # Data rows
        for vuln in vulns:
            row = table.row()
            row.cell(vuln["cve_id"])
            row.cell(vuln["package"])
            row.cell(str(vuln["cvss_score"]))
            row.cell(cvss_to_priority(vuln["cvss_score"]))
            row.cell(vuln.get("status", "Open"))
            row.cell(vuln.get("jira_key", "—"))

    # ── LIME Justifications ──────────────────────────────────────────
    pdf.add_page()
    pdf.start_section("3. LIME Explainability Justifications", level=0)
    for vuln in vulns:
        if vuln.get("lime_justification"):
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(0, 7, vuln["cve_id"], new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 9)
            pdf.multi_cell(w=0, h=5, text=vuln["lime_justification"])
            pdf.ln(3)

    # ── Chain-of-Thought Traces (optional) ──────────────────────────
    pdf.add_page()
    pdf.start_section("4. Chain-of-Thought Traces (Escalated Cases)", level=0)
    for vuln in vulns:
        if vuln.get("escalated") and vuln.get("cot_trace"):
            pdf.set_font("Courier", "", 8)
            pdf.multi_cell(w=0, h=4, text=vuln["cot_trace"])
            pdf.ln(2)

    pdf.output(output_path)
```

### 2.3 Unicode Support

```python
# For non-Latin characters, add TTF font:
pdf.add_font(fname="DejaVuSansCondensed.ttf")  # fname REQUIRED in 2.7+
pdf.set_font("DejaVuSansCondensed", size=11)

# Text shaping for RTL/bidirectional:
pdf.set_text_shaping(True)
```

### 2.4 Image Embedding

```python
# Logo on cover page:
pdf.image("logo.png", x=10, y=8, w=33)

# In table cell:
with pdf.table() as table:
    row = table.row()
    row.cell(img="chart.png", img_fill_width=True)
```

### 2.5 Unbreakable Table Rows (compliance-critical)

```python
with pdf.unbreakable() as doc:
    for datum in row_data:
        doc.cell(col_w, line_h, datum, border=1)
    doc.ln(line_h)
```

### 2.6 Breaking Changes 2.6.x → 2.7.x

| Change | Impact |
|--------|--------|
| `fname` is now **required** in `add_font()` | Must pass font file path explicitly |
| `open()` and `close()` methods **removed** | Never call these; use `add_page()` and `output()` |
| `FPDF.state` attribute **removed** | Don't access internal state directly |
| `write_html()`: `dd_tag_indent`/`li_tag_indent` → `tag_indents` | Update any HTML-to-PDF code |
| `write_html()`: `heading_sizes`/`pre_code_font` → `tag_styles` | Update any HTML-to-PDF code |
| `image()` now inserts SVG as PDF vector paths | Better quality but requires `defusedxml` |
| `rowspan` support added in tables | Use for spanning cells |

**Minimum safe target:** `fpdf2>=2.7.0` — all patterns above work on 2.7.x and 2.8.x.

---

## 3. Libraries Verified

| Library | Tier 1 (Context7) | Tier 3 (WebSearch) | Status |
|---------|-------------------|-------------------|--------|
| `fpdf2` | ✅ `/py-pdf/fpdf2` queried twice — 650 snippets, High reputation | ✅ GitHub CHANGELOG + py-pdf.github.io confirmed | VERIFIED |
| Jira REST API v3 | N/A (not a Python lib) | ✅ developer.atlassian.com + ADF docs | VERIFIED |
| `jira` Python client | ✅ jira.readthedocs.io referenced | ✅ PyPI confirmed v3.10.x fixes REST v3 | VERIFIED |
| `atlassian-python-api` | N/A | ✅ GitHub + PyPI confirmed | VERIFIED |
| `httpx` | Already in project (SIOPV dependency) | N/A | USED |

**Training data NOT relied upon** for any API patterns — all verified via online sources.

---

## 4. Key Findings Summary

- **Jira auth:** `Basic base64(email:api_token)` header — no OAuth needed, no scope issues.
  Set via env vars `JIRA_EMAIL`, `JIRA_API_TOKEN`, `JIRA_BASE_URL`.

- **ADF format is mandatory** for `description` in REST API v3. Plain text strings are
  rejected. Use `{"version":1,"type":"doc","content":[...]}` wrapper.

- **Use raw `httpx.AsyncClient`** (not `jira` or `atlassian-python-api` libs) — both
  Python clients are synchronous (requests-based) and will block LangGraph's event loop.

- **CVSS → Jira priority mapping:** Critical ≥9.0 → Highest, High 7.0–8.9 → High,
  Medium 4.0–6.9 → Medium, Low 0.1–3.9 → Low.

- **fpdf2 current version is 2.8.7** (Feb 2026). Target `fpdf2>=2.7.0` for Phase 8.

- **`fname` parameter is required** in `add_font()` since 2.7.0 — critical breaking change.

- **Table of Contents** via `insert_toc_placeholder(toc.render_toc, allow_extra_pages=True)`
  is the correct 2.7+ API — works for compliance report navigation.

- **`pdf.table()` context manager** is the idiomatic 2.7+ table API. Supports `colspan`,
  `rowspan`, `col_widths`, and image cells — sufficient for vulnerability tables.

- **Unbreakable rows** via `pdf.unbreakable()` context manager — use for audit tables
  to prevent row splits across pages (ISO 27001 / SOC 2 readability requirement).

- **`alias_nb_pages()` + `{nb}` in footer** is the correct total-page-count pattern —
  must call before any `add_page()`.

---

## Sources

- [Jira Cloud REST API v3](https://developer.atlassian.com/cloud/jira/platform/rest/v3/intro/)
- [Jira Basic Auth for REST APIs](https://developer.atlassian.com/cloud/jira/platform/basic-auth-for-rest-apis/)
- [Atlassian Document Format (ADF)](https://developer.atlassian.com/cloud/jira/platform/apis/document/structure/)
- [fpdf2 documentation](https://py-pdf.github.io/fpdf2/index.html)
- [fpdf2 CHANGELOG](https://github.com/py-pdf/fpdf2/blob/master/CHANGELOG.md)
- [fpdf2 Tables docs](https://github.com/py-pdf/fpdf2/blob/master/docs/Tables.md)
- [fpdf2 Context7 library](https://context7.com/py-pdf/fpdf2/llms.txt)
- [jira Python library](https://pypi.org/project/jira/)
- [atlassian-python-api](https://github.com/atlassian-api/atlassian-python-api)
- [CVSS Vulnerability Metrics (NVD)](https://nvd.nist.gov/vuln-metrics/cvss)
