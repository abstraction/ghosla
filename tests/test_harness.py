from pathlib import Path

from ghosla.core.models import GhoslaConfig, HarnessType
from ghosla.integrations.harness import (
    detect_shadowing,
    set_harness_status,
)


def test_set_harness_status(tmp_path: Path) -> None:
    config_file = tmp_path / "ghosla.toml"
    config_file.write_text(
        """[atelier]
name = "ghosla"
active_bundle = "baseline"

[harnesses.antigravity]
enabled = true
path = "~/.gemini/config/skills"

[harnesses.claude_code]
enabled = false
path = "~/.claude/skills"
""",
        encoding="utf-8",
    )

    # Enable claude_code
    set_harness_status(config_file, "claude_code", enabled=True)
    cfg = GhoslaConfig.from_toml_file(config_file)
    assert cfg.harnesses[HarnessType.CLAUDE_CODE].enabled is True

    # Disable antigravity
    set_harness_status(config_file, "antigravity", enabled=False)
    cfg = GhoslaConfig.from_toml_file(config_file)
    assert cfg.harnesses[HarnessType.ANTIGRAVITY].enabled is False


def test_detect_shadowing(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    local_skills = workspace / ".agents" / "skills"
    local_skills.mkdir(parents=True)
    (local_skills / "tdd").mkdir()
    (local_skills / "tdd" / "SKILL.md").write_text("local tdd", encoding="utf-8")

    global_harness = tmp_path / "global_harness"
    global_harness.mkdir()
    (global_harness / "tdd").mkdir()
    (global_harness / "tdd" / "SKILL.md").write_text("global tdd", encoding="utf-8")

    conflicts = detect_shadowing(workspace, [global_harness])
    assert len(conflicts) == 1
    assert conflicts[0]["skill_name"] == "tdd"
    assert "shadows" in conflicts[0]["message"].lower()
