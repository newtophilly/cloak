# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.1] - 2026-05-08

### Added
- Phase 3.5: `cloak context` now redacts JavaScript and TypeScript via tree-sitter. Supported file extensions: `.js`, `.mjs`, `.cjs`, `.jsx`, `.ts`, `.tsx`. Function declarations, method definitions, function expressions, generator functions, and arrow functions (block- and expression-bodied) all have their bodies redacted with `/* [REDACTED BY CLOAK] */`. Module-level UPPER_SNAKE_CASE `const`/`let`/`var` declarations holding object or array literals are redacted (the same "proprietary tables" pattern used for Python). TypeScript `interface` and `type alias` declarations are preserved (type shapes carry no logic). Output is byte-spliced into the original source, so all formatting and comments outside redacted regions are preserved.

## [0.1.0] - 2026-05-08

First tagged alpha. All three headline commands (`scan`, `context`, `obfuscate`) are functional for Python.

### Added
- GitHub Actions CI workflow: ruff format/check + mypy --strict + pytest, matrix across Python 3.11/3.12/3.13.
- GitHub Actions release workflow: tag-triggered (`v*`) build of sdist + wheel, publish to PyPI via Trusted Publisher (OIDC, no stored tokens).
- `pyproject.toml` switched to dynamic version sourced from `src/cloak/__init__.py` (single source of truth).
- README CI / license / Python-version badges.
- README "real example" section with three concrete day-in-the-life flows.
- CONTRIBUTING.md release runbook (one-time PyPI Trusted Publisher setup + per-release tag steps).
- Phase 0: validation experiment proving the redaction strategy on a fake industrial-automation pricing engine. Documented in `docs/research/`.
- Phase 1: package scaffold, `typer`-based CLI with `scan`, `context`, `obfuscate` subcommands, `.cloakpolicy` YAML loader, `.cloakignore` support, repo walker, smoke tests.
- Phase 2: `cloak scan` is now functional. Wraps `detect-secrets` and layers in `policy.secret_rules` custom regex rules. Returns structured `Finding` records with severity, file, line, rule_id, redacted preview, and suggested action. Raw secrets are never printed — every preview is redacted via `_redact()`. "Clean bill of health" terminal panel when no findings; rich table when findings exist. Exit code 1 on findings, 0 on clean. JSON contract documented in `docs/AGENT_INTEGRATION.md`.
- Phase 4 (Python v1): `cloak obfuscate` is now functional with `--verify`. Renames module-private identifiers (`_names`) within each file, skipping `policy.public_api` matches and dunders, optionally strips docstrings per `policy.obfuscate_defaults.strip_docstrings`. Pipeline copies non-Python files unchanged, writes `cloak-manifest.json` (sha256 of every source/output file, rename map keyed `path:original`, policy snapshot + hash, verify command and result, version + timestamp), and runs the user-supplied `--verify` shell command in the output dir. Exit code 1 on verify failure (output is still written for inspection but the UX warns clearly). Refuses to overwrite a non-empty output directory. v1 deferred (documented in source): cross-file renames, class-method renames, string encoding, control-flow flattening (aggressive profile).
- Phase 3 (Python): `cloak context` is now functional for Python files. AST-based redactor replaces function/method bodies with `...` (stub-file convention), redacts module-level UPPER_SNAKE constants holding dict/list/set/tuple literals (the "proprietary tables" pattern from the Phase 0 case study), preserves imports, class shapes, signatures, and docstrings. `--strict` mode aliases enum values to opaque names (`NORTHEAST = 'NE'` → `VALUE_0 = 'V0'`) and strips all docstrings — justified by the Phase 0 adversarial probe finding. CLI supports `--out FILE`, `--copy` (best-effort across pbcopy/xclip/wl-copy/clip.exe), and `--json` status mode. Generated markdown carries a stable header comment with version, policy source, and strict flag for downstream tooling. JS/TS lands in Phase 3.5 via tree-sitter.
- `docs/AGENT_INTEGRATION.md`: agent-readable integration spec for tools that call CLOAK as a subprocess (Codex, Claude, custom).
- README "Integrations" section linking fob and the agent guide.
- Build plan and competitive landscape research published in `docs/`.
