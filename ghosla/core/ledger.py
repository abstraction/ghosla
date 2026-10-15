import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


@dataclass
class DiffSummary:
    repo_name: str
    old_commit: Optional[str]
    new_commit: str
    commit_title: Optional[str] = None
    new_skills: List[str] = field(default_factory=list)
    modified_skills: List[Dict[str, Any]] = field(default_factory=list)
    deprecated_skills: List[str] = field(default_factory=list)
    forked_skills: List[Dict[str, Any]] = field(default_factory=list)


class EpistemicLedger:
    def __init__(self, ledger_dir: Path):
        self.ledger_dir = ledger_dir
        self.state_file = ledger_dir / "state.json"
        self.diffs_dir = ledger_dir / "diffs"

    def load_state(self) -> Dict[str, str]:
        """Loads repository commit state mapping {repo_name: commit_sha}."""
        if not self.state_file.exists():
            return {}
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def save_state(self, state: Dict[str, str]) -> None:
        """Saves repository commit state."""
        self.ledger_dir.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

    def compute_diff(
        self,
        vendir_lock_path: Path,
        upstream_dir: Path,
        skills_dir: Optional[Path] = None,
    ) -> List[DiffSummary]:
        """Compares current vendir.lock.yml against state.json."""
        if not vendir_lock_path.exists():
            return []

        with open(vendir_lock_path, "r", encoding="utf-8") as f:
            lock_data = yaml.safe_load(f)

        if not isinstance(lock_data, dict) or "directories" not in lock_data:
            return []

        # Discover any local forks in skills/
        local_forks: List[Dict[str, Any]] = []
        if skills_dir and skills_dir.exists():
            from ghosla.core.frontmatter import extract_skill_frontmatter

            for skill_md in sorted(skills_dir.rglob("SKILL.md")):
                fm, _, _ = extract_skill_frontmatter(skill_md)
                if fm and fm.is_fork:
                    upstream_source = str(fm.upstream_source or "")
                    local_forks.append({
                        "name": fm.name,
                        "path": skill_md.parent,
                        "upstream_source": upstream_source,
                    })

        current_state = self.load_state()
        diffs: List[DiffSummary] = []

        for entry in lock_data.get("directories", []):
            path_str = entry.get("path", "")
            # path is typically upstream/<repo_name>
            repo_name = Path(path_str).name
            contents = entry.get("contents", [])
            if not contents:
                continue

            git_info = contents[0].get("git", {})
            new_sha = git_info.get("sha", "")
            commit_title = git_info.get("commitTitle", "")

            old_sha = current_state.get(repo_name)
            if old_sha != new_sha:
                # Discovered an update
                repo_upstream_path = upstream_dir / repo_name
                new_skills: List[str] = []
                if repo_upstream_path.exists():
                    for skill_md in repo_upstream_path.rglob("SKILL.md"):
                        new_skills.append(skill_md.parent.name)

                # Check if any local forks originated from this repo
                forked_affected: List[Dict[str, Any]] = []
                for lf in local_forks:
                    up_src = lf["upstream_source"]

                    # Normalize upstream source reference
                    cleaned_src = up_src
                    if cleaned_src.startswith("upstream/"):
                        cleaned_src = cleaned_src[len("upstream/"):]

                    source_repo = (
                        cleaned_src.split("/")[0] if "/" in cleaned_src else cleaned_src
                    )

                    matches = (
                        source_repo == repo_name
                        or cleaned_src == repo_name
                        or cleaned_src.startswith(f"{repo_name}/")
                    )

                    # URL fallback matching (e.g. https://github.com/github/awesome-copilot/...)
                    if not matches and (
                        "github.com/" in up_src or "http://" in up_src or "https://" in up_src
                    ):
                        if repo_name in up_src:
                            matches = True
                        elif (
                            "awesome-copilot" in up_src
                            and repo_name == "github-copilot-community"
                        ):
                            matches = True
                        elif (
                            "compound-engineering" in up_src
                            and repo_name == "compound-engineering"
                        ):
                            matches = True
                        elif "cursor" in up_src and "plugins" in up_src and repo_name == "pstack":
                            matches = True

                    if matches:
                        cand_upstream_dir = upstream_dir / repo_name
                        cand_skill_dir: Optional[Path] = None

                        if "/blob/" in up_src:
                            blob_parts = up_src.split("/blob/")[-1].split("/")
                            skill_parts = [
                                p for p in blob_parts[1:] if p and p != "SKILL.md"
                            ]
                            upstream_skill_rel = "/".join(skill_parts)
                        elif "/" in cleaned_src:
                            upstream_skill_rel = cleaned_src[len(source_repo) + 1:].strip("/")
                        else:
                            upstream_skill_rel = lf["name"]

                        if (cand_upstream_dir / upstream_skill_rel / "SKILL.md").exists():
                            cand_skill_dir = cand_upstream_dir / upstream_skill_rel
                        elif (
                            cand_upstream_dir / "skills" / upstream_skill_rel / "SKILL.md"
                        ).exists():
                            cand_skill_dir = cand_upstream_dir / "skills" / upstream_skill_rel
                        elif (cand_upstream_dir / lf["name"] / "SKILL.md").exists():
                            cand_skill_dir = cand_upstream_dir / lf["name"]
                        else:
                            for cand in cand_upstream_dir.rglob("SKILL.md"):
                                if cand.parent.name in (lf["name"], Path(upstream_skill_rel).name):
                                    cand_skill_dir = cand.parent
                                    break

                        forked_affected.append({
                            "name": lf["name"],
                            "local_path": str(lf["path"]),
                            "upstream_source": up_src,
                            "upstream_path": str(cand_skill_dir) if cand_skill_dir else None,
                            "status": "preserved_untouched",
                        })

                diffs.append(
                    DiffSummary(
                        repo_name=repo_name,
                        old_commit=old_sha,
                        new_commit=new_sha,
                        commit_title=commit_title,
                        new_skills=new_skills,
                        forked_skills=forked_affected,
                    )
                )

        return diffs

    def record_diff_report(self, diff: DiffSummary) -> Path:
        """Emits a structured markdown diff summary into ledger/diffs/."""
        self.diffs_dir.mkdir(parents=True, exist_ok=True)
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        report_file = self.diffs_dir / f"{date_str}-{diff.repo_name}.md"

        skills_list = "\n".join(f"- `{s}`" for s in diff.new_skills) if diff.new_skills else "None"

        forks_section = ""
        if diff.forked_skills:
            forks_lines = []
            for f in diff.forked_skills:
                forks_lines.append(
                    f"- `{f['name']}` (upstream: `{f['upstream_source']}`)\n"
                    f"  - **Local Path:** `{f['local_path']}`\n"
                    f"  - **Status:** Preserved untouched for manual review\n"
                    f"  - **Upstream Path:** `{f.get('upstream_path') or 'N/A'}`"
                )
            joined_forks = "\n".join(forks_lines)
            forks_section = f"\n## Local Forks Affected (Preserved Untouched)\n{joined_forks}\n"

        content = f"""# Epistemic Diff: {diff.repo_name}
**Date:** {date_str}
**Previous Checkpoint:** `{diff.old_commit or 'initial'}`
**New Checkpoint:** `{diff.new_commit}`
**Commit Title:** {diff.commit_title or 'N/A'}

## Active Skills Discovered
{skills_list}
{forks_section}
## Judgment & Review Checklist
- [ ] Review any modified core workflows or anti-rationalization patterns.
- [ ] Verify byte limits (< 8,000 bytes) for Codex compatibility.
- [ ] Check for potential name collisions against local atelier skills.
- [ ] Inspect upstream diffs against local forks before manually merging changes.
"""
        report_file.write_text(content, encoding="utf-8")
        return report_file
