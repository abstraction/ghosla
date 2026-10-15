---
name: git-commit
description: 'Execute git commit with conventional commit message analysis, intelligent staging, and message generation. Use when user asks to commit changes, create a git commit, or mentions "/commit". Supports: (1) Auto-detecting type and scope from changes, (2) Generating conventional commit messages from diff, (3) Interactive commit with optional type/scope/description overrides, (4) Intelligent file staging for logical grouping'
license: MIT
allowed-tools: Bash
metadata:
  upstream_source: "github-copilot-community/git-commit"
  fork: true
---

# Git Commit with Conventional Commits

## Overview

Create standardized, semantic git commits using the Conventional Commits specification. Analyze the actual diff to determine appropriate type, scope, and message.

## Conventional Commit Format

```
<type>(optional-scope): <description>

[optional body]

[optional footer(s)]
```

## Commit Types

| Type       | Purpose                        |
| ---------- | ------------------------------ |
| `feat`     | New feature                    |
| `fix`      | Bug fix                        |
| `docs`     | Documentation only             |
| `style`    | Formatting/style (no logic)    |
| `refactor` | Code refactor (no feature/fix) |
| `perf`     | Performance improvement        |
| `test`     | Add/update tests               |
| `build`    | Build system/dependencies      |
| `ci`       | CI/config changes              |
| `chore`    | Maintenance/misc               |
| `revert`   | Revert commit                  |

## Breaking Changes

```
# Exclamation mark after type/scope
feat!: remove deprecated endpoint

# BREAKING CHANGE footer
feat: allow config to extend other configs

BREAKING CHANGE: `extends` key behavior changed
```

## Workflow

### 1. Analyze Diff

```bash
# If files are staged, use staged diff
git diff --staged

# If nothing staged, use working tree diff
git diff

# Also check status
git status --porcelain
```

### 2. Stage Files (if needed)

If nothing is staged or you want to group changes differently:

```bash
# Stage specific files
git add path/to/file1 path/to/file2

# Stage by pattern
git add *.test.*
git add src/components/*

# Interactive staging
git add -p
```

**Never commit secrets** (.env, credentials.json, private keys).

### 3. Generate Commit Message

Analyze the diff to determine:

- **Type**: What kind of change is this?
- **Scope**: What area/module is affected?
- **Description**: One-line summary of what changed (present tense, imperative mood, <72 chars)

**Commit Message Content Rules:**
1. **Apply the `unslop` skill** to the commit message to cut AI tells and ensure plain, human-like phrasing.
2. **Never leak agent context**: Do not include your agent name, skill names (e.g., "used unslop skill"), tool names, chat history, or any sensitive information in the commit message.
3. **STRICT ANTI-SLOP PROTOCOL**: Your commit messages must be DRY, BORING, and STRICTLY FACTUAL. Do NOT use marketing adjectives like "flawless", "pixel-perfect", "seamless", "robust", "comprehensive", "elegant", "efficient", or "optimized". A human writes `feat: add svg logo`, an AI writes `feat: add pixel-perfect svg logo for flawless rendering`. Be a human.

### 4. Execute Commit

```bash
# Single line
git commit -m "<type>(scope): <description>"

# Multi-line with body/footer
git commit -m "$(cat <<'EOF'
<type>(scope): <description>

<optional body>

<optional footer>
EOF
)"
```

## Best Practices

- One logical change per commit
- Present tense: "add" not "added"
- Imperative mood: "fix bug" not "fixes bug"
- Reference issues: `Closes #123`, `Refs #456`
- Keep description under 72 characters

## Git Safety Protocol

- NEVER update git config
- NEVER run destructive commands (--force, hard reset) without explicit request
- NEVER skip hooks (--no-verify) unless user asks
- NEVER force push to main/master
- If commit fails due to hooks, fix and create NEW commit (don't amend)

## Communication & Commit Hygiene

- **Never leak internal agent tooling:** When writing user-facing text, documentation, or especially git commit messages, never mention internal agent skills, directives, or tooling (e.g., do not say "applied unslop skill" or "used subagent for copywriting").
- **Professionalism:** Keep git history and codebase documentation strictly focused on the software itself, acting as a professional human engineer.
