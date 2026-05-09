"""Per-file redaction stats for `cloak diff-context`.

Re-walks each source file with the same predicates `cloak context` uses, and counts what
*would* be redacted instead of producing the markdown view. The point: developers want to
see what got removed before they trust the transformation. Output is a small terminal
table plus a JSON mode for CI / agents.
"""

import ast
from dataclasses import dataclass, field
from pathlib import Path

from cloak.context.generator import (
    _ENUM_BASE_NAMES,
    _is_docstring,
    _is_enum_class,
    _is_proprietary_table,
)
from cloak.context.js_redactor import (
    _VALUE_REPLACEMENT,
    language_for_extension,
    transform_js_like_source,
)
from cloak.policy import Policy


@dataclass
class FileDiff:
    path: Path
    rel: str
    language: str
    bytes_before: int = 0
    bytes_after: int = 0
    lines_before: int = 0
    lines_after: int = 0
    function_bodies_redacted: int = 0
    tables_redacted: int = 0
    docstrings_stripped: int = 0
    enum_classes_aliased: int = 0
    error: str | None = None

    @property
    def bytes_delta(self) -> int:
        return self.bytes_after - self.bytes_before

    @property
    def lines_delta(self) -> int:
        return self.lines_after - self.lines_before

    @property
    def reduction_pct(self) -> float:
        if self.bytes_before == 0:
            return 0.0
        return max(0.0, (1.0 - self.bytes_after / self.bytes_before) * 100.0)

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.rel,
            "language": self.language,
            "bytes_before": self.bytes_before,
            "bytes_after": self.bytes_after,
            "bytes_delta": self.bytes_delta,
            "lines_before": self.lines_before,
            "lines_after": self.lines_after,
            "lines_delta": self.lines_delta,
            "function_bodies_redacted": self.function_bodies_redacted,
            "tables_redacted": self.tables_redacted,
            "docstrings_stripped": self.docstrings_stripped,
            "enum_classes_aliased": self.enum_classes_aliased,
            "reduction_pct": round(self.reduction_pct, 1),
            "error": self.error,
        }


@dataclass
class DiffSummary:
    files: list[FileDiff] = field(default_factory=list)

    @property
    def bytes_before(self) -> int:
        return sum(f.bytes_before for f in self.files)

    @property
    def bytes_after(self) -> int:
        return sum(f.bytes_after for f in self.files)

    @property
    def reduction_pct(self) -> float:
        if self.bytes_before == 0:
            return 0.0
        return max(0.0, (1.0 - self.bytes_after / self.bytes_before) * 100.0)

    @property
    def function_bodies_redacted(self) -> int:
        return sum(f.function_bodies_redacted for f in self.files)

    @property
    def tables_redacted(self) -> int:
        return sum(f.tables_redacted for f in self.files)

    @property
    def docstrings_stripped(self) -> int:
        return sum(f.docstrings_stripped for f in self.files)

    @property
    def enum_classes_aliased(self) -> int:
        return sum(f.enum_classes_aliased for f in self.files)


def diff_context(
    paths: list[Path],
    policy: Policy,
    *,
    strict: bool = False,
    repo_root: Path | None = None,
) -> DiffSummary:
    """Compute per-file redaction stats matching what `cloak context` would emit."""
    if repo_root is None:
        repo_root = paths[0].parent if paths else Path.cwd()

    keep_docstrings = policy.context_defaults.keep_docstrings and not strict
    alias_enums = policy.context_defaults.alias_enums or strict

    out = DiffSummary()
    for p in paths:
        if not p.is_file():
            continue
        rel = _safe_rel(p, repo_root)
        if p.suffix == ".py":
            out.files.append(
                _diff_python(p, rel, keep_docstrings=keep_docstrings, alias_enums=alias_enums)
            )
        elif language_for_extension(p.suffix) is not None:
            kind = language_for_extension(p.suffix)
            assert kind is not None
            out.files.append(_diff_js_like(p, rel, kind))
    return out


def _diff_python(
    path: Path,
    rel: str,
    *,
    keep_docstrings: bool,
    alias_enums: bool,
) -> FileDiff:
    fd = FileDiff(path=path, rel=rel, language="python")
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        fd.error = f"unreadable: {e}"
        return fd

    fd.bytes_before = len(text.encode("utf-8"))
    fd.lines_before = text.count("\n") + (0 if text.endswith("\n") or not text else 1)

    try:
        tree = ast.parse(text)
    except SyntaxError as e:
        fd.error = f"parse error: {e.msg}"
        return fd

    _count_python(
        tree,
        fd,
        keep_docstrings=keep_docstrings,
        alias_enums=alias_enums,
    )

    redactor_text = _python_redacted_size(
        tree, keep_docstrings=keep_docstrings, alias_enums=alias_enums
    )
    fd.bytes_after = len(redactor_text.encode("utf-8"))
    fd.lines_after = redactor_text.count("\n") + (
        0 if redactor_text.endswith("\n") or not redactor_text else 1
    )
    return fd


