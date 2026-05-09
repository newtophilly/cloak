# CLOAK — current state

> This document used to be a phased build plan. It's now a **status report** of what actually exists, what works in v1 with known limits, and what's deferred. Written in plain prose, not checklists. Last updated 2026-05-08.

## What CLOAK is, in one paragraph

A local CLI that helps developers share code with LLMs without leaking proprietary IP or secrets. Three commands — `scan`, `context`, `obfuscate` — operate on a repo or file under a `.cloakpolicy` checked into the repo. Runs locally; no server, no SaaS. Apache 2.0. Published to PyPI as `cloak-cli`.

The pitch in one sentence: **the local-first, repo-governed answer to Shadow AI**.

What CLOAK is *not*: unbreakable protection. A motivated reader (human or LLM) given an obfuscated copy of your code can still extract logic. CLOAK reduces leak surface and creates friction. That distinction is non-negotiable in marketing copy.

## What's shipped and works

### `cloak scan` — secrets and proprietary markers

Wraps [`detect-secrets`](https://github.com/Yelp/detect-secrets) for the heavy lifting (years of regex/entropy tuning come for free) and layers in custom regex rules from `.cloakpolicy`'s `secret_rules`. Returns a structured findings list with severity, file, line, rule id, redacted preview, suggested action. **Raw secrets are never printed** — every preview goes through a redaction helper. Terminal mode shows a green "Clean" panel when no findings, a colored severity table when findings exist. JSON mode is forward-compatible with future fields. Exit 1 on findings, 0 clean.

This is genuinely commodity tech. The differentiator is that the policy file you wrote travels with the rest of the tool's output (`context`, `obfuscate`).

### `cloak context` — redacted markdown for LLM paste

Generates a markdown view of a repo where function bodies are replaced with `...` (Python) or `/* [REDACTED BY CLOAK] */` (JS/TS) and module-level `UPPER_SNAKE_CASE` constants holding dict/list/object/array literals are redacted. Imports, class shapes, function signatures, type definitions, and (per policy) docstrings are preserved.

`--strict` is the second redaction tier. It additionally aliases enum values (`NORTHEAST = "NE"` → `VALUE_0 = "V0"`) and strips all docstrings. This tier was justified by the Phase 0 case study (`docs/research/`): the default redaction was strong enough that an LLM couldn't extract specific numbers from a fake pricing engine, but enum names plus general industry knowledge let it correctly *order* regions and categories. `--strict` closes that gap for compliance/contractor scenarios.

`--copy` puts the result on the system clipboard. `--out FILE` writes to disk. Both compose with each other.

Python uses the stdlib `ast` module. JS/TS uses `tree-sitter` with a byte-splice strategy: parse → collect ranges → splice replacements. No "unparse" step; original formatting and comments outside redacted regions survive. Supported extensions: `.py`, `.js`, `.mjs`, `.cjs`, `.jsx`, `.ts`, `.tsx`.

### `cloak obfuscate` — verified transformed copy

Produces a transformed copy of a repo and (if you pass `--verify "<cmd>"`) runs your test command inside the output dir. **If the verify command fails, the operation reports failure (exit 1).** This is the headline differentiator — no other open-source LLM-privacy or general-purpose obfuscator runs the user's tests as a correctness gate.

Per file: rename module-private identifiers (names starting with `_`) to deterministic opaque names (`_a000`, `_a001`, ...). Skip dunder-like names (`__version`, `__dirname`), all-underscore names, and anything in `policy.public_api` (with trailing-`*` wildcard support). Optionally strip docstrings per `policy.obfuscate_defaults.strip_docstrings`. Non-source files are copied through unchanged.

Output dir gets a `cloak-manifest.json` with: cloak version, generated-at timestamp, sha256 of every source file and every output file, the rename map keyed `path:original`, the policy hash + full policy snapshot, the verify command + its result. This is the audit-trail artifact compliance buyers actually ask for.

Refuses to overwrite a non-empty output directory.

### `cloak policy init` — onboarding wizard

Detects project layout (Python via `pyproject.toml`/`setup.py`/top-level `.py`; Node via `package.json`/lockfiles; TypeScript via `tsconfig.json` or top-level `.ts`/`.tsx`; common `src/`, `lib/`, `app/`, `packages/` directories) and proposes a sensible default `.cloakpolicy`. Shows a preview panel + project summary, asks once for confirmation, writes the file. `--yes` for non-interactive use; `--force` to overwrite; `--out` for a custom path.

The reason this exists: a new user shouldn't have to copy `.cloakpolicy.example` and edit it. They should get a working policy in one command.

### Pre-commit hook integration

A `.pre-commit-hooks.yaml` at the repo root means any team can drop CLOAK into their `.pre-commit-config.yaml` and have `cloak scan` block commits with secrets. Same pattern detect-secrets, gitleaks, and ruff use.

### Examples

`examples/python-pricing-engine/` and `examples/js-api-client/` ship as runnable demos. Both have their own `.cloakpolicy` and `examples/python-pricing-engine/` includes a real pytest suite so `--verify "pytest"` exercises the verify loop end-to-end.

## v1 limitations — things that work for the common path but have known gaps

These are documented in source comments where relevant and in this list. Real production use will hit some of them. The mitigation in every case is `--verify`: if the test suite passes, the obfuscation didn't break anything.

**Obfuscate, both languages**

- Per-file rename only. If `from a import _helper` (Python) or `import { _helper } from './a'` (JS), the import statement keeps `_helper` but the source file rewrites it to `_a000`. Tests catch this immediately.
- Local-variable shadowing. If a function body locally defines `_helper` shadowing a module-level `_helper`, both names get renamed. Logic bugs may result. Tests catch this immediately.

**Obfuscate, JS/TS specific**

- Shorthand property in object literals (`{ _helper }`) is *not* renamed because doing so would silently change the object's shape (key vs. value).
- Destructuring patterns (`const { _helper } = ...`) are *not* renamed for the same reason.
- TypeScript `interface` and `type alias` declarations are intentionally preserved (they're shapes, no logic). They're also currently NOT considered for rename even if their name starts with `_` — this is conservative.
- Class methods are not renamed. Methods could be public API — too risky to touch in v1.

**Context, JS/TS**

- Tree-sitter recovers from invalid source rather than raising. Parsing a syntactically broken file may produce partial redaction. The CLI doesn't currently flag this — silent best-effort.

**Scan**

- The custom `secret_rules` regex engine is plain Python `re`. No entropy heuristics, no contextual rules, no path-aware filtering beyond the default ignore list. For most teams this is fine; for hardcore secrets-scanning use cases, fall back to the upstream `detect-secrets` or `gitleaks` toolchains directly.

**Policy**

- `policy.public_api` only supports exact match and trailing-`*` wildcard. No regex, no glob, no scoped (`Module.Class.method`) matching beyond literal string equality. Workable for v1; will expand if users ask.

## What's not started

- **`cloak eval`** — an LLM-prompt-based regression harness that runs pinned prompts against the redacted output of `cloak context` and verifies nothing leaked. Internal QA tool plus marketing artifact ("every release tested against this leak benchmark"). Not blocking adoption; will build when there's a release worth re-validating.

- **`cloak policy preview`** — show what `cloak context` would redact across a repo without writing output. Quality-of-life improvement; not in the box yet.

- **Cross-file rename for `cloak obfuscate`** — would require building a global symbol map across the repo and tracking imports. Real engineering work. Defer until users hit the per-file limitation in practice.

- **`--profile aggressive`** — control-flow flattening, fragmented string reconstruction, more aggressive renames. Original build plan mentioned this; deliberately skipped because (a) it's brittle, (b) it pushes CLOAK toward the "claim of strong protection" framing we explicitly avoid.

- **PyPI publish for the JS-only audience** — currently `pip install cloak-cli`. Some JS-only devs won't install Python tools. An npm wrapper package could fix this; not a priority until someone asks.

## Where the validation came from

Before building any CLI infrastructure, we validated the redaction strategy on a fake industrial-automation pricing engine (`docs/research/quotecraft.py`). We hand-redacted it, pasted both versions to ChatGPT under two prompts (a realistic developer code-review ask, and an adversarial pricing-strategy probe), and judged whether the LLM could extract the proprietary numbers. Strong PASS on the realistic prompt (zero specific numbers leaked, useful architectural critique). Conditional PASS on the adversarial prompt (no specific numbers leaked, but enum names + general business knowledge let it correctly *order* regions and categories — which is what justified `--strict` mode).

Full case study and the LLM responses are in `docs/research/`. Competitive landscape research at `docs/research/COMPETITOR_RESEARCH.md` confirmed the niche was unoccupied as of 2026-05-08.

## Releases and supply chain

Five PyPI releases shipped as of writing — `0.1.0` through `0.2.1`. Tag a `v*` and the `release.yml` workflow builds and publishes via PyPI Trusted Publisher (OIDC; no tokens stored). Branch protection on `main` requires the CI matrix (Python 3.11/3.12/3.13) green before any merge. The `pypi` GitHub environment + Trusted Publisher together mean only this repo's `release.yml` workflow can publish `cloak-cli` — no API tokens to steal, no other repo or workflow accepted by PyPI.
