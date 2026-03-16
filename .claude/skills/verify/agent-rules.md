# Universal Agent Rules (apply to ALL agents without exception)

Every agent spawned in this pipeline MUST follow these 4 rules. No exceptions.

## Rule 1 — Handoff Protocol (mandatory)

1. **FIRST action on start:** Write handoff file:
   Path: `{VERIFY_DIR}/handoffs/handoff-{agent-name}.md`
   Content: assigned files list, task description, start timestamp.

2. **After each file processed:** Append one line to handoff:
   `file: {path} | status: done | findings: {N}`

3. **At 65% context usage:** STOP immediately. Write final handoff state. Report to orchestrator:
   `"PAUSED at 65% context — handoff written at {path} — {N} files remaining: {list}"`
   Do not continue past this point. Orchestrator will respawn with handoff as input.

4. **Handoff size target:** 500–2,000 tokens. If it exceeds 2,000 tokens, summarize findings
   rather than dumping raw content. The handoff must be readable by a fresh agent with no
   prior context.

## Rule 2 — Tool Output Offloading

Any tool output exceeding 2,000 tokens MUST be written to a file in `{VERIFY_DIR}/` immediately
after retrieval. Keep only the file path + one-line summary in working context.
Never hold large outputs in memory across tool calls.

Example: After a Context7 `get-library-docs` response (10,000+ tokens):
-> Write full response to `{VERIFY_DIR}/context7-cache/{library}.md`
-> Keep in context: `"pydantic docs saved to {path} — key: ConfigDict replaces class Config"`

## Rule 3 — Explicit Scope Only

Process ONLY the files explicitly listed in your prompt. Do not discover additional files,
do not process files not in your batch. When your assigned files are done, STOP and report.
The prompt "complete all remaining work" is forbidden — every agent prompt specifies an
exact file list.

## Rule 4 — No Live Context7 Calls (scanner/fixer/review agents)

Only the pre-wave library-researcher agent queries Context7 MCP tools directly.
All other agents read from `{VERIFY_DIR}/context7-cache/` files — never call
`mcp__context7__resolve-library-id` or `mcp__context7__get-library-docs` directly.
The cache is pre-built before any wave starts.
