"""Tests for `cloak diff-context`."""

import json
from pathlib import Path

from typer.testing import CliRunner

from cloak.cli import app
from cloak.context.diff import diff_context
from cloak.policy import Policy

runner = CliRunner()


def _make_python_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pricing.py").write_text(
        '''"""Pricing engine."""

_TIER_DISCOUNTS = {"low": 0.0, "high": 0.15}

REGIONS = ["NE", "W", "S"]


def calculate_total(base: float, region: str) -> float:
    """Compute the customer-facing total."""
    return base * 1.1


class Quote:
    """A quote."""

    def render(self) -> str:
        return "..."
'''
    )
    return repo


def test_diff_context_python_counts_redactions(tmp_path: Path) -> None:
    repo = _make_python_repo(tmp_path)
    policy = Policy()
    files = sorted(repo.rglob("*.py"))
    summary = diff_context(files, policy, repo_root=repo)

    assert len(summary.files) == 1
    fd = summary.files[0]
    assert fd.language == "python"
    assert fd.function_bodies_redacted == 2  # calculate_total, render
    assert fd.tables_redacted == 2  # _TIER_DISCOUNTS, REGIONS
    assert fd.docstrings_stripped == 0  # default keeps them
    assert fd.bytes_after < fd.bytes_before
    assert fd.reduction_pct > 0


def test_diff_context_strict_strips_docstrings(tmp_path: Path) -> None:
    repo = _make_python_repo(tmp_path)
    policy = Policy()
    files = sorted(repo.rglob("*.py"))
    summary = diff_context(files, policy, strict=True, repo_root=repo)

    fd = summary.files[0]
    # Module docstring + function docstring + class docstring = 3
    assert fd.docstrings_stripped == 3


def test_diff_context_cli_terminal_output(tmp_path: Path) -> None:
    repo = _make_python_repo(tmp_path)
    result = runner.invoke(app, ["diff-context", str(repo)])
    assert result.exit_code == 0
    assert "cloak diff-context" in result.stdout
    assert "function bodies" in result.stdout
    assert "% reduction" in result.stdout
    assert "No files written" in result.stdout


def test_diff_context_cli_json_output(tmp_path: Path) -> None:
    repo = _make_python_repo(tmp_path)
    result = runner.invoke(app, ["diff-context", str(repo), "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["command"] == "diff-context"
    assert payload["status"] == "ok"
    assert payload["totals"]["files"] == 1
    assert payload["totals"]["function_bodies_redacted"] == 2
    assert payload["totals"]["tables_redacted"] == 2
    assert payload["files"][0]["path"] == "pricing.py"


def test_diff_context_javascript(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "client.js").write_text(
        """const API_KEYS = {
  prod: "real-key-here-pretend-its-long",
  staging: "another-key-here",
  dev: "dev-key",
};

const REGIONS = ["us-east-1", "us-west-2", "eu-central-1"];

function fetchUser(id) {
  const url = `https://api.example.com/users/${id}`;
  return fetch(url).then((r) => r.json());
}

function fetchOrder(id) {
  const url = `https://api.example.com/orders/${id}`;
  return fetch(url).then((r) => r.json());
}
"""
    )
    policy = Policy()
    files = sorted(repo.rglob("*.js"))
    summary = diff_context(files, policy, repo_root=repo)

    fd = summary.files[0]
    assert fd.language == "javascript"
    assert fd.function_bodies_redacted == 2
    assert fd.tables_redacted == 2
    assert fd.bytes_after < fd.bytes_before
