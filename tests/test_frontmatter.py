from pathlib import Path

from ghosla.core.frontmatter import (
    extract_skill_frontmatter,
    format_frontmatter,
    parse_frontmatter,
)


def test_parse_frontmatter_valid() -> None:
    content = """---
name: test-skill
description: A helpful description
allowed-tools: read_file,run_command
---
# Main Content
Here is the documentation.
"""
    fm_dict, body = parse_frontmatter(content)
    assert fm_dict["name"] == "test-skill"
    assert fm_dict["description"] == "A helpful description"
    assert fm_dict["allowed-tools"] == "read_file,run_command"
    assert "# Main Content" in body


def test_parse_frontmatter_missing() -> None:
    content = "# Just markdown\nNo frontmatter here."
    fm_dict, body = parse_frontmatter(content)
    assert fm_dict == {}
    assert body == content


def test_extract_skill_frontmatter(tmp_path: Path) -> None:
    skill_file = tmp_path / "SKILL.md"
    skill_file.write_text(
        """---
name: sample-skill
description: Valid skill description
---
## Workflow
1. Step one
""",
        encoding="utf-8",
    )
    fm, body, err = extract_skill_frontmatter(skill_file)
    assert err is None
    assert fm is not None
    assert fm.name == "sample-skill"
    assert fm.description == "Valid skill description"
    assert "## Workflow" in body


def test_extract_skill_frontmatter_invalid_schema(tmp_path: Path) -> None:
    skill_file = tmp_path / "SKILL.md"
    skill_file.write_text(
        """---
name: Invalid_Name
description: Missing proper kebab-case
---
Body
""",
        encoding="utf-8",
    )
    fm, body, err = extract_skill_frontmatter(skill_file)
    assert fm is None
    assert err is not None
    assert "Skill name must be lowercase alphanumeric with hyphens" in err


def test_format_frontmatter() -> None:
    data = {"name": "clean-skill", "description": "Short desc"}
    formatted = format_frontmatter(data)
    assert formatted.startswith("---\n")
    assert formatted.endswith("---\n")
    assert "name: clean-skill\n" in formatted


def test_extract_skill_frontmatter_with_fork_metadata(tmp_path: Path) -> None:
    skill_file = tmp_path / "SKILL.md"
    skill_file.write_text(
        """---
name: git-commit
description: Forked commit helper
metadata:
  upstream_source: github-copilot-community/git-commit
  fork: true
---
## Steps
1. Staging
""",
        encoding="utf-8",
    )
    fm, body, err = extract_skill_frontmatter(skill_file)
    assert err is None
    assert fm is not None
    assert fm.name == "git-commit"
    assert fm.is_fork is True
    assert fm.upstream_source == "github-copilot-community/git-commit"
    assert fm.metadata.get("fork") is True

