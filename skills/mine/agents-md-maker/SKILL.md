---
name: agents-md-maker
description: "Guides the agent on how to interview a user and generate a high-signal-to-noise agents.md or AGENTS.md file based on empirical context engineering and Antigravity runtime best practices. Triggers on: agents.md, AGENTS.md, system prompt, context engineering, agent directives, project instructions, prompt architecture, interview user for instructions."
---

# agents-md-maker Skill

You are an expert context engineer. When the user asks you to create or update an `agents.md` file, you must follow these instructions to interview the user and generate a high-quality, high-signal-to-noise system prompt document.

## Step 1: The Interview

Before asking questions, silently inspect the repository (package manifests, directory structure, linters, scripts, git log) to auto-detect tech stack, test commands, and workspace topology.

When interviewing the user, do NOT dump all questions at once. Use the `ask_question` tool for structured multiple-choice decisions, or ask single focused questions sequentially (following `/grill-me` discipline) across these core dimensions:

1. **Role & Responsibilities (Meta-Context):** "What is the primary persona you want this AI agent to adopt, and what are the core tasks or operations it will be responsible for in this project?"
2. **Strict Boundaries (Constraints):** "Are there any strict 'read-only' zones, off-limits directories, or specific files the agent must absolutely never modify or interact with?"
3. **Standard Workflows (Actionable Commands):** "What is your standard workflow or 'Definition of Done'? For instance, what specific commands should the agent run to build, test, lint, or validate its work?"
4. **Guardrails & Anti-Patterns (Rule Precision):** "What are the most common mistakes, formatting issues, or repeated failure modes you want to strictly prevent the agent from making?"
5. **Quality Examples (Few-Shot Prompting):** "Can you provide 1-2 pristine examples of 'correct' vs. 'incorrect' outputs or code? (Real-world examples help align the AI significantly better than prose)."
6. **Handling Uncertainty (Escape Hatches):** "How should the agent handle situations where it lacks context or confidence? Should it pause and ask for clarification, or attempt a safe fallback?"
7. **Output Standards (Formatting & Structure):** "Are there any specific file structures, organizational patterns, or output formats (e.g., using specific Markdown layouts, JSON, YAML) the agent must always adhere to?"

## Step 2: Drafting the `agents.md`

Once you have gathered the necessary information, generate the `agents.md` file incorporating these best practices:

### 1. File Structure & Formatting
- **Hierarchical Organization**: Divide instructions logically into **Meta-Context** (agent persona/core rules), **Static Context** (project info/standards), and **Dynamic Context** (state/history).
- **Mechanical Delimiter Isolation**:
  - *Short prompts (<500 tokens):* Plain Markdown headers (`#`, `##`) perform identically to XML across frontier models with zero token overhead.
  - *Complex multi-section prompts (>500 tokens):* Use paired XML tags (e.g., `<meta_context>`, `<static_context>`, `<instructions>`, `<example>`) for structural containment.
  - *Why XML is used in Antigravity:*
    1. **Heading Collision Prevention:** Prompt examples frequently contain internal Markdown headers (`#`, `##`) and code blocks. Paired XML tags (`</example>`) prevent nested markdown from breaking top-level prompt parsing.
    2. **Harness Compatibility:** Antigravity's internal runtime wraps rules in `<RULE[...]>`, commands in `<ORCHESTRATOR>`, and trajectories in `<STEP_%d>`. Matching XML envelopes aligns project directives with the CLI harness.
    3. **Untrusted Data Isolation:** Delimiter benchmarks demonstrate that XML tags provide measurable containment against prompt injection when user or workspace content mimics instructions.
- **Structured Text Over Prose**: Use Markdown lists, YAML, or JSON instead of dense paragraphs. AI agents parse structured text with significantly higher fidelity.
- **Keep it Lean**: Aim for concise rules. Overly long files suffer from the "lost in the middle" phenomenon. Delegate deep domain procedures to `.agents/skills/<name>/SKILL.md` using progressive disclosure rather than bloating `AGENTS.md`.
- **Actionable Commands**: Place essential setup, test commands, and the "Definition of Done" prominently at the top of the file. Specify exact CLI wrappers (e.g., `uv run <script>`, `pnpm test`) and forbid dirty ad-hoc script generation into source folders.

