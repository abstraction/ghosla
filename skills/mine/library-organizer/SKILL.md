---
name: library-organizer
description: >-
  Use this skill when the user asks to organize, sort, categorize, deduplicate, or clean up digital books, ebooks, PDFs, and reading materials according to the Johnny.Decimal standard (Area 60-69 Library & Literature). It provides automated binary deduplication, metadata extraction, filename normalization, and schema-driven classification via a safe, decoupled Python engine with dry-run and rollback capabilities.
---

# Digital Library Organizer (Johnny.Decimal Standard)

This skill automates the organization, deduplication, and metadata-driven classification of digital books, academic papers, and training manuals into the **Johnny.Decimal Master Library (`60-69 Library & Literature`)**.

The skill architecture strictly separates the **Immutable Execution Engine** (`organize_library.py`) from the **Declarative Taxonomy Schema** (`taxonomy.json`). Code is never modified at runtime; category expansions and custom rules are managed declaratively through JSON configuration with human approval.

---

## The Johnny.Decimal Master Library Standard (`60-69`)

All reference books, textbooks, manuals, and monographs belong in Area `60-69`:
- **`61 Computer Science & Technical Systems`**: Algorithms, systems programming, languages, DevOps, system design.
- **`62 Economics, Wealth & Markets`**: Investing, economic theory, trading psychology, market structure, Zerodha Varsity.
- **`63 Physical Culture, Health & Physiology`**: Biomechanics, mobility manuals (Functional Synergy, Jason Pak), hypertrophy (Eric Helms, Jeff Nippard), nutrition treatises, and athletics.
- **`64 Mind, Philosophy & Human Performance`**: Classical philosophy, epistemology, cognitive psychology, Deep Work, GTD, habits.
- **`65 Fiction & Modern Literature`**: Classic literature, novels, and narrative fiction.
- **`66 Serial Fiction & Web Novels`**: Progression fantasy, LitRPG, Xianxia, Wuxia, and translated light novels.
- **`67 Periodicals, Reports & Whitepapers`**: Institutional whitepapers, academic preprints, periodical archives.
- **`68 [RESERVED / SPARE]`**: Reserved for permanent major disciplines (e.g. History & Geopolitics); requires minimum 30+ document cluster and human approval.
- **`69 Reading Lists & Summaries`**: Video transcripts, executive chapter summaries, and personal reading notes.

> [!IMPORTANT]
> **The Workbench vs. Library Shelf Rule:**
> Active tracking logs, Hevy workout databases, and blood biomarker reports belong in **`30-39 Health & Performance`**, while all published training manuals and textbooks belong in **`63 Physical Culture`**. `30-39` connects to `63` via a directory symlink (`33 Training & Nutrition Guides/Reference Books & Guides`).

---

## The Admissions Gatekeeper Protocol

The Master Library (`60-69`) is reserved strictly for published, readable literature.
- **Disqualified Files**: Invoices, receipts, tax returns, bank statements, passports, Aadhaar cards, resumes, and medical lab reports.
- **Gatekeeper Action**: The engine automatically detects administrative or personal PII tokens and routes them to `00-09 System & Inbox/01 Intake & Inbox` for appropriate domain filing (`20-29 Wealth` or `70-79 Identity`), preventing library pollution.

---

## Workflow Instructions

### 1. Locate the Target Directory
Identify the target directory to organize (e.g., `/home/seren/Documents/2026-08-backup/60-69 Library & Literature` or an intake folder).

### 2. Run Dry-Run Simulation First
Always simulate planned moves before modifying files on disk:
```bash
python ~/.gemini/config/skills/library-organizer/scripts/organize_library.py \
  --dir "<TARGET_DIR>" \
  --dry-run
```
Review the execution summary for exact binary duplicates, gatekeeper exclusions, and unclassified files.

### 3. Execute Organization & Generate Transaction Manifest
Once verified, execute the organization:
```bash
python ~/.gemini/config/skills/library-organizer/scripts/organize_library.py \
  --dir "<TARGET_DIR>" \
  --json-report /tmp/library_execution.json
```
- **Transaction Journal**: The script automatically writes a timestamped manifest (`.jd_manifest_<timestamp>.json`) in the target directory.
- **Rollback**: Any execution can be 100% reversed using:
  ```bash
  python ~/.gemini/config/skills/library-organizer/scripts/organize_library.py --undo "<MANIFEST_PATH>"
  ```

### 4. Handle Staged & Unclassified Items
- **Review `00-09 System & Inbox/01 Intake & Inbox`**:
  Inspect unclassified documents. Read the title, table of contents, or first page using `pdftotext` or `view_file`.
  If the file matches an existing category, move it to its canonical folder.
- **Review Exact Duplicates**:
  Exact binary duplicates are safely staged in `_recycle_bin/staged_duplicates/`. **Never delete files permanently without explicit user permission.**
- **Multi-Format Works (`co_locate`)**:
  Both `.pdf` and `.epub` editions of the same book are preserved side-by-side in the same category folder with matching base names. Neither format is evicted.

---

## Taxonomy Expansion Protocol (Human-in-the-Loop)

> [!CAUTION]
> **Strict Agent Constraint: Never Modify Source Code Dynamically.**
> Agents must **never** rewrite `organize_library.py` or edit `SKILL.md` instructions at runtime. Self-modifying code introduces security risks (indirect prompt injection), syntax errors, and uncontrolled schema drift.

When incoming documents do not fit existing categories:

1. **Keep Files Safely in Staging**: Leave the unclassified documents in `00-09 System & Inbox/01 Intake & Inbox`.
2. **Cluster Analysis**: Check if 10+ documents share a coherent, enduring topic.
3. **Present a Taxonomy Expansion Proposal to the User**:
   - Proposed Category or Decimal ID (e.g., `61.10 Machine Learning & AI` or `68 History & Geopolitics`).
   - List of affected files and reasoning.
   - Proposed addition to `taxonomy.json` (or local `library_manifest.json`).
4. **Update Declarative Schema Only After Approval**:
   Upon explicit user confirmation, add the new category rule to `~/.gemini/config/skills/library-organizer/taxonomy.json` (or create a local `library_manifest.json` in the target directory). The engine will immediately recognize the new category on its next run.
