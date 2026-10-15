# ~/.gemini/ Topology, State Files, & Recovery

This reference maps the internal filesystem topology of `~/.gemini/`, detailing runtime persistence, session locking, dual-transcript architecture, inter-agent IPC, and customization resolution.

---

## 1. Directory Tree & Roles

```
~/.gemini/
├── antigravity-cli/             # Runtime engine room
│   ├── brain/<uuid>/            # Active working directory per conversation UUID
│   │   ├── .system_generated/
│   │   │   ├── logs/
│   │   │   │   ├── transcript.jsonl      # Compact transcript (large outputs truncated)
│   │   │   │   ├── transcript_full.jsonl # Complete authoritative transcript & thinking
│   │   │   │   └── chunks/               # Chunked log stream segments
│   │   │   ├── messages/                 # Inter-agent IPC & queued inputs
│   │   │   │   ├── <msg-uuid>.json       # Raw message payload
│   │   │   │   ├── read.json             # Delivery state marker
│   │   │   │   └── undelivered/          # Unacknowledged incoming messages
│   │   │   └── steps/<N>/content.md      # Large tool output payload buffers
│   │   ├── scratch/             # Temporary scratchpad directory
│   │   └── .user_uploaded/      # User-provided file attachments
│   ├── conversations/<uuid>.db  # Per-conversation SQLite trajectory & step store
│   ├── annotations/<uuid>.pbtxt # Protobuf text title metadata (read by /resume)
│   ├── presence/<uuid>.lock     # Target of Linux advisory flock
│   ├── implicit/<uuid>.pb       # Serialized binary embeddings and index cache
│   ├── conversation_summaries.db# SQLite 3 central session catalog
│   ├── worktrees/<uuid>/        # Ephemeral git worktree clones for branched subagents
│   ├── builtin/skills/          # Shipped baseline skills extracted from binary
│   ├── history.jsonl            # Chronological log of prompts and turns
│   ├── settings.json            # User preferences (queued messages, modes)
│   └── cli.log & log/           # Real-time diagnostic logs and stderr
├── config/                      # User customizations & extensions
│   ├── rules/                   # Global markdown rule files
│   ├── skills/                  # Global custom skills (<skill>/SKILL.md)
│   ├── hooks.json & hooks/      # Lifecycle event hooks (PreToolUse, Stop, etc.)
│   └── mcp_config.json          # Model Context Protocol external servers
└── trustedFolders.json          # Approved directory paths and tool permissions
```

---

## 2. The Dual-Transcript & Message Architecture

Under `brain/<uuid>/.system_generated/`:

1. **`transcript.jsonl` (Compact)**:
   - Structured for fast sequential reading by the runtime harness.
   - When tools emit large outputs, text is truncated, and the record marks:
     `"truncated_fields": ["content"]`.
2. **`transcript_full.jsonl` (Authoritative)**:
   - Contains 100% of untruncated content, tool inputs, stdout/stderr, and model thinking blocks.
   - Use this file to recover exact generated code or model reasoning from earlier turns.
3. **`steps/<N>/content.md`**:
   - Oversized tool payloads (e.g. from `read_url_content` or broad file searches) are stored here to keep prompt token windows clean.
4. **`messages/` (Agent IPC & Queuing)**:
   - When agents communicate via `send_message` or operators queue input during active turns, payloads are staged as `<uuid>.json` files under `messages/` and marked in `read.json` upon ingestion.

---

## 3. Session Locking & Presence Mechanics

- **Mechanism**: The harness acquires an advisory file lock (`flock`) on `presence/<conversation_id>.lock` (open file descriptor `17u`).
- **File Persistence**: The zero-byte `.lock` file remains on disk even after clean process exit. Thousands of harmless `.lock` files accumulate in `presence/`. Mere existence of a `.lock` file does **not** indicate a lock collision.
- **True Lock Collision**:
  Occurs only when a live background process still holds the open file descriptor on that lock file.
- **Diagnostic & Remediation Runbook**:
  ```bash
  # 1. Identify which PID holds the open file lock
  fuser ~/.gemini/antigravity-cli/presence/<UUID>.lock

  # 2. Terminate the hung or duplicate process holding the lock
  kill -9 <PID>

  # 3. Clean up the lock file if needed
  rm -f ~/.gemini/antigravity-cli/presence/<UUID>.lock
  ```

---

## 4. Ephemeral Worktrees (`worktrees/`)

When a subagent is spawned with `Workspace='branch'`:
1. `agy` creates an isolated Git worktree:
   `git worktree add ~/.gemini/antigravity-cli/worktrees/<uuid>/subagent-<role>-<id>`.
2. Subagents commit and execute tests without mutating the operator's active branch.
3. On termination, the harness prunes the tree. Clean orphan worktrees after abnormal crashes with:
   ```bash
   git worktree prune
   ```

---

## 5. Five-Tier Customization Precedence

When multiple rules, skills, or settings define overlapping behavior, `agy` resolves them in this strict order (highest priority first):

```
1. Workspace Project (Traversing from CWD upward to .git root: .agents/)
        │
        ▼
2. Workspace Declared Configurations (skills.json / plugins.json in workspace)
        │
        ▼
3. Global Discovery (~/.gemini/config/skills/, rules/, plugins/)
        │
        ▼
4. Built-in Customizations (~/.gemini/antigravity-cli/builtin/skills/)
        │
        ▼
5. Global Declared Configurations (~/.gemini/config/config.json)
```

> **Built-in Override**: Placing a skill in `~/.gemini/config/skills/<name>/SKILL.md` with the same name as a built-in skill overrides the default version shipped with Antigravity.
