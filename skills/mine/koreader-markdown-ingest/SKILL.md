---
name: koreader-markdown-ingest
description: >-
  Automates the ingestion of Markdown files into KOReader on a reMarkable tablet. It fetches a snippet, proposes a title using LLM reasoning, interactively confirms it with the user, renames the file safely, and generates a beautiful typographical e-ink cover.
---

# KOReader Markdown Ingest Skill

This skill allows agents to seamlessly process and beautify raw Markdown files residing on a reMarkable tablet (KOReader). It provides a native, interactive pipeline to clean up filenames and generate typographical covers that look great on e-ink displays.

## Execution Steps for the Agent

When a user asks to ingest, format, or set a cover for a Markdown file on their reMarkable, follow this exact pipeline:

### 1. Extract Snippet
Use SSH to fetch the first 2000 characters of the target file to understand its contents without downloading the whole file.
```bash
# Example:
ssh root@192.168.1.6 "head -c 2000 '/home/root/desk/raw_file.md'"
```

### 2. Analyze & Propose Title
Read the snippet in your context window. Determine a clean, polished, and concise Title for the document. 

### 3. Interactive Confirmation
You MUST use the `ask_question` tool to present your proposed title to the user.
- **Question:** "I suggest the following title for your document. Accept or provide a custom one?"
- **Options:** 
  1. `(Recommended) Accept: "[Your Proposed Title]"`
- Do not proceed until the user responds.

### 4. Rename Files on Device
Once the user confirms the final title, SSH into the device and rename both the `.md` file and its `.sdr` directory (if it exists) to match the new title. You MUST also ensure the `.sdr` directory exists so you can inject the cover in the next step.
```bash
# Example SSH commands:
ssh root@192.168.1.6 "mv '/home/root/desk/raw_file.md' '/home/root/desk/Final Title.md'"
ssh root@192.168.1.6 "mv '/home/root/desk/raw_file.sdr' '/home/root/desk/Final Title.sdr' 2>/dev/null || true"
ssh root@192.168.1.6 "mkdir -p '/home/root/desk/Final Title.sdr'"
```

### 5. Generate Typographical Cover
Execute the included Python script to dynamically generate a gorgeous, e-ink optimized typographical cover using the confirmed title.
```bash
uv run --with Pillow python ~/.gemini/config/skills/koreader-markdown-ingest/scripts/generate_cover.py "Final Title"
```
This outputs `generated_cover.jpg` in your current working directory.

### 6. Inject the Cover
`rsync` the generated cover directly into the `.sdr` directory on the tablet. It must be named `cover.jpg`.
```bash
rsync -avz generated_cover.jpg root@192.168.1.6:"'/home/root/desk/Final Title.sdr/cover.jpg'"
```

### 7. User Instruction (Cache Busting)
Inform the user that the process is complete. Instruct them to manually refresh the KOReader cache on their device:
> *"Open KOReader, long-press the file, select **Book information**, and tap **Refresh cached book information**."*
