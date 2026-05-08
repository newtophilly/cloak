"""Tests for `cloak context` JS/TS support (Phase 3.5)."""

from pathlib import Path

from typer.testing import CliRunner

from cloak.cli import app
from cloak.context.generator import generate
from cloak.context.js_redactor import (
    language_for_extension,
    transform_js_like_source,
)
from cloak.policy import Policy

runner = CliRunner()


# ---------- language detection ----------


def test_language_for_extension_maps_known_suffixes() -> None:
    assert language_for_extension(".js") == "javascript"
    assert language_for_extension(".mjs") == "javascript"
    assert language_for_extension(".cjs") == "javascript"
    assert language_for_extension(".jsx") == "javascript"
    assert language_for_extension(".ts") == "typescript"
    assert language_for_extension(".tsx") == "tsx"
    assert language_for_extension(".PY") is None
    assert language_for_extension(".rb") is None


# ---------- redactor unit tests ----------


def test_redactor_redacts_function_declaration_body() -> None:
    src = "function helper(x) { return x * 2; }"
    out = transform_js_like_source(src, "javascript")
    assert "return x * 2" not in out
    assert "[REDACTED BY CLOAK]" in out
    # Signature kept
    assert "function helper(x)" in out


def test_redactor_redacts_method_bodies() -> None:
    src = (
        "class Engine {\n"
        "  constructor(config) { this.config = config; }\n"
        "  calculate(c) { return c * 2; }\n"
        "}\n"
    )
    out = transform_js_like_source(src, "javascript")
    assert "this.config = config" not in out
    assert "return c * 2" not in out
    # Class shape + method signatures kept
    assert "class Engine" in out
    assert "constructor(config)" in out
    assert "calculate(c)" in out


def test_redactor_redacts_arrow_with_block_body() -> None:
    src = "const f = (a, b) => { return a + b; };"
    out = transform_js_like_source(src, "javascript")
    assert "return a + b" not in out
    assert "[REDACTED BY CLOAK]" in out
    assert "(a, b) =>" in out


def test_redactor_redacts_arrow_with_expression_body() -> None:
    src = "const f = (n) => n * 7;"
    out = transform_js_like_source(src, "javascript")
    assert "n * 7" not in out
    assert "[REDACTED BY CLOAK]" in out
    assert "(n) =>" in out


def test_redactor_redacts_module_level_proprietary_table() -> None:
    src = "const _TIERS = { low: 0.0, high: 0.15 };\nconst publicData = { foo: 1 };\n"
    out = transform_js_like_source(src, "javascript")
    # Proprietary table value gone
    assert "0.15" not in out
    assert "high:" not in out
    # Public (non-UPPER_SNAKE) data preserved
    assert "{ foo: 1 }" in out


def test_redactor_redacts_proprietary_array() -> None:
    src = "const _BUNDLE_RULES = [['a','b',0.04], ['c','d',0.075]];"
    out = transform_js_like_source(src, "javascript")
    assert "0.075" not in out
    assert "[REDACTED BY CLOAK]" in out


def test_redactor_does_not_redact_non_uppercase_names() -> None:
    src = "const tiers = { low: 0.0, high: 0.15 };"
    out = transform_js_like_source(src, "javascript")
    assert "0.15" in out
    assert "[REDACTED BY CLOAK]" not in out


def test_redactor_typescript_keeps_interfaces_and_types() -> None:
    src = (
        "export interface Customer { id: string; tier: 'low' | 'high'; }\n"
        "export type Result = { ok: boolean };\n"
        "export function check(c: Customer): boolean { return c.id.length > 0; }\n"
    )
    out = transform_js_like_source(src, "typescript")
    # Type definitions are shapes — they stay.
    assert "interface Customer" in out
    assert "type Result" in out
    assert "tier: 'low' | 'high'" in out
    # Function body redacted
    assert "c.id.length" not in out
    assert "[REDACTED BY CLOAK]" in out


def test_redactor_handles_nested_functions() -> None:
    """Inner functions are part of the outer function body and disappear with it."""
    src = "function outer() {\n  function inner() { return 42; }\n  return inner();\n}\n"
    out = transform_js_like_source(src, "javascript")
    # Outer signature kept; entire body (including inner function) gone.
    assert "function outer()" in out
    assert "return 42" not in out
    assert "function inner" not in out


def test_redactor_returns_original_when_no_function_or_table() -> None:
    src = "const x = 1;\nconst y = 2;\n"
    out = transform_js_like_source(src, "javascript")
    assert out == src


def test_redactor_handles_invalid_source_gracefully() -> None:
    """Unparseable JS shouldn't raise. Tree-sitter recovers; we may or may not redact bits."""
    src = "function broken( {{{"
    # Should not raise.
    transform_js_like_source(src, "javascript")


# ---------- generator integration ----------


def _sample_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "lib.js").write_text(
        "const _SECRET_RATES = { gold: 0.4 };\n"
        "export function compute(x) { return x * _SECRET_RATES.gold; }\n"
    )
    (repo / "types.ts").write_text(
        "export interface Order { id: string; }\n"
        "export const formatId = (o: Order): string => o.id.toUpperCase();\n"
    )
    return repo


def test_generator_includes_js_section_with_correct_fence(tmp_path: Path) -> None:
    repo = _sample_repo(tmp_path)
    md = generate(list(repo.iterdir()), Policy(), repo_root=repo)
    assert "## `lib.js`" in md
    assert "```javascript\n" in md
    assert "[REDACTED BY CLOAK]" in md
    # Proprietary table redacted
    assert "0.4" not in md


def test_generator_includes_ts_section_with_correct_fence(tmp_path: Path) -> None:
    repo = _sample_repo(tmp_path)
    md = generate(list(repo.iterdir()), Policy(), repo_root=repo)
    assert "## `types.ts`" in md
    assert "```typescript\n" in md
    assert "interface Order" in md  # type shape kept
    assert "toUpperCase" not in md  # arrow body redacted


def test_cli_context_works_against_mixed_repo(tmp_path: Path) -> None:
    repo = tmp_path / "mixed"
    repo.mkdir()
    (repo / "py_module.py").write_text("def foo(): return 1\n")
    (repo / "js_module.js").write_text("function bar(x) { return x; }")
    result = runner.invoke(app, ["context", str(repo)])
    assert result.exit_code == 0
    assert "## `py_module.py`" in result.stdout
    assert "## `js_module.js`" in result.stdout
    assert "[REDACTED BY CLOAK]" in result.stdout
