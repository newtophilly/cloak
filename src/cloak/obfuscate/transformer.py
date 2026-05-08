"""Phase 4 — Python AST transformer for `cloak obfuscate`.

v1 scope: per-file transformation that
  - renames module-level identifiers starting with `_` (underscore-private convention),
    skipping anything in `policy.public_api`;
  - optionally strips docstrings per `policy.obfuscate_defaults.strip_docstrings`.

What v1 deliberately does NOT do (deferred — see docs/BUILD_PLAN.md):
  - Cross-file rename. If `from foo import _bar` exists, the import keeps `_bar` but the
    target file rewrites to `_a000`; tests will catch this via `--verify` and fail safely.
  - Class method renaming (could be public API).
  - String literal encoding (footgun — strings are often SQL/log keys).
  - Control-flow flattening (only in --profile aggressive, future).

Output uses `ast.unparse` which loses comments and exact formatting. This is intentional for
obfuscate output: comments are stripped for free, and obfuscated code is not meant to be read.
"""

import ast
from dataclasses import dataclass, field

from cloak.policy import Policy


@dataclass
class TransformResult:
    """Result of transforming a single file."""

    source_text: str
    output_text: str
    rename_map: dict[str, str] = field(default_factory=dict)
    docstrings_stripped: int = 0


def transform_python_source(
    source: str, policy: Policy, file_label: str = "<source>"
) -> TransformResult:
    """Apply v1 obfuscation to a Python source string. Returns the transformed text + metadata."""
    tree = ast.parse(source, filename=file_label)

    module_private_names = _collect_module_private_names(tree, policy)
    rename_map = _build_rename_map(module_private_names)

    strip_docstrings = policy.obfuscate_defaults.strip_docstrings
    transformer = _ObfuscatingTransformer(rename_map=rename_map, strip_docstrings=strip_docstrings)
    transformed = transformer.visit(tree)
    ast.fix_missing_locations(transformed)

    output = ast.unparse(transformed)
    return TransformResult(
        source_text=source,
        output_text=output,
        rename_map=dict(rename_map),
        docstrings_stripped=transformer.docstrings_stripped,
    )


def _collect_module_private_names(tree: ast.Module, policy: Policy) -> list[str]:
    """Collect names defined at module level that start with `_` and are not in public_api."""
    public_api = set(policy.public_api)
    names: list[str] = []
    seen: set[str] = set()

    for stmt in tree.body:
        candidates: list[str] = []
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            candidates.append(stmt.name)
        elif isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if isinstance(target, ast.Name):
                    candidates.append(target.id)
        elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
            candidates.append(stmt.target.id)

        for name in candidates:
            if (
                name.startswith("_")
                and not name.startswith("__")
                and name not in seen
                and name not in public_api
                and not _matches_public_api_pattern(name, public_api)
            ):
                seen.add(name)
                names.append(name)
    return names


def _matches_public_api_pattern(name: str, public_api: set[str]) -> bool:
    """Crude wildcard match against names like `Foo.*` in public_api.

    v1 only handles the trailing-`.*` case for module-level names (which never have a dot
    in their own identifier). The dotted/wildcard rules are mostly for class-method
    protection in future phases.
    """
    for pattern in public_api:
        if pattern == name:
            return True
        # Simple "*" suffix: matches if name starts with the prefix. Useful for namespaces.
        if pattern.endswith("*") and name.startswith(pattern.rstrip("*")):
            return True
    return False


def _build_rename_map(names: list[str]) -> dict[str, str]:
    return {name: f"_a{i:03d}" for i, name in enumerate(names)}


class _ObfuscatingTransformer(ast.NodeTransformer):
    """Apply the rename map to Name references/definitions; optionally strip docstrings."""

    def __init__(self, *, rename_map: dict[str, str], strip_docstrings: bool) -> None:
        self.rename_map = rename_map
        self.strip_docstrings = strip_docstrings
        self.docstrings_stripped = 0

    # --- name renaming ----------------------------------------------------------------

    def visit_Name(self, node: ast.Name) -> ast.AST:
        if node.id in self.rename_map:
            return ast.copy_location(ast.Name(id=self.rename_map[node.id], ctx=node.ctx), node)
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        if node.name in self.rename_map:
            node.name = self.rename_map[node.name]
        self._maybe_strip_docstring(node)
        self.generic_visit(node)
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AST:
        if node.name in self.rename_map:
            node.name = self.rename_map[node.name]
        self._maybe_strip_docstring(node)
        self.generic_visit(node)
        return node

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.AST:
        if node.name in self.rename_map:
            node.name = self.rename_map[node.name]
        self._maybe_strip_docstring(node)
        self.generic_visit(node)
        return node

    def visit_Module(self, node: ast.Module) -> ast.AST:
        self._maybe_strip_docstring(node)
        self.generic_visit(node)
        return node

    # --- docstring stripping (in-place mutation) -------------------------------------

    def _maybe_strip_docstring(
        self, node: ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef
    ) -> None:
        if not self.strip_docstrings or not node.body:
            return
        first = node.body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            node.body = node.body[1:] or [ast.Pass()]
            self.docstrings_stripped += 1
