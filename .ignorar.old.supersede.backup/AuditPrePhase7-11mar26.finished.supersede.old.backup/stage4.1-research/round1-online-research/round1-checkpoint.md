# Round 1 Checkpoint — COMPLETE

**Timestamp:** 2026-03-13
**Status:** COMPLETE

## Files Produced

| File | Lines | Content |
|------|-------|---------|
| `2026-03-13-12.17.41-r1-agent-definitions-memory.md` | 189 | Agent definition format + memory system research |
| `2026-03-13-12.17.41-r1-hooks-settings.md` | 393 | Hook system (17 types) + settings.json schema |
| `2026-03-13-12.17.41-r1-skills-claudemd-workflow.md` | 233 | Skills 2.0 + CLAUDE.md + workflow patterns |
| `2026-03-13-12.17.41-r1-teams-new-features.md` | 296 | Agent teams + new features Jan–Mar 2026 |
| `round1-final-summary.md` | — | Consolidated summary of all 4 reports |

**Total research lines:** 1,111

## Key Findings (top 20)

1. Agent definitions: 13 frontmatter fields; only `name` + `description` required
2. New 2026 agent fields: `background`, `isolation`, `skills`, `memory`, `hooks`
3. Subagents CANNOT nest (spawn other agents)
4. Valid model values: `sonnet`, `opus`, `haiku`, full IDs, or `inherit`
5. Memory types: `user`, `project`, `local`
6. MEMORY.md: first 200 lines loaded at session start (hard cut)
7. Auto-memory on by default since v2.1.59; `autoMemoryDirectory` setting exists
8. Hook system: 17 confirmed event types total
9. TeammateIdle and TaskCompleted hooks are real and can block (exit code 2)
10. PostCompact does NOT exist — use SessionStart with `compact` matcher
11. SessionStart `compact` matcher bug #15174: stdout not injected post-compaction
12. PreCompact `transcript_path` null bug #13668: always guard with null check
13. Skills 2.0 (v2.1.3, Jan 2026): slash commands merged into skills
14. CLAUDE.md loading order: managed → personal → project → ancestor
15. CLAUDE.md target: under 200 lines
16. `.claude/workflow/` is a CUSTOM convention, not official — official recommends skills, rules, hooks, agents
17. Teams require v2.1.32+ and `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`
18. New tools: CronCreate/List/Delete (v2.1.71), ExitWorktree (v2.1.72)
19. Opus 4/4.1 removed → Opus 4.6; Sonnet 4.6 has 1M context
20. settings.json array settings MERGE across scopes (project + user)
