"""CLOAK policy file (`.cloakpolicy`) loader.

Sensible defaults are returned when no policy file is present, so commands work out of the box.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class ContextDefaults:
    keep_docstrings: bool = True
    redact_function_bodies: bool = True
    alias_enums: bool = False


@dataclass
class ObfuscateDefaults:
    rename_private: bool = True
    rename_public_api: bool = False
    encode_strings: bool = False
    strip_docstrings: bool = False
    profile: str = "standard"


@dataclass
class SecretRule:
    id: str
    pattern: str
    severity: str = "medium"


@dataclass
class Policy:
    """Parsed `.cloakpolicy` contents.

    Defaults represent the policy applied when no file is found, so a freshly cloned project
    gets safe-by-default behavior even before a maintainer commits a policy file.
    """

    version: int = 1
    sensitive_paths: list[str] = field(default_factory=list)
    public_api: list[str] = field(default_factory=list)
    secret_rules: list[SecretRule] = field(default_factory=list)
    allow_strings: list[str] = field(default_factory=list)
    context_defaults: ContextDefaults = field(default_factory=ContextDefaults)
    obfuscate_defaults: ObfuscateDefaults = field(default_factory=ObfuscateDefaults)
    source: Path | None = None


def load_policy(path: Path | None) -> Policy:
    """Load a `.cloakpolicy` file, or return defaults if `path` is None or missing."""
    if path is None or not path.is_file():
        return Policy()

    with path.open("r", encoding="utf-8") as f:
        raw: dict[str, Any] = yaml.safe_load(f) or {}

    return Policy(
        version=int(raw.get("version", 1)),
        sensitive_paths=list(raw.get("sensitive_paths", [])),
        public_api=list(raw.get("public_api", [])),
        secret_rules=[
            SecretRule(
                id=r["id"],
                pattern=r["pattern"],
                severity=r.get("severity", "medium"),
            )
            for r in raw.get("secret_rules", [])
        ],
        allow_strings=list(raw.get("allow_strings", [])),
        context_defaults=ContextDefaults(**(raw.get("context_defaults") or {})),
        obfuscate_defaults=ObfuscateDefaults(**(raw.get("obfuscate_defaults") or {})),
        source=path,
    )


def find_policy(start: Path) -> Path | None:
    """Walk up from `start` looking for `.cloakpolicy`. Return None if not found."""
    current = start.resolve()
    if current.is_file():
        current = current.parent
    while True:
        candidate = current / ".cloakpolicy"
        if candidate.is_file():
            return candidate
        if current == current.parent:
            return None
        current = current.parent
