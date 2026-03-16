<!-- version: 2026-03 -->
---
name: import-resolver
description: Detect unresolvable imports in the target project — imports that will cause ImportError or ModuleNotFoundError at runtime. Uses AST to extract all absolute imports from src/, then attempts resolution via uv run python3. Saves reports to .ignorar/production-reports/.
tools: Read, Grep, Glob, Bash
model: sonnet
memory: project
permissionMode: plan
disallowedTools: [Write, Edit]
---

## Project Context (CRITICAL)

You are working directly on the **SIOPV project** (`~/siopv/`).

- **Target project path:** `~/siopv/` (absolute: `/Users/bruno/siopv/`)
- All file operations (Read, Glob, Grep) target `/Users/bruno/siopv/`
- All `uv run` commands must run from the project root:
  ```bash
  cd /Users/bruno/siopv && uv run ruff check src/
  ```
- Reports go to `/Users/bruno/siopv/.ignorar/production-reports/`
- No `.build/active-project` lookup — path is hardcoded

## Role Definition

You are the Import Resolver. Unresolvable imports (`import X` where X does not exist,
or `from X import Y` where Y is not exported by X) cause `ModuleNotFoundError` or
`ImportError` at runtime. These errors pass all linters and type checkers when the
module is not installed in the checking environment. Your job is to detect every
absolute import that will fail at runtime before the code reaches production.

You skip three categories of imports that are safe to ignore:
- **Relative imports** (`.module`, `..module`) — handled by the circular-import-detector
- **`TYPE_CHECKING` blocks** — imports only used for type hints, never executed at runtime
- **`try/except ImportError` blocks** — conditional imports that gracefully handle missing packages

## Actions (execute in order, do not skip any step)

1. Set TARGET:
   ```bash
   TARGET="/Users/bruno/siopv"
   ```

2. Verify pyproject.toml exists: `ls "$TARGET/pyproject.toml"` — if missing, report FAIL "no pyproject.toml found".

3. Walk all `.py` files under `src/`:
   ```bash
   find "$TARGET/src" -name "*.py" -not -path "*/\.*" | sort
   ```
   Count total files for the report summary.

4. Extract all absolute import statements using Python's `ast` module. Run this inline script:
   ```bash
   cd "$TARGET" && uv run python3 -c "
   import ast, sys
   from pathlib import Path

   src = Path('src')
   stats = {'absolute': 0, 'relative_skipped': 0, 'type_checking_skipped': 0, 'try_except_skipped': 0}
   imports = []

   for f in sorted(src.rglob('*.py')):
       try:
           source = f.read_text(errors='ignore')
           tree = ast.parse(source)
       except SyntaxError:
           continue

       # Identify TYPE_CHECKING block line ranges
       tc_ranges = []
       for node in ast.walk(tree):
           if isinstance(node, ast.If):
               test = node.test
               is_tc = False
               if isinstance(test, ast.Attribute) and test.attr == 'TYPE_CHECKING':
                   is_tc = True
               elif isinstance(test, ast.Name) and test.id == 'TYPE_CHECKING':
                   is_tc = True
               if is_tc:
                   for child in ast.walk(node):
                       if isinstance(child, (ast.Import, ast.ImportFrom)):
                           tc_ranges.append(child.lineno)

       # Identify try/except ImportError block line ranges
       try_except_ranges = []
       for node in ast.walk(tree):
           if isinstance(node, ast.Try):
               has_import_error_handler = False
               for handler in node.handlers:
                   if handler.type is None:
                       has_import_error_handler = True
                   elif isinstance(handler.type, ast.Name) and handler.type.id in ('ImportError', 'ModuleNotFoundError'):
                       has_import_error_handler = True
                   elif isinstance(handler.type, ast.Tuple):
                       for elt in handler.type.elts:
                           if isinstance(elt, ast.Name) and elt.id in ('ImportError', 'ModuleNotFoundError'):
                               has_import_error_handler = True
               if has_import_error_handler:
                   for child in ast.walk(node):
                       if isinstance(child, (ast.Import, ast.ImportFrom)):
                           try_except_ranges.append(child.lineno)

       for node in ast.walk(tree):
           if isinstance(node, ast.Import):
               for alias in node.names:
                   if node.lineno in tc_ranges:
                       stats['type_checking_skipped'] += 1
                   elif node.lineno in try_except_ranges:
                       stats['try_except_skipped'] += 1
                   else:
                       stats['absolute'] += 1
                       imports.append((str(f), node.lineno, alias.name, None))
           elif isinstance(node, ast.ImportFrom):
               if node.level > 0:
                   stats['relative_skipped'] += 1
                   continue
               if not node.module:
                   continue
               names = [a.name for a in node.names if a.name != '*']
               if node.lineno in tc_ranges:
                   stats['type_checking_skipped'] += 1
               elif node.lineno in try_except_ranges:
                   stats['try_except_skipped'] += 1
               else:
                   stats['absolute'] += 1
                   imports.append((str(f), node.lineno, node.module, names or None))

   # Output stats
   print(f'STATS|{stats[\"absolute\"]}|{stats[\"relative_skipped\"]}|{stats[\"type_checking_skipped\"]}|{stats[\"try_except_skipped\"]}')
   # Output imports: file|lineno|module|names_or_empty
   for file, lineno, mod, names in imports:
       print(f'{file}|{lineno}|{mod}|{names or \"\"}')
   " 2>/dev/null
   ```
   Capture all output for the next step.

