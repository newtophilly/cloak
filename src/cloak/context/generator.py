"""Stub for Phase 3 — safe context generator.

Will use `tree-sitter` for cross-language structural parsing (Python + JS/TS) and emit a
markdown view that preserves imports, class shapes, signatures, and docstrings while redacting
function bodies and proprietary tables. `strict=True` additionally aliases enum values and
paraphrases docstrings (justified by Phase 0 adversarial testing).
"""

from pathlib import Path

from cloak.policy import Policy


def generate(paths: list[Path], policy: Policy, *, strict: bool = False) -> str:
    """Generate redacted markdown safe to paste into an LLM.

    Phase 1 raises NotImplementedError.
    """
    del paths, policy, strict
    raise NotImplementedError("context: Phase 3 not yet implemented")
