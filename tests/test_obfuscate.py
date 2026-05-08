"""Tests for `cloak obfuscate` (Phase 4)."""

import json
import shutil
from pathlib import Path

from typer.testing import CliRunner

from cloak.cli import app
from cloak.obfuscate.runner import ObfuscateError, run_obfuscate
from cloak.obfuscate.transformer import transform_python_source
from cloak.policy import ObfuscateDefaults, Policy

runner = CliRunner()


# ---------- transformer unit tests ----------


def test_transformer_renames_module_private_function() -> None:
    src = "def _helper(x):\n    return x + 1\n\ndef public_fn(x):\n    return _helper(x)\n"
    result = transform_python_source(src, Policy())
    assert "_helper" not in result.output_text
    assert "_a000" in result.output_text
    assert "public_fn" in result.output_text  # public name preserved
    assert result.rename_map == {"_helper": "_a000"}


def test_transformer_preserves_dunder_methods() -> None:
    """Dunder names like __init__ must not be renamed even though they start with underscore."""
    src = "class Foo:\n    def __init__(self):\n        self.x = 1\n"
    result = transform_python_source(src, Policy())
    assert "__init__" in result.output_text
    assert not result.rename_map


def test_transformer_respects_public_api_in_policy() -> None:
    src = "def _internal_api():\n    return 1\n"
    policy = Policy(public_api=["_internal_api"])
    result = transform_python_source(src, policy)
    assert "_internal_api" in result.output_text  # protected
    assert not result.rename_map


def test_transformer_strips_docstrings_when_policy_enabled() -> None:
    src = '"""Module doc."""\n\ndef f():\n    """Function doc."""\n    return 1\n'
    policy = Policy(obfuscate_defaults=ObfuscateDefaults(strip_docstrings=True))
    result = transform_python_source(src, policy)
    assert "Module doc." not in result.output_text
    assert "Function doc." not in result.output_text
    assert result.docstrings_stripped == 2


def test_transformer_keeps_docstrings_by_default() -> None:
    src = '"""Keep me."""\n\ndef f():\n    return 1\n'
    result = transform_python_source(src, Policy())
    assert "Keep me." in result.output_text


def test_transformer_renames_private_class() -> None:
    src = "class _Internal:\n    pass\n\ndef make() -> _Internal:\n    return _Internal()\n"
    result = transform_python_source(src, Policy())
    assert "_Internal" not in result.output_text
    assert "_a000" in result.output_text


# ---------- runner / pipeline integration tests ----------


def _make_sample_repo(tmp_path: Path) -> Path:
    """Realistic mini-repo: lib + matching tests that import the public function."""
    repo = tmp_path / "src_repo"
    repo.mkdir()
    (repo / "calc.py").write_text(
        '"""Calculator with private helper."""\n'
        "\n"
        "def _internal_double(x: int) -> int:\n"
        "    return x * 2\n"
        "\n"
        "def compute_total(values):\n"
        "    return sum(_internal_double(v) for v in values)\n"
    )
    (repo / "test_calc.py").write_text(
        "from calc import compute_total\n"
        "\n"
        "def test_compute_total():\n"
        "    assert compute_total([1, 2, 3]) == 12\n"
        "\n"
        "def test_empty():\n"
        "    assert compute_total([]) == 0\n"
    )
    return repo


def test_runner_full_pipeline_with_passing_verify(tmp_path: Path) -> None:
    repo = _make_sample_repo(tmp_path)
    out = tmp_path / "obfuscated"

    result = run_obfuscate(repo, out, Policy(), verify_command="pytest test_calc.py")

    assert result.verify_passed is True
    assert result.files_transformed == 2
    assert (out / "calc.py").exists()
    assert (out / "cloak-manifest.json").exists()

    # The renamed identifier should appear; the original should not.
    obfuscated_calc = (out / "calc.py").read_text()
    assert "_internal_double" not in obfuscated_calc
    assert "_a000" in obfuscated_calc

    # Manifest schema sanity.
    manifest = json.loads((out / "cloak-manifest.json").read_text())
    assert manifest["cloak_version"]
    assert manifest["verify_command"] == "pytest test_calc.py"
    assert manifest["verify_passed"] is True
    assert "calc.py" in manifest["source_files"]
    assert "calc.py" in manifest["output_files"]
    assert manifest["rename_map"]["calc.py:_internal_double"] == "_a000"


