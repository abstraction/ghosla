# Binary Reconnaissance: Strings, Offsets, & Symbol Recovery

This reference details static analysis and string reconnaissance techniques for inspecting stripped Antigravity binaries without decompilation.

---

## 1. Binary Location & Environment

- **Mise Managed Executable**: `~/.local/share/mise/installs/antigravity-cli/latest/antigravity` (points to active version `1.2.16`).
- **Path Resolution**: `which antigravity` or `which agy`.
- **Binary Profile**: Stripped ELF 64-bit x86-64 executable (~209 MB) compiled from Google internal monorepo (`google3/...`).
- **Go Symbol Table (`pclntab`)**: Embedded in `.lrodata` at offset `0x13c2dc0` with magic header `0xfffffff1`. Preserves over 173,000 function symbols, package hierarchies, and source filenames.

---

## 2. Using `antigy/tools/search_binary.py`

The script [`tools/search_binary.py`](file:///home/seren/code/antigy/tools/search_binary.py) scans binary strings with regex support, decimal byte offsets, and surrounding context lines.

### Global Invocation Syntax (Runnable from Any CWD)
```bash
# General search with 3 context lines
uv run --directory /home/seren/code/antigy python tools/search_binary.py "<pattern>" -C 3

# Filter matches strictly to Go source (*.go) and Protobuf (*.proto) paths
uv run --directory /home/seren/code/antigy python tools/search_binary.py "<pattern>" --source-only

# Case-sensitive search
uv run --directory /home/seren/code/antigy python tools/search_binary.py "<pattern>" -s
```

### High-Value Probing Queries
```bash
# 1. Quota management structs and fields
uv run --directory /home/seren/code/antigy python tools/search_binary.py "StatusLineQuotaBucket" -C 3

# 2. Hidden agentapi subcommands
uv run --directory /home/seren/code/antigy python tools/search_binary.py "new-conversation" -C 3

# 3. Interactive question model references
uv run --directory /home/seren/code/antigy python tools/search_binary.py "AskQuestionModel" --source-only

# 4. Lifecycle hooks schema embedded in binary
uv run --directory /home/seren/code/antigy python tools/search_binary.py "PreToolUse" -C 3
```

---

## 3. Zero-Dependency Shell Fallbacks

When operating on machines without the `antigy` repository, use direct shell pipes:

### A. Decimal Offset Grep
```bash
strings -a -td $(which antigravity) | grep -C 5 "StatusLineQuotaBucket"
```

### B. Discover Go Package Trees
```bash
strings $(which antigravity) | grep -E "google3/devtools/jetski/.*\.go" | head -n 30
```

### C. Discover Statusline Format Strings
```bash
strings $(which antigravity) | grep -E "(%s in \| %s out|reset_in_seconds|remaining_fraction)"
```

### D. Discover Rate Limit & Quota Identifiers
```bash
strings $(which antigravity) | grep -E "(gemini-5h|gemini-weekly|3p-5h|claude.*quota)"
```

---

## 4. Recovered Architectural Signatures

### Quota Engine (`google3/devtools/jetski/quota_manager.go`)
- `gemini-5h`: Sliding 5-hour rolling inference window for first-party models.
- `gemini-weekly`: Aggregate weekly token ceiling.
- `3p-5h`: Sliding 5-hour quota for third-party models (Claude).

### Statusline Metrics Struct (`types.StatusLineQuotaBucket`)
Recovered struct fields identified via adjacent reflection tags:
- `InputTokens` (`json:"input_tokens"`)
- `SubagentUSD` (`json:"subagent_usd"`)
- `Dirty` (`json:"dirty,omitempty"`)
- `ArtifactCount` (`json:"artifact_count,omitempty"`)
- `remaining_fraction`, `reset_in_seconds`

### Hidden Subcommand: `agentapi`
- `antigravity agentapi new-conversation [--model=...] [--title=...] <prompt>`
- `antigravity agentapi send-message [--title=...] <recipient_id> <content>`
- `antigravity agentapi get-conversation-metadata <conversation_id>`

---

## 5. Antigy Extraction Suite (`antigy/tools/`)

Run these scripts from `/home/seren/code/antigy` (or globally via `uv run --directory /home/seren/code/antigy ...`):

| Script | Purpose |
| :--- | :--- |
| `uv run python tools/extract_all.py` | Orchestrates symbol, string, and changelog extraction. |
| `uv run python tools/extract_symbols.py` | Recovers 173,000+ Go function symbols from `pclntab`. |
| `uv run python tools/extract_strings.py` | Extracts Protobuf descriptors and CLI parameters. |
| `uv run python tools/extract_changelog.py` | Emits structured JSON and Markdown changelogs. |
| `uv run python tools/summarize_changelog.py` | Generates categorized power-user digests from changelogs. |
| `uv run python tools/diff_release.py` | Compares symbols and descriptors between version releases. |
| `uv run python tools/search_binary.py` | Scans binary strings with decimal offsets and regex filtering. |
| `uv run python tools/autonomous_re_loop.py` | Autonomous RE loop: Ghidra MCP decompiler, BinDiff engine, Thompson Sampling bandit, and append-only TSV decision trail (`scratch/recon_decisions.tsv`). |
| `uv run python tools/heuristic_stats.py` | Heuristics tracker and Structural Safety Firewall verification (`check-firewall`). |
