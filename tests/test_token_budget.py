from pathlib import Path

from ghosla.core.token_counter import CODEX_MAX_BYTES, TokenAuditor, estimate_tokens


def test_estimate_tokens() -> None:
    text = "Hello world! This is a simple test prompt."
    tokens = estimate_tokens(text)
    assert tokens > 0
    assert tokens < 20


def test_audit_skill_missing_file(tmp_path: Path) -> None:
    audit_res = TokenAuditor.audit_skill(tmp_path)
    assert not audit_res.is_valid
    assert any("Missing SKILL.md" in e for e in audit_res.errors)


def test_audit_skill_valid(tmp_path: Path) -> None:
    skill_dir = tmp_path / "valid-skill"
    skill_dir.mkdir()
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        """---
name: valid-skill
description: A well-behaved test skill.
---
# Valid Skill
## Workflow
1. Step one
2. Step two
""",
        encoding="utf-8",
    )
    audit_res = TokenAuditor.audit_skill(skill_dir)
    assert audit_res.is_valid
    assert len(audit_res.errors) == 0
    assert audit_res.byte_size < CODEX_MAX_BYTES


def test_audit_skill_exceeds_codex_budget(tmp_path: Path) -> None:
    skill_dir = tmp_path / "bloated-skill"
    skill_dir.mkdir()
    skill_md = skill_dir / "SKILL.md"
    content = """---
name: bloated-skill
description: Extremely large skill.
---
## Workflow
""" + ("A" * (CODEX_MAX_BYTES + 500))
    skill_md.write_text(content, encoding="utf-8")

    audit_res = TokenAuditor.audit_skill(skill_dir)
    assert not audit_res.is_valid
    assert any("Byte budget exceeded" in e for e in audit_res.errors)


def test_audit_skill_structural_warning(tmp_path: Path) -> None:
    skill_dir = tmp_path / "noworkflow-skill"
    skill_dir.mkdir()
    skill_md = skill_dir / "SKILL.md"
    content = """---
name: noworkflow-skill
description: Missing workflow section early on.
---
# Just Intro
Here is some narrative without procedures.
"""
    skill_md.write_text(content, encoding="utf-8")

    audit_res = TokenAuditor.audit_skill(skill_dir)
    # Warnings do not fail is_valid unless errors exist
    assert audit_res.is_valid
    assert any("workflow or process" in w.lower() for w in audit_res.warnings)
