"""CLOAK CLI entry point."""

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from cloak import __version__
from cloak.context.generator import generate as run_context
from cloak.filesystem import walk_repo
from cloak.obfuscate.runner import ObfuscateError, ObfuscateResult
from cloak.obfuscate.runner import run_obfuscate as do_obfuscate
from cloak.policy import Policy, find_policy, load_policy
from cloak.scan.scanner import Finding
from cloak.scan.scanner import scan as run_scan

app = typer.Typer(
    name="cloak",
    help="Local CLI for safer LLM workflows. Run `cloak --help` for commands.",
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
console = Console()


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"cloak {__version__}")
        raise typer.Exit()


@app.callback()
def root(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=_version_callback,
            is_eager=True,
            help="Show version and exit.",
        ),
    ] = False,
) -> None:
    """CLOAK — local CLI for safer LLM workflows."""
    del version  # handled by callback


@app.command()
def scan(
    path: Annotated[Path, typer.Argument(help="Path to scan (file or directory).")],
    policy_path: Annotated[
        Path | None,
        typer.Option("--policy", help="Path to .cloakpolicy file. Default: walks up from `path`."),
    ] = None,
    json_out: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON instead of human-readable output."),
    ] = False,
) -> None:
    """Find secrets and proprietary markers in code.

    Wraps detect-secrets and layers in policy.secret_rules. Raw secrets are never printed —
    only redacted previews. Exits 1 if findings exist, 0 if clean.
    """
    policy = load_policy(policy_path or find_policy(path))
    repo_root = path.resolve() if path.is_dir() else path.resolve().parent
    files = list(walk_repo(path, policy))
    findings = run_scan(files, policy, repo_root=repo_root)

    if json_out:
        _emit_scan_json(policy, files, findings)
    else:
        _emit_scan_terminal(policy, files, findings)

    raise typer.Exit(code=1 if findings else 0)


@app.command()
def context(
    path: Annotated[Path, typer.Argument(help="Path to generate context from.")],
    out: Annotated[
        Path | None,
        typer.Option("--out", help="Output file. Default: stdout."),
    ] = None,
    copy: Annotated[
        bool,
        typer.Option("--copy", help="Copy result to system clipboard."),
    ] = False,
    strict: Annotated[
        bool,
        typer.Option(
            "--strict",
            help="Use strict redaction (alias enums, paraphrase docstrings).",
        ),
    ] = False,
    policy_path: Annotated[
        Path | None,
        typer.Option("--policy", help="Path to .cloakpolicy file."),
    ] = None,
    json_out: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON status instead of generating context."),
    ] = False,
) -> None:
    """Generate redacted markdown safe to paste into an LLM.

    Function bodies are replaced with `...`; module-level UPPER_SNAKE constants holding
    dict/list/set/tuple literals are redacted. `--strict` aliases enum values and strips
    docstrings. Output goes to stdout, `--out`, and/or `--copy` (clipboard) — flags compose.
    """
    policy = load_policy(policy_path or find_policy(path))
    repo_root = path.resolve() if path.is_dir() else path.resolve().parent
    files = list(walk_repo(path, policy))

    if json_out:
        _emit_context_status_json(policy, files, strict=strict)
        return

    markdown = run_context(files, policy, strict=strict, repo_root=repo_root)

    wrote_anywhere = False
    if out is not None:
        out.write_text(markdown, encoding="utf-8")
        console.print(f"[green]✓[/green] wrote {len(markdown):,} chars to {out}")
        wrote_anywhere = True

    if copy:
        if _copy_to_clipboard(markdown):
            console.print(f"[green]✓[/green] copied {len(markdown):,} chars to clipboard")
            wrote_anywhere = True
        else:
            console.print(
                "[yellow]![/yellow] no clipboard tool found "
                "(install pbcopy / xclip / wl-copy / clip.exe)"
            )

    if not wrote_anywhere:
        # Default: print to stdout (use plain print to avoid rich wrapping markdown).
        print(markdown)


