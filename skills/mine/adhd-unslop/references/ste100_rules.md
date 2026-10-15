# ASD-STE100 Reference Guide

ASD-STE100 (Simplified Technical English) is an international specification designed to eliminate ambiguity in technical documentation. It controls grammar, sentence structure, and vocabulary.

---

## 1. Structural Rules (Enforced)

Structural rules describe sentence shape and syntactic constraints. These can be evaluated deterministically.

### Rule 1: Active Voice
- Subject performs the action: Actor + Action + Object.
- Standard: "The compiler validates the syntax."
- Violation: "The syntax is validated by the compiler."
- Exception: Passive voice is permitted only when the actor is genuinely unknown or irrelevant.

### Rule 2: Sentence Length Caps
- Instructions and procedures: Maximum 20 words per sentence.
- Descriptions and explanations: Maximum 25 words per sentence.
- Split compound sentences with commas and conjunctions into atomic sentences.

### Rule 3: One Instruction Per Sentence
- Each sentence must convey exactly one action or proposition.
- Standard: "Open `config.yaml`. Set `port` to `8080`."
- Violation: "Open `config.yaml` and set `port` to `8080`, then restart the daemon."

### Rule 4: Ban Semicolons (Rule 8.1)
- ASD-STE100 bans semicolons (`;`) entirely.
- Use a period to create two independent, easily parseable statements.

### Rule 5: Noun Clusters
- Restrict noun clusters to at most 3 consecutive nouns.
- Standard: "database connection timeout" (3 nouns).
- Violation: "production database connection timeout retry handler" (6 nouns).
- Fix: Break using prepositions: "retry handler for production database timeouts".

### Rule 6: No Phrasal Verbs (Rule 9.3)
- Multi-word verbs carry unpredictable idioms for non-native speakers and LLM parsers.
- Use direct single-word verbs:
  - `start`, `launch` (not `spin up`, `kick off`)
  - `inspect`, `examine`, `read` (not `look into`, `dive into`, `drill down`)
  - `remove`, `detach` (not `take off`, `strip out`)
  - `stop`, `terminate` (not `wind down`, `wrap up`)

### Rule 7: No Nominalization (Rule 3.7)
- Do not convert action verbs into abstract nouns.
- Standard: "Analyze the crash dump." / "Decide immediately."
- Violation: "Perform an analysis of the crash dump." / "Make a decision immediately."

### Rule 8: Modality Preservation
- Never alter author confidence or probability hedges.
- If the original states "The lock may time out under load", do NOT simplify to "The lock times out under load."
- Upgrading a possibility to a certainty introduces factual falsehoods.

### Rule 9: Simple Tenses
- Prefer simple present, simple past, and imperative.
- Avoid compound tenses (present perfect, future perfect) unless current state relevance is essential.
- Standard: "We updated the schema." (not "We have updated the schema.")

---

## 2. Lexical Rules (Advisory)

ASD-STE100 enforces a controlled vocabulary where each approved word has one meaning and one part of speech.

### One Word, One Meaning
- Select one verb for an action and maintain it consistently.
- Do not alternate between "verify", "check", "confirm", and "test" for the identical action.
- Pick "verify" and stick with it.

### Avoid Synonym Cycling
- Calling a component "token cache", "credential store", and "auth buffer" in the same document causes confusion.
- Name the component once and repeat that exact name.

---

## 3. Two Operating Modes

1. **Strict Mode**: Applied to CLI instructions, system commands, error messages, and API tool contracts. Enforces hard word caps and rigid grammar constraints.
2. **STE-Flavored Mode**: Applied to architectural narratives and summaries. Enforces active voice, sentence length caps, no semicolons, and no phrasal verbs, while allowing technical domain vocabulary.
