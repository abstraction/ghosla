# SQLite Databases & Schema Reference

The Antigravity runtime uses SQLite 3 for both global session indexing and per-conversation step trajectory storage:
1. **Catalog Index**: `~/.gemini/antigravity-cli/conversation_summaries.db`
2. **Trajectory Store**: `~/.gemini/antigravity-cli/conversations/<UUID>.db`

---

## 1. Catalog Index: `conversation_summaries.db`

Tracks session metadata, step counts, hierarchy trees, and idle states across all historical conversations.

### Table DDL
```sql
CREATE TABLE `conversation_summaries` (
    `conversation_id` TEXT PRIMARY KEY,
    `title` TEXT NOT NULL DEFAULT "",
    `preview` TEXT NOT NULL DEFAULT "",
    `step_count` INTEGER NOT NULL DEFAULT 0,
    `last_modified_time` DATETIME NOT NULL,
    `workspace_uris` TEXT NOT NULL,
    `status` TEXT NOT NULL DEFAULT "",
    `source` TEXT NOT NULL DEFAULT "",
    `project_id` TEXT NOT NULL DEFAULT "",
    `agent_name` TEXT NOT NULL DEFAULT "",
    `parent_conversation_id` TEXT NOT NULL DEFAULT "",  -- Empty for root; set for subagents
    `nesting_depth` INTEGER NOT NULL DEFAULT 0,          -- 0=root, 1=DeepCoder, 2=Worker
    `battle_id` TEXT NOT NULL DEFAULT "",
    `winning_conversation_id` TEXT NOT NULL DEFAULT "",
    `not_fully_idle` NUMERIC NOT NULL DEFAULT false,     -- 1 if active work remains
    `killed` NUMERIC NOT NULL DEFAULT false,             -- 1 if terminated forcefully
    `last_user_input_time` DATETIME NOT NULL,
    `last_user_input_step_index` INTEGER NOT NULL DEFAULT -1,
    `app_data_dir` TEXT NOT NULL DEFAULT "",
    `raw_summary` BLOB,
    `group_id` TEXT NOT NULL DEFAULT ''
);

CREATE INDEX `idx_conversation_summaries_last_user_input_time` 
    ON `conversation_summaries`(`last_user_input_time`);

CREATE INDEX `idx_conversation_summaries_last_modified_time` 
    ON `conversation_summaries`(`last_modified_time`);
```

### Column Semantics

| Column | Type | Values & Semantics |
| :--- | :--- | :--- |
| `conversation_id` | `TEXT` | Session UUID matching `brain/<uuid>/` and `conversations/<uuid>.db`. |
| `title` | `TEXT` | Session title shown in `/resume` picker. |
| `preview` | `TEXT` | Snippet of initial prompt. |
| `step_count` | `INTEGER` | Total tool steps executed in conversation. |
| `status` | `TEXT` | Execution state: `CASCADE_RUN_STATUS_IDLE` or `CASCADE_RUN_STATUS_RUNNING`. |
| `nesting_depth` | `INTEGER` | `0` = Root session; `1` = Subagent orchestrator; `2` = Worker subagent. |
| `parent_conversation_id`| `TEXT` | UUID of calling parent session. |
| `workspace_uris` | `TEXT` | JSON array of `file://` URIs (e.g. `["file:///home/seren/code/antigy"]`). |
| `not_fully_idle` | `NUMERIC` | `1` indicates background process or turn still running; `0` when idle. |
| `killed` | `NUMERIC` | `1` indicates session was terminated via signal or abort command. |
| `last_modified_time` | `DATETIME` | ISO-8601 UTC timestamp of last state write. |

### Operational SQL Queries