def _count_python(
    tree: ast.AST,
    fd: FileDiff,
    *,
    keep_docstrings: bool,
    alias_enums: bool,
) -> None:
    if isinstance(tree, ast.Module):
        for i, stmt in enumerate(tree.body):
            if i == 0 and _is_docstring(stmt):
                if not keep_docstrings:
                    fd.docstrings_stripped += 1
                continue
            if _is_proprietary_table(stmt):
                fd.tables_redacted += 1
                continue
            _count_python_stmt(stmt, fd, keep_docstrings=keep_docstrings, alias_enums=alias_enums)


def _count_python_stmt(
    node: ast.AST,
    fd: FileDiff,
    *,
    keep_docstrings: bool,
    alias_enums: bool,
) -> None:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        fd.function_bodies_redacted += 1
        if node.body and _is_docstring(node.body[0]) and not keep_docstrings:
            fd.docstrings_stripped += 1
        return
    if isinstance(node, ast.ClassDef):
        if alias_enums and _is_enum_class(node):
            fd.enum_classes_aliased += 1
            # Enum classes get rewritten wholesale; don't double-count their members.
            if node.body and _is_docstring(node.body[0]) and not keep_docstrings:
                fd.docstrings_stripped += 1
            return
        for i, child in enumerate(node.body):
            if i == 0 and _is_docstring(child):
                if not keep_docstrings:
                    fd.docstrings_stripped += 1
                continue
            _count_python_stmt(child, fd, keep_docstrings=keep_docstrings, alias_enums=alias_enums)


def _python_redacted_size(
    tree: ast.AST,
    *,
    keep_docstrings: bool,
    alias_enums: bool,
) -> str:
    # Cheap: re-run the real redactor so the byte count exactly matches what `cloak context`
    # would emit. We import lazily to avoid an import cycle at module load.
    from cloak.context.generator import _Redactor

    redactor = _Redactor(keep_docstrings=keep_docstrings, alias_enums=alias_enums)
    redacted = redactor.visit(tree)
    ast.fix_missing_locations(redacted)
    return ast.unparse(redacted)


def _diff_js_like(path: Path, rel: str, kind: str) -> FileDiff:
    language_label = (
        "tsx" if kind == "tsx" else ("typescript" if kind == "typescript" else "javascript")
    )
    fd = FileDiff(path=path, rel=rel, language=language_label)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        fd.error = f"unreadable: {e}"
        return fd

    fd.bytes_before = len(text.encode("utf-8"))
    fd.lines_before = text.count("\n") + (0 if text.endswith("\n") or not text else 1)

    redacted = transform_js_like_source(text, kind)  # type: ignore[arg-type]
    fd.bytes_after = len(redacted.encode("utf-8"))
    fd.lines_after = redacted.count("\n") + (0 if redacted.endswith("\n") or not redacted else 1)

    # `_VALUE_REPLACEMENT` contains the body-marker text as a substring (both share the
    # `/* [REDACTED BY CLOAK] */` fingerprint). Count value-style first, then derive body
    # count from the total minus value occurrences.
    fingerprint = "/* [REDACTED BY CLOAK] */"
    value_marker = _VALUE_REPLACEMENT.decode("utf-8").strip()
    total_markers = redacted.count(fingerprint)
    value_count = redacted.count(value_marker)
    fd.function_bodies_redacted = max(0, total_markers - value_count)
    # In JS we don't separate "table" vs "arrow body expression" — both use VALUE marker.
    # Count just the upper-case-named declarations as tables to avoid lying.
    fd.tables_redacted = _count_js_proprietary_tables(text)
    return fd


def _count_js_proprietary_tables(source: str) -> int:
    """Heuristic count of module-level UPPER_SNAKE = {...}/[...] declarations.

    Mirrors `_is_proprietary_table_name` in js_redactor without re-parsing.
    """
    import re

    pattern = re.compile(
        r"^\s*(?:const|let|var)\s+([A-Z_][A-Z0-9_]*)\s*=\s*[\{\[]",
        re.MULTILINE,
    )
    return sum(1 for m in pattern.finditer(source) if m.group(1).replace("_", ""))


def _safe_rel(p: Path, repo_root: Path) -> str:
    try:
        return str(p.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        return str(p)


# Re-export so callers don't have to reach into generator.py for these.
__all__ = [
    "_ENUM_BASE_NAMES",
    "DiffSummary",
    "FileDiff",
    "diff_context",
]
