import re
from pathlib import Path
from typing import Dict, List


def set_harness_status(config_file: Path, harness_name: str, enabled: bool) -> None:
    """Updates the enabled status of a harness in ghosla.toml."""
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file {config_file} not found")

    content = config_file.read_text(encoding="utf-8")
    section_pattern = re.compile(
        rf"(\[harnesses\.{harness_name}\][^\[]*?enabled\s*=\s*)(true|false)",
        re.MULTILINE,
    )

    if section_pattern.search(content):
        new_content = section_pattern.sub(rf"\g<1>{str(enabled).lower()}", content)
    else:
        # Append section if not present
        enabled_str = str(enabled).lower()
        new_content = (
            content.rstrip()
            + f"\n\n[harnesses.{harness_name}]\nenabled = {enabled_str}\n"
            + f"path = \"~/.{harness_name}/skills\"\n"
        )

    config_file.write_text(new_content, encoding="utf-8")


def detect_shadowing(
    workspace_dir: Path,
    harness_dirs: List[Path],
) -> List[Dict[str, str]]:
    """Detects shadowing conflicts between workspace-local skills and global harness skills."""
    conflicts: List[Dict[str, str]] = []
    local_skills_dir = workspace_dir / ".agents" / "skills"
    if not local_skills_dir.exists():
        return conflicts

    local_skills = {
        p.name: p for p in local_skills_dir.iterdir()
        if p.is_dir() and (p / "SKILL.md").exists()
    }

    for h_dir in harness_dirs:
        h_resolved = h_dir.expanduser().resolve()
        if not h_resolved.exists():
            continue

        for p in h_resolved.iterdir():
            if p.is_dir() and (p / "SKILL.md").exists() and p.name in local_skills:
                conflicts.append({
                    "skill_name": p.name,
                    "local_path": str(local_skills[p.name]),
                    "global_path": str(p),
                    "message": (
                        f"Workspace-local skill '{p.name}' in {local_skills[p.name]} "
                        f"shadows global skill in {p}"
                    ),
                })

    return conflicts