```bash
# 1. List actively running sessions
sqlite3 ~/.gemini/antigravity-cli/conversation_summaries.db \
  "SELECT conversation_id, title, agent_name, step_count, datetime(last_modified_time) 
   FROM conversation_summaries 
   WHERE status = 'CASCADE_RUN_STATUS_RUNNING' OR not_fully_idle = 1 
   ORDER BY last_modified_time DESC;"

# 2. Trace complete subagent hierarchy for a parent UUID
sqlite3 ~/.gemini/antigravity-cli/conversation_summaries.db \
  "SELECT conversation_id, agent_name, nesting_depth, step_count, status, killed 
   FROM conversation_summaries 
   WHERE parent_conversation_id = '<PARENT_UUID>' 
   ORDER BY last_modified_time ASC;"

# 3. Locate sessions by workspace path
sqlite3 ~/.gemini/antigravity-cli/conversation_summaries.db \
  "SELECT conversation_id, title, step_count, datetime(last_modified_time) 
   FROM conversation_summaries 
   WHERE workspace_uris LIKE '%antigy%' 
   ORDER BY last_modified_time DESC LIMIT 5;"

# 4. Count sessions grouped by agent persona
sqlite3 ~/.gemini/antigravity-cli/conversation_summaries.db \
  "SELECT agent_name, count(*) as count 
   FROM conversation_summaries 
   WHERE agent_name != '' 
   GROUP BY agent_name 
   ORDER BY count DESC;"
```

---

## 2. Trajectory Store: `conversations/<UUID>.db`

Each conversation has an isolated database recording step payloads, execution status, and generator metadata.

### Schema Layout
```sql
CREATE TABLE `trajectory_meta` (
    `trajectory_id` TEXT PRIMARY KEY,
    `cascade_id` TEXT,           -- Matches conversation_id UUID
    `trajectory_type` INTEGER,
    `source` INTEGER
);

CREATE TABLE `steps` (
    `idx` INTEGER PRIMARY KEY,   -- Step sequence index (0, 1, 2, ...)
    `step_type` INTEGER NOT NULL DEFAULT 0,
    `status` INTEGER NOT NULL DEFAULT 0,
    `has_subtrajectory` NUMERIC NOT NULL DEFAULT false,
    `metadata` BLOB,
    `error_details` BLOB,
    `permissions` BLOB,
    `task_details` BLOB,
    `render_info` BLOB,
    `step_payload` BLOB,
    `step_format` INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX `idx_steps_status` ON `steps`(`status`);
CREATE INDEX `idx_steps_step_type` ON `steps`(`step_type`);

CREATE TABLE `gen_metadata` (`idx` INTEGER PRIMARY KEY, `data` BLOB, `size` INTEGER NOT NULL DEFAULT 0);
CREATE TABLE `executor_metadata` (`idx` INTEGER PRIMARY KEY, `data` BLOB);
CREATE TABLE `parent_references` (`idx` INTEGER PRIMARY KEY, `data` BLOB);
CREATE TABLE `trajectory_metadata_blob` (`id` TEXT PRIMARY KEY DEFAULT "main", `data` BLOB);
CREATE TABLE `battle_mode_infos` (`idx` INTEGER PRIMARY KEY, `data` BLOB);
```

### Operational Trajectory Queries

```bash
# 1. Inspect step count and trajectory metadata for a session
sqlite3 ~/.gemini/antigravity-cli/conversations/<UUID>.db \
  "SELECT trajectory_id, cascade_id, trajectory_type FROM trajectory_meta;"

# 2. Check execution status of all steps in a session
sqlite3 ~/.gemini/antigravity-cli/conversations/<UUID>.db \
  "SELECT idx, step_type, status, has_subtrajectory FROM steps ORDER BY idx ASC;"

# 3. Find failed or anomalous steps
sqlite3 ~/.gemini/antigravity-cli/conversations/<UUID>.db \
  "SELECT idx, step_type, status FROM steps WHERE error_details IS NOT NULL OR status != 3;"
```

---

## 3. Filesystem Manifest for a Session UUID

A single `conversation_id` corresponds to these disk locations:

| Path | Purpose |
| :--- | :--- |
| `~/.gemini/antigravity-cli/conversations/<UUID>.db` | Structured step trajectory database. |
| `~/.gemini/antigravity-cli/brain/<UUID>/.system_generated/logs/transcript_full.jsonl` | Complete untruncated transcript and model thoughts. |
| `~/.gemini/antigravity-cli/brain/<UUID>/.system_generated/logs/transcript.jsonl` | Compact transcript. |
| `~/.gemini/antigravity-cli/brain/<UUID>/.system_generated/messages/` | Inter-agent messages and queued inputs. |
| `~/.gemini/antigravity-cli/presence/<UUID>.lock` | Target of advisory file lock (`flock`). |
| `~/.gemini/antigravity-cli/annotations/<UUID>.pbtxt` | Protobuf title metadata. |
| `~/.gemini/antigravity-cli/implicit/<UUID>.pb` | Serialized embeddings and repository index. |