@app.command()
def obfuscate(
    path: Annotated[Path, typer.Argument(help="Path to obfuscate.")],
    out: Annotated[Path, typer.Option("--out", help="Output directory.")],
    verify: Annotated[
        str | None,
        typer.Option(
            "--verify",
            help="Test command to run against the output (must pass for the operation to succeed).",
        ),
    ] = None,
    profile: Annotated[
        str,
        typer.Option("--profile", help="Obfuscation profile: standard or aggressive."),
    ] = "standard",
    policy_path: Annotated[
        Path | None,
        typer.Option("--policy", help="Path to .cloakpolicy file."),
    ] = None,
    json_out: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON status instead of running obfuscation."),
    ] = False,
) -> None:
    """Produce a transformed copy of a repo, verified against a test command.

    v1 (Python only): renames module-private `_names`, optionally strips docstrings per
    policy, copies non-Python files unchanged, writes a `cloak-manifest.json` audit trail
    with source/output sha256 hashes and the rename map. If `--verify` is given, runs the
    test command in the output dir; on non-zero exit, the operation fails.
    """
    policy = load_policy(policy_path or find_policy(path))

    try:
        result = do_obfuscate(
            path,
            out,
            policy,
            verify_command=verify,
            profile=profile,
        )
    except ObfuscateError as e:
        if json_out:
            print(json.dumps({"command": "obfuscate", "status": "error", "error": str(e)}))
        else:
            console.print(f"[red]✗ obfuscate failed:[/red] {e}")
        raise typer.Exit(code=2) from e

    exit_code = 0
    if verify and result.verify_passed is False:
        exit_code = 1

    if json_out:
        _emit_obfuscate_json(policy, result)
    else:
        _emit_obfuscate_terminal(policy, result)

    raise typer.Exit(code=exit_code)


def _emit_obfuscate_json(policy: Policy, result: ObfuscateResult) -> None:
    payload = {
        "command": "obfuscate",
        "status": ("ok" if result.verify_passed in (True, None) else "verify_failed"),
        "output_dir": str(result.output_dir),
        "manifest_path": str(result.manifest_path),
        "files_copied": result.files_copied,
        "files_transformed": result.files_transformed,
        "rename_count": len(result.rename_map),
        "policy_loaded_from": str(policy.source) if policy.source else None,
        "verify_command": result.verify_command,
        "verify_passed": result.verify_passed,
    }
    print(json.dumps(payload, indent=2))


def _emit_obfuscate_terminal(policy: Policy, result: ObfuscateResult) -> None:
    if result.verify_command and result.verify_passed is False:
        console.print(
            Panel.fit(
                f"[bold red]✗ Verify failed[/bold red]\n"
                f"command: {result.verify_command}\n\n"
                f"{(result.verify_output or '').rstrip()[:2000]}",
                border_style="red",
                title="cloak obfuscate",
            )
        )
        console.print(
            "  [yellow]Output written, but verification failed — do not ship this bundle.[/yellow]"
        )
        return

    title = "cloak obfuscate"
    lines = [
        "[bold green]✓ Obfuscated[/bold green]",
        f"output:        {result.output_dir}",
        f"manifest:      {result.manifest_path}",
        f"transformed:   {result.files_transformed} python files",
        f"copied:        {result.files_copied} other files",
        f"renames:       {len(result.rename_map)} module-private identifiers",
    ]
    if result.verify_command:
        lines.append(f"verify:        [green]passed[/green] ({result.verify_command})")
    elif result.verify_command is None:
        lines.append(
            'verify:        [yellow]not run[/yellow] — pass --verify "pytest" to gate the output'
        )
    console.print(Panel.fit("\n".join(lines), border_style="green", title=title))
    if not policy.source:
        console.print("  [dim]no .cloakpolicy found; default obfuscate rules applied[/dim]")


