"""Filesystem walking with `.cloakignore` support."""

from collections.abc import Iterator
from pathlib import Path

import pathspec

from cloak.policy import Policy

_DEFAULT_IGNORES = [
    "__pycache__/",
    "*.pyc",
    "*.pyo",
    ".git/",
    ".venv/",
    "venv/",
    "node_modules/",
    "dist/",
    "build/",
    "*.egg-info/",
    ".pytest_cache/",
    ".mypy_cache/",
    ".ruff_cache/",
    ".DS_Store",
]


def _load_cloakignore(root: Path) -> "pathspec.PathSpec[pathspec.Pattern]":
    patterns = list(_DEFAULT_IGNORES)
    cloakignore = root / ".cloakignore"
    if cloakignore.is_file():
        with cloakignore.open("r", encoding="utf-8") as f:
            patterns.extend(
                line.rstrip() for line in f if line.strip() and not line.startswith("#")
            )
    return pathspec.PathSpec.from_lines("gitignore", patterns)


def walk_repo(path: Path, policy: Policy) -> Iterator[Path]:
    """Yield file paths under `path` that aren't ignored.

    `policy` is accepted for forward compatibility (policy.sensitive_paths may influence
    walking in later phases) but is currently unused.
    """
    del policy  # forward-compat hook
    root = path.resolve()
    if root.is_file():
        yield root
        return

    spec = _load_cloakignore(root)
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(root)
        if spec.match_file(str(rel)):
            continue
        yield p
