import shutil
from pathlib import Path
from typing import List, Optional

from ghosla.core.frontmatter import extract_skill_frontmatter, format_frontmatter, parse_frontmatter
from ghosla.core.linker import atomic_symlink
from ghosla.core.models import SkillFrontmatter, SkillMetadata, SkillSource
from ghosla.core.token_counter import estimate_tokens


def scan_intake_skills(intake_dir: Path) -> List[SkillMetadata]:
    """Scans the intake directory for skills."""
    skills: List[SkillMetadata] = []
    if not intake_dir.exists():
        return skills

    for item in sorted(intake_dir.iterdir(), key=lambda p: p.name):
        if not item.is_dir():
            continue
        skill_file = item / "SKILL.md"
        if not skill_file.exists():
            continue

        fm, body, err = extract_skill_frontmatter(skill_file)
        if not fm:
            # Fallback for untracked raw skill without strict frontmatter
            name = item.name.lower().replace("_", "-")
            fm = SkillFrontmatter(
                name=name,
                description=f"Auto-discovered skill from {item.name}",
            )

        content_bytes = skill_file.read_bytes()
        content_text = content_bytes.decode("utf-8", errors="replace")
        meta = SkillMetadata(
            name=fm.name,
            source_type=SkillSource.INBOX,
            path=item,
            frontmatter=fm,
            byte_size=len(content_bytes),
            estimated_tokens=estimate_tokens(content_text),
            has_anti_rationalization="anti-rationalization" in content_text.lower(),
            reference_depth=0,
        )
        skills.append(meta)

    return skills


def bridge_external_skills(
    intake_dir: Path,
    gemini_dir: Path,
    bridge_prefix: str = "",
) -> List[Path]:
    """Bridges external skills from intake into Antigravity (~/.gemini/config/skills)."""
    bridged: List[Path] = []
    gemini_dir.mkdir(parents=True, exist_ok=True)

    skills = scan_intake_skills(intake_dir)
    for skill in skills:
        target_name = f"{bridge_prefix}{skill.name}"
        dest_link = gemini_dir / target_name

        # If dest already exists and points to the same target, skip
        if dest_link.is_symlink():
            try:
                if dest_link.resolve() == skill.path.resolve():
                    continue
            except (FileNotFoundError, RuntimeError):
                pass

        atomic_symlink(skill.path, dest_link)
        bridged.append(dest_link)

    return bridged


def adopt_skill(
    source_path: Path,
    target_atelier_skills: Path,
    target_name: Optional[str] = None,
) -> Path:
    """Copies an external skill into atelier skills/, normalizing frontmatter."""
    resolved_source = source_path.resolve()
    if not resolved_source.exists():
        raise FileNotFoundError(f"Source skill does not exist: {source_path}")

    name = target_name if target_name else resolved_source.name.lower().replace("_", "-")
    target_dir = target_atelier_skills / name
    if target_dir.exists():
        shutil.rmtree(target_dir)

    shutil.copytree(resolved_source, target_dir)

    # Normalize SKILL.md
    skill_file = target_dir / "SKILL.md"
    if skill_file.exists():
        raw_text = skill_file.read_text(encoding="utf-8", errors="replace")
        fm_dict, body = parse_frontmatter(raw_text)
        fm_dict["name"] = name
        if "description" not in fm_dict:
            fm_dict["description"] = f"Adopted skill: {name}"

        # Re-write normalized file
        normalized_content = format_frontmatter(fm_dict) + body.lstrip()
        skill_file.write_text(normalized_content, encoding="utf-8")

    return target_dir
