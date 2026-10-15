import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, NoReturn, Optional, Set

import click
import yaml
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

from ghosla.core.frontmatter import extract_skill_frontmatter
from ghosla.core.ledger import EpistemicLedger
from ghosla.core.linker import DEFAULT_HARNESS_PATHS, LinkerEngine
from ghosla.core.models import (
    GhoslaConfig,
    HarnessType,
    SkillBundle,
    SkillFrontmatter,
    SkillMetadata,
    SkillSource,
)
from ghosla.core.token_counter import TokenAuditor, estimate_tokens
from ghosla.core.vendor import compile_sources, run_vendir_sync
from ghosla.integrations.harness import detect_shadowing, set_harness_status
from ghosla.integrations.intake import adopt_skill, bridge_external_skills, scan_intake_skills
from ghosla.integrations.obsidian import ObsidianLumaExporter

console = Console()


def exit_with_pointed_error(
    message: str, location: Optional[str] = None, code: int = 1
) -> NoReturn:
    """Outputs a single-line pointed error message to save tokens and exits cleanly."""
    loc_prefix = f"[{location}] " if location else ""
    console.print(f"[bold red]Error:[/bold red] {escape(loc_prefix)}{escape(message.strip())}")
    sys.exit(code)



class PointedGroup(click.Group):
    """Custom Click Group that captures uncaught exceptions and prints pointed errors."""

    def invoke(self, ctx: click.Context) -> Any:
        try:
            return super().invoke(ctx)
        except (click.ClickException, SystemExit):
            raise
        except Exception as exc:
            if os.environ.get("GHOSLA_DEBUG") == "1":
                raise
            err_name = type(exc).__name__
            exit_with_pointed_error(str(exc), location=err_name)


def find_workspace_root() -> Path:
    """Finds the ghosla workspace root containing ghosla.toml."""
    cur = Path.cwd().resolve()
    for parent in [cur] + list(cur.parents):
        if (parent / "ghosla.toml").exists():
            return parent
    return cur


def load_atelier_config(workspace_root: Path) -> GhoslaConfig:
    config_file = workspace_root / "ghosla.toml"
    if not config_file.exists():
        return GhoslaConfig(active_bundle="baseline", harnesses={})
    return GhoslaConfig.from_toml_file(config_file)


def load_bundles(workspace_root: Path) -> Dict[str, SkillBundle]:
    bundles_dir = workspace_root / "bundles"
    bundles: Dict[str, SkillBundle] = {}
    if not bundles_dir.exists():
        return bundles

    for f in bundles_dir.glob("*.yaml"):
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = yaml.safe_load(fp)
            if isinstance(data, dict):
                bundles[data["name"]] = SkillBundle(**data)
        except Exception:
            continue
    return bundles


