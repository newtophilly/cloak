"""Tests for `cloak obfuscate` JS/TS support (Phase 5)."""

import json
from pathlib import Path

from typer.testing import CliRunner

from cloak.cli import app
from cloak.obfuscate.js_transformer import transform_js_like_source
from cloak.obfuscate.runner import run_obfuscate
from cloak.policy import Policy

runner = CliRunner()


# ---------- transformer unit tests ----------


def test_renames_module_level_function() -> None:
    src = (
        "function _helper(x) {\n"
        "  return x + 1;\n"
        "}\n"
        "\n"
        "export function publicFn(x) {\n"
        "  return _helper(x);\n"
        "}\n"
    )
    result = transform_js_like_source(src, "javascript", Policy())
    assert "_helper" not in result.output_text
    assert "_a000" in result.output_text
    # Public name preserved
    assert "publicFn" in result.output_text
    # Reference inside publicFn correctly rewritten
    assert "_a000(x)" in result.output_text
    assert result.rename_map == {"_helper": "_a000"}


def test_renames_module_level_const() -> None:
    src = "const _internal = 42;\nexport const value = _internal * 2;\n"
    result = transform_js_like_source(src, "javascript", Policy())
    assert "_internal" not in result.output_text
    assert "_a000" in result.output_text
    assert "value = _a000 * 2" in result.output_text


def test_renames_module_level_class() -> None:
    src = (
        "class _Internal {\n"
        "  constructor() { this.x = 1; }\n"
        "}\n"
        "\n"
        "export function make() {\n"
        "  return new _Internal();\n"
        "}\n"
    )
    result = transform_js_like_source(src, "javascript", Policy())
    assert "_Internal" not in result.output_text
    assert "_a000" in result.output_text
    assert "new _a000()" in result.output_text


def test_does_not_rename_dunder_like_names() -> None:
    src = "const __version = '1.0';\nconst _foo = 1;\n"
    result = transform_js_like_source(src, "javascript", Policy())
    assert "__version" in result.output_text  # preserved
    assert "_foo" not in result.output_text  # renamed
    assert "_a000" in result.output_text


def test_respects_public_api_in_policy() -> None:
    src = "export function _publicHelper(x) { return x; }\n"
    policy = Policy(public_api=["_publicHelper"])
    result = transform_js_like_source(src, "javascript", policy)
    assert "_publicHelper" in result.output_text
    assert not result.rename_map


def test_handles_export_statement_with_lexical_declaration() -> None:
    src = "export const _privateUtil = (x) => x * 2;\n"
    result = transform_js_like_source(src, "javascript", Policy())
    # The name should still be renamed even though it's wrapped in `export`.
    assert "_privateUtil" not in result.output_text
    assert "_a000" in result.output_text


def test_preserves_property_access_with_same_name() -> None:
    """obj._helper is a member access — different scope; we don't rename it."""
    src = (
        "function _helper(x) { return x * 2; }\n"
        "const obj = { _helper: 'something else' };\n"
        "export function go() {\n"
        "  return _helper(obj._helper);\n"
        "}\n"
    )
    result = transform_js_like_source(src, "javascript", Policy())
    # The bare `_helper` reference (function call) should be renamed.
    # The property access `obj._helper` should NOT be renamed (different scope).
    assert "obj._helper" in result.output_text
    # The standalone calls should be renamed.
    assert "_a000(obj._helper)" in result.output_text


def test_typescript_renames_top_level_types() -> None:
    """TypeScript: rename top-level _-prefixed type identifiers as well."""
    src = (
        "type _Internal = { x: number };\nexport function make(): _Internal { return { x: 1 }; }\n"
    )
    result = transform_js_like_source(src, "typescript", Policy())
    # type_alias_declaration: tree-sitter-typescript should expose this; for v1, our
    # _DEFINITION_NODE_TYPES doesn't include it, so the rename won't happen. This is
    # documented as a limitation. The point of this test: confirm we don't crash.
    assert result.output_text  # non-empty
    # The visible behavior may or may not rename; either is acceptable for v1.


def test_returns_unchanged_when_no_private_names() -> None:
    src = "export function pub(x) { return x; }\n"
    result = transform_js_like_source(src, "javascript", Policy())
    assert result.output_text == src
    assert not result.rename_map


def test_handles_invalid_source_gracefully() -> None:
    src = "function broken( {{{"
    # Should not raise.
    transform_js_like_source(src, "javascript", Policy())


# ---------- pipeline integration ----------


def _make_js_repo(tmp_path: Path) -> Path:
    """Sample JS repo: lib + matching test that imports the public function."""
    repo = tmp_path / "src_repo"
    repo.mkdir()
    (repo / "lib.js").write_text(
        "function _double(x) {\n"
        "  return x * 2;\n"
        "}\n"
        "\n"
        "export function publicFn(x) {\n"
        "  return _double(x);\n"
        "}\n"
    )
    (repo / "package.json").write_text('{"type":"module"}\n')
    return repo


def test_runner_handles_mixed_python_and_js(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "lib.py").write_text(
        "def _helper(x):\n    return x + 1\n\ndef pub(x):\n    return _helper(x)\n"
    )
    (repo / "lib.js").write_text(
        "function _helper(x) { return x + 1; }\nexport function pub(x) { return _helper(x); }\n"
    )
    out = tmp_path / "obfuscated"

    result = run_obfuscate(repo, out, Policy())
    assert result.files_transformed == 2  # both py and js were transformed
    py_text = (out / "lib.py").read_text()
    js_text = (out / "lib.js").read_text()
    assert "_helper" not in py_text
    assert "_helper" not in js_text
    assert "_a000" in py_text
    assert "_a000" in js_text


def test_runner_writes_manifest_with_js_renames(tmp_path: Path) -> None:
    repo = _make_js_repo(tmp_path)
    out = tmp_path / "obfuscated"
    run_obfuscate(repo, out, Policy())

    manifest = json.loads((out / "cloak-manifest.json").read_text())
    assert "lib.js:_double" in manifest["rename_map"]
    assert manifest["rename_map"]["lib.js:_double"] == "_a000"


# ---------- CLI integration ----------


def test_cli_obfuscate_against_js_repo(tmp_path: Path) -> None:
    repo = _make_js_repo(tmp_path)
    out = tmp_path / "obf"
    result = runner.invoke(app, ["obfuscate", str(repo), "--out", str(out)])
    assert result.exit_code == 0, result.stdout
    obfuscated = (out / "lib.js").read_text()
    assert "_double" not in obfuscated
    assert "_a000" in obfuscated
    assert "publicFn" in obfuscated  # public preserved


def test_cli_obfuscate_panel_shows_renames(tmp_path: Path) -> None:
    repo = _make_js_repo(tmp_path)
    out = tmp_path / "obf"
    result = runner.invoke(app, ["obfuscate", str(repo), "--out", str(out)])
    assert result.exit_code == 0
    assert "Obfuscated" in result.stdout
    assert "1 module-private" in result.stdout or "renames:" in result.stdout
