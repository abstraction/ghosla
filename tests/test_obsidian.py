from pathlib import Path

from ghosla.core.models import SkillFrontmatter, SkillMetadata, SkillSource
from ghosla.integrations.obsidian import ObsidianLumaExporter


def test_obsidian_luma_exporter(tmp_path: Path) -> None:
    vault = tmp_path / "obsidian"
    exporter = ObsidianLumaExporter(vault_path=vault)

    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        """---
name: my-skill
description: Tests obsidian study export
---
# Instructions
Do this and that.
""",
        encoding="utf-8",
    )

    meta = SkillMetadata(
        name="my-skill",
        source_type=SkillSource.LOCAL,
        path=skill_dir,
        frontmatter=SkillFrontmatter(name="my-skill", description="Tests obsidian study export"),
        byte_size=len(skill_md.read_bytes()),
        estimated_tokens=25,
        has_anti_rationalization=False,
        reference_depth=0,
    )

    dest_file = exporter.export_for_study(meta)
    assert dest_file.exists()
    assert dest_file.parent == vault / "ai-workspace" / "skills-inbox"

    content = dest_file.read_text(encoding="utf-8")
    assert "Skill Study: my-skill" in content
    assert "tags:" in content
    assert "luma-inbox" in content
    assert "Do this and that." in content