def get_catalog(workspace_root: Path, include_upstream: bool = True) -> Dict[str, SkillMetadata]:
    catalog: Dict[str, SkillMetadata] = {}
    root = workspace_root.resolve()

    # 1. Local atelier skills
    local_skills_dir = root / "skills"
    if local_skills_dir.exists():
        for skill_file in sorted(local_skills_dir.rglob("SKILL.md")):
            skill_dir = skill_file.parent
            fm, body, _ = extract_skill_frontmatter(skill_file)
            if not fm:
                try:
                    clean_name = "".join(
                        c if c.isalnum() or c == "-" else "-" for c in skill_dir.name.lower()
                    )
                    fm = SkillFrontmatter(name=clean_name, description=f"Skill {clean_name}")
                except Exception:
                    continue

            name = fm.name
            content_bytes = skill_file.read_bytes()
            content_text = content_bytes.decode("utf-8", errors="replace")
            is_fork = bool(fm and fm.is_fork)
            source_type = SkillSource.FORK if is_fork else SkillSource.LOCAL
            upstream_source = fm.upstream_source if fm else None

            meta = SkillMetadata(
                name=name,
                source_type=source_type,
                path=skill_dir,
                frontmatter=fm,
                byte_size=len(content_bytes),
                estimated_tokens=estimate_tokens(content_text),
                has_anti_rationalization="anti-rationalization" in content_text.lower(),
                reference_depth=0,
                upstream_repo=upstream_source,
                upstream_source=upstream_source,
            )
            catalog[name] = meta
            rel_parts = skill_dir.relative_to(local_skills_dir).parts
            if len(rel_parts) > 1:
                category = rel_parts[0]
                catalog[f"{category}/{name}"] = meta
            if is_fork and upstream_source:
                catalog[f"local/{name}"] = meta

    # 2. Upstream skills
    if include_upstream:
        upstream_dir = root / "upstream"
        if upstream_dir.exists():
            for skill_file in sorted(upstream_dir.rglob("SKILL.md")):
                skill_dir = skill_file.parent
                fm, body, _ = extract_skill_frontmatter(skill_file)
                name = fm.name if fm else skill_dir.name
                if not fm:
                    continue

                content_bytes = skill_file.read_bytes()
                content_text = content_bytes.decode("utf-8", errors="replace")
                repo_name = skill_dir.relative_to(upstream_dir).parts[0]
                rel_to_repo = str(skill_dir.relative_to(upstream_dir / repo_name))

                meta = SkillMetadata(
                    name=name,
                    source_type=SkillSource.UPSTREAM,
                    path=skill_dir,
                    frontmatter=fm,
                    byte_size=len(content_bytes),
                    estimated_tokens=estimate_tokens(content_text),
                    has_anti_rationalization="anti-rationalization" in content_text.lower(),
                    reference_depth=0,
                    upstream_repo=repo_name,
                    upstream_source=f"{repo_name}/{rel_to_repo}",
                )

                # Always register namespaced references
                catalog[f"{repo_name}/{name}"] = meta
                if rel_to_repo != name:
                    catalog[f"{repo_name}/{rel_to_repo}"] = meta
                catalog[f"upstream/{repo_name}/{rel_to_repo}"] = meta

                # Register bare name if not already claimed by a local skill
                # or a previously registered upstream candidate
                if name not in catalog:
                    catalog[name] = meta

    return catalog


@click.group(cls=PointedGroup)
def cli() -> None:
    """Ghosla: Atelier for Agent Instructions and Skills."""
    pass