def test_runner_refuses_non_empty_output(tmp_path: Path) -> None:
    repo = _make_sample_repo(tmp_path)
    out = tmp_path / "out"
    out.mkdir()
    (out / "existing.txt").write_text("hi")

    try:
        run_obfuscate(repo, out, Policy())
    except ObfuscateError as e:
        assert "not empty" in str(e)
    else:
        raise AssertionError("expected ObfuscateError")


def test_runner_handles_unparseable_python_gracefully(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "ok.py").write_text("def _ok(): return 1\n")
    (repo / "broken.py").write_text("def broken(:::\n")
    out = tmp_path / "out"
    run_obfuscate(repo, out, Policy())
    # broken.py should still be present (copied through), just not transformed.
    assert (out / "broken.py").exists()
    assert (out / "ok.py").exists()
    assert "_ok" not in (out / "ok.py").read_text()
    assert "_a000" in (out / "ok.py").read_text()


# ---------- CLI integration tests ----------


def test_cli_obfuscate_with_passing_verify(tmp_path: Path) -> None:
    repo = _make_sample_repo(tmp_path)
    out = tmp_path / "obf"
    result = runner.invoke(
        app, ["obfuscate", str(repo), "--out", str(out), "--verify", "pytest test_calc.py"]
    )
    assert result.exit_code == 0, result.stdout
    assert "Obfuscated" in result.stdout
    assert (out / "cloak-manifest.json").exists()


def test_cli_obfuscate_failing_verify_returns_1(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "lib.py").write_text("def _h(x): return x + 1\ndef pf(x): return _h(x)\n")
    (repo / "test_fail.py").write_text(
        "from lib import pf\n\ndef test_x():\n    assert pf(1) == 999\n"
    )
    out = tmp_path / "obf"
    result = runner.invoke(
        app, ["obfuscate", str(repo), "--out", str(out), "--verify", "pytest test_fail.py"]
    )
    assert result.exit_code == 1
    # Output is still written for inspection, but UX warns clearly.
    assert "Verify failed" in result.stdout
    assert (out / "cloak-manifest.json").exists()


def test_cli_obfuscate_json_output(tmp_path: Path) -> None:
    repo = _make_sample_repo(tmp_path)
    out = tmp_path / "obf"
    result = runner.invoke(app, ["obfuscate", str(repo), "--out", str(out), "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["command"] == "obfuscate"
    assert payload["status"] == "ok"
    assert payload["files_transformed"] == 2
    assert payload["rename_count"] >= 1


def test_cli_obfuscate_refuses_to_overwrite(tmp_path: Path) -> None:
    repo = _make_sample_repo(tmp_path)
    out = tmp_path / "obf"
    out.mkdir()
    (out / "leftover.txt").write_text("don't clobber me")
    result = runner.invoke(app, ["obfuscate", str(repo), "--out", str(out)])
    assert result.exit_code == 2
    assert "not empty" in result.stdout.lower()
    # Original leftover untouched.
    assert (out / "leftover.txt").read_text() == "don't clobber me"


def test_cli_obfuscate_copies_non_python_files(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "main.py").write_text("def f(): return 1\n")
    (repo / "config.toml").write_text("[settings]\nx = 1\n")
    out = tmp_path / "obf"
    result = runner.invoke(app, ["obfuscate", str(repo), "--out", str(out)])
    assert result.exit_code == 0
    assert (out / "config.toml").exists()
    assert (out / "config.toml").read_text() == "[settings]\nx = 1\n"
    # Cleanup so subsequent tests in this run aren't affected.
    shutil.rmtree(out, ignore_errors=True)
