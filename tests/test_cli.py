"""Smoke tests for the Phase 1 CLI scaffold.

These verify the package wires correctly: subcommands exist, the policy loader runs,
the file walker walks, JSON output is parseable. Real detection / redaction logic is
tested in later phases as it lands.
"""

import json
from pathlib import Path

from typer.testing import CliRunner

from cloak.cli import app

runner = CliRunner()


def _make_sample_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "sample.py").write_text("def foo() -> int:\n    return 1\n")
    (repo / "README.md").write_text("# sample\n")
    return repo


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "cloak" in result.stdout


def test_help_lists_subcommands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "scan" in result.stdout
    assert "context" in result.stdout
    assert "obfuscate" in result.stdout


def test_scan_skeleton(tmp_path: Path) -> None:
    repo = _make_sample_repo(tmp_path)
    result = runner.invoke(app, ["scan", str(repo)])
    assert result.exit_code == 0
    assert "scaffold" in result.stdout.lower()
    assert "files found" in result.stdout.lower()


def test_context_skeleton(tmp_path: Path) -> None:
    repo = _make_sample_repo(tmp_path)
    result = runner.invoke(app, ["context", str(repo)])
    assert result.exit_code == 0


def test_obfuscate_skeleton(tmp_path: Path) -> None:
    repo = _make_sample_repo(tmp_path)
    out = tmp_path / "out"
    result = runner.invoke(app, ["obfuscate", str(repo), "--out", str(out)])
    assert result.exit_code == 0


def test_json_output_is_valid(tmp_path: Path) -> None:
    repo = _make_sample_repo(tmp_path)
    result = runner.invoke(app, ["scan", str(repo), "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["command"] == "scan"
    assert payload["status"] == "scaffold-only"
    assert payload["files_discovered"] >= 1


def test_policy_loads_when_present(tmp_path: Path) -> None:
    repo = _make_sample_repo(tmp_path)
    (repo / ".cloakpolicy").write_text("version: 1\nsensitive_paths:\n  - 'src/**'\n")
    result = runner.invoke(app, ["scan", str(repo), "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["policy_loaded_from"] is not None
    assert ".cloakpolicy" in payload["policy_loaded_from"]


def test_cloakignore_excludes_files(tmp_path: Path) -> None:
    repo = _make_sample_repo(tmp_path)
    (repo / "secret.txt").write_text("ignore me")
    (repo / ".cloakignore").write_text("secret.txt\n")
    result = runner.invoke(app, ["scan", str(repo), "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    # sample.py + README.md + .cloakignore = 3; secret.txt should be excluded.
    discovered = int(payload["files_discovered"])
    assert discovered >= 2  # at minimum sample.py + README.md
    # Verify by hand: secret.txt should not appear when we walk ourselves.
    from cloak.filesystem import walk_repo
    from cloak.policy import Policy

    files = [p.name for p in walk_repo(repo, Policy())]
    assert "secret.txt" not in files
