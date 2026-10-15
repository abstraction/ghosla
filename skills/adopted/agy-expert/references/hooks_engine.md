# Lifecycle Hooks Engine (`hooks.json`) Reference

The Antigravity runtime provides a deterministic lifecycle hooks engine configured via `~/.gemini/config/hooks.json` (global) or `.agents/hooks.json` (workspace).

---

## 1. Supported Event Types

| Event | When It Fires | Matcher Target | Schema Structure |
| :--- | :--- | :--- | :--- |
| `PreToolUse` | Before a tool step executes. | Tool name (e.g. `run_command`). | Grouped (`matcher` + `hooks`). |
| `PostToolUse` | After a tool step completes. | Tool name (e.g. `run_command`). | Grouped (`matcher` + `hooks`). |
| `PreInvocation` | Before the model is invoked. | N/A (ignored). | Flat array of hook handlers. |
| `PostInvocation` | After tool calls finish. | N/A (ignored). | Flat array of hook handlers. |
| `Stop` | When the execution loop terminates. | N/A (ignored). | Flat array of hook handlers. |

---

## 2. Configuration Top-Level Schema

Hooks are keyed by arbitrary namespace identifiers. Each namespace contains event arrays:

```json
{
  "security-guard": {
    "enabled": true,
    "PreToolUse": [
      {
        "matcher": "run_command",
        "hooks": [
          {
            "type": "command",
            "command": "bash /home/seren/.gemini/config/hooks/check-cmd.sh",
            "timeout": 10
          }
        ]
      }
    ]
  },
  "context-injector": {
    "PreInvocation": [
      {
        "type": "command",
        "command": "bash /home/seren/.gemini/config/hooks/inject-context.sh",
        "timeout": 5
      }
    ]
  }
}
```

### Handler Fields
- `type` (string, optional): `"command"` (shell execution via `sh -c` on Linux, `cmd /c` on Windows). Defaults to `"command"`.
- `command` (string, required): Shell command. Working directory is set to the directory containing `hooks.json`. `~` expands to `$HOME`.
- `timeout` (integer, optional): Maximum execution seconds. Defaults to `30`.

### Matcher Rules (for `PreToolUse` and `PostToolUse`)
- `"matcher": "*"` or `""`: Matches all tool invocations.
- `"matcher": "run_command"`: Matches exact tool name.
- `"matcher": "run_command|replace_file_content"`: Regex pipe matching.
- `"matcher": "browser_.*"`: Regex prefix matching.

---

## 3. Common Input Payload (stdin)

All hook handlers receive a JSON payload on `stdin` with camelCase keys:

```json
{
  "conversationId": "3523d17a-a54a-41a3-8a39-306ea578826b",
  "workspacePaths": ["/home/seren/code/antigy"],
  "transcriptPath": "/home/seren/.gemini/antigravity-cli/brain/3523d17a.../.system_generated/logs/transcript.jsonl",
  "artifactDirectoryPath": "/home/seren/.gemini/antigravity-cli/brain/3523d17a.../scratch",
  "modelName": "auto"
}
```

---

## 4. Event Contracts

### A. `PreToolUse` Contract
Intercepts, audits, rewrites, or denies a tool call before execution.

#### Additional Input Fields
```json
{
  "toolCall": {
    "name": "run_command",
    "args": {
      "CommandLine": "rm -rf /tmp/test"
    }
  },
  "stepIdx": 14
}
```

#### Output JSON (stdout)
```json
{
  "decision": "deny",
  "reason": "Destructive command rejected by policy.",
  "overwrite": {
    "CommandLine": "rm -ri /tmp/test"
  },
  "permissionOverrides": ["command(rm -ri /tmp/test)"]
}
```

- `decision` (string, required):
  - `"allow"`: Permit execution immediately.
  - `"deny"`: Block tool execution; feeds `reason` back to model.
  - `"ask"`: Prompt operator for interactive permission.
  - `"force_ask"`: Always prompt operator, ignoring cached approvals.
- `reason` (string, optional): Rejection or confirmation text presented to model or operator.
- `overwrite` (object, optional): Top-level shallow argument override merged into `toolCall.args`.
- `permissionOverrides` (array of strings, optional): Dynamic permission grants.

---

### B. `PostToolUse` Contract
Runs post-execution analysis or cleanup.

#### Additional Input Fields
```json
{
  "stepIdx": 14,
  "error": "exit status 1"
}
```
*Note: `error` is present only when the tool failed.*

#### Output JSON (stdout)
Expects an empty JSON object: `{}`.

---

### C. `PreInvocation` Contract
Injects instructions or transient messages before the model runs.

#### Additional Input Fields
```json
{
  "invocationNum": 2,
  "initialNumSteps": 8
}
```

#### Output JSON (stdout)
```json
{
  "injectSteps": [
    {
      "ephemeralMessage": "Ensure all unit tests pass before finishing turn."
    }
  ]
}
```

Supported `injectSteps` items:
- `{"ephemeralMessage": "text"}`: Transient system instruction.
- `{"userMessage": "text"}`: Injected user prompt.
- `{"toolCall": {"name": "...", "args": {...}}}`: Programmatic tool invocation.

---

### D. `PostInvocation` Contract
Inspects model output and controls execution loop continuation.

#### Additional Input Fields
Same as `PreInvocation`.

#### Output JSON (stdout)
```json
{
  "injectSteps": [],
  "terminationBehavior": "force_continue"
}
```
- `terminationBehavior`: `"force_continue"` (forces another turn cycle), `"terminate"` (stops loop), or `""` (default).

---

### E. `Stop` Contract
Prevents the agent from terminating when unfinished background tasks or unmet goals exist.

#### Additional Input Fields
```json
{
  "executionNum": 1,
  "terminationReason": "model_stop",
  "error": "",
  "fullyIdle": true
}
```

#### Output JSON (stdout)
```json
{
  "decision": "continue",
  "reason": "Background test suite is still running. Do not exit."
}
```
- `decision`: Set to `"continue"` to force the agent back into execution.
- `reason`: Explanation presented to model as system prompt.

---

## 5. D-Bus Safeguard Hook Recipe

Block automated processes from probing credentials over D-Bus:

```bash
#!/usr/bin/env bash
PAYLOAD=$(cat)
CMD=$(echo "$PAYLOAD" | jq -r '.toolCall.args.CommandLine // empty')

if [[ "$CMD" =~ (secret-tool|keyring|gemini.*username|acs\ switch) ]]; then
  cat <<'EOF'
{
  "decision": "deny",
  "reason": "CRITICAL SECURITY RULE: D-Bus credential access and acs switching are strictly forbidden in automated sessions."
}
EOF
  exit 0
fi

echo '{"decision": "allow"}'
```
