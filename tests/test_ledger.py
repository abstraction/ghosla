from pathlib import Path

from ghosla.core.ledger import EpistemicLedger


def test_ledger_state_save_and_load(tmp_path: Path) -> None:
    ledger_dir = tmp_path / "ledger"
    ledger = EpistemicLedger(ledger_dir=ledger_dir)

    initial_state = ledger.load_state()
    assert initial_state == {}

    new_state = {"compound-engineering": "7a68002fc", "pstack": "6ce45c59b"}
    ledger.save_state(new_state)

    loaded = ledger.load_state()
    assert loaded["compound-engineering"] == "7a68002fc"
    assert loaded["pstack"] == "6ce45c59b"


def test_ledger_compute_diff_and_record(tmp_path: Path) -> None:
    ledger_dir = tmp_path / "ledger"
    ledger = EpistemicLedger(ledger_dir=ledger_dir)

    # Initial state with old commit
    ledger.save_state({"compound-engineering": "old_commit_123"})

    lock_file = tmp_path / "vendir.lock.yml"
    lock_file.write_text(
        """apiVersion: vendir.k14s.io/v1alpha1
kind: LockConfig
directories:
- path: upstream/compound-engineering
  contents:
  - git:
      sha: new_commit_456
      commitTitle: "feat: add new review skill"
""",
        encoding="utf-8",
    )

    upstream_repo_dir = tmp_path / "upstream" / "compound-engineering"
    upstream_repo_dir.mkdir(parents=True)
    # Add a skill
    skill_dir = upstream_repo_dir / "skills" / "new-review-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: new-review-skill\ndescription: A new review tool\n---\n# Workflow\n",
        encoding="utf-8",
    )

    diffs = ledger.compute_diff(lock_file, tmp_path / "upstream")
    assert len(diffs) == 1
    diff = diffs[0]
    assert diff.repo_name == "compound-engineering"
    assert diff.old_commit == "old_commit_123"
    assert diff.new_commit == "new_commit_456"

    report_path = ledger.record_diff_report(diff)
    assert report_path.exists()
    assert report_path.suffix == ".md"
    content = report_path.read_text(encoding="utf-8")
    assert "compound-engineering" in content
    assert "old_commit_123" in content
    assert "new_commit_456" in content


def test_ledger_detects_forked_skills_and_preserves_untouched(tmp_path: Path) -> None:
    ledger_dir = tmp_path / "ledger"
    ledger = EpistemicLedger(ledger_dir=ledger_dir)

    # Old state for github-copilot-community
    ledger.save_state({"github-copilot-community": "commit_aaa"})

    lock_file = tmp_path / "vendir.lock.yml"
    lock_file.write_text(
        """apiVersion: vendir.k14s.io/v1alpha1
kind: LockConfig
directories:
- path: upstream/github-copilot-community
  contents:
  - git:
      sha: commit_bbb
      commitTitle: "chore: upstream release"
""",
        encoding="utf-8",
    )

    upstream_repo_dir = tmp_path / "upstream" / "github-copilot-community"
    upstream_skill_dir = upstream_repo_dir / "git-commit"
    upstream_skill_dir.mkdir(parents=True)
    (upstream_skill_dir / "SKILL.md").write_text(
        "---\nname: git-commit\ndescription: Upstream tool\n---\n# Upstream\n",
        encoding="utf-8",
    )

    # Local fork in skills/
    skills_dir = tmp_path / "skills"
    local_fork_dir = skills_dir / "git-commit"
    local_fork_dir.mkdir(parents=True)
    initial_fork_content = """---
name: git-commit
description: Local custom git-commit
metadata:
  upstream_source: github-copilot-community/git-commit
  fork: true
---
# Custom Local Workflow
"""
    fork_file = local_fork_dir / "SKILL.md"
    fork_file.write_text(initial_fork_content, encoding="utf-8")

    diffs = ledger.compute_diff(lock_file, tmp_path / "upstream", skills_dir=skills_dir)
    assert len(diffs) == 1
    diff = diffs[0]
    assert diff.repo_name == "github-copilot-community"
    assert len(diff.forked_skills) == 1

    fork_info = diff.forked_skills[0]
    assert fork_info["name"] == "git-commit"
    assert fork_info["upstream_source"] == "github-copilot-community/git-commit"
    assert fork_info["status"] == "preserved_untouched"

    # Assert local fork was not modified
    assert fork_file.read_text(encoding="utf-8") == initial_fork_content

    # Assert diff report documents preserved status
    report_file = ledger.record_diff_report(diff)
    report_content = report_file.read_text(encoding="utf-8")
    assert "Local Forks Affected (Preserved Untouched)" in report_content
    assert "git-commit" in report_content
    assert "Preserved untouched for manual review" in report_content


def test_ledger_detects_fork_with_url_upstream_source(tmp_path: Path) -> None:
    ledger_dir = tmp_path / "ledger"
    ledger = EpistemicLedger(ledger_dir=ledger_dir)
    ledger.save_state({"github-copilot-community": "commit_old"})

    lock_file = tmp_path / "vendir.lock.yml"
    lock_file.write_text(
        """apiVersion: vendir.k14s.io/v1alpha1
kind: LockConfig
directories:
- path: upstream/github-copilot-community
  contents:
  - git:
      sha: commit_new
      commitTitle: "update: sync awesome-copilot"
""",
        encoding="utf-8",
    )

    upstream_repo_dir = tmp_path / "upstream" / "github-copilot-community"
    upstream_skill_dir = upstream_repo_dir / "skills" / "git-commit"
    upstream_skill_dir.mkdir(parents=True)
    (upstream_skill_dir / "SKILL.md").write_text("---\nname: git-commit\ndescription: tool\n---\n")

    # Local fork using full GitHub URL in metadata.upstream_source
    skills_dir = tmp_path / "skills"
    local_fork_dir = skills_dir / "git-commit"
    local_fork_dir.mkdir(parents=True)
    (local_fork_dir / "SKILL.md").write_text(
        """---
name: git-commit
description: Local custom git-commit
metadata:
  upstream_source: "https://github.com/github/awesome-copilot/blob/main/skills/git-commit/SKILL.md"
  fork: true
---
# Custom
""",
        encoding="utf-8",
    )

    diffs = ledger.compute_diff(lock_file, tmp_path / "upstream", skills_dir=skills_dir)
    assert len(diffs) == 1
    assert len(diffs[0].forked_skills) == 1
    fork = diffs[0].forked_skills[0]
    assert fork["name"] == "git-commit"
    assert fork["status"] == "preserved_untouched"
    assert fork["upstream_path"] == str(upstream_skill_dir)


def test_ledger_clean_checkpoint_after_save(tmp_path: Path) -> None:
    ledger_dir = tmp_path / "ledger"
    ledger = EpistemicLedger(ledger_dir=ledger_dir)

    lock_file = tmp_path / "vendir.lock.yml"
    lock_file.write_text(
        """apiVersion: vendir.k14s.io/v1alpha1
kind: LockConfig
directories:
- path: upstream/pstack
  contents:
  - git:
      sha: sha_abc_123
""",
        encoding="utf-8",
    )

    # Before saving state, diff is detected
    diffs = ledger.compute_diff(lock_file, tmp_path / "upstream")
    assert len(diffs) == 1
    assert diffs[0].new_commit == "sha_abc_123"

    # After saving checkpoint state with the new sha
    ledger.save_state({"pstack": "sha_abc_123"})
    diffs_after = ledger.compute_diff(lock_file, tmp_path / "upstream")
    assert len(diffs_after) == 0

