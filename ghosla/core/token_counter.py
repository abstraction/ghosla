import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

CODEX_MAX_BYTES = 8000
CLAUDE_MAX_TOKENS = 5000
SYSTEM_PROMPT_MAX_DESC_CHARS = 1024


def estimate_tokens(text: str) -> int:
    """Calculates a heuristic token estimate (~4 chars per token)."""
    if not text:
        return 0
    # Average across English text is ~4 characters per token
    return max(1, len(text) // 4)


@dataclass
class AuditResult:
    is_valid: bool
    byte_size: int = 0
    line_count: int = 0
    estimated_tokens: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class TokenAuditor:
    @staticmethod
    def audit_skill(skill_dir: Path) -> AuditResult:
        errors: List[str] = []
        warnings: List[str] = []
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            return AuditResult(
                is_valid=False,
                errors=[f"Missing SKILL.md in {skill_dir}"],
            )

        try:
            content_bytes = skill_file.read_bytes()
            content_text = content_bytes.decode("utf-8", errors="replace")
        except Exception as e:
            return AuditResult(
                is_valid=False,
                errors=[f"Could not read {skill_file}: {e}"],
            )

        byte_len = len(content_bytes)
        lines = content_text.splitlines()
        line_count = len(lines)
        est_tokens = estimate_tokens(content_text)

        # 1. Codex Byte Budget Assertion
        if byte_len > CODEX_MAX_BYTES:
            errors.append(
                f"Byte budget exceeded: {byte_len} bytes > {CODEX_MAX_BYTES} byte limit. "
                "Codex will silently truncate this skill."
            )

        # 2. Line Count Recommendation
        if line_count > 500:
            warnings.append(f"Line count high: {line_count} lines > 500 line recommendation.")

        # 3. Structure Check: Load-bearing ordering
        from ghosla.core.frontmatter import parse_frontmatter
        _, body = parse_frontmatter(content_text)
        body_lines = body.splitlines()
        head_text = "\n".join(body_lines[:150]).lower()
        if "workflow" not in head_text and "process" not in head_text:
            warnings.append(
                "Structural warning: No workflow or process section identified in "
                "the first 150 lines."
            )

        # 4. Check for Anti-rationalization table
        if "anti-rationalization" not in content_text.lower():
            warnings.append(
                "Prompt engineering suggestion: No anti-rationalization table detected."
            )

        # 5. Check reference depth (relative links)
        # Markdown link pattern: [anchor](url)
        md_links = re.findall(r"\[.*?\]\((.*?)\)", content_text)
        for link in md_links:
            # Strip anchors #...
            clean_link = link.split("#")[0]
            if clean_link.startswith(("http://", "https://", "file://", "mailto:")):
                continue
            if "../.." in clean_link:
                warnings.append(f"Reference depth > 1 detected in link: {link}")

        is_valid = len(errors) == 0
        return AuditResult(
            is_valid=is_valid,
            byte_size=byte_len,
            line_count=line_count,
            estimated_tokens=est_tokens,
            errors=errors,
            warnings=warnings,
        )
