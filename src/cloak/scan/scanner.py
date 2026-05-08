"""Phase 2 — secrets scanner.

Wraps `detect-secrets` for the heavy lifting (years of regex/entropy tuning) and layers in
the policy's custom `secret_rules` on top. Raw secrets are never returned or printed —
only redacted previews.
"""

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from detect_secrets.core.secrets_collection import SecretsCollection
from detect_secrets.settings import default_settings

from cloak.policy import Policy

# detect-secrets output severity defaults to "high" — most plugin types correspond to real
# credentials. We do not try to second-guess that here. Policy-custom rules carry their own
# severity from the policy file.
_DEFAULT_DETECT_SECRETS_SEVERITY = "high"


@dataclass
class Finding:
    """A single secret or proprietary-marker finding.

    `redacted_preview` is the only secret-derived value safe to print. The raw secret is never
    stored on this object.
    """

    severity: str
    file: str
    line: int
    rule_id: str
    redacted_preview: str
    suggested_action: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _redact(value: str) -> str:
    """Return a preview that confirms the shape of a secret without revealing it."""
    if not value:
        return ""
    n = len(value)
    if n <= 8:
        return "*" * n
    keep = 4
    return f"{value[:keep]}{'*' * (n - keep * 2)}{value[-keep:]}"


def _scan_with_detect_secrets(file_path: Path, repo_root: Path) -> list[Finding]:
    """Run detect-secrets against a single file and yield Findings."""
    findings: list[Finding] = []
    try:
        with default_settings():
            collection = SecretsCollection()
            collection.scan_file(str(file_path))
    except Exception:
        # detect-secrets can raise on weird files (binary, encoding issues, etc.); skip them.
        return findings

    rel = _safe_rel(file_path, repo_root)
    for _filename, secret_set in collection.data.items():
        for secret in secret_set:
            preview = _redact(secret.secret_value or "")
            findings.append(
                Finding(
                    severity=_DEFAULT_DETECT_SECRETS_SEVERITY,
                    file=rel,
                    line=int(secret.line_number),
                    rule_id=f"detect-secrets/{secret.type}",
                    redacted_preview=preview,
                    suggested_action="Rotate this credential and remove it from source.",
                )
            )
    return findings


def _scan_with_policy_rules(file_path: Path, policy: Policy, repo_root: Path) -> list[Finding]:
    """Run the policy's custom regex rules against a file and yield Findings."""
    if not policy.secret_rules:
        return []

    try:
        text = file_path.read_text(encoding="utf-8", errors="strict")
    except (UnicodeDecodeError, OSError):
        return []  # Binary or unreadable file; let detect-secrets handle skipping.

    rel = _safe_rel(file_path, repo_root)
    findings: list[Finding] = []
    for rule in policy.secret_rules:
        try:
            compiled = re.compile(rule.pattern)
        except re.error:
            continue  # Skip malformed user regex; surface in a future `cloak policy lint`.
        for line_no, line in enumerate(text.splitlines(), start=1):
            for match in compiled.finditer(line):
                findings.append(
                    Finding(
                        severity=rule.severity,
                        file=rel,
                        line=line_no,
                        rule_id=f"policy/{rule.id}",
                        redacted_preview=_redact(match.group(0)),
                        suggested_action=f"Review the match against policy rule '{rule.id}'.",
                    )
                )
    return findings


def _safe_rel(file_path: Path, repo_root: Path) -> str:
    """Return file_path relative to repo_root if possible; absolute string otherwise."""
    try:
        return str(file_path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        return str(file_path)


def scan(paths: list[Path], policy: Policy, repo_root: Path | None = None) -> list[Finding]:
    """Scan `paths` for secrets and proprietary markers, returning a list of Findings.

    `repo_root` controls relative-path display in findings. If None, paths are reported
    relative to their own parent directory.
    """
    if repo_root is None:
        repo_root = paths[0].parent if paths else Path.cwd()

    all_findings: list[Finding] = []
    for path in paths:
        if not path.is_file():
            continue
        all_findings.extend(_scan_with_detect_secrets(path, repo_root))
        all_findings.extend(_scan_with_policy_rules(path, policy, repo_root))

    # Stable order: by severity (high → low), then file, then line.
    severity_rank = {"high": 0, "medium": 1, "low": 2}
    all_findings.sort(key=lambda f: (severity_rank.get(f.severity, 99), f.file, f.line, f.rule_id))
    return all_findings
