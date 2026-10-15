# Polyglot Multi-Agent Test Pipeline

Synthesized from the `awesome-copilot/polyglot-test-agent` architecture.

## Architecture

```
┌────────────────────────────────────────────────────────┐
│                    TEST GENERATOR                      │
│   Coordinates the pipeline and manages execution state  │
└──────────────────────────┬─────────────────────────────┘
                           │
       ┌───────────────────┼───────────────────┐
       ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  RESEARCHER  │    │   PLANNER    │    │ IMPLEMENTER  │
│  Analyzes    │ ─> │  Creates     │ ─> │ Writes tests │
│  codebase &  │    │  phased test │    │ in vertical  │
│  seams       │    │  strategy    │    │ slices       │
└──────────────┘    └──────────────┘    └──────┬───────┘
                                               │
                         ┌──────────┬──────────┴──────────┬──────────┐
                         ▼          ▼                     ▼          ▼
                     ┌────────┐ ┌────────┐            ┌────────┐ ┌────────┐
                     │BUILDER │ │ TESTER │            │ FIXER  │ │ LINTER │
                     │Compile │ │ Run    │            │ Auto-  │ │ Format │
                     │checks  │ │ tests  │            │ repair │ │ & lint │
                     └────────┘ └────────┘            └────────┘ └────────┘
```

## Phase Breakdown

1. **Researcher Phase:**
   - Detects language (`Python`), test frameworks (`unittest`, `pytest`), build tools (`uv`), and existing test conventions.
   - Discovers public seams and external boundary touchpoints (keyring, filesystem, subprocesses).

2. **Planner Phase:**
   - Decomposes test requirements into 2-4 logical phases.
   - Establishes test cases, fixture isolation requirements, and target coverage goals (target 80%+).

3. **Implementer & Fixer Loop:**
   - Writes the test in the designated test suite.
   - Executes test command (`uv run pytest` or `uv run python -m unittest`).
   - If tests fail, diagnose the failure:
     - Is it an expected failure in red-green TDD?
     - Or an unintended regression/syntax error?
   - Apply minimal fixes and rerun until green.
   - Run formatters and linters (`ruff check --fix`, `ruff format`, `mypy --strict`).
