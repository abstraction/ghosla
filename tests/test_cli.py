import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from ghosla.cli import cli
from ghosla.core.ledger import EpistemicLedger


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_cli_help(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "audit" in result.output
    assert "bundle" in result.output
    assert "status" in result.output
    assert "vendor" in result.output


def test_cli_status_json(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["status", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "active_bundle" in data
    assert "harnesses" in data


def test_cli_bundle_list_and_switch(runner: CliRunner) -> None:
    res = runner.invoke(cli, ["bundle", "list", "--json"])
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert any(b["name"] == "baseline" for b in data)

    switch_res = runner.invoke(cli, ["bundle", "switch", "full-stack"])
    assert switch_res.exit_code == 0
    assert "Switched active bundle to 'full-stack'" in switch_res.output

    # Switch back to baseline
    runner.invoke(cli, ["bundle", "switch", "baseline"])


def test_cli_harness_list_and_toggle(runner: CliRunner) -> None:
    res = runner.invoke(cli, ["harness", "list", "--json"])
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert "antigravity" in data
    assert data["antigravity"]["enabled"] is True

    # Toggle claude_code
    enable_res = runner.invoke(cli, ["harness", "enable", "claude_code"])
    assert enable_res.exit_code == 0
    assert "Enabled harness claude_code" in enable_res.output

    disable_res = runner.invoke(cli, ["harness", "disable", "claude_code"])
    assert disable_res.exit_code == 0
    assert "Disabled harness claude_code" in disable_res.output


def test_cli_audit(runner: CliRunner) -> None:
    res = runner.invoke(cli, ["audit", "--json"])
    # Exit code is 0 if all valid or 3 if budget exceeded
    assert res.exit_code in (0, 3)
    data = json.loads(res.output)
    assert "skills" in data
    assert "summary" in data


def test_cli_clip(runner: CliRunner) -> None:
    res = runner.invoke(
        cli,
        ["clip", "Some awesome prompt instructions here", "--name", "test-prompt"],
    )
    assert res.exit_code == 0
    assert "Clipped to" in res.output
    clip_path = Path("inbox/clippings/test-prompt.md")
    assert clip_path.exists()
    content = clip_path.read_text(encoding="utf-8")
    assert "Some awesome prompt instructions here" in content
    clip_path.unlink()


def test_cli_diff_detects_forked_skills(runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    # Ensure pending diffs are detected deterministically
    monkeypatch.setattr(EpistemicLedger, "load_state", lambda self: {})
    res = runner.invoke(cli, ["diff", "--json"])
    assert res.exit_code == 2
    diffs = json.loads(res.output)
    gh_copilot_diff = next(
        (d for d in diffs if d["repo"] == "github-copilot-community"), None
    )
    assert gh_copilot_diff is not None
    assert "forked_skills" in gh_copilot_diff
    fork_names = [f["name"] for f in gh_copilot_diff["forked_skills"]]
    assert "git-commit" in fork_names
    fork = next(f for f in gh_copilot_diff["forked_skills"] if f["name"] == "git-commit")
    assert fork["status"] == "preserved_untouched"
    assert "github-copilot-community/git-commit" in fork["upstream_source"]


def test_cli_diff_clean_state(runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    # When state matches lockfile, diff reports clean
    import yaml
    lock_file = Path("vendir.lock.yml")
    if lock_file.exists():
        lock_data = yaml.safe_load(lock_file.read_text(encoding="utf-8"))
        current_shas = {
            Path(e["path"]).name: e["contents"][0]["git"]["sha"]
            for e in lock_data.get("directories", [])
        }
        monkeypatch.setattr(EpistemicLedger, "load_state", lambda self: current_shas)
        res = runner.invoke(cli, ["diff"])
        assert res.exit_code == 0
        assert "clean" in res.output.lower()


def test_cli_link_resolves_unslop_from_upstream(runner: CliRunner) -> None:
    res = runner.invoke(cli, ["link"])
    assert res.exit_code == 0
    assert "Linked" in res.output


def test_cli_audit_verbose_flag(runner: CliRunner) -> None:
    res = runner.invoke(cli, ["audit", "-v"])
    assert res.exit_code in (0, 3)
    assert "Auditing" in res.output


def test_cli_pointed_error_on_unknown_bundle(runner: CliRunner) -> None:
    res = runner.invoke(cli, ["bundle", "switch", "does-not-exist"])
    assert res.exit_code == 1
    assert "Error:" in res.output
    assert "[bundles/]" in res.output
    assert "Traceback" not in res.output


