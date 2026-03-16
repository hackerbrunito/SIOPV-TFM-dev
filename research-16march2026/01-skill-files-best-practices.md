# Claude Code Skill Files — Best Practices Research (March 2026)

> **Researched:** 2026-03-16
> **Sources:** Official Anthropic docs, community guides, GitHub issues, empirical testing reports

---

## 1. Recommended Maximum Length for SKILL.md

### Official Recommendation

> **"Keep SKILL.md under 500 lines."** — [Claude Code Docs: Skills](https://code.claude.com/docs/en/skills)

> **"Keep SKILL.md body under 500 lines for optimal performance. If your content exceeds this, split it into separate files using the progressive disclosure patterns."** — [Anthropic API Docs: Skill Authoring Best Practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)

### Community Guidance (MindStudio Architecture Article)

> **"A well-structured skill.md should typically be 40–100 lines. If yours is significantly longer, it's likely because context has leaked into the process file."** — [MindStudio: Claude Code Skills Architecture](https://www.mindstudio.ai/blog/claude-code-skills-architecture-skill-md-reference-files)

### Character Budget for Skill Descriptions (System Prompt)

There is an undocumented **cumulative character budget** for skill metadata loaded into the system prompt:

- **Approximate limit:** 15,500–16,000 characters total for ALL skill descriptions
- **Budget formula:** 2% of context window, with a fallback of 16,000 characters
- **Override:** Set `SLASH_COMMAND_TOOL_CHAR_BUDGET` environment variable
- **Impact:** With 63 installed skills, 21 (33%) were completely hidden from the agent

> Source: [GitHub Issue #13099](https://github.com/anthropics/claude-code/issues/13099)

**Guidelines to maximize visibility:**
- 60+ skills: Keep descriptions ≤ 130 characters
- 40–60 skills: Keep descriptions ≤ 150 characters
- All collections: Front-load trigger keywords in first 50 characters

### Summary of Length Limits

| Element | Hard Limit | Recommended |
|---------|-----------|-------------|
| `name` field | 64 characters | Short, descriptive |
| `description` field | 1,024 characters | 130–200 characters |
| SKILL.md body | No hard limit | **40–100 lines** (ideal), **< 500 lines** (max) |
| Total skills budget | ~16,000 chars | Keep ≤ 20–30 skills |

---

## 2. Recommended Structure/Format for SKILL.md

### Official Format (from Claude Code Docs)

```yaml
---
name: my-skill-name
description: What this skill does and when to use it. Third person. Include trigger keywords.
---

# Skill Title

## Instructions
[Step-by-step process Claude follows]

## Examples
[Input/output pairs showing expected behavior]

## Additional resources
- For X details, see [reference.md](reference.md)
- For Y examples, see [examples.md](examples.md)
```

### All Available Frontmatter Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | No (uses dir name) | Lowercase letters, numbers, hyphens only. Max 64 chars. No "anthropic" or "claude". |
| `description` | Recommended | What skill does + when to use it. Max 1,024 chars. Third person. |
| `argument-hint` | No | Hint shown during autocomplete, e.g., `[issue-number]` |
| `disable-model-invocation` | No | `true` = only user can invoke (for deploy, commit, etc.) |
| `user-invocable` | No | `false` = hidden from `/` menu (background knowledge only) |
| `allowed-tools` | No | Tools allowed without permission prompts, e.g., `Read, Grep, Glob` |
| `model` | No | Model override when skill is active |
| `context` | No | `fork` = run in isolated subagent context |
| `agent` | No | Subagent type when `context: fork` is set (`Explore`, `Plan`, `general-purpose`, or custom) |
| `hooks` | No | Hooks scoped to this skill's lifecycle |

### String Substitution Variables

| Variable | Description |
|----------|-------------|
| `$ARGUMENTS` | All arguments passed when invoking |
| `$ARGUMENTS[N]` or `$N` | Access specific argument by 0-based index |
| `${CLAUDE_SESSION_ID}` | Current session ID |
| `${CLAUDE_SKILL_DIR}` | Directory containing the SKILL.md file |

### Dynamic Context Injection

Use `` !`command` `` syntax to run shell commands before skill content is sent to Claude:

```yaml
---
name: pr-summary
description: Summarize changes in a pull request
context: fork
agent: Explore
---

## Pull request context
- PR diff: !`gh pr diff`
- PR comments: !`gh pr view --comments`
```

---

## 3. Best Practices for Writing Effective Skill Files

### Core Principles

#### 3.1 Conciseness is Key

> **"Default assumption: Claude is already very smart. Only add context Claude doesn't already have."** — [Anthropic Best Practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)

Challenge each piece of information:
- "Does Claude really need this explanation?"
- "Can I assume Claude knows this?"
- "Does this paragraph justify its token cost?"

#### 3.2 Process in SKILL.md, Context in Reference Files

> **"Process goes in skill.md, context goes in reference files."** — [MindStudio](https://www.mindstudio.ai/blog/claude-code-skills-architecture-skill-md-reference-files)

**SKILL.md should contain:**
- Brief skill description (2–4 sentences)
- Prerequisites/inputs specification
- Numbered, explicit process steps
- Output specification

**Reference files should contain:**
- Domain definitions and terminology
- Templates and example outputs
- Rules, constraints, and requirements
- Edge case handling

#### 3.3 Progressive Disclosure (Three Levels)

| Level | What | When Loaded | Token Cost |
|-------|------|-------------|------------|
| Level 1 | Metadata (name + description) | Always at startup | ~100 tokens |
| Level 2 | SKILL.md body | When skill is triggered | < 5,000 tokens ideal |
| Level 3 | Referenced files | On-demand by Claude | Only when accessed |

#### 3.4 Write Effective Descriptions

> **"Always write in third person. The description is injected into the system prompt, and inconsistent point-of-view can cause discovery problems."** — [Anthropic Best Practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)

**Good:** "Processes Excel files and generates reports. Use when analyzing .xlsx files or tabular data."
**Bad:** "I can help you process Excel files" / "You can use this to process Excel files"

Include "USE WHEN" patterns with specific trigger keywords.

#### 3.5 Naming Conventions

Use **gerund form** (verb + -ing):
- `processing-pdfs`, `analyzing-spreadsheets`, `testing-code`

Avoid: `helper`, `utils`, `tools`, `documents` (too vague)

#### 3.6 Set Appropriate Degrees of Freedom

- **High freedom** (text instructions): Multiple valid approaches, context-dependent
- **Medium freedom** (pseudocode/templates): Preferred pattern exists, some variation OK
- **Low freedom** (exact scripts): Operations are fragile, consistency critical

#### 3.7 Keep References One Level Deep

**Bad:** SKILL.md → advanced.md → details.md (Claude may only partially read deeply nested files)

**Good:** SKILL.md → advanced.md, SKILL.md → reference.md, SKILL.md → examples.md

#### 3.8 Test Across Models

> **"Skills act as additions to models, so effectiveness depends on the underlying model."** — [Anthropic Best Practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)

What works for Opus might need more detail for Haiku.

### Activation Optimization

Empirical testing across 200+ prompts:

| Strategy | Activation Rate |
|----------|----------------|
| No optimization | ~20% |
| Optimized descriptions | ~50% |
| LLM pre-eval hook | ~80% |
| Forced eval hook | ~84% |

> Source: [Skills Structure and Usage Guide (Gist)](https://gist.github.com/mellanon/50816550ecb5f3b239aa77eef7b8ed8d)

---

## 4. What Should vs. Should NOT Be in a Skill File

### SHOULD be in SKILL.md

- Clear, specific description with trigger keywords
- Step-by-step process instructions (numbered)
- Quick-start example (most common use case)
- Links to reference files for detailed content
- Workflow checklists for complex multi-step tasks
- Feedback loops (validate → fix → repeat)
- Input/output examples

### SHOULD NOT be in SKILL.md

- Long reference documentation (put in separate files)
- API keys, tokens, or credentials (use env vars)
- Time-sensitive information (or use "old patterns" sections)
- Explanations of things Claude already knows (PDFs, libraries, etc.)
- Windows-style paths (always use forward slashes)
- Multiple equivalent approaches without a clear default
- Vague descriptions ("helps with files", "processes data")
- Deeply nested file references
- "Voodoo constants" — unexplained magic numbers

### SHOULD be in Reference Files

- Brand guidelines and voice standards
- Domain-specific definitions and terminology
- Templates for output format
- Complete API documentation
- Extensive example collections
- Compliance rules and constraints
- Edge case handling instructions

---

## 5. Examples of Well-Structured Skill Files

### Example A: Simple Reference Skill (Inline)

```yaml
---
name: api-conventions
description: API design patterns for this codebase. Use when writing or reviewing API endpoints, REST routes, or request handlers.
---

When writing API endpoints:
- Use RESTful naming conventions
- Return consistent error formats
- Include request validation
```

### Example B: Task Skill with Manual Invocation

```yaml
---
name: deploy
description: Deploy the application to production
disable-model-invocation: true
---

Deploy $ARGUMENTS to production:

1. Run the test suite
2. Build the application
3. Push to the deployment target
4. Verify the deployment succeeded
```

### Example C: Multi-File Skill with Progressive Disclosure

```
pdf-processing/
├── SKILL.md
├── FORMS.md
├── reference.md
├── examples.md
└── scripts/
    ├── analyze_form.py
    ├── fill_form.py
    └── validate.py
```

```yaml
---
name: pdf-processing
description: Extracts text and tables from PDF files, fills forms, and merges documents. Use when working with PDF files or when the user mentions PDFs, forms, or document extraction.
---

# PDF Processing

## Quick start

Extract text with pdfplumber:

```python
import pdfplumber
with pdfplumber.open("file.pdf") as pdf:
    text = pdf.pages[0].extract_text()
```

## Advanced features

**Form filling**: See [FORMS.md](FORMS.md) for complete guide
**API reference**: See [reference.md](reference.md) for all methods
**Examples**: See [examples.md](examples.md) for common patterns
```

### Example D: Forked Subagent Skill

```yaml
---
name: deep-research
description: Research a topic thoroughly in the codebase. Use when exploring unfamiliar code areas or investigating how systems work.
context: fork
agent: Explore
---

Research $ARGUMENTS thoroughly:

1. Find relevant files using Glob and Grep
2. Read and analyze the code
3. Summarize findings with specific file references
```

### Example E: Commit Helper with Feedback Loop

```yaml
---
name: commit
description: Generate descriptive commit messages by analyzing git diffs. Use when the user asks for help writing commit messages.
disable-model-invocation: true
---

## Commit message workflow

1. Run `git diff --staged` to see changes
2. Analyze the diff for logical groupings
3. Generate a commit message following Conventional Commits:
   - type(scope): brief description
   - Blank line
   - Detailed explanation of what and why

4. Present the message for approval
5. If approved, execute `git commit -m "..."`
```

---

## 6. Directory Organization

### Recommended Structure

```
.claude/skills/
├── my-skill/
│   ├── SKILL.md              # Main instructions (required, < 500 lines)
│   ├── reference.md           # Detailed docs (loaded on demand)
│   ├── examples.md            # Usage examples (loaded on demand)
│   ├── templates/             # Output templates
│   │   └── report-template.md
│   └── scripts/               # Executable helpers
│       └── validate.sh
├── shared-reference/           # Cross-skill shared content
│   ├── brand-voice.md
│   └── compliance-rules.md
└── another-skill/
    └── SKILL.md
```

### Where Skills Live

| Location | Path | Scope |
|----------|------|-------|
| Enterprise | Managed settings | All org users |
| Personal | `~/.claude/skills/<name>/SKILL.md` | All your projects |
| Project | `.claude/skills/<name>/SKILL.md` | This project only |
| Plugin | `<plugin>/skills/<name>/SKILL.md` | Where plugin enabled |

Priority: Enterprise > Personal > Project. Plugin skills use namespace `plugin-name:skill-name`.

---

## 7. Key Takeaways

1. **SKILL.md < 500 lines** (official), ideally **40–100 lines** (community best practice)
2. **Description < 1,024 chars**, ideally **130–200 chars** with trigger keywords in third person
3. **Limit to 20–30 skills** to stay within the ~16,000 char system prompt budget
4. **Process in SKILL.md, context in reference files** — the golden architecture rule
5. **Progressive disclosure**: metadata always loaded → SKILL.md on trigger → reference files on demand
6. **One level deep references only** — avoid nested file chains
7. **Test across models** — what works for Opus may need more detail for Haiku
8. **Front-load trigger keywords** in the first 50 chars of descriptions
9. **Use gerund naming**: `processing-pdfs`, `analyzing-code`, `managing-deploys`
10. **Never hardcode secrets** — use environment variables or MCP

---

## Sources

- [Claude Code Docs: Extend Claude with Skills](https://code.claude.com/docs/en/skills) — Official documentation
- [Anthropic API Docs: Skill Authoring Best Practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) — Official best practices
- [Claude Help Center: How to Create Custom Skills](https://support.claude.com/en/articles/12512198-how-to-create-custom-skills) — Official help article
- [GitHub Issue #13099: Character Budget Limit](https://github.com/anthropics/claude-code/issues/13099) — Undocumented budget limit
- [MindStudio: Claude Code Skills Architecture](https://www.mindstudio.ai/blog/claude-code-skills-architecture-skill-md-reference-files) — Architecture guidance
- [Skills Structure and Usage Guide (Gist)](https://gist.github.com/mellanon/50816550ecb5f3b239aa77eef7b8ed8d) — Activation statistics
- [GitHub: anthropics/skills](https://github.com/anthropics/skills) — Official Anthropic skills repository
- [GitHub: awesome-claude-skills](https://github.com/travisvn/awesome-claude-skills) — Community curated list
- [Geeky Gadgets: Why 20–30 Beats 1,000](https://www.geeky-gadgets.com/claude-code-skills-best-practices/) — Quantity guidance
- [Dev Genius: Why Anthropic Merged Slash Commands into Skills](https://blog.devgenius.io/why-did-anthropic-merge-slash-commands-into-skills-4bf6464c96ca) — January 2026 merge context
- [Essential Claude Code Skills and Commands (Batsov)](https://batsov.com/articles/2026/03/11/essential-claude-code-skills-and-commands/) — Practitioner guide
