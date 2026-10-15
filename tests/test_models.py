from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from ghosla.core.models import (
    GhoslaConfig,
    HarnessConfig,
    HarnessType,
    IntakeConfig,
    SkillBundle,
    SkillFrontmatter,
    UpstreamDefaults,
    UpstreamSource,
)


def test_harness_type_values() -> None:
    assert HarnessType.ANTIGRAVITY.value == "antigravity"
    assert HarnessType.AGENTS_GLOBAL.value == "agents_global"
    assert HarnessType.CLAUDE_CODE.value == "claude_code"
    assert HarnessType.CODEX.value == "codex"
    assert HarnessType.CURSOR.value == "cursor"


def test_skill_frontmatter_valid() -> None:
    data: dict[str, Any] = {
        "name": "test-skill",
        "description": "A test skill for unit testing",
        "license": "MIT",
        "allowed-tools": "bash,read_file",
        "disable-model-invocation": True,
    }
    fm = SkillFrontmatter.model_validate(data)
    assert fm.name == "test-skill"
    assert fm.description == "A test skill for unit testing"
    assert fm.allowed_tools == "bash,read_file"
    assert fm.disable_model_invocation is True


def test_skill_frontmatter_invalid_name() -> None:
    with pytest.raises(ValidationError):
        SkillFrontmatter(name="Invalid_Name", description="Test")

    with pytest.raises(ValidationError):
        SkillFrontmatter(name="UPPERCASE", description="Test")

    with pytest.raises(ValidationError):
        SkillFrontmatter(name="spaces not allowed", description="Test")


def test_skill_frontmatter_long_description() -> None:
    with pytest.raises(ValidationError):
        SkillFrontmatter(name="valid-name", description="x" * 1025)


def test_ghosla_config_parsing() -> None:
    cfg = GhoslaConfig(
        active_bundle="baseline",
        harnesses={
            HarnessType.ANTIGRAVITY: HarnessConfig(
                enabled=True, path=Path("~/.gemini/config/skills")
            ),
            HarnessType.AGENTS_GLOBAL: HarnessConfig(
                enabled=False, path=Path("~/.agents/skills")
            ),
        },
        intake=IntakeConfig(
            catch_all_path=Path("~/.agents/skills"),
            auto_bridge_to_gemini=True,
            bridge_prefix="",
        ),
    )
    assert cfg.active_bundle == "baseline"
    assert cfg.harnesses[HarnessType.ANTIGRAVITY].enabled is True
    assert cfg.harnesses[HarnessType.AGENTS_GLOBAL].enabled is False
    assert cfg.intake.auto_bridge_to_gemini is True


def test_skill_bundle() -> None:
    bundle = SkillBundle(
        name="baseline",
        description="Core daily drivers",
        skills=["git-commit", "unslop"],
        target_harnesses=[HarnessType.ANTIGRAVITY],
    )
    assert bundle.name == "baseline"
    assert len(bundle.skills) == 2
    assert HarnessType.ANTIGRAVITY in bundle.target_harnesses


def test_upstream_source_and_defaults() -> None:
    defaults = UpstreamDefaults(
        apiVersion="ghosla.io/v1alpha1",
        kind="UpstreamDefaults",
        excludePaths=[".git/**", "node_modules/**"],
    )
    assert len(defaults.excludePaths) == 2

    source = UpstreamSource(
        name="pstack",
        git={"url": "https://github.com/cursor/plugins", "ref": "main"},
        newRootPath="pstack",
        extraExcludePaths=["docs/**"],
    )
    assert source.name == "pstack"
    assert source.newRootPath == "pstack"
    assert source.extraExcludePaths == ["docs/**"]


def test_skill_metadata_fork_status(tmp_path: Path) -> None:
    from ghosla.core.models import SkillMetadata, SkillSource

    fm = SkillFrontmatter(
        name="git-commit",
        description="Forked commit tool",
        metadata={"upstream_source": "github-copilot-community/git-commit", "fork": True},
    )
    meta = SkillMetadata(
        name="git-commit",
        source_type=SkillSource.FORK,
        path=tmp_path / "git-commit",
        frontmatter=fm,
        byte_size=1200,
        estimated_tokens=300,
        has_anti_rationalization=False,
        reference_depth=0,
        upstream_repo="github-copilot-community/git-commit",
    )
    assert meta.is_fork is True
    assert meta.source_type == SkillSource.FORK
    assert meta.upstream_repo == "github-copilot-community/git-commit"

