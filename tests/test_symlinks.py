from pathlib import Path

from ghosla.core.linker import LinkerEngine, atomic_symlink
from ghosla.core.models import (
    HarnessConfig,
    HarnessType,
    SkillBundle,
    SkillFrontmatter,
    SkillMetadata,
    SkillSource,
)


def test_atomic_symlink_create_and_replace(tmp_path: Path) -> None:
    source1 = tmp_path / "skill_v1"
    source1.mkdir()
    (source1 / "SKILL.md").write_text("v1", encoding="utf-8")

    source2 = tmp_path / "skill_v2"
    source2.mkdir()
    (source2 / "SKILL.md").write_text("v2", encoding="utf-8")

    target = tmp_path / "harness" / "my-skill"

    # Initial creation
    atomic_symlink(source1, target)
    assert target.is_symlink()
    assert (target / "SKILL.md").read_text(encoding="utf-8") == "v1"

    # Atomic update to v2
    atomic_symlink(source2, target)
    assert target.is_symlink()
    assert (target / "SKILL.md").read_text(encoding="utf-8") == "v2"


def test_atomic_symlink_replaces_existing_directory(tmp_path: Path) -> None:
    # Target starts as a real physical directory (not a symlink)
    target = tmp_path / "harness" / "my-skill"
    target.mkdir(parents=True)
    (target / "SKILL.md").write_text("old directory content", encoding="utf-8")

    source = tmp_path / "ghosla_skill"
    source.mkdir()
    (source / "SKILL.md").write_text("new ghosla content", encoding="utf-8")

    atomic_symlink(source, target)
    assert target.is_symlink()
    assert (target / "SKILL.md").read_text(encoding="utf-8") == "new ghosla content"


def test_linker_engine_respects_harness_toggle(tmp_path: Path) -> None:
    workspace = tmp_path / "ghosla"
    workspace.mkdir()
    skill_dir = workspace / "skills" / "my-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("content", encoding="utf-8")

    harness1_dir = tmp_path / "harness_enabled"
    harness2_dir = tmp_path / "harness_disabled"

    custom_paths = {
        HarnessType.ANTIGRAVITY: harness1_dir,
        HarnessType.CLAUDE_CODE: harness2_dir,
    }

    harness_configs = {
        HarnessType.ANTIGRAVITY: HarnessConfig(enabled=True, path=harness1_dir),
        HarnessType.CLAUDE_CODE: HarnessConfig(enabled=False, path=harness2_dir),
    }

    catalog = {
        "my-skill": SkillMetadata(
            name="my-skill",
            source_type=SkillSource.LOCAL,
            path=skill_dir,
            frontmatter=SkillFrontmatter(name="my-skill", description="desc"),
            byte_size=100,
            estimated_tokens=25,
            has_anti_rationalization=False,
            reference_depth=0,
        )
    }

    bundle = SkillBundle(
        name="test",
        description="desc",
        skills=["my-skill"],
        target_harnesses=[HarnessType.ANTIGRAVITY, HarnessType.CLAUDE_CODE],
    )

    engine = LinkerEngine(workspace_root=workspace, harness_paths=custom_paths)
    created = engine.link_bundle(bundle, catalog, harnesses_config=harness_configs)

    assert len(created) == 1
    assert (harness1_dir / "my-skill").is_symlink()
    assert not (harness2_dir / "my-skill").exists()


def test_clean_orphaned_links(tmp_path: Path) -> None:
    workspace = tmp_path / "ghosla"
    workspace.mkdir()
    skill1 = workspace / "skills" / "skill1"
    skill1.mkdir(parents=True)
    (skill1 / "SKILL.md").write_text("content", encoding="utf-8")

    skill2 = workspace / "skills" / "skill2"
    skill2.mkdir(parents=True)
    (skill2 / "SKILL.md").write_text("content", encoding="utf-8")

    harness_dir = tmp_path / "harness"
    harness_dir.mkdir()

    # Link both
    link1 = harness_dir / "skill1"
    link2 = harness_dir / "skill2"
    atomic_symlink(skill1, link1)
    atomic_symlink(skill2, link2)

    # Active bundle only has skill1
    bundle = SkillBundle(
        name="active",
        description="desc",
        skills=["skill1"],
        target_harnesses=[HarnessType.ANTIGRAVITY],
    )

    custom_paths = {HarnessType.ANTIGRAVITY: harness_dir}
    engine = LinkerEngine(workspace_root=workspace, harness_paths=custom_paths)
    removed = engine.clean_orphaned_links([bundle])

    assert link2 in removed
    assert not link2.exists()
    assert link1.exists()


