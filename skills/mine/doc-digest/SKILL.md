---
name: doc-digest
description: "Digest and compile raw PDFs, EPUBs, text dumps, and Gemini Deep Research reports into atomic Google OKF v0.2 concept notes, Maps of Content, and cryptographic Blake3 checksums inside ai-workspace/. Triggers on: /doc-digest, doc-digest, ingest document, digest book, compile research, import pdf into vault, incremental reading preparation."
---

# Document Digest & OKF Compilation Skill (`/doc-digest`)

This skill governs the on-demand ingestion, distillation, and synthesis of longform literature, books, whitepapers, and Gemini Deep Research reports into the **Unified Knowledge Sanctuary** (`/home/seren/Documents/obsidian/ai-workspace/`).

It enforces the **Google Open Knowledge Format (OKF v0.2)** standard with cryptographic Blake3 content fingerprints, title-case naming, two-token search aliases, and automated Map of Content (MOC) updates while preserving human note boundaries.

---

## 1. Trigger Conditions

Activate this skill whenever:
- The user issues `/doc-digest` or mentions `/doc-digest "<path>"`.
- The user asks to ingest, digest, or summarize a PDF, EPUB, or longform article into Obsidian.
- Raw files are dropped into `ai-workspace/ingest/` for processing.
- A Gemini Deep Research report needs compilation into atomic concept notes and MOCs.

---

## 2. Directory Governance

| Path | Purpose | Behavior |
| :--- | :--- | :--- |
| `ai-workspace/ingest/` | Raw drop zone | Unindexed intake buffer for incoming binaries and dumps. |
| `ai-workspace/ingest/archive/` | Cold storage | Processed original binaries moved here post-compilation. |
| `ai-workspace/deep-research/` | Longform reports | Full-text Gemini Deep Research reports and comprehensive literature. |
| `ai-workspace/concepts/` | Atomic OKF notes | Immutable concept notes with byte-exact Blake3 hashes. |
| `ai-workspace/synthesis/` | Maps of Content | Thematic MOCs linking atomic concept notes together. |
| `sources/ai-research/` | Ephemeral Luma copies | Temporary reading copies staged for highlighting and shredding. |

---

## 3. The 4-Stage Compilation Engine

The pipeline runs deterministically via `ai-workspace/scripts/doc_digest.py`:

```bash
python3 /home/seren/Documents/obsidian/ai-workspace/scripts/doc_digest.py "<path_to_file_or_dir>" [--topic "Topic Name"]
```

### Stage 1: Extraction & Binary Conversion
- **PDF**: Uses `/usr/bin/pdftotext -layout` to extract layout-aware UTF-8 text.
- **EPUB**: Uses `/usr/bin/ebook-convert` to unpack chapters into clean plaintext.
- **Markdown / Text**: Direct parsing. If detected as Gemini Deep Research, stores the complete verbatim document in `ai-workspace/deep-research/`.

### Stage 2: Decomposition (Minimum Information Principle)
- Divides longform material into atomic conceptual sections (1 idea per note).
- Generates natural, scannable Title Case headers.

### Stage 3: Normalization & Blake3 Hashing
- **Title Sanitization**: Replaces OS-forbidden characters (`:`, `/`, `"`, `?`, `*`) and Obsidian-breaking characters (`#`, `^`, `[`, `]`, `%`).
- **Triple Synchronization**: Synchronizes filename (`{Title}.md`), YAML `title: "{Title}"`, and body heading (`# {Title}`).
- **Aliases**: Injects original slug into YAML `aliases: []` for instant Quick Switcher search.
- **Trust Tier**: Sets `trust_tier: Machine-Confirmed`.
- **Namespaced Tag**: Injects `tags: [ai-workspace/concept]`.
- **Blake3 Checksum**: Calculates cryptographic hash over canonical body text and records `content_fingerprint: "<blake3_hash>"`.

### Stage 4: Topological Synthesis & Archival
- Appends `## 🔗 Knowledge Graph` footer to concept notes with outbound `[[wikilinks]]`.
- Creates or updates the relevant Map of Content in `ai-workspace/synthesis/MOC - {Topic}.md`.
- Moves the processed source binary to `ai-workspace/ingest/archive/`.

---

## 4. Reading Bridge to Obsidian-Luma

To read a generated concept note in Luma without corrupting its Blake3 hash:

```bash
python3 /home/seren/Documents/obsidian/ai-workspace/scripts/stage_for_luma.py "<Concept Title>"
```

1. Staging copies the note to `sources/ai-research/{Title}.md` with `luma_type: topic`, `tags: [sources/reading-copy]`, and `source_master: "[[ai-workspace/concepts/{Title}.md]]"`.
2. Adds the ephemeral warning callout at line 1.
3. The user reads and highlights in Luma (`Alt+X`), generating Anki clozes (`Alt+Z`).
4. Shredding with `Alt+Shift+D` removes the ephemeral copy. The master OKF note in `ai-workspace/concepts/` remains 100% clean and cryptographically valid.

---

## 5. Architectural Invariants

1. **Write Boundary**: AI writes ONLY within `ai-workspace/` and `sources/ai-research/`. Never pollute vault root or human notes.
2. **Tag Scoping**: All machine tags must live under `ai-workspace/` or `sources/reading-copy`. Never use `#human-only-publish` under any circumstances.
3. **Master Immutability**: Never mutate master notes directly in Luma; always use the ephemeral reading bridge.
