# Changelog

Notable changes by release. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow [SemVer](https://semver.org/).

## [Unreleased]

## [0.2.1] — 2026-05-08

- Added `.pre-commit-hooks.yaml` so teams can drop `cloak-scan` into their `.pre-commit-config.yaml` and have it gate commits.
- Added `examples/python-pricing-engine/` (with a real pytest suite, so `--verify "pytest"` actually runs) and `examples/js-api-client/`. Each ships with its own `.cloakpolicy`.
- README now points at the examples and shows the pre-commit setup.

## [0.2.0] — 2026-05-08

Feature matrix complete: every command now works for both Python and JS/TS.

- Added JS/TS support to `cloak obfuscate`. Per-file rename of module-level `_names` (functions, classes, generator functions, simple `const`/`let`/`var` bindings) using tree-sitter. Skips dunder-like names, all-underscore names, and anything in `policy.public_api`. Property access, shorthand object properties, and destructuring patterns are deliberately not renamed in v1 — they'd silently change object shapes.
- A mixed Python+JS repo now obfuscates in one pass with one manifest and one verify command.

## [0.1.2] — 2026-05-08

- Added `cloak policy init` — interactive wizard that detects project layout (Python / Node / TypeScript / common src directories) and scaffolds a sensible `.cloakpolicy`. Supports `--yes` (non-interactive), `--force` (overwrite), `--out` (custom path).
- New `cloak policy ...` subcommand group; more policy commands will go here.

## [0.1.1] — 2026-05-08

- Added JS/TS support to `cloak context` via tree-sitter. Supported extensions: `.js`, `.mjs`, `.cjs`, `.jsx`, `.ts`, `.tsx`. Function/method/arrow bodies and module-level `UPPER_SNAKE_CASE` object/array constants get redacted; type definitions and signatures are preserved. Output is byte-spliced into the original source so formatting and surrounding comments survive.

## [0.1.0] — 2026-05-08

First tagged alpha. All three headline commands are functional for Python.

- `cloak scan`: wraps `detect-secrets` and layers in `policy.secret_rules`. Returns severity / file / line / rule_id / redacted preview / suggested action. Raw secrets never appear in output. Exit 1 on findings, 0 clean.
- `cloak context` (Python): AST-based redactor. Function bodies → `...`, module-level `UPPER_SNAKE` dict/list/set/tuple constants → `...`. Imports, class shapes, signatures, docstrings preserved. `--strict` aliases enum values and strips docstrings (justified by the Phase 0 adversarial probe). `--out`, `--copy`, `--json` all supported.
- `cloak obfuscate` (Python): renames module-private `_names` skipping `policy.public_api` and dunders; optional docstring stripping per policy. Writes `cloak-manifest.json` (sha256s, rename map, full policy snapshot, verify result). `--verify "<cmd>"` gates success on the user's test suite — exit 1 if tests fail. Refuses to overwrite a non-empty output directory.
- GitHub Actions CI (ruff format/check + mypy --strict + pytest matrix on 3.11/3.12/3.13) and a tag-triggered release workflow that publishes to PyPI via Trusted Publisher (OIDC, no stored tokens).
- `pyproject.toml` reads version dynamically from `src/cloak/__init__.py` (single source of truth).
- Phase 0 validation experiment documented in `docs/research/`.
