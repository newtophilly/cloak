"""Manifest emitted alongside an obfuscated copy of a repo.

The manifest is the audit-trail artifact for compliance buyers: it records what was transformed,
under which policy, and provides cryptographic hashes of source and output for later verification.
Optional signing (Phase 4+) adds vendor-identity proof to the bundle.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class Manifest:
    """Schema for `cloak-manifest.json`."""

    cloak_version: str
    ruleset_version: str | None = None
    generated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    source_files: dict[str, str] = field(default_factory=dict)  # rel_path -> sha256
    output_files: dict[str, str] = field(default_factory=dict)  # rel_path -> sha256
    rename_map: dict[str, str] = field(default_factory=dict)
    policy_hash: str | None = None
    policy_snapshot: str | None = None
    verify_command: str | None = None
    verify_passed: bool | None = None
    signature: str | None = None  # populated when --sign is passed (future)
