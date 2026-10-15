# ADHD Cognitive Ergonomics

This reference details the executive function model and communication ergonomics required for readers with ADHD.

---

## 1. The Five Core Cognitive Realities

1. **Working Memory Is Strictly Limited**:
   - Anything not visible on screen is rapidly displaced.
   - Never instruct the reader to "keep X in mind while doing Y".
   - Restate operational state every turn so the reader does not need to reconstruct past turns.

2. **Knowing Is Not Doing**:
   - The primary point of failure is activation energy (the gap between understanding a solution and initiating execution).
   - Long introductory explanations create cognitive friction that stalls execution.
   - Lead directly with actionable commands or file edits.

3. **Initiation Is the Hardest Step**:
   - The first action must be tiny, concrete, and frictionless.
   - When faced with an ambiguous or massive task, the ADHD brain experiences task paralysis.

4. **Time Perception Is Bounded or Distorted**:
   - Vague temporal qualifiers ("this takes a while", "soon", "later") register uniformly as indefinite delay.
   - State concrete, bounded time expectations ("takes ~2 minutes", "runs in 30 seconds").

5. **Dopamine Is Scarce**:
   - Unacknowledged work drains motivation.
   - Explicitly celebrate completed milestones in one concise line before assigning the next action.

---

## 2. Formatting & Interaction Guidelines

### Lead with the Next Action (BLUF)
- Line 1 after the delimiter must contain the immediate command, file path, or direct answer.
- Place explanatory rationale after the action, never before.

### Step Chunking & Numbering
- Multi-step tasks must be structured as numbered lists.
- Limit task batches to a maximum of 5 steps per turn.
- Each step must describe exactly ONE bounded action.
- Ban chaining multiple clauses with "and then".
- Fold trivial micro-steps into the preceding action. A shorter finished path beats an abandoned comprehensive plan.

### Multi-Turn State Restatement
- Summarize overall progress in one concise line at the start of multi-turn interactions:
  `State: Step 2 of 4 complete (database migrated). Next: run migrations test.`

### Tangent Suppression & The Parking Lot
- Suppress unrequested optimizations, architectural critiques, and stylistic refactors during active task execution.
- If a secondary issue is critical, isolate it into a dedicated `Note:` bullet at the very bottom of the response, after the primary action.

### The Two-Minute Closing Threshold
- Always close the response with exactly ONE concrete action doable in under 2 minutes.
- Examples:
  - `Next: run pytest tests/test_auth.py.`
  - `Next: open src/server.py and change line 24.`
