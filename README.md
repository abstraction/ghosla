<div align="center">
  <p>
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="./logo-dark.svg">
      <source media="(prefers-color-scheme: light)" srcset="./logo-light.svg">
      <img alt="ghosla" src="./logo-light.svg" height="80">
    </picture>
  </p>
  <strong>A personal atelier to curate, test, and atomically deploy AI agent skills.</strong>
  <p>
    <code>Python &gt;= 3.12</code> &nbsp;|&nbsp;
    <code>uv</code> &nbsp;|&nbsp;
    <code>vendir</code> &nbsp;|&nbsp;
    <code>mypy --strict</code> &nbsp;|&nbsp;
    <code>49/49 tests passing</code>
  </p>
</div>

---

## Quickstart

Run status checks and verify active harness projections in under 10 seconds:

```bash
# Clone the atelier
git clone https://github.com/username/ghosla.git && cd ghosla

# Inspect active projections and harness health
uv run ghosla status
```

Output:
```text
╭─────────────────────────── Ghosla Atelier Status ────────────────────────────╮
│ Active Profile: baseline (2 skills)                                          │
│ Repositories: 9 upstream tracked (compound-eng, pstack, humanlayer...)       │
╰──────────────────────────────────────────────────────────────────────────────╯
Harness Projections:
  ✓ ~/.gemini/config/skills: 2/2 linked (0 broken) [ENABLED]
  ○ ~/.agents/skills: 0/0 linked (0 broken) [DISABLED]
```

To sync all modular upstream sources and review incoming changes:

```bash
uv run ghosla vendor sync
uv run ghosla diff
```

---

## Architecture & Mechanisms

Ghosla delivers operational stability through five core software mechanisms:

```
┌─────────────────┐      os.replace       ┌────────────────────────┐
│ skills/ (Forks) │ ────────────────────> │ ~/.gemini/config/      │
│ upstream/       │   (Atomic Swap <5ms)  │ (Active Agent Harness) │
└─────────────────┘                       └────────────────────────┘
         ▲                                             │
         │ Epistemic Diff Ledger                       │ Catch-All Bridge
         │ (State Checkpoint)                          │ (Auto-Symlink)
┌─────────────────┐                       ┌────────────────────────┐
│ vendir.lock.yml │                       │ ~/.agents/skills/      │
│ sources.d/*.yml │                       │ (Third-Party Intake)   │
└─────────────────┘                       └────────────────────────┘
```

1. **Atomic Symlink Engine (`os.replace`)**:
   Writing symlinks in-place causes broken references during agent runs. Ghosla stages changes in a hidden temporary link in the destination folder, then executes an atomic POSIX rename (`os.replace`). Link swaps take <5ms with zero downtime.

2. **Exclude-First Modular Vendoring (`sources.d/` + `vendir`)**:
   Monolithic vendor configs break when upstreams update. Ghosla defines each upstream in an isolated YAML manifest under `sources.d/`. The compiler merges shared defaults (`sources.d/_defaults.yml`) to strip repository bloat (`.git`, `.github`, `.codex`, compiler caches), capturing new upstream skills automatically on sync.

3. **Epistemic Diff Ledger (`ghosla diff`)**:
   Upstream updates should not overwrite local modifications. Ghosla checkpoints commit hashes in `ledger/state.json`. When upstreams change, it generates markdown diff reports in `ledger/diffs/` and preserves local forks in `skills/` untouched.

4. **Context Budget Auditor (`ghosla audit`)**:
   OpenAI Codex silently truncates skills larger than 8,000 bytes, dropping rules placed at the bottom. `ghosla audit` deterministically inspects byte counts, verifies load-bearing section order in the first 150 lines, and validates YAML frontmatter against strict Pydantic schemas.

5. **Catch-All Intake Bridge (`ghosla intake`)**:
   External installers (`skills.sh`, SpecStory) drop skills into `~/.agents/skills/`. Because Antigravity discovers global skills from `~/.gemini/config/skills/`, external skills become fragmented. Ghosla scans the catch-all folder and bridges skills into Antigravity with a single command.

---

## Capabilities

- **Zero Broken Links During Agent Runs**: Atomic directory swaps prevent partial file reads when agents execute tools during updates.
- **Protection from Codex Truncation**: Validates every skill against the hard 8,000-byte cap and alerts on high line counts before context pollution occurs.
- **Safe Fork Customization**: Keeps local modifications in `skills/<name>` registered as explicit forks. Upstream updates never wipe your personal rules.
- **Unified Tool Discovery**: Merges external skills from `~/.agents/skills/` into your active Antigravity runtime in one command.
- **Decoupled Study Pipeline**: Exports any skill note into Obsidian (`ai-workspace/skills-inbox/`) with YAML frontmatter tags for incremental reading and Anki card creation.

---

## Why Ghosla: The Atelier Philosophy

I find it pointless that using a skill has become blind copy-pasting. I don't know *how* it works, and I don't know *why* it works. Abstractions over abstractions, over abstractions.

Skills are recipes for agent harnesses. If you don't know how to cook, what use is the recipe? You can prepare the dish, but you cannot adapt it when edge cases fail. Learning the mechanics behind instructions reveals why specific constraints exist.

That being said, agents can do this as well. That is what I do. So, the idea behind this repository is to add my skills and vendored skills to explore the boundaries of agent instructions to further my understanding. Acknowledging I may lag behind agents, but at least I am still human in the loop, and that too requires constant plumbing.

### Overcoming Curation Bankruptcy

Collecting 500 unvetted skills causes cognitive paralysis. When an operator faces 500 choices, they use none of them. Ghosla organizes skills into strict, curated bundles:

- **Layer 1 (Global Baseline)**: Pinned core skills (`git-commit`, `unslop`, `tdd`, `adversarial-plan-critique`) loaded in `~/.gemini/config/skills/`.
- **Layer 2 (Project-Local)**: Context-specific skills committed directly inside project repositories.
- **Layer 3 (Ghosla Atelier)**: The master workshop for vendoring, diff analysis, token budgeting, and study.

---

## Command Reference

| Command | Engineering Mechanism | Outcome |
| :--- | :--- | :--- |
| `ghosla status` | Scans harness directories and symlink targets | Displays active links, broken paths, and shadowing |
| `ghosla vendor sync` | Compiles `sources.d/*.yml` into `vendir.yml` | Pulls upstream updates into gitignored `upstream/` |
| `ghosla diff` | Compares upstream SHAs to `ledger/state.json` | Emits markdown reports in `ledger/diffs/` |
| `ghosla audit` | Enforces byte limits, ordering, and schemas | Prevents Codex truncation and bad frontmatter |
| `ghosla link` | Executes atomic `os.replace` symlinks | Projects active bundles into enabled harnesses |
| `ghosla bundle switch <name>` | Updates `active_bundle` and cleans orphans | Activates curated skill profiles instantly |
| `ghosla intake scan` | Inspects `~/.agents/skills/` for external skills | Reports untracked skills and token estimates |
| `ghosla intake bridge` | Creates atomic symlinks into Antigravity path | Unifies external skills in active runtime |
| `ghosla adopt <path>` | Copies skill into `skills/` and normalizes YAML | Converts third-party tools into local forks |
| `ghosla study export <name>` | Formats markdown study card for Obsidian | Prepares notes for Luma incremental reading |

---

## Development

The atelier is built with typed Python (>= 3.12) managed via `uv`:

```bash
# Run unit and contract tests (49 tests)
uv run pytest

# Run linter
uv run ruff check .

# Run static type checker
uv run mypy --strict ghosla tests
```
