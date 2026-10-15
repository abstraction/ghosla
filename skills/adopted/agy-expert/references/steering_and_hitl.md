# Agent Steering, Slash Commands, & HITL Protocols

This reference covers the Cascade runtime loop, slash command mechanics, CLI execution flags, queued message steering, emergency killswitches, and strict Linux D-Bus keyring safety.

---

## 1. The Cascade Execution Loop

Antigravity executes conversational turns through the **Cascade** engine:
- **Turn**: A prompt submitted by the operator.
- **Step**: An individual tool call executed by the harness (e.g. `run_command`, `replace_file_content`). A turn routinely spans 1 to 50+ steps.
- **Interruption**: Pressing `Esc` or `Ctrl+C` halts the active step immediately and returns prompt control without corrupting session history.

---

## 2. Slash Command Pipeline & Semantics

Slash commands operate across four pipeline stages:
1. **Lexical Stacking**: Consecutive leading commands are extracted and executed in sequence (e.g. `/plan /grill-me`).
2. **Protobuf Scoping**: Command parameters are encapsulated into a `SlashCommandScopeItem`.
3. **Context Expansion**: `GetModelFacingText()` generates authoritative XML envelopes (`<ORCHESTRATOR>`, `<GRILL_ME>`) placed in `<ADDITIONAL_METADATA>`.
4. **Harness Loop Interception**: Modifies toolsets, permissions, or turn exit conditions.

### Core Slash Commands

| Command | Harness Effect |
| :--- | :--- |
| `/boost` | Activates orchestrator mode. Forbids raw ad-hoc coding; requires delegation to `DeepCoder` or `DeepInvestigator` subagents. Enforces multi-round diff audits. |
| `/plan` | Switches mode to `plan`. Disarms file modification tools (`replace_file_content`, `write_to_file`) until the operator clicks the interactive "Proceed" button. |
| `/grill-me` | Enforces single-question interview discipline via `ask_question`. Discovers codebase facts silently first before questioning the operator. |
| `/goal` | Intercepts turn completion. If model output lacks `<!-- GOAL_COMPLETE -->`, the harness automatically re-prompts the model to continue working. |
| `/schedule` | Sets recurring cron jobs or one-shot notification timers. |
| `/config` | Opens interactive settings menu (toggle values with `←`/`→`). |
| `/resume` | Opens visual conversation selector to resume historical sessions. |

### Practical Stacking Combinations
- `/plan /grill-me <prompt>`: Clarifies architectural requirements first, then locks into planning mode to draft an approved implementation plan.
- `/boost /goal <prompt>`: Spawns an orchestrator managing deep subagents for long-running autonomous execution until the task passes verification.

---

## 3. CLI Execution Flags & Headless Scripting

```bash
# Launch interactive pairing session
agy

# Continue last active session
agy -c

# Resume specific session by ID
agy --conversation <CONVERSATION_ID>

# Add auxiliary workspace directories
agy --add-dir /path/to/extra/dir

# Adjust reasoning effort level
agy --effort [low|medium|high|xhigh|max]

# Set execution mode
agy --mode [plan|accept-edits]

# Headless one-shot prompt
agy -p "Summarize git commit history for today"

# Headless structured JSON output
agy -p "List all exported API routes" --output-format json

# Enforce JSON schema on response
agy -p "Audit dependencies" --json-schema schema.json --output-format json

# Headless stream-json NDJSON pipeline
echo '{"message": "Audit tools/extract_all.py"}' | \
  agy --input-format stream-json --output-format stream-json
```

---

## 4. Queued Messages Configuration

In `~/.gemini/antigravity-cli/settings.json` or `/config` (toggle with `←`/`→`):
- **`queue` (Default)**: Messages submitted mid-turn are queued and delivered when the current turn ends.
- **`send-immediately`**: Messages interrupt the active turn as high-priority guidance.
- JSON configuration:
  ```json
  {
    "queuedMessages": "send-immediately"
  }
  ```

---

## 5. STRICT Keyring Non-Collision with `antigravity-cli-switcher` (`acs`)

> [!CAUTION]
> **CRITICAL OPERATIONAL SAFEGUARD**: The host machine manages multi-account quota failover using [`/home/seren/code/antigravity-cli-switcher`](file:///home/seren/code/antigravity-cli-switcher) (`acs`).

### Why Sandboxing Tricks Fail
- `agy` queries credentials directly from the Linux FreeDesktop Secret Service over D-Bus (`service=gemini`, `username=antigravity`).
- Overriding `$HOME` or setting custom environment variables **does not isolate credentials**. All child processes share the same desktop D-Bus session socket.
- Querying or mutating credentials inside an automated turn overwrites the active session token and terminates running processes.

### Invariant Rules
1. **Never Touch Keyring via Automation**: Never invoke `secret-tool`, `keyring`, or credential commands in scripts or agent turns.
2. **Never Run Account Switching Commands**: Do not call `acs switch` inside agent turns. Account switching is strictly performed by the operator in an external terminal.
3. **Static Analysis Only**: Scripts in `antigy/tools/` inspect static binaries and catalogs only.

---

## 6. Emergency Killswitches & Interventions

### In-Session Control
- `Esc` or `Ctrl+C`: Aborts active tool step immediately.
- `Ctrl+D Ctrl+D` or `/exit`: Cleanly exits CLI session.

### Hung Child Process Termination
If a background command or child worker hangs:
```bash
# 1. Identify child process PID
ps aux | grep -E "antigravity|node|python|cargo" | grep -v grep

# 2. Terminate hung PID (agent receives exit status 137 and continues cleanly)
kill -9 <PID>
```

### Emergency Process Kill
If the CLI UI freezes completely:
```bash
killall -9 antigravity agy agentapi 2>/dev/null || pkill -9 -f antigravity
```

### Quota Exhaustion & Failover Protocol
When hitting quota limits (`"Your AI credits balance is too low to continue"` or 429/ResourceExhausted on subagents):
1. **Never spam retry prompts**: Retries burn remaining burst tokens and extend backoff penalties.
2. **Failover via `acs switch`**: The operator switches active profile in an external terminal:
   ```bash
   acs switch <profile_name>
   ```
3. **Resume via `/resume-session`**: Trigger `/resume-session` in the interrupted session.
4. **Resumption Invariants**:
   - **Fresh Quota Active**: The agent treats all historical quota errors in `transcript_full.jsonl` as past interruption triggers, NOT present constraints.
   - **Enforce Delegation Routine**: Never downgrade to Solo Routine or bypass `DeepCoder`/`DeepInvestigator` due to past subagent quota errors. Re-dispatch the required subagents with full fidelity.
   - **Zero Corner-Cutting**: Resumed sessions must execute with full engineering rigor (tests, linters, types, complete implementations).
5. **Check Reset Time (Alternative to Failover)**:
   The operator inspects usage in an external terminal or via `acs watch` (http mode):
   ```bash
   acs watch
   ```