def test_resolve_skill_and_link_upstream_and_fork(tmp_path: Path) -> None:
    workspace = tmp_path / "ghosla"
    workspace.mkdir()

    # Upstream unslop (no local fork in skills/)
    upstream_unslop = workspace / "upstream" / "pstack" / "skills" / "unslop"
    upstream_unslop.mkdir(parents=True)
    (upstream_unslop / "SKILL.md").write_text(
        "---\nname: unslop\ndescription: Upstream unslop\n---\n", encoding="utf-8"
    )

    # Local forked git-commit in skills/
    local_git_commit = workspace / "skills" / "git-commit"
    local_git_commit.mkdir(parents=True)
    (local_git_commit / "SKILL.md").write_text(
        """---
name: git-commit
description: Local forked git-commit
metadata:
  upstream_source: github-copilot-community/git-commit
  fork: true
---
""",
        encoding="utf-8",
    )

    catalog = {
        "unslop": SkillMetadata(
            name="unslop",
            source_type=SkillSource.UPSTREAM,
            path=upstream_unslop,
            frontmatter=SkillFrontmatter(name="unslop", description="Upstream unslop"),
            byte_size=100,
            estimated_tokens=25,
            has_anti_rationalization=False,
            reference_depth=0,
            upstream_repo="pstack",
        ),
        "git-commit": SkillMetadata(
            name="git-commit",
            source_type=SkillSource.FORK,
            path=local_git_commit,
            frontmatter=SkillFrontmatter(
                name="git-commit",
                description="Local forked git-commit",
                metadata={"upstream_source": "github-copilot-community/git-commit", "fork": True},
            ),
            byte_size=200,
            estimated_tokens=50,
            has_anti_rationalization=False,
            reference_depth=0,
            upstream_repo="github-copilot-community/git-commit",
        ),
    }

    harness_dir = tmp_path / "gemini_skills"
    harness_dir.mkdir()
    custom_paths = {HarnessType.ANTIGRAVITY: harness_dir}
    engine = LinkerEngine(workspace_root=workspace, harness_paths=custom_paths)

    # 1. Test resolve_skill by name, path, and prefix
    assert engine.resolve_skill("unslop", catalog) is catalog["unslop"]
    assert engine.resolve_skill("upstream/pstack/skills/unslop", catalog) is catalog["unslop"]
    assert engine.resolve_skill("pstack/unslop", catalog) is catalog["unslop"]
    assert engine.resolve_skill("git-commit", catalog) is catalog["git-commit"]

    # 2. Test bundle linking
    bundle = SkillBundle(
        name="baseline",
        description="Core bundle",
        skills=["git-commit", "unslop"],
        target_harnesses=[HarnessType.ANTIGRAVITY],
    )
    links = engine.link_bundle(bundle, catalog)
    assert len(links) == 2

    dest_unslop = harness_dir / "unslop"
    dest_git_commit = harness_dir / "git-commit"

    assert dest_unslop.is_symlink()
    assert dest_unslop.resolve() == upstream_unslop.resolve()

    assert dest_git_commit.is_symlink()
    assert dest_git_commit.resolve() == local_git_commit.resolve()


