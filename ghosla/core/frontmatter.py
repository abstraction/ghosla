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
    """Extracts and validates SkillFrontmatter from a SKILL.md file with pointed errors."""
    if not skill_md_path.exists():
        return None, "", f"File does not exist: {skill_md_path}"

    try:
        content = skill_md_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return None, "", f"Error reading {skill_md_path}: {e}"

    match = FRONTMATTER_PATTERN.match(content)
    if not match:
        return None, content, f"No valid YAML frontmatter found in {skill_md_path}"

    yaml_text = match.group(1)
    body = content[match.end():]

    try:
        data = yaml.safe_load(yaml_text)
    except yaml.MarkedYAMLError as e:
        line = (e.problem_mark.line + 2) if e.problem_mark else 1
        col = (e.problem_mark.column + 1) if e.problem_mark else 1
        return None, body, f"YAML syntax error at {skill_md_path}:{line}:{col}: {e.problem}"
    except yaml.YAMLError as e:
        return None, body, f"YAML parsing error in {skill_md_path}: {e}"

    if not isinstance(data, dict):
        return None, body, f"No valid YAML frontmatter found in {skill_md_path}"

    try:
        fm = SkillFrontmatter(**data)
        return fm, body, None
    except ValidationError as e:
        err_items = []
        for err in e.errors():
            loc_tag = ".".join(str(part) for part in err["loc"])
            err_items.append(f"{loc_tag}: {err['msg']}")
        return None, body, f"Frontmatter schema validation error: {'; '.join(err_items)}"



def format_frontmatter(metadata: Dict[str, Any]) -> str:
    """Formats a dict into YAML frontmatter string."""
    dumped = yaml.safe_dump(metadata, sort_keys=False, default_flow_style=False)
    return f"---\n{dumped}---\n"
