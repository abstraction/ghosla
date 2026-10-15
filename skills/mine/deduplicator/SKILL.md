---
name: deduplicator
description: >-
  Use this skill to detect, verify, and deduplicate files across any directory tree.
  Provides high-speed cryptographic binary deduplication (SHA-256 with size pre-filtering)
  and intelligent semantic deduplication for PDFs (normalized text comparison),
  images (perceptual dHash and dimensions), text documents (stripped export headers),
  and corrupted or incomplete archive downloads. Moves duplicates to a local recycle bin
  with atomic JSON manifests and complete one-command rollback support.
---

# Content and Binary Deduplication Engine

This skill provides an automated workflow to find and quarantine duplicate files across large file trees without risking data loss. It combines fast cryptographic hashing for bit-identical files with semantic normalization for files whose binary headers or metadata differ.

Execution is managed by a standalone Python script located in `scripts/dedup.py`, runnable with `uv`. It runs in dry-run mode by default and requires an explicit `--execute` flag before moving any file.

---

## Capabilities

1. **Exact binary matching**:
   Filters candidates by file size first, then computes a partial head and tail block hash, and finishes with a full chunked SHA-256 hash. Files with unique sizes are never read from disk.

2. **Semantic PDF matching**:
   Extracts text using `pdftotext`, normalizes whitespace, and strips transient timestamps, print headers, and generation metadata. Detects repeated downloads of tickets, receipts, and invoices even when internal PDF creation timestamps differ.

3. **Perceptual image matching**:
   Uses Pillow to check dimensions and compute a 64-bit difference hash (dHash). Detects duplicate images that differ only by file stem or duplicate extensions like `.jpg.jpg`.

4. **Markdown and text document comparison**:
   Strips export headers such as `Exported at: <timestamp>` or frontmatter dates before comparing document bodies.

5. **Incomplete download detection**:
   Flags truncated or broken archive downloads (tested via `zipfile.ZipFile`) paired with intact complete archives, as well as zero-byte download stubs.

6. **Canonical keeper selection**:
   Selects the best file to keep based on filename cleanliness (penalizing `(1)`, ` - Copy`, duplicate extensions), directory organization depth (preferring structured subfolders over root or staging directories like `Downloads` and `Inbox`), and original file age.

7. **Reversibility**:
   Never executes `rm`. Redundant files are moved to `<target>/_recycle_bin/staged_duplicates/` preserving their relative path. An atomic manifest (`.dedup_manifest_<timestamp>.json`) tracks every move, file size, hash, and removed empty directory, allowing a full restore with a single command.

---

## Usage

Run via `uv` without installing dependencies into the global environment:

### 1. Simulation (Dry-Run)
```bash
uv run ~/.gemini/config/skills/deduplicator/scripts/dedup.py /path/to/target
```

### 2. Live Execution
```bash
uv run ~/.gemini/config/skills/deduplicator/scripts/dedup.py /path/to/target --execute
```

To specify a custom recycle bin location outside the target folder:
```bash
uv run ~/.gemini/config/skills/deduplicator/scripts/dedup.py /path/to/target --execute --recycle-bin /path/to/custom_recycle_bin
```

### 3. Pure Binary Mode (Skip Semantic Normalization)
```bash
uv run ~/.gemini/config/skills/deduplicator/scripts/dedup.py /path/to/target --execute --no-semantic
```

### 4. Undo / Rollback
```bash
uv run ~/.gemini/config/skills/deduplicator/scripts/dedup.py --undo /path/to/target/_recycle_bin/.dedup_manifest_YYYYMMDD_HHMMSS.json
```

The script will restore all moved files, recreate any pruned directories, clean up the recycle bin staging tree, and rename the manifest file to indicate completion.

---

## Options Reference

Flag | Description
:--- | :---
`target` | Path to target directory (defaults to current directory `.`).
`--execute` | Apply moves to disk. Defaults to simulation mode if omitted.
`--dry-run` | Explicitly enforce simulation mode.
`--recycle-bin <dir>` | Directory to stage duplicates in (default: `<target>/_recycle_bin`).
`--no-semantic` | Disable semantic normalization, running only binary SHA-256 matching.
`--no-binary` | Disable binary deduplication, running only semantic matching.
`--min-size <bytes>` | Skip files smaller than the given byte threshold.
`--exclude <pattern>` | Exclude files or subdirectories containing the specified pattern.
`--undo <manifest>` | Reverse moves recorded in a previous transaction manifest.
`-v`, `--verbose` | Output detailed debugging logs during traversal and comparison.