@cli.command("status")
@click.option("--json", "as_json", is_flag=True, help="Output machine-readable JSON")
def status_cmd(as_json: bool) -> None:
    """Display active links, workspace shadowing status, and health matrix."""
    root = find_workspace_root()
    cfg = load_atelier_config(root)
    bundles = load_bundles(root)
    active_bundle = bundles.get(cfg.active_bundle)

    # Check upstream repos
    upstream_dir = root / "upstream"
    upstream_repos = (
        [p.name for p in upstream_dir.iterdir() if p.is_dir()]
        if upstream_dir.exists()
        else []
    )

    # Check harnesses projection status
    harness_status: Dict[str, Dict[str, Any]] = {}
    active_skills_count = len(active_bundle.skills) if active_bundle else 0

    for h_type, default_path in DEFAULT_HARNESS_PATHS.items():
        h_cfg = cfg.harnesses.get(h_type)
        enabled = h_cfg.enabled if h_cfg else False
        p = (h_cfg.path if h_cfg else default_path).expanduser().resolve()
        linked = 0
        broken = 0
        if p.exists():
            for item in p.iterdir():
                if item.is_symlink():
                    try:
                        resolved = item.resolve()
                        if root in resolved.parents:
                            linked += 1
                    except (FileNotFoundError, RuntimeError):
                        try:
                            raw_target = os.readlink(item)
                            target_path = Path(raw_target)
                            if not target_path.is_absolute():
                                target_path = (p / target_path).resolve()
                            else:
                                target_path = target_path.resolve()
                            if root in target_path.parents or target_path == root:
                                broken += 1
                        except Exception:
                            pass

        harness_status[h_type.value] = {
            "enabled": enabled,
            "path": str(p),
            "linked": linked,
            "broken": broken,
            "target_total": active_skills_count if enabled else 0,
        }

    # Shadowing checks
    harness_dirs = [p.expanduser().resolve() for p in DEFAULT_HARNESS_PATHS.values()]
    shadowing_warnings = detect_shadowing(root, harness_dirs)

    if as_json:
        click.echo(json.dumps({
            "active_bundle": cfg.active_bundle,
            "upstream_repositories": upstream_repos,
            "harnesses": harness_status,
            "shadowing": shadowing_warnings,
        }, indent=2))
        return

    # Visual Output
    if len(upstream_repos) <= 4:
        repos_desc = f"{len(upstream_repos)} upstream tracked ({', '.join(upstream_repos)})"
    else:
        first_repos = ", ".join(upstream_repos[:4])
        more_count = len(upstream_repos) - 4
        repos_desc = f"{len(upstream_repos)} upstream tracked ({first_repos}, +{more_count} more)"

    panel_text = (
        f"Active Profile: [bold cyan]{cfg.active_bundle}[/bold cyan] "
        f"({active_skills_count} skills)\n"
        f"Repositories: [bold green]{repos_desc}[/bold green]"
    )
    console.print(Panel(panel_text, title="Ghosla Atelier Status", expand=False))

    console.print("[bold]Harness Projections:[/bold]")
    for h_name, h_info in harness_status.items():
        status_mark = "✓" if h_info["enabled"] else "○"
        status_color = "green" if h_info["enabled"] else "dim"
        console.print(
            f"  [{status_color}]{status_mark} {h_info['path']}[/{status_color}]: "
            f"{h_info['linked']}/{h_info['target_total']} linked ({h_info['broken']} broken) "
            f"[{'ENABLED' if h_info['enabled'] else 'DISABLED'}]"
        )

    console.print("\n[bold]Shadowing & Collision Warnings:[/bold]")
    if shadowing_warnings:
        max_show = 3
        for warn in shadowing_warnings[:max_show]:
            console.print(f"  [yellow]• {warn['message']}[/yellow]")
        if len(shadowing_warnings) > max_show:
            remaining = len(shadowing_warnings) - max_show
            console.print(f"  [dim]• ... and {remaining} more shadowing warnings[/dim]")
    else:
        console.print("  [dim]• No active shadowing detected across active workspace.[/dim]")


@cli.group("vendor", cls=PointedGroup)
def vendor_group() -> None:
    """Manage vendored upstreams with exclude-first discovery."""
    pass


@vendor_group.command("compile")
def vendor_compile_cmd() -> None:
    """Compile sources.d/*.yml manifests into vendir.yml."""
    root = find_workspace_root()
    sources_d = root / "sources.d"
    output_vendir = root / "vendir.yml"
    compile_sources(sources_d, output_vendir)
    console.print(f"[green]Compiled {sources_d} into {output_vendir}[/green]")


@vendor_group.command("sync")
def vendor_sync_cmd() -> None:
    """Compile sources and run vendir sync."""
    root = find_workspace_root()
    code, stdout, stderr = run_vendir_sync(root)
    if code != 0:
        err_msg = stderr.strip() or stdout.strip() or f"Vendir sync exited with code {code}"
        clean_err = err_msg.splitlines()[0] if err_msg else "Unknown failure"
        exit_with_pointed_error(clean_err, location="vendir sync", code=1)
    console.print("[green]Vendir sync completed successfully.[/green]")
    if stdout:
        console.print(stdout)


@cli.group("harness", cls=PointedGroup)
def harness_group() -> None:
    """Inspect and toggle active target harnesses."""
    pass


