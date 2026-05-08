"""Phase 3.5 — JS/TS redactor for `cloak context`.

Uses tree-sitter for cross-language structural parsing. Strategy:
  1. Parse the source into a syntax tree.
  2. Walk the tree collecting byte-range edits (replace function bodies, replace module-level
     proprietary-table values).
  3. Apply edits in reverse byte-order so earlier offsets remain valid.

We never need to "unparse" a tree — byte-splicing preserves all original formatting and
comments outside the redacted regions. Comments inside redacted bodies are gone, which is
intended.
"""

from typing import Literal

import tree_sitter_javascript as ts_js
import tree_sitter_typescript as ts_ts
from tree_sitter import Language, Parser

JsLikeKind = Literal["javascript", "typescript", "tsx"]

_BODY_REPLACEMENT = b" /* [REDACTED BY CLOAK] */ "
_VALUE_REPLACEMENT = b"/* [REDACTED BY CLOAK] */ null"

_FUNCTION_NODE_TYPES = {
    "function_declaration",
    "method_definition",
    "function_expression",
    "generator_function_declaration",
    "generator_function",
    "arrow_function",
}

# Cached Language objects — building them is non-trivial.
_LANGUAGE_CACHE: dict[JsLikeKind, Language] = {}


def _get_language(kind: JsLikeKind) -> Language:
    if kind not in _LANGUAGE_CACHE:
        if kind == "javascript":
            _LANGUAGE_CACHE[kind] = Language(ts_js.language())
        elif kind == "typescript":
            _LANGUAGE_CACHE[kind] = Language(ts_ts.language_typescript())
        elif kind == "tsx":
            _LANGUAGE_CACHE[kind] = Language(ts_ts.language_tsx())
        else:  # pragma: no cover — defensive
            raise ValueError(f"unknown language kind: {kind}")
    return _LANGUAGE_CACHE[kind]


def language_for_extension(suffix: str) -> JsLikeKind | None:
    """Map a file suffix (with the dot) to a tree-sitter language kind."""
    s = suffix.lower()
    if s in {".js", ".mjs", ".cjs", ".jsx"}:
        return "javascript"
    if s == ".ts":
        return "typescript"
    if s == ".tsx":
        return "tsx"
    return None


def transform_js_like_source(
    source: str,
    kind: JsLikeKind,
) -> str:
    """Redact function bodies and module-level proprietary tables in JS/TS source.

    Returns the transformed source; on parse failure or any unexpected error, returns the
    original source unchanged (callers can detect this by string equality or upstream
    framing).
    """
    src_bytes = source.encode("utf-8")
    parser = Parser(_get_language(kind))
    tree = parser.parse(src_bytes)

    edits: list[tuple[int, int, bytes]] = []
    _walk(tree.root_node, src_bytes, edits, in_function=False)

    if not edits:
        return source

    # Apply largest offsets first so earlier ones remain valid.
    edits.sort(key=lambda e: e[0], reverse=True)
    out = bytearray(src_bytes)
    for start, end, replacement in edits:
        out[start:end] = replacement
    return out.decode("utf-8", errors="replace")


def _walk(node, src: bytes, edits: list[tuple[int, int, bytes]], *, in_function: bool) -> None:  # type: ignore[no-untyped-def]
    if node.type in _FUNCTION_NODE_TYPES:
        body = node.child_by_field_name("body")
        if body is not None:
            if body.type == "statement_block":
                # Replace contents between `{` and `}` (preserve the braces).
                inner_start = body.start_byte + 1
                inner_end = body.end_byte - 1
                if inner_end > inner_start:
                    edits.append((inner_start, inner_end, _BODY_REPLACEMENT))
            elif node.type == "arrow_function":
                # Arrow function with expression body — replace the whole expression.
                edits.append((body.start_byte, body.end_byte, _VALUE_REPLACEMENT))
        # Do not recurse into function bodies — they're handled.
        return

    # Module-level proprietary table redaction (only outside functions).
    if not in_function and node.type in {"lexical_declaration", "variable_declaration"}:
        redacted_any_table = False
        for child in node.children:
            if child.type != "variable_declarator":
                continue
            name_node = child.child_by_field_name("name")
            value_node = child.child_by_field_name("value")
            if name_node is None or value_node is None:
                continue
            name = src[name_node.start_byte : name_node.end_byte].decode("utf-8", errors="replace")
            if _is_proprietary_table_name(name) and value_node.type in {"object", "array"}:
                edits.append((value_node.start_byte, value_node.end_byte, _VALUE_REPLACEMENT))
                redacted_any_table = True
        if redacted_any_table:
            # Whole declarator handled — skip recursion.
            return
        # Otherwise the declaration holds e.g. `const f = () => {...}` — fall through so the
        # arrow function body still gets redacted.

    for child in node.children:
        _walk(child, src, edits, in_function=in_function)


def _is_proprietary_table_name(name: str) -> bool:
    """Heuristic: name looks like UPPER_SNAKE_CASE (with optional leading underscores)."""
    stripped = name.lstrip("_")
    if not stripped:
        return False
    if not any(c.isalpha() for c in stripped):
        return False
    return stripped.replace("_", "").isupper()