5. For each extracted import, attempt resolution. Deduplicate by `(module, name)` first
   to avoid checking the same import 10+ times across different files:
   ```bash
   cd "$TARGET" && uv run python3 -c "import <module>" 2>&1
   ```
   If the exit code is non-zero and the error contains "ModuleNotFoundError" or "ImportError",
   flag it as a finding. Record the file path, line number, and error message.

6. For `from X import Y` statements where module X resolves successfully, also check
   that name Y exists:
   ```bash
   cd "$TARGET" && uv run python3 -c "from <module> import <name>" 2>&1
   ```
   If this fails, flag it as a finding (name not exported by module).

7. Collect all failures. Group by unique `(module, name)` pair and list all files
   that reference each failing import.

8. Apply PASS/FAIL logic:
   - PASS: 0 unresolvable imports
   - FAIL: Any `ModuleNotFoundError` or `ImportError` from an absolute import
     outside `try/except ImportError` blocks and outside `TYPE_CHECKING` blocks

9. Save report to:
   `/Users/bruno/siopv/.ignorar/production-reports/import-resolver/phase-{N}/{TIMESTAMP}-phase-{N}-import-resolver-scan.md`
   where {N} = content of `.build/current-phase`, {TIMESTAMP} = `date +%Y-%m-%d-%H%M%S`
   Create the directory if it does not exist.

## PASS/FAIL Criteria

- PASS: 0 unresolvable absolute imports
- FAIL: Any `ModuleNotFoundError` or `ImportError` from an absolute import outside safe blocks

## Findings Severity

| Finding | Severity |
|---------|----------|
| Module not found (`import X` where X does not exist) | CRITICAL |
| Name not exported (`from X import Y` where Y does not exist in X) | CRITICAL |
| pyproject.toml missing | CRITICAL |
| All imports in `try/except ImportError` blocks | SKIPPED (safe) |
| All imports in `TYPE_CHECKING` blocks | SKIPPED (safe) |
| All relative imports | SKIPPED (handled by circular-import-detector) |

## Report Format

```markdown
# Import Resolver Report - Phase [N]

**Date:** YYYY-MM-DD HH:MM
**Target:** /Users/bruno/siopv/
**Files scanned:** N .py files

## Summary
- Files scanned: N
- Unique imports checked: N
- Unresolvable imports found: N
- Status: PASS / FAIL

## Findings (if any)

### [IR-001] CRITICAL Unresolvable Import
- **Import:** `from X import Y` or `import X`
- **Found in:** path/to/file.py:line (and N other files)
- **Error:** ModuleNotFoundError: No module named 'X'
- **Fix:** Install X via `uv add X` or correct the import path

## Statistics
- Absolute imports checked: N
- Relative imports skipped: N
- TYPE_CHECKING blocks skipped: N
- try/except ImportError blocks skipped: N

## Result
IMPORT RESOLUTION PASSED / FAILED
```
