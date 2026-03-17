---
task: detect unresolvable absolute imports
start: 2026-03-17T11:00:00Z
agent: wave6-imports (import-resolver)
status: IN PROGRESS
---

## Method
1. Walk all .py files under src/ using ast to extract absolute import statements
2. For each import: uv run python3 -c "import {module}"
3. For from-imports: uv run python3 -c "from {module} import {name}"
4. Skip: relative imports, TYPE_CHECKING blocks, try/except ImportError blocks
5. Flag any ModuleNotFoundError or ImportError as CRITICAL
6. Deduplicate findings by (module, name)

## Status
- [ ] AST extraction complete
- [ ] Import resolution complete
- [ ] Report written
