"""Tests for `cloak policy init` (project detection + scaffolding)."""

from pathlib import Path

import yaml
from typer.testing import CliRunner

from cloak.cli import app
from cloak.policy_init import build_starter_policy, detect_project

runner = CliRunner()


# ---------- detect_project unit tests ----------


def test_detect_python_via_pyproject(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
    d = detect_project(tmp_path)
    assert d.has_python is True
    assert d.has_node is False
    assert d.has_typescript is False
    assert d.label == "Python"


def test_detect_python_via_top_level_py_file(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("print(1)\n")
    d = detect_project(tmp_path)
    assert d.has_python is True


def test_detect_node_via_package_json(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text('{"name":"x"}\n')
    d = detect_project(tmp_path)
    assert d.has_node is True
    assert d.has_typescript is False
    assert d.label == "JavaScript"


def test_detect_typescript_via_tsconfig(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text('{"name":"x"}\n')
    (tmp_path / "tsconfig.json").write_text("{}\n")
    d = detect_project(tmp_path)
    assert d.has_typescript is True
    assert d.label == "TypeScript"  # TS supersedes JS in the label


def test_detect_typescript_via_top_level_ts_file(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text('{"name":"x"}\n')
    (tmp_path / "main.ts").write_text("export const x = 1;\n")
    d = detect_project(tmp_path)
    assert d.has_typescript is True


def test_detect_mixed_python_and_typescript(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
    (tmp_path / "package.json").write_text('{"name":"x"}\n')
    (tmp_path / "tsconfig.json").write_text("{}\n")
    d = detect_project(tmp_path)
    assert d.has_python is True
    assert d.has_typescript is True
    assert "Python" in d.label and "TypeScript" in d.label


def test_detect_common_src_dirs(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "lib").mkdir()
    (tmp_path / "packages").mkdir()
    d = detect_project(tmp_path)
    assert "src/**" in d.src_dirs
    assert "lib/**" in d.src_dirs
    assert "packages/**" in d.src_dirs


def test_detect_empty_dir_returns_generic_with_no_src(tmp_path: Path) -> None:
    d = detect_project(tmp_path)
    assert d.has_python is False
    assert d.has_node is False
    assert d.has_typescript is False
    assert d.src_dirs == []
    assert d.label == "generic"


# ---------- build_starter_policy ----------


def test_starter_policy_is_valid_yaml(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    detection = detect_project(tmp_path)
    yaml_text = build_starter_policy(detection)
    parsed = yaml.safe_load(yaml_text)
    assert parsed["version"] == 1
    assert parsed["sensitive_paths"] == ["src/**"]
    assert parsed["public_api"] == []
    assert parsed["secret_rules"] == []
    assert parsed["context_defaults"]["keep_docstrings"] is True
    assert parsed["obfuscate_defaults"]["profile"] == "standard"


def test_starter_policy_falls_back_to_src_when_no_dirs_detected(tmp_path: Path) -> None:
    detection = detect_project(tmp_path)
    yaml_text = build_starter_policy(detection)
    parsed = yaml.safe_load(yaml_text)
    # Default sensible fallback so the file is useful out of the box.
    assert "src/**" in parsed["sensitive_paths"]


# ---------- CLI integration ----------


def test_cli_writes_file_with_yes(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
    result = runner.invoke(app, ["policy", "init", "--yes"])
    assert result.exit_code == 0, result.stdout
    written = (tmp_path / ".cloakpolicy").read_text()
    parsed = yaml.safe_load(written)
    assert parsed["version"] == 1


def test_cli_refuses_to_overwrite_existing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".cloakpolicy").write_text("# existing\nversion: 1\n")
    result = runner.invoke(app, ["policy", "init", "--yes"])
    assert result.exit_code == 2
    assert "already exists" in result.stdout.lower()
    # Original untouched
    assert (tmp_path / ".cloakpolicy").read_text() == "# existing\nversion: 1\n"


def test_cli_overwrites_with_force(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".cloakpolicy").write_text("# old\n")
    result = runner.invoke(app, ["policy", "init", "--yes", "--force"])
    assert result.exit_code == 0
    parsed = yaml.safe_load((tmp_path / ".cloakpolicy").read_text())
    assert parsed["version"] == 1


def test_cli_writes_to_custom_out(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    custom = tmp_path / "configs" / "cloak.yml"
    custom.parent.mkdir()
    result = runner.invoke(app, ["policy", "init", "--yes", "--out", str(custom)])
    assert result.exit_code == 0
    assert custom.exists()


def test_cli_aborts_on_no_response(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    # Feed "n" to the confirm prompt.
    result = runner.invoke(app, ["policy", "init"], input="n\n")
    assert result.exit_code == 0
    assert not (tmp_path / ".cloakpolicy").exists()
    assert "aborted" in result.stdout.lower()


def test_cli_writes_on_yes_response(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    # Feed "y" to the confirm prompt.
    result = runner.invoke(app, ["policy", "init"], input="y\n")
    assert result.exit_code == 0
    assert (tmp_path / ".cloakpolicy").exists()


def test_policy_subcommand_appears_in_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert "policy" in result.stdout
    sub = runner.invoke(app, ["policy", "--help"])
    assert sub.exit_code == 0
    assert "init" in sub.stdout
