import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import yaml
from pydantic import ValidationError

from ghosla.core.models import SkillFrontmatter

FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


def parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """Extracts YAML frontmatter dict and remaining markdown content."""
    match = FRONTMATTER_PATTERN.match(content)
    if not match:
        return {}, content

    yaml_text = match.group(1)
    body = content[match.end():]
    try:
        data = yaml.safe_load(yaml_text)
        if isinstance(data, dict):
            return data, body
        return {}, body
    except yaml.YAMLError:
        return {}, content


def extract_skill_frontmatter(
    skill_md_path: Path,
) -> Tuple[Optional[SkillFrontmatter], str, Optional[str]]:
    """Extracts and validates SkillFrontmatter from a SKILL.md file."""
    if not skill_md_path.exists():
        return None, "", f"File does not exist: {skill_md_path}"

    try:
        content = skill_md_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return None, "", f"Error reading {skill_md_path}: {e}"

    data, body = parse_frontmatter(content)
    if not data:
        return None, body, f"No valid YAML frontmatter found in {skill_md_path}"

    try:
        fm = SkillFrontmatter(**data)
        return fm, body, None
    except ValidationError as e:
        error_msgs = "; ".join(f"{err['loc']}: {err['msg']}" for err in e.errors())
        return None, body, f"Frontmatter schema validation error: {error_msgs}"


def format_frontmatter(metadata: Dict[str, Any]) -> str:
    """Formats a dict into YAML frontmatter string."""
    dumped = yaml.safe_dump(metadata, sort_keys=False, default_flow_style=False)
    return f"---\n{dumped}---\n"