def test_clean_orphaned_links_does_not_touch_external_broken_symlinks(tmp_path: Path) -> None:
    workspace = tmp_path / "ghosla"
    workspace.mkdir()
    skill_active = workspace / "skills" / "active-skill"
    skill_active.mkdir(parents=True)
    (skill_active / "SKILL.md").write_text("active", encoding="utf-8")

    harness_dir = tmp_path / "harness"
    harness_dir.mkdir()

    # Active link pointing into ghosla
    active_link = harness_dir / "active-skill"
    atomic_symlink(skill_active, active_link)

    # Broken link pointing into ghosla (deleted ghosla skill)
    ghosla_deleted = workspace / "skills" / "deleted-skill"
    ghosla_broken_link = harness_dir / "deleted-skill"
    ghosla_broken_link.symlink_to(ghosla_deleted, target_is_directory=True)

    # External broken link pointing somewhere outside ghosla
    external_deleted = tmp_path / "external_other" / "missing-skill"
    external_broken_link = harness_dir / "external-broken-skill"
    external_broken_link.symlink_to(external_deleted, target_is_directory=True)

    bundle = SkillBundle(
        name="active",
        description="active bundle",
        skills=["active-skill"],
        target_harnesses=[HarnessType.ANTIGRAVITY],
    )

    engine = LinkerEngine(
        workspace_root=workspace,
        harness_paths={HarnessType.ANTIGRAVITY: harness_dir},
    )
    removed = engine.clean_orphaned_links([bundle])

    # Only the ghosla broken link is cleaned; external broken link is preserved untouched!
    assert ghosla_broken_link in removed
    assert not ghosla_broken_link.exists()
    assert not ghosla_broken_link.is_symlink()

    assert external_broken_link not in removed
    assert external_broken_link.is_symlink()

    assert active_link.exists()


def test_resolve_skill_relative_paths(tmp_path: Path) -> None:
    workspace = tmp_path / "ghosla"
    workspace.mkdir()
    unslop_dir = workspace / "upstream" / "pstack" / "skills" / "unslop"
    unslop_dir.mkdir(parents=True)
    (unslop_dir / "SKILL.md").write_text("---\nname: unslop\ndescription: desc\n---\n")

    catalog = {
        "unslop": SkillMetadata(
            name="unslop",
            source_type=SkillSource.UPSTREAM,
            path=unslop_dir,
            frontmatter=SkillFrontmatter(name="unslop", description="desc"),
            byte_size=100,
            estimated_tokens=25,
            has_anti_rationalization=False,
            reference_depth=0,
            upstream_repo="pstack",
        )
    }

    engine = LinkerEngine(workspace_root=workspace)
    resolved = engine.resolve_skill("upstream/pstack/skills/unslop", catalog)
    assert resolved is not None
    assert resolved.name == "unslop"
    assert resolved.path.resolve() == unslop_dir.resolve()


def test_resolve_skill_upstream_collision_disambiguation(tmp_path: Path) -> None:
    workspace = tmp_path / "ghosla"
    workspace.mkdir()

    repo_a_skill = workspace / "upstream" / "repo-a" / "skills" / "tool"
    repo_a_skill.mkdir(parents=True)
    (repo_a_skill / "SKILL.md").write_text("---\nname: tool\ndescription: Tool A\n---\n")

    repo_b_skill = workspace / "upstream" / "repo-b" / "skills" / "tool"
    repo_b_skill.mkdir(parents=True)
    (repo_b_skill / "SKILL.md").write_text("---\nname: tool\ndescription: Tool B\n---\n")

    catalog = {
        "tool": SkillMetadata(
            name="tool",
            source_type=SkillSource.UPSTREAM,
            path=repo_a_skill,
            frontmatter=SkillFrontmatter(name="tool", description="Tool A"),
            byte_size=100,
            estimated_tokens=25,
            has_anti_rationalization=False,
            reference_depth=0,
            upstream_repo="repo-a",
        ),
        "repo-a/tool": SkillMetadata(
            name="tool",
            source_type=SkillSource.UPSTREAM,
            path=repo_a_skill,
            frontmatter=SkillFrontmatter(name="tool", description="Tool A"),
            byte_size=100,
            estimated_tokens=25,
            has_anti_rationalization=False,
            reference_depth=0,
            upstream_repo="repo-a",
        ),
        "repo-b/tool": SkillMetadata(
            name="tool",
            source_type=SkillSource.UPSTREAM,
            path=repo_b_skill,
            frontmatter=SkillFrontmatter(name="tool", description="Tool B"),
            byte_size=100,
            estimated_tokens=25,
            has_anti_rationalization=False,
            reference_depth=0,
            upstream_repo="repo-b",
        ),
    }

    engine = LinkerEngine(workspace_root=workspace)
    assert engine.resolve_skill("repo-a/tool", catalog) is catalog["repo-a/tool"]
    assert engine.resolve_skill("repo-b/tool", catalog) is catalog["repo-b/tool"]

