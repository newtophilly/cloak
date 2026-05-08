"""Stub for Phase 2 — secrets scanner.

The real implementation will wrap `detect-secrets` or `gitleaks` and layer policy `secret_rules`
on top. Reuse is intentional and documented.
"""

from pathlib import Path

from cloak.policy import Policy


def scan(paths: list[Path], policy: Policy) -> list[dict[str, object]]:
    """Run the scanner over `paths` and return findings.

    Returns a list of finding dicts with keys: severity, file, line, rule_id, redacted_preview,
    suggested_action. Phase 1 raises NotImplementedError.
    """
    del paths, policy
    raise NotImplementedError("scan: Phase 2 not yet implemented")
