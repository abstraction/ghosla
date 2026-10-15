---
name: koreader-metadata-sync
description: >-
  Use this skill when the user asks to standardize book filenames, fix book titles/authors, or correct the metadata shown in KOReader for EPUB/PDF files. It safely rewrites internal tags and perfectly migrates KOReader .sdr reading progress caches.
---

# KOReader Metadata & Library Sync Skill

This skill allows the agent to safely standardize book file names and rewrite internal EPUB/PDF metadata tags without destroying the user's KOReader reading progress. 

## The Problem
KOReader extracts metadata from internal EPUB OPF tags or PDF Info dictionaries. If these are messy, the UI looks terrible. However, if you modify the book files or rename them, KOReader will lose the user's reading progress (stored in `.sdr` folders) unless handled meticulously. 
KOReader links a book to its `.sdr` directory using:
1. The exact folder name (e.g., `Book Title.sdr`).
2. The `doc_path` variable inside `metadata.*.lua`.
3. The `partial_md5_checksum` of the first 1024 bytes of the book file.

## Execution Steps

### 1. Download Files
Always sync the target directory from the device locally first using `rsync` into a scratch workspace so you can use Python libraries safely.
```bash
mkdir -p scratch/koreader_sync
rsync -avz root@192.168.1.6:/home/root/desk/ scratch/koreader_sync/
```

### 2. Identify Metadata Overrides
Analyze the files. If the author/title strings are messy, deduce the clean versions yourself using your knowledge base or web search. If a book is ambiguous, ask the user using the `ask_question` tool before proceeding. Create a JSON mapping or a Python dict of `old_filename -> (Clean Author, Clean Title)`.

### 3. Run the Safe Sync Script
Use the provided python script to inject the metadata, rename the files, and migrate the `.sdr` folders correctly.
```bash
# Provide the directory to the script
uv run --with pypdf --with EbookLib python ~/.gemini/config/skills/koreader-metadata-sync/scripts/sync_metadata.py scratch/koreader_sync/
```
*Note: Ensure you read and edit `sync_metadata.py` to inject your proposed `overrides` dictionary before running it.*

### 4. Verify & Upload
Verify the local files look correct, then sync back to the device. **You MUST use `--delete`** so that the old messy files are erased.
```bash
rsync -avz --delete scratch/koreader_sync/ root@192.168.1.6:/home/root/desk/
```
