# CLAUDE.md Best Practices — Research Report (March 2026)

> **Compiled:** 2026-03-16
> **Sources:** Anthropic official docs, community guides, blog posts (see Sources section)

---

## 1. What is CLAUDE.md?

CLAUDE.md is a special markdown file that Claude Code reads at the start of every conversation. It provides persistent, project-specific context — think of it as a configuration file that Claude automatically incorporates into every session. It is **not** enforced configuration; it is context that Claude reads and tries to follow.

> "CLAUDE.md files are markdown files that give Claude persistent instructions for a project, your personal workflow, or your entire organization." — [Anthropic Official Docs](https://code.claude.com/docs/en/memory)

> "CLAUDE.md content is delivered as a user message after the system prompt, not as part of the system prompt itself. Claude reads it and tries to follow it, but there's no guarantee of strict compliance, especially for vague or conflicting instructions." — [Anthropic Official Docs](https://code.claude.com/docs/en/memory)

---

## 2. Recommended Structure and Sections

### Official Recommendation (Anthropic)

There is **no required format**. Keep it short and human-readable. The official example shows just two sections:

```markdown
# Code style
- Use ES modules (import/export) syntax, not CommonJS (require)
- Destructure imports when possible

# Workflow
- Be sure to typecheck when you're done making a series of code changes
- Prefer running single tests, and not the whole test suite, for performance
```

### Community-Recommended Sections

Based on multiple sources, the most effective CLAUDE.md files cover:

1. **Project Overview** — What the project is (1-2 sentences)
2. **Tech Stack** — Key technologies, frameworks, versions
3. **Architecture** — Folder structure, patterns (hexagonal, monorepo, etc.)
4. **Build/Test/Lint Commands** — Exact commands Claude should use
5. **Coding Standards** — Only rules that differ from defaults or that Claude can't infer
6. **File Organization** — Where things live (especially non-obvious locations)
7. **Workflows** — How to approach features, bugs, commits, PRs
8. **Gotchas/Warnings** — Project-specific pitfalls and non-obvious behaviors

> "The WHY, WHAT, HOW framework: WHAT — tell Claude about the tech, your stack, the project structure. WHY — share project purpose. HOW — explain how to work on the project." — [HumanLayer Blog](https://www.humanlayer.dev/blog/writing-a-good-claude-md)

---

## 3. Recommended Length / Maximum Length

### Official Guidance

> "**Size**: target under 200 lines per CLAUDE.md file. Longer files consume more context and reduce adherence." — [Anthropic Official Docs](https://code.claude.com/docs/en/memory)

### Community Findings

| Source | Recommendation |
|--------|---------------|
| Anthropic Official | < 200 lines per file |
| HumanLayer | < 300 lines; ideal < 60 lines |
| SFEIR Institute | < 100 lines (critical at > 200) |
| Morph/Community | 50-100 lines ideal, 200 max |
| Dev.to patterns | 30 lines outperforms longer files |

### Hard Limits

- **200 lines**: Files exceeding this may see reduced adherence due to context dilution
- **40,000 characters**: Reported as a performance-impacting threshold
- **MEMORY.md**: Only first 200 lines loaded at session start (hard truncation)

### Instruction Budget

> "Research suggests frontier LLMs reliably follow around 150-200 distinct instructions. Claude Code's system prompt already contains ~50 built-in instructions, leaving an effective 100-150 item budget." — [Morph Guide](https://www.morphllm.com/claude-md-examples)

**Key insight**: Every line in CLAUDE.md competes with your actual conversation for context window space. The shorter your CLAUDE.md, the more room Claude has for your code.

---

## 4. What Belongs in CLAUDE.md vs. Other Config Files

### Include in CLAUDE.md

| Category | Example |
|----------|---------|
| Bash commands Claude can't guess | `npm run test:integration -- --bail` |
| Code style rules that differ from defaults | "Use 2-space indentation" |
| Testing instructions | "Run `pytest -x` before committing" |
| Repository etiquette | "Branch naming: `feat/TICKET-description`" |
| Architectural decisions | "API handlers live in `src/api/handlers/`" |
| Dev environment quirks | "Requires `REDIS_URL` env var to run tests" |
| Common gotchas | "Don't modify `legacy/` — frozen for compliance" |

### Exclude from CLAUDE.md

| Category | Why |
|----------|-----|
| Things Claude can figure out by reading code | Wastes context |
| Standard language conventions Claude already knows | Redundant |
| Detailed API documentation | Link to docs instead |
| Information that changes frequently | Will become stale |
| Long explanations or tutorials | Too verbose |
| File-by-file descriptions of the codebase | Claude can explore |
| Self-evident practices like "write clean code" | No value added |
| Code style enforceable by linters | Use linters instead |
| Secrets, API keys, credentials | Security risk |

> "Never send an LLM to do a linter's job. LLMs are comparably expensive and incredibly slow compared to traditional linters and formatters." — [HumanLayer Blog](https://www.humanlayer.dev/blog/writing-a-good-claude-md)

### Where to Put What

| Content Type | File/Location |
|-------------|---------------|
| Universal project rules | `./CLAUDE.md` (checked in) |
| Personal preferences | `~/.claude/CLAUDE.md` |
| Sensitive local config | `CLAUDE.local.md` (gitignored) |
| Topic-specific rules | `.claude/rules/*.md` |
| File-type-scoped rules | `.claude/rules/*.md` with `paths:` frontmatter |
| On-demand workflows | `.claude/skills/*/SKILL.md` |
| Org-wide policies | `/Library/Application Support/ClaudeCode/CLAUDE.md` (macOS) |

---

## 5. File Hierarchy and Priority

### Location Hierarchy (from broadest to most specific)

| Scope | Location | Shared With |
|-------|----------|-------------|
| **Managed policy** (IT/DevOps) | `/Library/Application Support/ClaudeCode/CLAUDE.md` (macOS) | All org users |
| **User instructions** | `~/.claude/CLAUDE.md` | Just you (all projects) |
| **User rules** | `~/.claude/rules/*.md` | Just you (all projects) |
| **Project instructions** | `./CLAUDE.md` or `./.claude/CLAUDE.md` | Team via git |
| **Project rules** | `./.claude/rules/*.md` | Team via git |
| **Subdirectory** | `./subdir/CLAUDE.md` | Team via git |

### How They Combine

> "Levels combine (don't replace). All rules apply simultaneously, with more specific levels overriding on conflicts." — [Community consensus](https://github.com/shanraisshan/claude-code-best-practice)

- **User-level rules** load before project rules → project rules have higher priority
- **Parent directory** CLAUDE.md files load at launch (walking up from working directory)
- **Subdirectory** CLAUDE.md files load on demand when Claude reads files in those directories
- **Managed policy** CLAUDE.md cannot be excluded by individual settings
- **`claudeMdExcludes`** setting can skip irrelevant files in monorepos

### Loading Behavior

> "Claude Code reads CLAUDE.md files by walking up the directory tree from your current working directory, checking each directory along the way. This means if you run Claude Code in `foo/bar/`, it loads instructions from both `foo/bar/CLAUDE.md` and `foo/CLAUDE.md`." — [Anthropic Official Docs](https://code.claude.com/docs/en/memory)

---

## 6. The `@path/to/file` Import Syntax

### Basic Syntax

```markdown
See @README.md for project overview and @package.json for available npm commands.

# Additional Instructions
- Git workflow: @docs/git-instructions.md
- Personal overrides: @~/.claude/my-project-instructions.md
```

### Key Rules

| Rule | Detail |
|------|--------|
| **Path resolution** | Relative to the file containing the import (not working directory) |
| **Absolute paths** | Supported (e.g., `@~/.claude/personal.md`) |
| **Recursive imports** | Imported files can import other files |
| **Max depth** | 5 hops maximum |
| **First-time approval** | Claude Code shows a dialog the first time it encounters external imports |

### When to Use

- **Modularize large CLAUDE.md**: Split into topic files, import them
- **Reuse existing docs**: Import README, CONTRIBUTING.md, etc. instead of duplicating
- **Personal overrides**: Import `~/.claude/my-project-instructions.md` from shared CLAUDE.md
- **Cross-repo sharing**: Import shared standards from a central location

> "Prefer pointers to copies. Don't include code snippets in these files if possible — they will become out-of-date quickly. Instead, include `file:line` references." — [HumanLayer Blog](https://www.humanlayer.dev/blog/writing-a-good-claude-md)

---

## 7. Best Practices for Keeping CLAUDE.md Concise and Effective

### The Pruning Test

> "For each line, ask: 'Would removing this cause Claude to make mistakes?' If not, cut it. Bloated CLAUDE.md files cause Claude to ignore your actual instructions!" — [Anthropic Official Docs](https://code.claude.com/docs/en/best-practices)

### Structural Best Practices

1. **Use markdown headers and bullets** — Claude scans structure like a reader
2. **Write specific, verifiable instructions** — "Use 2-space indentation" beats "format code properly"
3. **Use positive phrasing** — "Use named exports exclusively" instead of "Do NOT use default exports"
4. **Anchor critical rules at top and bottom** — Leverage primacy and recency bias
5. **Add emphasis for critical rules** — Use `IMPORTANT` or `YOU MUST` to improve adherence
6. **Progressive disclosure** — Keep root file lean, link to detail files

### The 30-Line Rule (Community Pattern)

> "A 30-line CLAUDE.md covering only the things Claude cannot infer from your code outperforms a comprehensive 200-line file every time." — [Dev.to Patterns](https://dev.to/docat0209/5-patterns-that-make-claude-code-actually-follow-your-rules-44dh)

### Use `.claude/rules/` for Modular Rules

```
.claude/
├── CLAUDE.md           # Main project instructions (lean)
└── rules/
    ├── code-style.md   # Code style guidelines
    ├── testing.md      # Testing conventions
    └── security.md     # Security requirements
```

Rules can be **path-scoped** with YAML frontmatter:

```markdown
---
paths:
  - "src/api/**/*.ts"
---
# API Development Rules
- All API endpoints must include input validation
```

### Use Hooks Instead of CLAUDE.md for Hard Enforcement

> "If you have told Claude not to do something 3 times and it keeps doing it, move that rule from CLAUDE.md to a hook." — [Dev.to Patterns](https://dev.to/docat0209/5-patterns-that-make-claude-code-actually-follow-your-rules-44dh)

---

## 8. Common Mistakes to Avoid

### Critical Mistakes (ranked by impact)

| # | Mistake | Impact | Fix |
|---|---------|--------|-----|
| 1 | **File too long** (>200 lines) | Instructions silently ignored | Prune ruthlessly; move detail to `.claude/rules/` |
| 2 | **Vague instructions** | Inconsistent behavior | Make every rule specific and verifiable |
| 3 | **Contradictory rules** across hierarchy | Arbitrary behavior | Audit all files periodically; resolve conflicts |
| 4 | **Using negation** ("Do NOT...") | LLMs struggle with negation | Rephrase as positive directives |
| 5 | **Duplicating linter's job** | Wasted context, expensive | Use ruff/eslint/prettier instead |
| 6 | **Secrets in CLAUDE.md** | Security vulnerability | Use `CLAUDE.local.md` (gitignored) |
| 7 | **Unsupervised Auto Memory** | Context pollution | Audit MEMORY.md every 2 weeks |
| 8 | **No project-level CLAUDE.md** | Claude rediscovers everything each session | Create even a minimal 10-line file |

### Anti-Patterns

> "The over-specified CLAUDE.md: If your CLAUDE.md is too long, Claude ignores half of it because important rules get lost in the noise." — [Anthropic Official Docs](https://code.claude.com/docs/en/best-practices)

> "If Claude keeps doing something you don't want despite having a rule against it, the file is probably too long and the rule is getting lost." — [Anthropic Official Docs](https://code.claude.com/docs/en/best-practices)

> "Precise instructions improve response compliance by 40% compared to generic instructions." — [SFEIR Institute](https://institute.sfeir.com/en/claude-code/claude-code-memory-system-claude-md/errors/)

---

## 9. Community Examples of Well-Structured CLAUDE.md Files

### Example 1: Minimal (25-30 lines)

```markdown
# Project
Small TypeScript CLI tool for data transformation.

# Stack
TypeScript 5.4, Node 22, Vitest, Biome

# Commands
- `bun run dev` — start dev server on port 3001
- `bun test` — run all tests
- `bun run lint` — lint and format

# Conventions
- Strict TypeScript: never use `any`
- Named exports only
- Tests live next to source files (*.test.ts)

# Gotchas
- Port 3001 must be free (no fallback)
- `.env.local` required for API keys (copy from `.env.example`)
```

### Example 2: Monorepo Root (~60 lines)

```markdown
# Monorepo Structure
- `packages/core` — shared business logic
- `packages/web` — Next.js frontend
- `packages/api` — Express API server
- `packages/shared-types` — TypeScript types used across packages

# Commands
- `pnpm install` — install all dependencies
- `pnpm -F web dev` — start web frontend
- `pnpm test` — run all tests across packages

# Cross-Package Rules
- Shared types go in `packages/shared-types`
- Never install dependencies at root — always scope to a package
- Breaking changes to `shared-types` require updating all consumers

# Git
- Branch: `feat/TICKET-description` or `fix/TICKET-description`
- Commits: conventional commits (feat:, fix:, chore:)
- CI must pass before merge
```

### Example 3: Python ML Project (~70 lines)

```markdown
# Project
ML pipeline for vulnerability classification using XGBoost.

# Stack
Python 3.11, XGBoost, scikit-learn, Pydantic v2, pytest, ruff, mypy

# Commands
- `uv run pytest -x` — run tests (stop on first failure)
- `uv run ruff check && uv run ruff format` — lint and format
- `uv run mypy src/` — type checking

# Architecture
Hexagonal: domain/ → ports (interfaces) → adapters (implementations)
- Domain must never import from adapters
- Use cases receive ports via dependency injection

# Conventions
- Type hints on all function signatures
- Pydantic v2 models for all data structures
- structlog for logging (no print statements)
- pathlib.Path instead of os.path

# Data
- `data/raw/` — immutable input data
- `data/processed/` — generated artifacts (gitignored)
- Test fixtures in `tests/fixtures/`
```

---

## 10. Advanced Patterns

### CLAUDE.local.md

For personal, non-committed preferences. Add to `.gitignore`. Used for:
- Local environment paths
- Personal workflow overrides
- Sensitive configuration

### Path-Scoped Rules (`.claude/rules/`)

```markdown
---
paths:
  - "src/**/*.{ts,tsx}"
  - "tests/**/*.test.ts"
---
# Frontend Rules
- Use React Server Components by default
- Client components only when interactivity is needed
```

### Symlinks for Shared Rules

```bash
ln -s ~/shared-claude-rules .claude/rules/shared
ln -s ~/company-standards/security.md .claude/rules/security.md
```

### Compaction-Proof Instructions

> "CLAUDE.md fully survives compaction. After `/compact`, Claude re-reads your CLAUDE.md from disk and re-injects it fresh into the session." — [Anthropic Official Docs](https://code.claude.com/docs/en/memory)

Add instructions like: `"When compacting, always preserve the full list of modified files and any test commands"` to ensure critical context survives summarization.

### Diagnostics

Run `/memory` to see exactly which CLAUDE.md files and rules are loaded in the current session. Use `InstructionsLoaded` hook for debugging path-specific rules.

---

## 11. Summary: The Golden Rules

1. **< 200 lines** per file (ideally 50-100)
2. **Only include what Claude can't infer** from reading code
3. **Be specific and verifiable** — no vague directives
4. **Use positive phrasing** — avoid negation
5. **Use `.claude/rules/`** for modular, path-scoped instructions
6. **Use hooks** for rules that must be enforced deterministically
7. **Use skills** for on-demand workflows (not loaded every session)
8. **Use `@imports`** to keep the root file lean
9. **Prune regularly** — treat it like code, review when things go wrong
10. **Check in to git** — it compounds in value for the whole team

---

## Sources

- [Anthropic Official — Best Practices for Claude Code](https://code.claude.com/docs/en/best-practices)
- [Anthropic Official — How Claude Remembers Your Project](https://code.claude.com/docs/en/memory)
- [Anthropic Blog — Using CLAUDE.MD Files](https://claude.com/blog/using-claude-md-files)
- [HumanLayer — Writing a Good CLAUDE.md](https://www.humanlayer.dev/blog/writing-a-good-claude-md)
- [Builder.io — How to Write a Good CLAUDE.md File](https://www.builder.io/blog/claude-md-guide)
- [Morph — CLAUDE.md Examples and Best Practices 2026](https://www.morphllm.com/claude-md-examples)
- [SFEIR Institute — The CLAUDE.md Memory System Common Mistakes](https://institute.sfeir.com/en/claude-code/claude-code-memory-system-claude-md/errors/)
- [Dev.to — 5 Patterns That Make Claude Code Actually Follow Your Rules](https://dev.to/docat0209/5-patterns-that-make-claude-code-actually-follow-your-rules-44dh)
- [Eesel.ai — 7 Claude Code Best Practices for 2026](https://www.eesel.ai/blog/claude-code-best-practices)
- [shanraisshan — Claude Code Best Practice (GitHub)](https://github.com/shanraisshan/claude-code-best-practice)
- [Steve Kinney — Referencing Files in Claude Code](https://stevekinney.com/courses/ai-development/referencing-files-in-claude-code)
- [GitHub Issue #2950 — Imports or CLAUDE.local.md](https://github.com/anthropics/claude-code/issues/2950)
- [UX Planet — CLAUDE.md Best Practices (March 2026)](https://uxplanet.org/claude-md-best-practices-1ef4f861ce7c)
