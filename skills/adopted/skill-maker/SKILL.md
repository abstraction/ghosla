---
name: skill-maker
description: "Interview the operator to generate high-precision agent skills or AGENTS.md files adhering to empirical harness engineering standards. Triggers on: skill-maker, create skill, new skill, author skill, update skill, agents.md, AGENTS.md, harness engineering, agent instructions."
---

# skill-maker

You are an expert harness engineer. When the operator asks to create or update an agent skill or an `AGENTS.md` file, execute this workflow. You synthesize empirical research (AAIF, ETH Zurich, GitHub 2,500-repo study) with Antigravity runtime mechanics according to [SKILL_AUTHORING_PLAYBOOK.md](file:///home/seren/code/antigy/hitl/SKILL_AUTHORING_PLAYBOOK.md).

---

## Workflow overview

```
Step 1: Silent Discovery ──► Step 2: Grilling Interview ──► Step 3: Drafting ──► Step 4: Verification
(Inspect repo silently)      (One frontier round at a time)   (Structured files)    (Pre-commit checklist)
```

---

## Step 1: Silent discovery and repository inspection

Before asking questions, silently inspect the repository to detect context:

1. Check package manifests (`package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`).
2. Detect test frameworks (`pytest`, `vitest`, `go test`, `cargo test`, `jest`).
3. Detect linters and formatters (`ruff`, `eslint`, `biome`, `golangci-lint`, `prettier`).
4. Inspect existing skills in `.agents/skills/` and `~/.gemini/config/skills/`.
5. Check if an `AGENTS.md` or `GEMINI.md` exists at the workspace root.

Do not ask the user for information you can detect from files on disk.

---

## Step 2: Grilling decision-tree interview

Never dump all interview questions at once. Walk the decision tree using the `ask_question` tool or focused sequential turns following `/grill-me` discipline ([03_matt_pocock_grilling_skill.md](file:///home/seren/code/antigy/references/curated_corpus/empirical_agents_md/03_matt_pocock_grilling_skill.md)). Present the frontier of settled decisions, number each question, and provide your recommended answer.

### Interview branch A: Authoring a skill

If creating or updating a skill in `.agents/skills/<name>/SKILL.md`:

#### Round 1: Intent, name, and triggers
Call `ask_question`:
```json
{
  "questions": [
    {
      "question": "What is the primary objective of this skill?",
      "options": [
        "(Recommended) [Propose name in gerund form]: [One-sentence capability statement]",
        "Alternative option 1",
        "Alternative option 2"
      ],
      "is_multi_select": false
    }
  ]
}
```
- **Skill name**: Name in gerund form (e.g. `auditing-dependencies`, `syncing-schemas`). Maximum 64 characters, lowercase and hyphens only.
- **Triggers**: Define 4 to 8 concrete trigger phrases for the YAML `description`.
- **Target location**: Confirm workspace `.agents/skills/<name>/` or global `~/.gemini/config/skills/<name>/`.

#### Round 2: Degree of freedom and scope
- **Degree of freedom**: Choose based on task fragility:
  - *High*: Text heuristics for open-ended reviews or planning.
  - *Medium*: Parameterized templates for structured documents or diffs.
  - *Low*: Fixed, deterministic scripts for fragile migrations, builds, or deployments.
- **Scope boundaries**: Define what the skill must touch and what it is forbidden from touching.

#### Round 3: Execution workflow and checkpoints
- What are the exact ordered steps the agent must follow?
- What are the checkpoints where the agent produces concrete evidence?
- Does the skill require deterministic helper scripts in `scripts/` or reference files in `reference.md`?

#### Round 4: Anti-rationalization discovery
- What shortcuts, excuses, or assumptions will an agent make when executing this task?
- Draft 3 to 5 pairs of common rationalizations and their explicit rebuttals ([02_addy_osmani_anti_rationalization.md](file:///home/seren/code/antigy/references/curated_corpus/empirical_agents_md/02_addy_osmani_anti_rationalization.md)).

#### Round 5: Verification and exit criteria
- What exact command validates completion?
- What is the definition of done?
- Should passing test output be swallowed via `hooks.json` `OverwriteResult` backpressure ([`tools/test_runner_backpressure.sh`](file:///home/seren/code/antigy/tools/test_runner_backpressure.sh))?

---

### Interview branch B: Authoring `AGENTS.md`

If creating or updating a root `AGENTS.md` file ([01_github_2500_repo_study.md](file:///home/seren/code/antigy/references/curated_corpus/empirical_agents_md/01_github_2500_repo_study.md) and [07_phil_schmid_writing_good_agents.md](file:///home/seren/code/antigy/references/curated_corpus/empirical_agents_md/07_phil_schmid_writing_good_agents.md)):

#### Round 1: Primary persona and core responsibilities
- What is the primary role of the agent in this repository?
- What are the primary operations it executes daily?

#### Round 2: Tech stack and actionable commands
- What are the specific technologies and versions?
- What are the exact commands for:
  - Setup and install
  - Running tests (with fail-fast flags)
  - Linting and type-checking
  - Building the project

#### Round 3: Three-tier boundaries
- **Always do**: Mandatory actions on every turn (run linters, verify tests).
- **Ask first**: Actions requiring explicit operator approval (schema migrations, external network calls, dependency additions).
- **Never do**: Prohibited actions (modifying credentials, deleting tests, modifying code outside target scope).

#### Round 4: Pristine few-shot examples
- Collect 1 or 2 concrete examples of correct versus incorrect output or code formatting.

---

## Step 3: Drafting the artifact

Once interview rounds are complete, draft the artifact adhering to empirical standards.

### Boilerplate template for a skill (`.agents/skills/<name>/SKILL.md`)

```markdown
---
name: [gerund-name-lowercase-hyphens]
description: "[One-sentence capability statement]. Use when the user asks to [action], [action], or mentions [triggers]."
---

# [gerund-name]

[Brief explanation of the skill's purpose and operational boundaries.]

For full schema details, see [reference.md](reference.md).

---

## Workflow

1. **Step 1: Discover & Inspect**
   - Inspect target files before modifying them.
   - Run baseline check: `[exact check command]`

2. **Step 2: Execute Modification**
   - Apply minimal scoped edits.
   - Do not refactor untouched files.

3. **Step 3: Deterministic Verification**
   - Run verification command: `[exact test/lint command]`
   - Verify exit code is 0.

---

## Anti-rationalization table

| Agent rationalization | Enforcement rebuttal |
| :--- | :--- |
| "The modification is trivial, so tests are unnecessary." | Every modification requires test verification. Zero exceptions. |
| "I will run the tests after finishing everything." | Test immediately after each step. |
| "I should improve adjacent code while I am here." | Scope discipline. Modify only what was requested. |

---

## Definition of done

- [ ] All modified files pass `[linter command]`
- [ ] Automated tests pass with exit code 0 via `[test command]`
- [ ] No files outside the target scope were modified
```

### Boilerplate template for root `AGENTS.md`

```markdown
<meta_context>
# Agent Persona
You are an expert AI software engineer. Your core purpose is to maintain and extend this repository with high precision, adhering strictly to the boundaries below.

# Core Rules
- **Absolute Scope Discipline**: Touch only what is requested. Never perform unsolicited refactoring.
- **Escape Hatch**: If context is missing or ambiguous, pause and ask the operator for clarification using `ask_question`.
</meta_context>

<static_context>
# Actionable Commands
- **Install**: `[package manager install command]`
- **Test**: `[test runner command with fail-fast flag]`
- **Lint**: `[linter command]`
- **Build**: `[build command]`

# Three-Tier Boundaries
1. **Always do**: Run linters before completing turns. Write tests for every code change.
2. **Ask first**: Database migrations. External network calls. Dependency version upgrades.
3. **Never do**: Commit secrets or credentials. Delete failing tests. Edit files outside target scope.

# Definition of Done
- All tests pass locally with exit code 0.
- All modified files pass linter and type checks.
- Changes remain within the requested boundary.
</static_context>

<instructions>
# Task Directives
- **Plan Before Acting**: Use a `<thought_process>` block to outline strategy before editing files.
- **Evidence-Grounded Output**: Terminate every turn with concrete verification evidence.
</instructions>

<examples>
# Examples
<example>
<task_input>
[Real-world example task]
</task_input>
<thought_process>
[Structured reasoning steps]
</thought_process>
<execution_plan>
[Exact commands to execute]
</execution_plan>
<correct_output>
[Pristine expected output]
</correct_output>
</example>
</examples>
```

---

## Step 4: Verification and pre-commit check

Before presenting the final file to the operator, run this verification audit:

```bash
# Verify line counts (SKILL.md < 500 lines, AGENTS.md < 300 lines)
wc -l .agents/skills/<name>/SKILL.md

# Verify absence of marketing slop
python3 -c "
import re
banned = ['seamless', 'robust', 'flawless', 'comprehensive', 'cutting-edge', 'blazing-fast', 'effortless', 'elegant', 'groundbreaking', 'paradigm', 'leverage', 'utilize']
with open('.agents/skills/<name>/SKILL.md') as f:
    text = f.read()
found = [w for w in banned if re.search(r'\b' + w + r'\b', text, re.I)]
print('Banned words found:', found if found else 'None (Clean)')
"
```

Pre-commit checklist:
- [ ] Name follows gerund form, under 64 chars, lowercase and hyphens only
- [ ] Description is under 1,024 chars and states both capability and trigger conditions
- [ ] File length: `SKILL.md` < 500 lines; `AGENTS.md` < 300 lines
- [ ] Actionable commands appear first with exact flags
- [ ] Workflow uses numbered steps with explicit exit criteria
- [ ] Anti-rationalization table contains at least 3 concrete rebuttals
- [ ] Scope discipline stated: forbids unsolicited refactoring
- [ ] All file links use Unix forward slashes (`/`)
- [ ] Zero marketing slop, active voice, factual mechanisms

If helper scripts were created in `scripts/`, execute a linter check (`ruff check` or `shellcheck`) before concluding.

---

## Anti-rationalization table

| Agent rationalization | Skill-maker rebuttal |
| :--- | :--- |
| "I can skip the interview because the user's initial prompt was clear." | Ambiguous requirements produce unmaintainable skills. Walk the frontier of the design tree first. |
| "I should dump all 6 interview questions at once to be efficient." | Cognitive overload causes rushed answers. Ask one round at a time with recommendations. |
| "I will include a full directory tree in AGENTS.md." | The ETH Zurich study proved directory trees waste context tokens without helping file discovery. |
| "I can omit the anti-rationalization table for simple skills." | Anti-rationalization tables are mandatory. Models will find excuses to skip steps without them. |
| "I can write descriptive reference prose instead of a workflow." | Process over prose. A skill without numbered steps and verification checkpoints is ignored in practice. |
