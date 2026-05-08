"""CLOAK CLI entry point.

Phase 1 wires the package layout, subcommand structure, policy loading, and file walking.
The detection / redaction / obfuscation logic itself arrives in Phases 2-5.
"""

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from cloak import __version__
from cloak.filesystem import walk_repo
from cloak.policy import Policy, find_policy, load_policy

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
    """Find secrets and proprietary markers in code (Phase 2 — not yet implemented)."""
    policy = load_policy(policy_path or find_policy(path))
    files = list(walk_repo(path, policy))
    _emit_skeleton_status("scan", policy, files, json_out=json_out)


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
    """Generate redacted markdown safe to paste into an LLM (Phase 3 — not yet implemented)."""
    del out, copy, strict  # accepted now, wired in Phase 3
    policy = load_policy(policy_path or find_policy(path))
    files = list(walk_repo(path, policy))
    _emit_skeleton_status("context", policy, files, json_out=json_out)


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
    """Produce a verified transformed copy of a repo (Phases 4-5 — not yet implemented)."""
    del out, verify, profile  # accepted now, wired in Phases 4-5
    policy = load_policy(policy_path or find_policy(path))
    files = list(walk_repo(path, policy))
    _emit_skeleton_status("obfuscate", policy, files, json_out=json_out)


def _emit_skeleton_status(
    command: str,
    policy: Policy,
    files: list[Path],
    *,
    json_out: bool,
) -> None:
    """Phase 1 placeholder output: prove the skeleton wired correctly without faking results."""
    if json_out:
        payload = {
            "command": command,
            "status": "scaffold-only",
            "policy_loaded_from": str(policy.source) if policy.source else None,
            "policy_version": policy.version,
            "files_discovered": len(files),
            "implementation_status": (
                "Phase 1 — scaffolding only. Real logic arrives in a later phase."
            ),
        }
        print(json.dumps(payload, indent=2))
        return

    console.print(f"[bold cyan]cloak {command}[/bold cyan]  [dim](Phase 1 scaffold)[/dim]")
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
