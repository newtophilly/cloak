"""Phase 5 — JS/TS obfuscation transformer.

Per-file rename of module-level identifiers that start with `_` (and aren't dunder-like or
all underscores). Same shape as the Python obfuscator: collect candidate names, build a
deterministic rename map (`_a000`, `_a001`, ...), then byte-splice every reference of those
names in the file with their new identifier.

Tree-sitter is used as a parser only — we don't unparse. Edits happen at the byte level so
all formatting and comments outside renamed identifiers survive.

v1 limitations (deferred — caught by `--verify`):
  - Cross-file rename. If `import { _helper } from './lib'`, the import keeps `_helper` but
    the target file renames it; tests will fail and the user knows immediately.
  - Local-variable shadowing. If a function body defines `const _helper = ...` shadowing a
    module-level `_helper`, both get renamed; tests will catch logic bugs that arise.
  - Shorthand property in object literals (`{ _helper }`) and destructuring patterns
    (`const { _helper } = ...`) are NOT renamed (would change object shape silently). This
    means a module-level `_helper` referenced via shorthand goes un-renamed there.
  - Class methods are NOT renamed (could be public API).
"""

from dataclasses import dataclass, field

from tree_sitter import Node, Parser

from cloak.context.js_redactor import JsLikeKind, _get_language
from cloak.policy import Policy

_RENAMEABLE_IDENTIFIER_TYPES = {"identifier", "type_identifier"}

_DEFINITION_NODE_TYPES = {
    "function_declaration",
    "generator_function_declaration",
    "class_declaration",
    "lexical_declaration",
    "variable_declaration",
}


@dataclass
class JsTransformResult:
    """Result of transforming a single JS/TS file."""

    source_text: str
    output_text: str
    rename_map: dict[str, str] = field(default_factory=dict)


def transform_js_like_source(
    source: str,
    kind: JsLikeKind,
    policy: Policy,
) -> JsTransformResult:
    """Apply v1 obfuscation to a JS/TS source string. Returns transformed text + rename map."""
    src_bytes = source.encode("utf-8")
    parser = Parser(_get_language(kind))
    tree = parser.parse(src_bytes)

    names = _collect_top_level_private_names(tree.root_node, src_bytes, policy)
    rename_map = _build_rename_map(names)

    if not rename_map:
        return JsTransformResult(source_text=source, output_text=source)

    edits: list[tuple[int, int, bytes]] = []
    _collect_rename_edits(tree.root_node, src_bytes, rename_map, edits)

    if not edits:
        return JsTransformResult(source_text=source, output_text=source, rename_map=rename_map)

    edits.sort(key=lambda e: e[0], reverse=True)
    out = bytearray(src_bytes)
    for start, end, replacement in edits:
        out[start:end] = replacement
    return JsTransformResult(
        source_text=source,
        output_text=out.decode("utf-8", errors="replace"),
        rename_map=rename_map,
    )


def _collect_top_level_private_names(root_node: Node, src: bytes, policy: Policy) -> list[str]:
    """Find top-level definitions whose name starts with `_`. Skips dunders, all-underscore."""
    names: list[str] = []
    seen: set[str] = set()
    public_api = set(policy.public_api)

    for child in root_node.children:
        # `export ...` wraps a real declaration — peek through one level.
        target = child
        if child.type == "export_statement":
            for inner in child.children:
                if inner.type in _DEFINITION_NODE_TYPES:
                    target = inner
                    break

        for name in _extract_definition_names(target, src):
            if _should_rename(name, public_api) and name not in seen:
                seen.add(name)
                names.append(name)

    return names


def _extract_definition_names(node: Node, src: bytes) -> list[str]:
    """Return the symbol names this top-level definition introduces."""
    if node.type in {
        "function_declaration",
        "generator_function_declaration",
        "class_declaration",
    }:
        name_node = node.child_by_field_name("name")
        if name_node is not None:
            return [_text(name_node, src)]
        return []

    if node.type in {"lexical_declaration", "variable_declaration"}:
        result: list[str] = []
        for declarator in node.children:
            if declarator.type != "variable_declarator":
                continue
            name_node = declarator.child_by_field_name("name")
            # Only handle the simple `const _foo = ...` case. Destructuring patterns
            # (object_pattern, array_pattern) are skipped — too risky to rename in v1.
            if name_node is not None and name_node.type == "identifier":
                result.append(_text(name_node, src))
        return result

    return []


def _should_rename(name: str, public_api: set[str]) -> bool:
    if not name.startswith("_"):
        return False
    if name.startswith("__"):
        # Dunder-like; conservative skip (e.g. `__dirname` in CommonJS).
        return False
    if all(c == "_" for c in name):
        return False
    if name in public_api:
        return False
    for pattern in public_api:
        if pattern.endswith("*") and name.startswith(pattern.rstrip("*")):
            return False
    return True


def _build_rename_map(names: list[str]) -> dict[str, str]:
    return {name: f"_a{i:03d}" for i, name in enumerate(names)}


def _collect_rename_edits(
    node: Node,
    src: bytes,
    rename_map: dict[str, str],
    edits: list[tuple[int, int, bytes]],
) -> None:
    """Walk the tree; replace `identifier`/`type_identifier` nodes whose text is in the map.

    Critically: we do NOT touch `property_identifier` (member access — `.foo` is a different
    scope), `shorthand_property_identifier` (would silently change object shape), or
    destructuring identifiers — see v1 limitations in module docstring.
    """
    if node.type in _RENAMEABLE_IDENTIFIER_TYPES:
        text = _text(node, src)
        if text in rename_map:
            edits.append((node.start_byte, node.end_byte, rename_map[text].encode("utf-8")))
        return  # leaf

    for child in node.children:
        _collect_rename_edits(child, src, rename_map, edits)


def _text(node: Node, src: bytes) -> str:
    return src[node.start_byte : node.end_byte].decode("utf-8", errors="replace")