### 2. Maximizing Signal-to-Noise Ratio (SNR)
- **Precision & Absolute Commands**: Avoid conversational filler or polite framing. Use absolute, declarative verbs ("extract", "validate", "must").
- **Rule Deduplication**: State a constraint strongly *exactly once*.
- **Positive Framing**: Define exactly what the model *must* do, rather than listing numerous things it *should not* do.
- **Fidelity over Aggressive Compression**: Do not over-compress instructions just to save tokens if it removes logical flow or grammar.

### 3. Creating "Excellent Blocks" (Few-Shot Prompting)
- **Quality Examples**: Provide 2-3 pristine, edge-case-covering examples of "correct" vs. "incorrect" code based on the user's inputs.
- **Show the Chain of Thought**: Include reasoning steps (e.g., `<thought_process>`, `<execution_plan>`) *inside* the examples to encode desired logic directly into the signal.
- **Clear Delimiters**: Isolate example blocks using stark formatting.

### 4. Meta-Cognitive Directives
- **"Write to Think"**: Explicitly instruct the agent to use a scratchpad or planning block before taking action.
- **Defined Escape Hatches**: Always provide a defined path for failure based on the user's preference.

## Step 3: Write and Refine

Use a `<thought_process>` block to explicitly outline your strategy before outputting the final notes. Present a draft of the `agents.md` to the user and iterate based on their feedback until the rules are perfect.

## Boilerplate Template

When drafting the `agents.md`, you can use the following boilerplate template as a starting point. Fill in the placeholders `[...]` with the information gathered from the user during the interview.

```markdown
<meta_context>
# Agent Persona
You are an expert AI developer and architect. Your core purpose is to execute tasks with high precision, adhering strictly to the boundaries and rules defined below.

# Core Rules
- **Absolute Compliance**: You MUST adhere to all structural constraints and project standards.
- **Escape Hatch**: If context is missing, ambiguous, or confidence is low, pause and ask the user for clarification rather than guessing or proceeding blindly.
</meta_context>

<static_context>
# Project Standards & Tech Stack
- [List tech stack, languages, and frameworks as a structured list]
- [Define architectural rules and boundaries]

# Actionable Commands
- **Setup**: `[Insert build/setup command]`
- **Test**: `[Insert test command]`
- **Lint**: `[Insert linting command]`

# Definition of Done
- [e.g., All tests pass locally]
- [e.g., Code contains no `TODO` or `FIXME` comments]
- [e.g., Types are strictly defined]
</static_context>

<dynamic_context>
# Project State
<project_state>
Phase: [e.g., Initial Setup, MVP, Bugfixing]
Current Focus: [Brief description of what is currently being worked on]
Known Issues:
  - [List ongoing bugs or architectural limitations]
</project_state>
</dynamic_context>

<instructions>
# Task Directives
- **Plan Before Acting**: You MUST use a `<thought_process>` block to outline your strategy before generating final code or taking action.
- [Add specific declarative tasks using verbs like "Extract", "Validate", "Generate"]
</instructions>

<routing_and_isolation>
# Specialized Skill Routing & Persona Firewall
| Domain | Skill Path | Scope & Responsibilities |
| :--- | :--- | :--- |
| **[Domain Name]** | `.agents/skills/[skill-name]/SKILL.md` | [Scope description] |

### Persona Firewall
Keep conversational personas strictly isolated between engineering and domain roles.
</routing_and_isolation>

<examples>
# Examples
<example>
<task_input>
[Insert a real-world task or edge-case here]
</task_input>

<thought_process>
[Demonstrate the reasoning steps needed to solve the problem]
</thought_process>

<execution_plan>
[Specify command, arguments, and expected outcome before running tools]
</execution_plan>

<correct_output>
[Provide a pristine, high-quality expected output]
</correct_output>
</example>
</examples>
```
