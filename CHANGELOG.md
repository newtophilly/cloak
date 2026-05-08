# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Phase 0: validation experiment proving the redaction strategy on a fake industrial-automation pricing engine. Documented in `docs/research/`.
- Phase 1: package scaffold, `typer`-based CLI with `scan`, `context`, `obfuscate` subcommands, `.cloakpolicy` YAML loader, `.cloakignore` support, repo walker, smoke tests.
- Phase 2: `cloak scan` is now functional. Wraps `detect-secrets` and layers in `policy.secret_rules` custom regex rules. Returns structured `Finding` records with severity, file, line, rule_id, redacted preview, and suggested action. Raw secrets are never printed — every preview is redacted via `_redact()`. "Clean bill of health" terminal panel when no findings; rich table when findings exist. Exit code 1 on findings, 0 on clean. JSON contract documented in `docs/AGENT_INTEGRATION.md`.
- Phase 3 (Python): `cloak context` is now functional for Python files. AST-based redactor replaces function/method bodies with `...` (stub-file convention), redacts module-level UPPER_SNAKE constants holding dict/list/set/tuple literals (the "proprietary tables" pattern from the Phase 0 case study), preserves imports, class shapes, signatures, and docstrings. `--strict` mode aliases enum values to opaque names (`NORTHEAST = 'NE'` → `VALUE_0 = 'V0'`) and strips all docstrings — justified by the Phase 0 adversarial probe finding. CLI supports `--out FILE`, `--copy` (best-effort across pbcopy/xclip/wl-copy/clip.exe), and `--json` status mode. Generated markdown carries a stable header comment with version, policy source, and strict flag for downstream tooling. JS/TS lands in Phase 3.5 via tree-sitter.
- `docs/AGENT_INTEGRATION.md`: agent-readable integration spec for tools that call CLOAK as a subprocess (Codex, Claude, custom).
- README "Integrations" section linking fob and the agent guide.
- Build plan and competitive landscape research published in `docs/`.
