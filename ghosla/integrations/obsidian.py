from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ghosla.core.models import SkillMetadata

DEFAULT_OBSIDIAN_VAULT = Path.home() / "Documents" / "obsidian"


class ObsidianLumaExporter:
    def __init__(self, vault_path: Optional[Path] = None):
        self.vault = vault_path if vault_path is not None else DEFAULT_OBSIDIAN_VAULT
        self.inbox = self.vault / "ai-workspace" / "skills-inbox"

    def export_for_study(self, skill: SkillMetadata, notes: Optional[str] = None) -> Path:
        """Exports a skill into Obsidian Luma study inbox for incremental reading."""
        self.inbox.mkdir(parents=True, exist_ok=True)
        dest_file = self.inbox / f"{skill.name}.md"

        skill_md = skill.path / "SKILL.md"
        if skill_md.exists():
            skill_doc = skill_md.read_text(encoding="utf-8", errors="replace")
        else:
            skill_doc = "No SKILL.md found."

        date_exported = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        default_notes = (
            "- [ ] Review why the workflow is ordered this way.\n"
            "- [ ] Identify anti-rationalization patterns.\n"
            "- [ ] Formulate Anki cards for non-obvious failure modes."
        )

        study_content = f"""---
title: "Skill Study: {skill.name}"
source_path: "{skill.path}"
upstream_repo: "{skill.upstream_repo or 'local'}"
tags:
  - agent-skill
  - study-lab
  - luma-inbox
priority: 50
date_exported: "{date_exported}"
---

# Skill Study: {skill.name}

> [!abstract] Architectural Purpose
> **Capability:** {skill.frontmatter.description}
> **Estimated Tokens:** ~{skill.estimated_tokens} | **Byte Size:** {skill.byte_size} bytes
> **Local Atelier Path:** `{skill.path}`

---

## Operator Reading & Dissection Notes
*(Use this section for Luma extracts, SuperMemo analysis, or Anki cloze formulation)*

{notes or default_notes}

---

## Original Skill Instruction Body

{skill_doc}
"""
        dest_file.write_text(study_content, encoding="utf-8")
        return dest_file
