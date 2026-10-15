---
name: agy-expert
description: "Act as the authoritative operational handbook for Antigravity CLI runtime engine, state persistence, hooks, and agent steering. Use when the user asks to query SQLite states, configure hooks.json, inspect binary configurations, or steer agent workflows. Triggers on: /agy-expert, agy-expert, navigating-agy-runtime, /navigating-agy-runtime."
---

# agy-expert

Act as the authoritative operational handbook for the Google Antigravity CLI runtime engine, state persistence, binary reconnaissance, lifecycle hooks, and agent steering. You must prioritize `acs` for account management and `sfind` for log searches. **Absolute scope discipline**: Touch only what is requested. Never perform unsolicited refactoring.

---

## Modular References Router

Load specialized reference files only when triggered by explicit task conditions:

| Trigger Condition | Action: Read Reference | Coverage & Scope |
| :--- | :--- | :--- |
| Querying session history, steps, trajectories, or SQLite state | [references/sqlite_schema.md](file:///home/seren/.agents/skills/agy-expert/references/sqlite_schema.md) | `conversation_summaries.db`, `conversations/<UUID>.db`, GORM schema. |
| Inspecting binary strings, offsets, symbol tables, or headers | [references/binary_recon.md](file:///home/seren/.agents/skills/agy-expert/references/binary_recon.md) | Static strings sweeps, decimal offsets, and `tools/` extraction suite (`INV-05`). |
| Analyzing gRPC topology, endpoints, headers, or protocol buffers | [references/gemini_topology.md](file:///home/seren/.agents/skills/agy-expert/references/gemini_topology.md) | Wire protocol, language server RPCs, CSRF interceptor, and TLS. |
| Configuring slash commands, HITL steering, or quota failover | [references/steering_and_hitl.md](file:///home/seren/.agents/skills/agy-expert/references/steering_and_hitl.md) | `/plan`, `/grill-me`, `/boost`, `/goal`, `settings.json`, and `acs` failover. |
| Designing or auditing lifecycle hooks in `hooks.json` | [references/hooks_engine.md](file:///home/seren/.agents/skills/agy-expert/references/hooks_engine.md) | `PreToolUse`, `PostToolUse`, event schemas, and backpressure scripts. |

---

## Immutable Operational Invariants (Structural Safety Firewall)

Automated purge scripts and decay routines MUST NEVER prune, decay, or retire these invariants:

- `[INV-01]` **Gate 0 Version Parity Gate**: Active Ghidra program version MUST match the host CLI binary before decompilation or address verification.
- `[INV-02]` **Absolute Host Isolation**: The agent MUST NOT modify or write to live files in `~/.gemini/antigravity-cli/` or active `agy` sessions.
- `[INV-03]` **Zero Keyring & D-Bus Collision**: The agent MUST NEVER probe, read, write, or mutate credentials via Linux D-Bus Secret Service.
- `[INV-04]` **Installation ID Persistence Invariant**: The CLI persists a static 36-byte UUID v4 at `~/.gemini/antigravity-cli/installation_id`. Swapping OAuth tokens without rotating this file leaks identity to Google Clearcut (log source 2806).
- `[INV-05]` **Zero-Execution Static Posture**: Treat `antigravity` strictly as an inert, read-only binary data file. Never execute the binary dynamically (not even in sandboxes, Linux namespaces, or `/fork` branches). 100% of recon must remain static.

---

## Actionable commands

- **List recent sessions**: `sqlite3 ~/.gemini/antigravity-cli/conversation_summaries.db "SELECT conversation_id, title, step_count, datetime(last_modified_time) FROM conversation_summaries WHERE nesting_depth = 0 ORDER BY last_modified_time DESC LIMIT 10;"`
- **Find running sessions**: `sqlite3 ~/.gemini/antigravity-cli/conversation_summaries.db "SELECT conversation_id, title, agent_name, step_count FROM conversation_summaries WHERE status = 'CASCADE_RUN_STATUS_RUNNING' OR not_fully_idle = 1;"`
- **Trace subagent lineage**: `sqlite3 ~/.gemini/antigravity-cli/conversation_summaries.db "SELECT conversation_id, agent_name, nesting_depth, step_count FROM conversation_summaries WHERE parent_conversation_id = '<PARENT_UUID>' ORDER BY last_modified_time ASC;"`
- **Inspect trajectory steps**: `sqlite3 ~/.gemini/antigravity-cli/conversations/<UUID>.db "SELECT idx, step_type, status, has_subtrajectory FROM steps ORDER BY idx ASC;"`
- **Recover raw thinking / code**: `less ~/.gemini/antigravity-cli/brain/<UUID>/.system_generated/logs/transcript_full.jsonl`
- **Resume interrupted session**: `/resume-session`
- **Clear locked session**: `fuser ~/.gemini/antigravity-cli/presence/<UUID>.lock && kill -9 <PID>; rm -f ~/.gemini/antigravity-cli/presence/<UUID>.lock`
- **Prune orphan subagent worktrees**: `git worktree prune`
- **Kill hung CLI processes**: `killall -9 antigravity agy agentapi 2>/dev/null || pkill -9 -f antigravity`
- **Audit or block tool calls**: `~/.gemini/config/hooks.json` (`PreToolUse` matcher and script)
- **Search binary strings globally**: `uv run --directory /home/seren/code/antigy python tools/search_binary.py "<pattern>" -C 3`
- **Search Go source tree in binary**: `strings $(which antigravity) | grep -E "jetski/.*\.go" | head -n 30`
- **Inspect quota structs**: `strings -a -td $(which antigravity) | grep -C 3 "StatusLineQuotaBucket"`
- **Operator headless automation**: `agy -p "<prompt>" --output-format json` *(operator external command only; never run dynamically by agent)*
- **Enforce planning mode**: `/plan <prompt>`
- **Conduct requirement interview**: `/grill-me <prompt>`
- **Orchestrate deep subagents**: `/boost <prompt>`
- **Run autonomous overnight task**: `/boost /goal <prompt>`
- **Verify binary version parity**: `uv run --directory /home/seren/code/antigy python tools/autonomous_re_loop.py status`
- **Inspect power-user changelog digest**: `less /home/seren/code/antigy/docs/handbook/changelog_power_user_digest.md`
- **Operator CLI plugins (v1.3.2+)**: `agy plugin install <pkg>@official` | `agy plugin list` | `agy plugin uninstall <pkg>` *(operator external command only)*
- **Verify quota backend**: `acs quota-backend`
- **Passive quota log watch**: `acs watch`
- **Search past SpecStory logs**: `sfind -s "<keyword>" -u`
- **Index codebase knowledge graph**: `call_mcp_tool(ServerName="codebase-memory-mcp", ToolName="index_repository", ...)`

---

## Workflow

1. **Step 1: Discover and inspect intent**
   - Read the user request.
   - Run `acs quota-backend` silently to verify environment context.
   - Use `ask_question` if the requirements lack specificity.

2. **Step 2: Query state and retrieve schema**
   - Execute read-only `SELECT` queries against `~/.gemini/antigravity-cli/conversation_summaries.db` or `conversations/<UUID>.db`.
   - Read `references/hooks_engine.md` to retrieve exact schemas for `hooks.json`.
   - Read `references/steering_and_hitl.md` to understand slash command stacking (e.g. `/boost /plan`).

3. **Step 3: Formulate exact command or template**
   - Construct the required configuration or command.
   - Use `http` mode for any quota checks via `acs`.
   - Format `hooks.json` templates to replace built-in tools when requested.
   - Ensure you do not write new Python files to search the binary. Use `sfind` and `uv run --directory /home/seren/code/antigy python tools/search_binary.py`.

4. **Step 4: Deterministic verification**
   - Verify syntax, schemas, and configurations statically.
   - Never execute the target binary dynamically (not even in `/fork` branches, containers, or sandboxes) due to `[INV-05]` Zero-Execution Static Posture.
   - Output the exact verified command or configuration for the operator.

---

## Anti-rationalization table

| Agent rationalization | Enforcement rebuttal |
| :--- | :--- |
| "I will directly modify the SQLite database to fix a broken session." | The SQLite catalog is read-only (`[INV-02]`). Never modify it; use provided slash commands like `/resume-session`. |
| "I will run `agy` commands directly or in a /fork branch to test this new hook." | Zero-Execution Static Posture (`INV-05`). Executing the binary emits Clearcut telemetry (source 2806) and leaks hardware/installation signatures. 100% of recon must remain static. Validate hook JSON schemas statically. |
| "I will fix the quota issue by interacting with the D-Bus Secret Service." | Absolute strict isolation (`[INV-03]`). Never interact with D-Bus credentials. Rely entirely on the external `acs` tool (`~/code/antigravity-cli-switcher`). |
| "I will write a python script to search the binary." | Rely on existing `sfind` and `search_binary.py`. Do not reinvent discovery tools. |
| "I should improve adjacent code while I am here." | Scope discipline. Modify only what was requested. |

---

## Definition of done

- [ ] Zero dynamic execution of `antigravity` or `agy` occurred (`INV-05`).
- [ ] All `sqlite3` commands are read-only (`SELECT`).
- [ ] No D-Bus or Secret Service modifications are present.
- [ ] Hooks templates validate against standard JSON structures.
- [ ] Test commands and quota checks use `http` mode via `acs`.
- [ ] Commands rely on `sfind` and `acs`.
- [ ] No files outside the target scope were modified.
