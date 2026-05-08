"""Smoke tests for the CLI surface (Phases 1+2).

Covers: version, help, scan (clean + with findings + with policy custom rules + with .cloakignore),
JSON contract, exit codes. Phase-3+ commands still in scaffold mode are tested for skeleton output.
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


def test_scan_clean_repo_exits_0(tmp_path: Path) -> None:
    repo = _make_sample_repo(tmp_path)
    result = runner.invoke(app, ["scan", str(repo)])
    assert result.exit_code == 0
    assert "clean" in result.stdout.lower()


def test_scan_finds_aws_key_and_exits_1(tmp_path: Path) -> None:
    repo = _make_sample_repo(tmp_path)
    (repo / "leaky.py").write_text('# example creds\nAWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"\n')
    result = runner.invoke(app, ["scan", str(repo), "--json"])
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "findings"
    assert len(payload["findings"]) >= 1
    finding = payload["findings"][0]
    assert finding["severity"] == "high"
    assert finding["file"].endswith("leaky.py")
    assert finding["rule_id"].startswith("detect-secrets/")
    # Critically: the raw secret must NEVER appear in output.
    assert "AKIAIOSFODNN7EXAMPLE" not in result.stdout
    assert "*" in finding["redacted_preview"]


def test_scan_applies_policy_custom_rules(tmp_path: Path) -> None:
    repo = _make_sample_repo(tmp_path)
    (repo / "config.py").write_text('CUSTOMER = "CUST-XYZ-123456"\n')
    (repo / ".cloakpolicy").write_text(
        "version: 1\n"
        "secret_rules:\n"
        "  - id: customer_id_pattern\n"
        "    pattern: 'CUST-[A-Z]{3}-\\d{6}'\n"
        "    severity: medium\n"
    )
    result = runner.invoke(app, ["scan", str(repo), "--json"])
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    rule_ids = [f["rule_id"] for f in payload["findings"]]
    assert "policy/customer_id_pattern" in rule_ids
    customer_finding = next(
        f for f in payload["findings"] if f["rule_id"].endswith("customer_id_pattern")
    )
    assert customer_finding["severity"] == "medium"
    # Original raw match should not be in output.
    assert "CUST-XYZ-123456" not in result.stdout


def test_scan_terminal_clean_mode(tmp_path: Path) -> None:
    repo = _make_sample_repo(tmp_path)
    result = runner.invoke(app, ["scan", str(repo)])
    assert result.exit_code == 0
    assert "Clean" in result.stdout


def test_scan_terminal_findings_mode(tmp_path: Path) -> None:
    repo = _make_sample_repo(tmp_path)
    (repo / "leaky.py").write_text('AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"\n')
    result = runner.invoke(app, ["scan", str(repo)])
    assert result.exit_code == 1
    assert "AKIAIOSFODNN7EXAMPLE" not in result.stdout
    assert "high" in result.stdout.lower()


def test_scan_json_clean(tmp_path: Path) -> None:
    repo = _make_sample_repo(tmp_path)
    result = runner.invoke(app, ["scan", str(repo), "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["command"] == "scan"
    assert payload["status"] == "ok"
    assert payload["findings"] == []


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
    # secret.txt should be excluded; sample.py + README.md still discovered.
    assert int(payload["files_scanned"]) >= 2
    from cloak.filesystem import walk_repo
    from cloak.policy import Policy

    files = [p.name for p in walk_repo(repo, Policy())]
    assert "secret.txt" not in files


def test_context_skeleton(tmp_path: Path) -> None:
    repo = _make_sample_repo(tmp_path)
    result = runner.invoke(app, ["context", str(repo)])
    assert result.exit_code == 0


def test_obfuscate_skeleton(tmp_path: Path) -> None:
    repo = _make_sample_repo(tmp_path)
    out = tmp_path / "out"
    result = runner.invoke(app, ["obfuscate", str(repo), "--out", str(out)])
    assert result.exit_code == 0
