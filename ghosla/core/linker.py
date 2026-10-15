import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Set

from ghosla.core.models import (
    HarnessConfig,
    HarnessType,
    SkillBundle,
    SkillMetadata,
)

DEFAULT_HARNESS_PATHS: Dict[HarnessType, Path] = {
    HarnessType.AGENTS_GLOBAL: Path.home() / ".agents" / "skills",
    HarnessType.ANTIGRAVITY: Path.home() / ".gemini" / "config" / "skills",
    HarnessType.CLAUDE_CODE: Path.home() / ".claude" / "skills",
    HarnessType.CODEX: Path.home() / ".codex" / "skills",
    HarnessType.CURSOR: Path.home() / ".cursor" / "skills",
}


def atomic_symlink(source: Path, target: Path) -> None:
    """Atomically creates or updates a symlink using os.replace."""
    target_parent = target.parent
    target_parent.mkdir(parents=True, exist_ok=True)

    tmp_link = target_parent / f".tmp_{target.name}_{os.getpid()}"
    try:
        if tmp_link.is_symlink() or tmp_link.exists():
            if tmp_link.is_dir() and not tmp_link.is_symlink():
                shutil.rmtree(tmp_link)
            else:
                tmp_link.unlink()

        resolved_source = source.resolve()
        is_dir = resolved_source.is_dir()
        tmp_link.symlink_to(resolved_source, target_is_directory=is_dir)

        if target.exists() and target.is_dir() and not target.is_symlink():
            backup = target_parent / f".bak_{target.name}_{os.getpid()}"
            os.replace(target, backup)
            try:
                os.replace(tmp_link, target)
                shutil.rmtree(backup)
            except Exception:
                os.replace(backup, target)
                raise
        else:
            os.replace(tmp_link, target)
    except Exception:
        if tmp_link.is_symlink() or tmp_link.exists():
            if tmp_link.is_dir() and not tmp_link.is_symlink():
                shutil.rmtree(tmp_link)
            else:
                tmp_link.unlink()
        raise


class LinkerEngine:
    def __init__(
        self,
        workspace_root: Path,
        harness_paths: Optional[Dict[HarnessType, Path]] = None,
    ):
        self.root = workspace_root.resolve()
        self.harness_paths = harness_paths if harness_paths is not None else DEFAULT_HARNESS_PATHS

    def resolve_skill(
        self,
        skill_ref: str,
        catalog: Dict[str, SkillMetadata],
    ) -> Optional[SkillMetadata]:
        """Resolves a skill reference from catalog by name, relative path, or upstream prefix."""
        # 1. Exact name match in catalog
        if skill_ref in catalog:
            return catalog[skill_ref]

        normalized_ref = skill_ref.strip("/")
        root_resolved = self.root.resolve()

        # 2. Match by path relative to workspace root (e.g. upstream/pstack/skills/unslop)
        for skill in catalog.values():
            try:
                rel = str(skill.path.resolve().relative_to(root_resolved))
                if rel == normalized_ref:
                    return skill
            except ValueError:
                pass

        # 3. Match by upstream repo prefix (e.g. pstack/skills/unslop or pstack/unslop)
        for skill in catalog.values():
            repo = skill.upstream_repo
            if repo:
                repo_prefix = repo.split("/")[0] if "/" in repo else repo
                for prefix in (repo, repo_prefix):
                    if normalized_ref.startswith(f"{prefix}/"):
                        remainder = normalized_ref[len(prefix) + 1:].strip("/")
                        if remainder in (skill.name, f"skills/{skill.name}"):
                            return skill
                        try:
                            rel_to_repo = str(
                                skill.path.resolve().relative_to(
                                    (root_resolved / "upstream" / prefix).resolve()
                                )
                            )
                            if remainder == rel_to_repo:
                                return skill
                        except ValueError:
                            pass

        # 4. Fallback: match by basename if unique
        base_name = Path(normalized_ref).name
        candidates = [s for s in catalog.values() if s.name == base_name]
        unique_skills = {s.path.resolve(): s for s in candidates}
        if len(unique_skills) == 1:
            return list(unique_skills.values())[0]

        return None

    def link_bundle(
        self,
        bundle: SkillBundle,
        catalog: Dict[str, SkillMetadata],
        harnesses_config: Optional[Dict[HarnessType, HarnessConfig]] = None,
    ) -> List[Path]:
        """Atomically links all skills in bundle to enabled target harnesses."""
        created_links: List[Path] = []
        for harness in bundle.target_harnesses:
            if harnesses_config is not None:
                h_cfg = harnesses_config.get(harness)
                if not h_cfg or not h_cfg.enabled:
                    continue

            target_dir = self.harness_paths.get(harness)
            if not target_dir:
                continue

            target_dir = target_dir.expanduser().resolve()
            target_dir.mkdir(parents=True, exist_ok=True)

            for skill_name in bundle.skills:
                skill = self.resolve_skill(skill_name, catalog)
                if not skill:
                    msg = (
                        f"Skill '{skill_name}' declared in bundle '{bundle.name}' "
                        "not found in catalog"
                    )
                    raise KeyError(msg)

                dest_link = target_dir / skill.name
                atomic_symlink(skill.path, dest_link)
                created_links.append(dest_link)

        return created_links

    def clean_orphaned_links(
        self,
        active_bundles: List[SkillBundle],
        catalog: Optional[Dict[str, SkillMetadata]] = None,
    ) -> List[Path]:
        """Scans harness dirs and removes symlinks pointing into ghosla that are inactive."""
        removed: List[Path] = []
        active_skill_names: Set[str] = set()
        for b in active_bundles:
            for s in b.skills:
                skill = self.resolve_skill(s, catalog) if catalog else None
                if skill:
                    active_skill_names.add(skill.name)
                else:
                    active_skill_names.add(Path(s).name)

        root_resolved = self.root.resolve()

        for harness_dir in self.harness_paths.values():
            h_resolved = harness_dir.expanduser().resolve()
            if not h_resolved.exists():
                continue

            for item in h_resolved.iterdir():
                if item.is_symlink():
                    try:
                        resolved = item.resolve()
                        if (
                            root_resolved in resolved.parents
                            and item.name not in active_skill_names
                        ):
                            item.unlink()
                            removed.append(item)
                    except (FileNotFoundError, RuntimeError):
                        # Broken symlink - remove ONLY if it pointed into ghosla workspace
                        try:
                            raw_target = os.readlink(item)
                            target_path = Path(raw_target)
                            if not target_path.is_absolute():
                                target_path = (h_resolved / target_path).resolve()
                            else:
                                target_path = target_path.resolve()
                            if (
                                root_resolved in target_path.parents
                                or target_path == root_resolved
                            ):
                                item.unlink()
                                removed.append(item)
                        except Exception:
                            pass

        return removed
