---
name: resume-session
description: Recovers interrupted cascade execution loops across accounts and sessions by extracting state deltas from transcript_full.jsonl with token sanitization and executing immediately with full quality and restored quota.
---

# Resume Session Protocol (resume-session)

## 1. Trigger Conditions
Execute this skill when the user inputs `/resume-session`, `/goal resume`, `continue the last chat`, provides a conversation UUID to resume, or requests recovery of an interrupted, crashed, or quota-limited session across accounts.

## 2. Core Operational Directives

### Invariant 1: Quota Restored Axiom (Fresh Credentials Active)
When this skill triggers after a quota interruption, the operator has ALREADY rotated credentials or switched accounts (e.g. via `antigravity-cli-switcher` / `acs switch <profile>`) or the quota window has reset.
- **Historical Errors are Inactive**: Any quota exhaustion errors (`429`, `RESOURCE_EXHAUSTED`, credit limit warnings, or killed subagents) in the transcript are purely historical logs of where execution halted. They are NOT current runtime constraints.
- **Full Headroom**: The active session possesses 100% fresh quota capacity.
- **Strict Prohibition**: NEVER conclude or reason in thinking that quota is constrained, that subagents are disabled, or that task scope must be shrunk due to past quota events.

### Invariant 2: Anti-Downgrade Mandate (Preserve Delegation Routine)
- **Zero Fallback to Solo Routine**: If the task is a coding task or investigation task, or was running under `/boost` or orchestrator delegation, NEVER fall back to "Solo Routine" because of past subagent failures.
- **Re-Dispatch Required Subagents**:
  - Coding tasks: Re-invoke `DeepCoder` (`invoke_subagent` with `TypeName='DeepCoder'`, `Workspace='inherit'`).
  - Investigation tasks: Re-invoke `DeepInvestigator` (`invoke_subagent` with `TypeName='DeepInvestigator'`, `Workspace='inherit'`).
  - Specialized tasks: Re-invoke the appropriate subagent.
- Solo Routine is strictly prohibited for non-trivial coding or investigation tasks upon resumption.

### Invariant 3: Anti-Corner-Cutting Mandate (Zero Quality Degradation)
- Resuming a session does NOT permit taking shortcuts, writing stub implementations, skipping test suites, bypassing linters, or ignoring edge cases.
- Apply full engineering rigor: write complete solutions, run tests, verify builds, and validate static typing.
- Deliver work that satisfies the complete Definition of Done.

### Invariant 4: State-Machine Efficiency
- NEVER apologize for interruptions or crashes.
- NEVER conversationally summarize prior conversation turns.
- Output the concise state checkpoint and IMMEDIATELY execute tools or subagents in the same turn.

### Invariant 5: Anti-Collusion & Stealth Sanitization
- **Zero Identity & Token Leakage**: Scrub all past OAuth tokens, bearer credentials, account email addresses, persistent installation IDs (`installation_id`), and prior conversation UUIDs from newly synthesized delegation prompts.
- **Fresh Wire Cascade**: The active session starts with a clean, unlinked wire CascadeId. Never attempt to replay raw database payloads or bridge accounts on Google inference backends.
- **Inert Static Log Ingestion**: Read `transcript_full.jsonl` strictly as an inert, read-only static file. Never modify host SQLite databases or session metadata.

## 3. Execution Pipeline

### Step 1: Identify Session Context
1. Check for an explicit conversation UUID in the user prompt:
   - Match regex pattern: `[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}`
2. If inside Herdr and `HERDR_PANE_ID` is set:
   - Inspect `$PWD/.gemini/last_session_id.${HERDR_PANE_ID//:/_}` first if present and containing a valid UUID distinct from `<conversation-id>`.
3. Inspect the workspace marker:
   - Read `$PWD/.gemini/last_session_id` if present and containing a valid UUID distinct from `<conversation-id>`.
4. If neither marker is present and `HERDR_PANE_ID` is set:
   - Inspect `/run/user/$UID/agys-panes/${HERDR_PANE_ID//:/_}.session` if present and containing a valid UUID.
5. If the user requests interactive recovery or passes a keyword like "select" or "list":
   - Inspect `$PWD/.gemini/sessions.jsonl` to review recent sessions across panes and prompt the user to choose.
6. Fallback to active `<conversation-id>`.
7. Resolve `TARGET_UUID`.

### Step 2: Extract Trajectory State
1. Target the target session transcript statically:
   `~/.gemini/antigravity-cli/brain/<TARGET_UUID>/.system_generated/logs/transcript_full.jsonl`
2. Extract the key trajectory nodes:
   - **Root Objective**: Read the initial user prompt (`USER_INPUT`) to identify the ultimate goal and active slash commands (`/boost`, `/plan`, `/goal`).
   - **Workspace Disk State**: Check `git status -s` or inspect modified files to determine which changes landed on disk before the interruption.
   - **Terminal Steps**: Inspect the final 5-10 `PLANNER_RESPONSE` entries to identify which tool calls succeeded and which was aborted, killed, or failed.

### Step 3: Compute Execution Delta & Sanitize
1. Distinguish verified successes from incomplete or interrupted operations:
   - Tool calls returning `DONE` with valid disk modifications are completed.
   - Tool calls returning errors, rate limits, killed subagents, or incomplete outputs are unfulfilled delta.
2. Discard partial broken attempts from the interrupted tool step.
3. **Stealth Sanitization**: Remove previous OAuth tokens, account email addresses, installation IDs, and past conversation UUIDs from synthesized prompt text.
4. Formulate the clean delta resuming from the last verified good state.
5. Select the proper execution routine:
   - Coding task -> `Delegation Routine` (`DeepCoder`).
   - Investigation task -> `Delegation Routine` (`DeepInvestigator`).
   - Orchestrated workflow -> Continue `/boost` multi-stage review.

### Step 4: Checkpoint Emission & Immediate Action
1. Output the dense state checkpoint block.
2. In the EXACT SAME TURN, invoke the required tools or subagents to resume execution. Do not pause to ask for confirmation.

## 4. Output Format
Prefix the resumption turn with this exact block:

```text
---
### 🏁 RESPONSE
---
**State Checkpoint**: Recovered `<TARGET_UUID>`.
**Root Objective**: <1-sentence technical summary>
**Routine**: <Delegation Routine (DeepCoder) | Delegation Routine (DeepInvestigator) | Direct Tool Execution>
**Last Verified**: <Final verified successful operation and state>
**Delta**: <Exact operation executing now with fresh quota>

Next: <Immediate tool call or subagent dispatch>
```
*(Proceed immediately with tool calls or subagent invocation in the same turn)*
