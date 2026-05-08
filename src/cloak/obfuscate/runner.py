"""Phase 4 — orchestrator for `cloak obfuscate`.

Pipeline:
  1. Validate output directory (must not exist or be empty).
  2. Walk source repo (respecting `.cloakignore`) and copy/transform each file.
  3. Compute SHA-256 hashes for every source and output file.
  4. Write `cloak-manifest.json` with the audit-trail artifact.
  5. If `--verify "cmd"` was provided, run it inside the output dir; on non-zero exit,
     report failure (operation fails — this is the differentiator).
"""

import hashlib
import json
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from cloak import __version__
from cloak.context.js_redactor import language_for_extension
from cloak.filesystem import walk_repo
from cloak.obfuscate.js_transformer import transform_js_like_source
from cloak.obfuscate.manifest import Manifest
from cloak.obfuscate.transformer import transform_python_source
from cloak.policy import Policy


@dataclass
class ObfuscateResult:
    """Result of running the obfuscate pipeline. Returned to the CLI for display."""

    output_dir: Path
    manifest_path: Path
    files_copied: int = 0
    files_transformed: int = 0
    rename_map: dict[str, str] = field(default_factory=dict)
    verify_command: str | None = None
    verify_passed: bool | None = None
    verify_output: str | None = None


class ObfuscateError(Exception):
    """Raised when the obfuscate pipeline cannot proceed."""


def run_obfuscate(
    source_path: Path,
    output_dir: Path,
    policy: Policy,
    *,
    verify_command: str | None = None,
    profile: str = "standard",
) -> ObfuscateResult:
    """Execute the full obfuscate pipeline. Raises ObfuscateError on validation failures."""
    del profile  # accepted for forward compatibility; v1 ignores it
    source_path = source_path.resolve()
    output_dir = output_dir.resolve()

    if not source_path.exists():
        raise ObfuscateError(f"source path does not exist: {source_path}")

    if output_dir.exists() and any(output_dir.iterdir()):
        raise ObfuscateError(
            f"output directory is not empty: {output_dir}\n"
            "Refuse to overwrite. Pick an empty/nonexistent directory or remove this one first."
        )

    output_dir.mkdir(parents=True, exist_ok=True)

    repo_root = source_path if source_path.is_dir() else source_path.parent
    files = list(walk_repo(source_path, policy))

    rename_map_global: dict[str, str] = {}
    source_hashes: dict[str, str] = {}
    output_hashes: dict[str, str] = {}
    files_copied = 0
    files_transformed = 0

    for src_file in files:
        rel = src_file.relative_to(repo_root)
        out_file = output_dir / rel
        out_file.parent.mkdir(parents=True, exist_ok=True)

        source_hashes[str(rel)] = _sha256_file(src_file)

        js_like_kind = language_for_extension(src_file.suffix)

        if src_file.suffix == ".py":
            try:
                source_text = src_file.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                shutil.copy2(src_file, out_file)
                output_hashes[str(rel)] = _sha256_file(out_file)
                files_copied += 1
                continue

            try:
                py_result = transform_python_source(source_text, policy, file_label=str(rel))
            except SyntaxError:
                # Don't break on un-parseable files. Copy them through unchanged.
                shutil.copy2(src_file, out_file)
                output_hashes[str(rel)] = _sha256_file(out_file)
                files_copied += 1
                continue

            out_file.write_text(py_result.output_text, encoding="utf-8")
            output_hashes[str(rel)] = _sha256_file(out_file)
            for orig, new in py_result.rename_map.items():
                rename_map_global[f"{rel}:{orig}"] = new
            files_transformed += 1
        elif js_like_kind is not None:
            try:
                source_text = src_file.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                shutil.copy2(src_file, out_file)
                output_hashes[str(rel)] = _sha256_file(out_file)
                files_copied += 1
                continue

            js_result = transform_js_like_source(source_text, js_like_kind, policy)
            out_file.write_text(js_result.output_text, encoding="utf-8")
            output_hashes[str(rel)] = _sha256_file(out_file)
            for orig, new in js_result.rename_map.items():
                rename_map_global[f"{rel}:{orig}"] = new
            files_transformed += 1
        else:
            shutil.copy2(src_file, out_file)
            output_hashes[str(rel)] = _sha256_file(out_file)
            files_copied += 1

    verify_passed: bool | None = None
    verify_output: str | None = None
    if verify_command:
        verify_passed, verify_output = _run_verify(verify_command, output_dir)

    manifest = Manifest(
        cloak_version=__version__,
        ruleset_version=str(policy.version),
        source_files=source_hashes,
        output_files=output_hashes,
        rename_map=rename_map_global,
        policy_hash=_sha256_of_policy(policy),
        policy_snapshot=_policy_snapshot(policy),
        verify_command=verify_command,
        verify_passed=verify_passed,
    )
    manifest_path = output_dir / "cloak-manifest.json"
    manifest_path.write_text(json.dumps(_manifest_to_dict(manifest), indent=2), encoding="utf-8")

    return ObfuscateResult(
        output_dir=output_dir,
        manifest_path=manifest_path,
        files_copied=files_copied,
        files_transformed=files_transformed,
        rename_map=rename_map_global,
        verify_command=verify_command,
        verify_passed=verify_passed,
        verify_output=verify_output,
    )


def _run_verify(command: str, cwd: Path) -> tuple[bool, str]:
    """Run `command` as a shell command in `cwd`. Returns (passed, combined_output)."""
    try:
        completed = subprocess.run(
            command,
            shell=True,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=600,
        )
    except subprocess.TimeoutExpired:
        return False, "verify command timed out after 600s"
    except OSError as e:
        return False, f"verify command failed to start: {e}"

    output = (completed.stdout or "") + (completed.stderr or "")
    return completed.returncode == 0, output


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(64 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_of_policy(policy: Policy) -> str | None:
    if policy.source is None or not policy.source.exists():
        return None
    return _sha256_file(policy.source)


def _policy_snapshot(policy: Policy) -> str | None:
    if policy.source is None or not policy.source.exists():
        return None
    try:
        return policy.source.read_text(encoding="utf-8")
    except OSError:
        return None


def _manifest_to_dict(m: Manifest) -> dict[str, object]:
    return {
        "cloak_version": m.cloak_version,
        "ruleset_version": m.ruleset_version,
        "generated_at": m.generated_at,
        "source_files": m.source_files,
        "output_files": m.output_files,
        "rename_map": m.rename_map,
        "policy_hash": m.policy_hash,
        "policy_snapshot": m.policy_snapshot,
        "verify_command": m.verify_command,
        "verify_passed": m.verify_passed,
        "signature": m.signature,
    }