def _copy_to_clipboard(text: str) -> bool:
    """Best-effort copy to system clipboard. Returns True on success."""
    import shutil
    import subprocess

    candidates: list[list[str]] = []
    if shutil.which("pbcopy"):  # macOS
        candidates.append(["pbcopy"])
    if shutil.which("wl-copy"):  # Wayland
        candidates.append(["wl-copy"])
    if shutil.which("xclip"):  # X11
        candidates.append(["xclip", "-selection", "clipboard"])
    if shutil.which("clip.exe"):  # Windows
        candidates.append(["clip.exe"])

    for cmd in candidates:
        try:
            subprocess.run(cmd, input=text, text=True, check=True, timeout=5)
            return True
        except (subprocess.SubprocessError, OSError):
            continue
    return False


def _emit_context_status_json(policy: Policy, files: list[Path], *, strict: bool) -> None:
    payload = {
        "command": "context",
        "status": "ok",
        "files_discovered": len(files),
        "policy_loaded_from": str(policy.source) if policy.source else None,
        "policy_version": policy.version,
        "strict": strict,
        "implementation_status": "Phase 3 — Python supported; JS/TS in Phase 3.5.",
    }
    print(json.dumps(payload, indent=2))


def _emit_scan_json(policy: Policy, files: list[Path], findings: list[Finding]) -> None:
    payload = {
        "command": "scan",
        "status": "ok" if not findings else "findings",
        "files_scanned": len(files),
        "policy_loaded_from": str(policy.source) if policy.source else None,
        "policy_version": policy.version,
        "findings": [f.to_dict() for f in findings],
    }
    print(json.dumps(payload, indent=2))


def _emit_scan_terminal(policy: Policy, files: list[Path], findings: list[Finding]) -> None:
    if not findings:
        console.print(
            Panel.fit(
                f"[bold green]✓ Clean — {len(files)} files scanned, 0 findings[/bold green]",
                border_style="green",
                title="cloak scan",
            )
        )
        if not policy.source:
            console.print("  [dim]no .cloakpolicy found; default scanner rules applied[/dim]")
        return

    table = Table(title=f"cloak scan — {len(findings)} finding(s)", header_style="bold red")
    table.add_column("severity", style="bold")
    table.add_column("file")
    table.add_column("line", justify="right")
    table.add_column("rule", style="dim")
    table.add_column("preview")
    for f in findings:
        sev_style = {"high": "red", "medium": "yellow", "low": "cyan"}.get(f.severity, "white")
        table.add_row(
            f"[{sev_style}]{f.severity}[/{sev_style}]",
            f.file,
            str(f.line),
            f.rule_id,
            f.redacted_preview,
        )
    console.print(table)
    console.print(
        f"\n  [dim]{len(files)} files scanned • "
        f"policy: {policy.source or 'defaults'}[/dim]\n"
        f"  [yellow]Action:[/yellow] rotate any real credentials and remove from source."
    )


def _emit_skeleton_status(
    command: str,
    policy: Policy,
    files: list[Path],
    *,
    json_out: bool,
) -> None:
    """Placeholder output for not-yet-implemented commands."""
    if json_out:
        payload = {
            "command": command,
            "status": "scaffold-only",
            "policy_loaded_from": str(policy.source) if policy.source else None,
            "policy_version": policy.version,
            "files_discovered": len(files),
            "implementation_status": ("Scaffolding only — real logic arrives in a later phase."),
        }
        print(json.dumps(payload, indent=2))
        return

    console.print(f"[bold cyan]cloak {command}[/bold cyan]  [dim](scaffold)[/dim]")
    console.print()
    if policy.source:
        console.print(f"  policy:        {policy.source}")
    else:
        console.print("  policy:        [yellow]none found, using defaults[/yellow]")
    console.print(f"  files found:   {len(files)}")
    console.print()
    console.print(
        f"  [yellow]implementation:[/yellow] not yet wired — "
        f"`cloak {command}` arrives in a later phase.\n"
        "  See [link=https://github.com/newtophilly/cloak/blob/main/docs/BUILD_PLAN.md]"
        "docs/BUILD_PLAN.md[/link] for the roadmap."
    )


if __name__ == "__main__":
    app()
