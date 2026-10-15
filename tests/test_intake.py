from pathlib import Path

from ghosla.integrations.intake import (
    adopt_skill,
    bridge_external_skills,
    scan_intake_skills,
)


def test_scan_intake_skills(tmp_path: Path) -> None:
    intake_dir = tmp_path / "agents_skills"
    intake_dir.mkdir()

    # Skill 1: valid
    s1 = intake_dir / "external-tool"
    s1.mkdir()
    (s1 / "SKILL.md").write_text(
        "---\nname: external-tool\ndescription: An external tool\n---\n# Body\n",
        encoding="utf-8",
    )

    # Skill 2: not a directory / no SKILL.md
    (intake_dir / "random.txt").write_text("hello", encoding="utf-8")

    skills = scan_intake_skills(intake_dir)
    assert len(skills) == 1
    assert skills[0].name == "external-tool"
    assert skills[0].frontmatter.description == "An external tool"


def test_bridge_external_skills(tmp_path: Path) -> None:
    intake_dir = tmp_path / "agents_skills"
    intake_dir.mkdir()
    s1 = intake_dir / "external-tool"
    s1.mkdir()
    (s1 / "SKILL.md").write_text(
        "---\nname: external-tool\ndescription: An external tool\n---\n# Body\n",
        encoding="utf-8",
    )

    gemini_dir = tmp_path / "gemini_skills"
    gemini_dir.mkdir()

    bridged = bridge_external_skills(intake_dir, gemini_dir)
    assert len(bridged) == 1
    dest = gemini_dir / "external-tool"
    assert dest.is_symlink()
    assert dest.resolve() == s1.resolve()


def test_adopt_skill(tmp_path: Path) -> None:
    intake_dir = tmp_path / "agents_skills"
    intake_dir.mkdir()
    s1 = intake_dir / "external-tool"
    s1.mkdir()
    (s1 / "SKILL.md").write_text(
        "---\nname: external-tool\ndescription: External desc\n---\n## Workflow\n1. Do something\n",
        encoding="utf-8",
    )

    local_skills_dir = tmp_path / "ghosla_skills"
    local_skills_dir.mkdir()

    adopted_path = adopt_skill(s1, local_skills_dir, target_name="adopted-tool")
    assert adopted_path.exists()
    assert (adopted_path / "SKILL.md").exists()
    assert adopted_path.name == "adopted-tool"

    content = (adopted_path / "SKILL.md").read_text(encoding="utf-8")
    assert "name: adopted-tool" in content