@harness_group.command("list")
@click.option("--json", "as_json", is_flag=True)
def harness_list_cmd(as_json: bool) -> None:
    """List registered harnesses and status."""
    root = find_workspace_root()
    cfg = load_atelier_config(root)

    data: Dict[str, Dict[str, Any]] = {}
    for ht in HarnessType:
        h_cfg = cfg.harnesses.get(ht)
        enabled = h_cfg.enabled if h_cfg else False
        path = h_cfg.path if h_cfg else DEFAULT_HARNESS_PATHS.get(ht, Path(""))
        data[ht.value] = {
            "enabled": enabled,
            "path": str(path),
        }

    if as_json:
        click.echo(json.dumps(data, indent=2))
        return

    table = Table(title="Host Harnesses")
    table.add_column("Harness", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Path", style="magenta")

    for h_name, h_val in data.items():
        status_str = "[green]ENABLED[/green]" if h_val["enabled"] else "[dim]DISABLED[/dim]"
        table.add_row(h_name, status_str, h_val["path"])

    console.print(table)


@harness_group.command("enable")
@click.argument("name")
def harness_enable_cmd(name: str) -> None:
    """Enable a host harness in ghosla.toml."""
    root = find_workspace_root()
    config_file = root / "ghosla.toml"
    set_harness_status(config_file, name, enabled=True)
    console.print(f"[green]Enabled harness {name}[/green]")


@harness_group.command("disable")
@click.argument("name")
def harness_disable_cmd(name: str) -> None:
    """Disable a host harness in ghosla.toml."""
    root = find_workspace_root()
    config_file = root / "ghosla.toml"
    set_harness_status(config_file, name, enabled=False)
    console.print(f"[yellow]Disabled harness {name}[/yellow]")


@cli.group("intake", cls=PointedGroup)
def intake_group() -> None:
    """Catch-all intake bridge for external skills."""
    pass


@intake_group.command("scan")
@click.option("--json", "as_json", is_flag=True)
def intake_scan_cmd(as_json: bool) -> None:
    """Scan catch-all zone (~/.agents/skills) for external skills."""
    root = find_workspace_root()
    cfg = load_atelier_config(root)
    intake_dir = cfg.intake.resolved_catch_all_path()
    skills = scan_intake_skills(intake_dir)

    if as_json:
        click.echo(json.dumps([s.model_dump(mode="json") for s in skills], indent=2))
        return

    console.print(f"[cyan]Scanning catch-all zone: {intake_dir}[/cyan]")
    console.print(f"Found {len(skills)} external skills:")
    for s in skills:
        token_info = f"~{s.estimated_tokens} tokens, {s.byte_size} bytes"
        console.print(f"  • [bold]{s.name}[/bold] ({token_info})")


@intake_group.command("bridge")
@click.option("--json", "as_json", is_flag=True)
def intake_bridge_cmd(as_json: bool) -> None:
    """Bridge external skills into Antigravity (~/.gemini/config/skills)."""
    root = find_workspace_root()
    cfg = load_atelier_config(root)
    intake_dir = cfg.intake.resolved_catch_all_path()
    gemini_dir = DEFAULT_HARNESS_PATHS[HarnessType.ANTIGRAVITY].expanduser().resolve()
    bridged = bridge_external_skills(
        intake_dir, gemini_dir, bridge_prefix=cfg.intake.bridge_prefix
    )

    if as_json:
        click.echo(json.dumps([str(p) for p in bridged], indent=2))
        return

    bridge_msg = (
        f"[green]Created {len(bridged)} atomic symlinks in {gemini_dir} -> {intake_dir}[/green]"
    )
    console.print(bridge_msg)
    console.print("[green]Zero fragmentation: external skills bridged to Antigravity CLI.[/green]")


@cli.command("adopt")
@click.argument("source_path", type=click.Path(exists=True))
@click.option("--name", default=None, help="Custom skill name")
def adopt_cmd(source_path: str, name: Optional[str]) -> None:
    """Adopt an external skill into local atelier skills/."""
    root = find_workspace_root()
    local_skills_dir = root / "skills"
    try:
        adopted = adopt_skill(Path(source_path), local_skills_dir, target_name=name)
        console.print(f"[green]Adopted skill to {adopted}[/green]")
    except (FileNotFoundError, ValueError) as err:
        exit_with_pointed_error(str(err), location="adopt")



@cli.group("bundle", cls=PointedGroup)
def bundle_group() -> None:
    """Manage curated skill bundles."""
    pass


@bundle_group.command("list")
@click.option("--json", "as_json", is_flag=True)
def bundle_list_cmd(as_json: bool) -> None:
    """List available skill bundles."""
    root = find_workspace_root()
    bundles = load_bundles(root)

    if as_json:
        click.echo(json.dumps([b.model_dump(mode="json") for b in bundles.values()], indent=2))
        return

    table = Table(title="Skill Bundles")
    table.add_column("Name", style="cyan")
    table.add_column("Skills Count", style="green")
    table.add_column("Description")

    for b in bundles.values():
        table.add_row(b.name, str(len(b.skills)), b.description)

    console.print(table)


@bundle_group.command("show")
@click.argument("name")
@click.option("--json", "as_json", is_flag=True)
def bundle_show_cmd(name: str, as_json: bool) -> None:
    """Show skills in a bundle."""
    root = find_workspace_root()
    bundles = load_bundles(root)
    bundle = bundles.get(name)
    if not bundle:
        exit_with_pointed_error(f"Bundle '{name}' not found.", location="bundles/")

    if as_json:
        click.echo(json.dumps(bundle.model_dump(mode="json"), indent=2))
        return

    console.print(f"[bold cyan]Bundle: {bundle.name}[/bold cyan]")
    console.print(f"[dim]{bundle.description}[/dim]")
    console.print("\nSkills included:")
    for s in bundle.skills:
        console.print(f"  • {s}")


@bundle_group.command("switch")
@click.argument("name")
def bundle_switch_cmd(name: str) -> None:
    """Switch active bundle in ghosla.toml."""
    root = find_workspace_root()
    bundles = load_bundles(root)
    if name not in bundles:
        exit_with_pointed_error(f"Bundle '{name}' does not exist in bundles/", location="bundles/")

    config_file = root / "ghosla.toml"
    content = config_file.read_text(encoding="utf-8")
    new_content = re.sub(
        r'(active_bundle\s*=\s*")[^"]*(")',
        rf'\g<1>{name}\g<2>',
        content,
    )
    config_file.write_text(new_content, encoding="utf-8")
    console.print(f"[green]Switched active bundle to '{name}'[/green]")


@cli.command("link")
@click.option("--clean", is_flag=True, help="Clean orphaned symlinks")
def link_cmd(clean: bool) -> None:
    """Project active bundles into host harnesses."""
    root = find_workspace_root()
    cfg = load_atelier_config(root)
    bundles = load_bundles(root)
    active_bundle = bundles.get(cfg.active_bundle)
    if not active_bundle:
        exit_with_pointed_error(
            f"Active bundle '{cfg.active_bundle}' not found in bundles/",
            location="ghosla.toml",
        )

    catalog = get_catalog(root, include_upstream=True)
    engine = LinkerEngine(workspace_root=root)
    try:
        created = engine.link_bundle(active_bundle, catalog, harnesses_config=cfg.harnesses)
    except KeyError as err:
        exit_with_pointed_error(str(err).strip("'"), location=f"bundles/{active_bundle.name}.yaml")

    console.print(f"[green]Linked {len(created)} skills into enabled harnesses.[/green]")

    if clean:
        removed = engine.clean_orphaned_links([active_bundle], catalog=catalog)
        if removed:
            console.print(f"[yellow]Cleaned {len(removed)} orphaned symlinks.[/yellow]")


@cli.command("audit")
@click.option("--all", "audit_all", is_flag=True, help="Audit both local and vendored skills")
@click.option("--verbose", "-v", is_flag=True, help="Show full audit details for all skills")
@click.option("--json", "as_json", is_flag=True)
def audit_cmd(audit_all: bool, verbose: bool, as_json: bool) -> None:
    """Validate frontmatter, token budgets, byte limits, and reference depths."""
    root = find_workspace_root()
    catalog = get_catalog(root, include_upstream=audit_all)

    results: List[Dict[str, Any]] = []
    has_budget_violation = False
    seen_paths: Set[Path] = set()

    for name, skill in catalog.items():
        res_p = skill.path.resolve()
        if res_p in seen_paths:
            continue
        seen_paths.add(res_p)

        audit_res = TokenAuditor.audit_skill(skill.path)
        if not audit_res.is_valid:
            has_budget_violation = True
        results.append({
            "name": name,
            "source": skill.source_type.value,
            "path": str(skill.path),
            "byte_size": audit_res.byte_size,
            "line_count": audit_res.line_count,
            "estimated_tokens": audit_res.estimated_tokens,
            "is_valid": audit_res.is_valid,
            "errors": audit_res.errors,
            "warnings": audit_res.warnings,
        })

    if as_json:
        summary = {
            "total_checked": len(results),
            "valid": sum(1 for r in results if r["is_valid"]),
            "failed": sum(1 for r in results if not r["is_valid"]),
        }
        indent = 2 if verbose else None
        separators = (",", ": ") if verbose else (",", ":")
        payload = json.dumps(
            {"summary": summary, "skills": results},
            indent=indent,
            separators=separators,
        )
        click.echo(payload)
        sys.exit(3 if has_budget_violation else 0)

    failed_skills = [r for r in results if not r["is_valid"]]
    valid_count = len(results) - len(failed_skills)

    if verbose:
        console.print(f"Auditing {len(results)} skills...")
        for r in results:
            status_tag = "[green]PASS[/green]" if r["is_valid"] else "[red]FAIL[/red]"
            console.print(
                f"[{status_tag}] {r['name']}: {r['byte_size']} bytes | "
                f"{r['line_count']} lines | ~{r['estimated_tokens']} tokens"
            )
            for err in r["errors"]:
                console.print(f"    [red]• {err}[/red]")
            for warn in r["warnings"]:
                console.print(f"    [yellow]• {warn}[/yellow]")
    else:
        # Terse / Token-Optimized mode: only report failures and clean summary
        if failed_skills:
            fail_count = len(failed_skills)
            total_count = len(results)
            console.print(f"[bold red]Audit Failures ({fail_count}/{total_count}):[/bold red]")
            for r in failed_skills:
                meta_info = f"{r['byte_size']} bytes, ~{r['estimated_tokens']} tokens"
                console.print(
                    f"  [red]FAIL[/red] [bold]{r['name']}[/bold] ({meta_info}):"
                )
                for err in r["errors"]:
                    console.print(f"    [red]• {err}[/red]")
                for warn in r["warnings"]:
                    console.print(f"    [yellow]• {warn}[/yellow]")

        if not failed_skills:
            console.print(
                f"[green]Audit complete: all {len(results)} skills passed "
                "budget and integrity checks.[/green]"
            )
        else:
            console.print(
                f"[yellow]Audit finished: {len(results)} checked, {valid_count} passed, "
                f"[red]{len(failed_skills)} failed[/red]. (Use -v for full list)[/yellow]"
            )

    if has_budget_violation:
        sys.exit(3)



@cli.command("diff")
@click.option("--json", "as_json", is_flag=True)
@click.option(
    "--update/--no-update",
    "update_state",
    default=True,
    help="Update checkpoint state in ledger/state.json",
)
def diff_cmd(as_json: bool, update_state: bool) -> None:
    """Inspect upstream changes and update Epistemic Diff Ledger."""
    root = find_workspace_root()
    ledger = EpistemicLedger(ledger_dir=root / "ledger")
    lock_file = root / "vendir.lock.yml"
    upstream_dir = root / "upstream"
    skills_dir = root / "skills"

    diffs = ledger.compute_diff(lock_file, upstream_dir, skills_dir=skills_dir)

    if as_json:
        click.echo(json.dumps([
            {
                "repo": d.repo_name,
                "old_commit": d.old_commit,
                "new_commit": d.new_commit,
                "commit_title": d.commit_title,
                "new_skills": d.new_skills,
                "forked_skills": d.forked_skills,
            }
            for d in diffs
        ], indent=2))
        if diffs:
            sys.exit(2)
        sys.exit(0)

    if not diffs:
        console.print("[green]Epistemic ledger clean. No upstream changes detected.[/green]")
        sys.exit(0)

    console.print(f"Discovered updates across {len(diffs)} upstream repositories:")
    current_state = ledger.load_state()
    for d in diffs:
        report_file = ledger.record_diff_report(d)
        if update_state:
            current_state[d.repo_name] = d.new_commit
        commit_range = f"{d.old_commit or 'initial'} -> {d.new_commit}"
        console.print(f"[bold cyan]{d.repo_name}[/bold cyan] ({commit_range})")
        if d.commit_title:
            console.print(f"  Title: {d.commit_title}")
        if d.forked_skills:
            console.print("  [yellow]Local forks preserved untouched:[/yellow]")
            for f in d.forked_skills:
                console.print(f"    • {f['name']} (upstream: {f['upstream_source']})")
        console.print(f"  Ledger recorded: {report_file}")

    if update_state and diffs:
        ledger.save_state(current_state)

    sys.exit(2)


@cli.group("study", cls=PointedGroup)
def study_group() -> None:
    """Export skills into Obsidian Luma study lab for incremental reading."""
    pass


@study_group.command("export")
@click.argument("skill_name")
@click.option("--vault", default=None, help="Custom Obsidian vault path")
def study_export_cmd(skill_name: str, vault: Optional[str]) -> None:
    """Export a study card into Obsidian Luma study inbox."""
    root = find_workspace_root()
    catalog = get_catalog(root, include_upstream=True)
    engine = LinkerEngine(workspace_root=root)
    skill = engine.resolve_skill(skill_name, catalog) or catalog.get(skill_name)
    if not skill:
        exit_with_pointed_error(
            f"Skill '{skill_name}' not found in atelier catalog.",
            location="catalog",
        )

    vault_path = Path(vault) if vault else None
    exporter = ObsidianLumaExporter(vault_path=vault_path)
    dest = exporter.export_for_study(skill)
    console.print(f"[green]Exported study card to:[/green]\n{dest}")
    console.print("[dim]Ready for incremental reading and Luma embeddings.[/dim]")


@cli.command("clip")
@click.argument("text_or_path")
@click.option("--name", default=None, help="Clipping name")
@click.option("--url", default=None, help="Source URL or tweet link")
def clip_cmd(text_or_path: str, name: Optional[str], url: Optional[str]) -> None:
    """Ingest a web clipping, tweet, or prompt into inbox/clippings/ with provenance."""
    root = find_workspace_root()
    inbox_dir = root / "inbox" / "clippings"
    inbox_dir.mkdir(parents=True, exist_ok=True)

    # Check if text_or_path is a path
    p = Path(text_or_path)
    if p.exists() and p.is_file():
        body = p.read_text(encoding="utf-8", errors="replace")
        clip_name = name or p.stem
    else:
        body = text_or_path
        clip_name = name or f"clipping-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    frontmatter = {
        "name": clip_name,
        "source_url": url or "manual-input",
        "date_clipped": date_str,
        "tags": ["clipping", "inbox"],
    }

    content = f"---\n{yaml.safe_dump(frontmatter, sort_keys=False)}---\n\n{body}\n"
    target_file = inbox_dir / f"{clip_name}.md"
    target_file.write_text(content, encoding="utf-8")
    console.print(f"[green]Clipped to {target_file}[/green]")


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
