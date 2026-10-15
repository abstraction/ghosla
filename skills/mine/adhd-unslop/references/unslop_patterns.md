# Complete Unslop Pattern Taxonomy

This reference catalogs the complete 31 patterns that identify AI-generated text, along with concrete rewrite rules.

---

## 1. Content & Framing Tells

1. **Puffery**: Phrases like "pivotal moment", "testament to", "evolving landscape", "setting the stage for". State concrete facts and events directly.
2. **Name-dropping**: Listing media outlets or tools without substantive context.
3. **Superficial -ing phrases**: Trailing participle clauses ("highlighting...", "ensuring...", "reflecting...", "showcasing...", "fostering..."). Rewrite as independent sentences or delete.
4. **Promotional language**: "nestled", "vibrant", "breathtaking", "groundbreaking", "renowned", "stunning". Use neutral, factual descriptions.
5. **Vague attributions**: "Experts believe", "Industry reports suggest", "Some argue". Name the source or delete the sentence.
6. **Formulaic challenges**: "Despite challenges... continues to thrive." Replace with specific measurements and trade-offs.

---

## 2. Language & Lexical Tells

7. **AI vocabulary**:
   - `additionally` -> `also`, or start a new sentence
   - `crucial` / `pivotal` -> `critical`, `key`, `required`
   - `delve` / `dive into` -> `examine`, `read`, `inspect`
   - `enduring` / `tapestry` / `landscape` -> delete or name the specific system
   - `enhance` / `foster` -> `improve`, `build`, `help`
   - `intricate` -> `complex`, `detailed`
   - `showcase` -> `show`, `display`
   - `testament` / `underscore` -> `evidence`, `shows`, `highlights`
   - `utilize` / `leverage` -> `use`
8. **Fancy ways to say "is"**: "serves as", "stands as", "boasts", "features". Replace with "is" or "has".
9. **"Not just X, but Y"**: Say the point directly without artificial contrast staging.
10. **Rule of three**: Forcing ideas into triplets artificially. Use the natural count.
11. **Synonym cycling**: Cycling synonyms for the same subject across a paragraph. Pick one noun and repeat it.
12. **False ranges**: "From frontend to backend" when describing unrelated items. List topics directly.

---

## 3. Style & Punctuation Tells

13. **Em dash overuse (`—` or `--`)**: AI models overuse em dashes to link disparate clauses. Replace with periods or commas.
14. **Mid-sentence colon connectors**: Avoid using colons to introduce comparisons mid-sentence.
15. **Boldface overuse**: Do not bold every acronym, proper noun, or technical keyword.
16. **Inline-header lists**: Avoid restating the bullet label: "**Performance:** Performance improved...". State details directly.
17. **Title case headings**: Use standard sentence case for subheadings.
18. **Decorative emojis**: Ban rocket ships, lightbulbs, gears, and sparkles. Functional delimiters (e.g. `───────── ౨ৎ ─────────`) are permitted.
19. **Curly quotes**: Use straight quotes (`"`, `'`).

---

## 4. Communication Artifacts

20. **Chatbot phrases**: "Certainly!", "I hope this helps!", "Let me know if you have questions!", "Found the smoking gun!". Strip them completely.
21. **Cutoff disclaimers**: "While specific details are limited...". Find the source or omit.
22. **Sycophantic tone**: "Great question!", "You are absolutely right!". Respond directly to the technical substance.

---

## 5. Filler & Padding

23. **Filler phrases**:
   - "In order to" -> "To"
   - "Due to the fact that" -> "Because"
   - "It is important to note that" -> delete
24. **Excessive hedging**: "could potentially possibly be argued" -> "may".
25. **Generic conclusions**: "The future looks bright." Replace with concrete status or delete.

---

## 6. Jargon Metaphors

26. **Abstract metaphor nouns**:
   `substrate`, `wedge`, `vector`, `locus`, `vantage`, `nexus`, `primitive`, `harness`, `surface`, `bedrock`, `scaffolding`, `modality`, `paradigm`, `gold-plating`, `ratchet`, `evacuate`, `endgame`, `north star`, `flywheel`.
   Replace with plain technical terms:
   - "event substrate" -> "event queue"
   - "wedge in" -> "add"
   - "attack vector" -> "attack method"
   - "bedrock" -> "foundation"
   - "ratchet" -> "enforced limit"

---

## 7. Plain Speech Rules

27. **Say what it does, not how it feels**: Replace emotional descriptions with mechanisms or benchmark numbers ("finishes in 4ms", not "blazing-fast").
28. **Shorten or split dense sentences**: One proposition per sentence.
29. **Active voice**: Actor + Action + Object.
30. **Cut adverbs**: Use stronger, accurate verbs instead of adverb crutches.
31. **Prefer the plain word**: "use" over "utilize", "help" over "facilitate", "many" over "numerous".
