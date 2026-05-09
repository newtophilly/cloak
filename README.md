# CLOAK

[![ci](https://github.com/newtophilly/cloak/actions/workflows/ci.yml/badge.svg)](https://github.com/newtophilly/cloak/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/cloak-cli.svg)](https://pypi.org/project/cloak-cli/)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache_2.0-blue.svg)](LICENSE)
[![Python: 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](pyproject.toml)

> Local CLI for safer LLM workflows. Redact code before pasting into ChatGPT or Claude. Generate verified obfuscated copies for sharing. Enforce policy from your repo.

![demo](docs/demo.gif)

> [!NOTE]
> CLOAK is at **v0.3** — the three headline commands (`scan`, `context`, `obfuscate`) work for both Python and JS/TS, plus `diff-context` for previewing redactions. The `.cloakpolicy` format and CLI flags may still change before 1.0. See [docs/BUILD_PLAN.md](docs/BUILD_PLAN.md) for what's shipped, the known v1 limitations, and what's not started.

## What CLOAK is

A command-line tool for developers who want to share code with LLMs without leaking proprietary IP or secrets. Runs **locally** — no server, no SaaS, no cloud — and is governed by a `.cloakpolicy` file checked into your repo, so engineering teams have an enforceable answer to "what code is allowed to reach an LLM?"

Three commands:

```bash
cloak scan ./repo
cloak context ./repo --out safe-context.md --copy
cloak obfuscate ./repo --out ./repo.cloaked --verify "pytest"
```

- **`cloak scan`** — Find secrets and proprietary markers in code (wraps `detect-secrets` and layers your policy's custom regex rules on top).
- **`cloak context`** — Generate a redacted markdown view of a repo (function bodies hidden, signatures + docstrings kept) safe to paste into an LLM for architectural feedback. Use `--strict` to also alias enums and paraphrase docstrings.
- **`cloak obfuscate`** — Produce a transformed copy of your code that **still passes your test suite**, for sharing with contractors or third parties. The `--verify` flag is the differentiator: if your tests don't pass against the transformed copy, the operation fails.

There's also `cloak diff-context` — a dry-run that previews exactly what `cloak context` would redact (function bodies, proprietary tables, docstrings under `--strict`) and the byte reduction, without writing anything. Run it before you trust the transformation.

## Why this exists

The "Shadow AI" problem is real: leadership says "don't paste code into ChatGPT" and developers do it anyway because they have deadlines. Existing solutions are either enterprise-grade network DLP (expensive, blunt, requires IT) or policy documents nobody reads.

CLOAK is the developer-side, repo-governed alternative. A CTO commits a `.cloakpolicy` once; developers run `cloak context --copy` before they paste; the right thing happens by default. Authority follows repo merge access — no separate permissions system to invent.

## What CLOAK is NOT

Honest positioning matters in security tooling.

- **Not unbreakable.** A motivated reader (human or LLM) given an obfuscated copy of your code can still extract logic. CLOAK reduces leak surface and creates friction; it does not provide cryptographic protection. Real protection comes from blocking, redacting, encrypting, compiling, or simply never sending the source.
- **Not a replacement for enterprise DLP.** Network-layer enforcement (Lasso, Polymer, Cyberhaven, Prisma AIRS, etc.) operates at a different layer and is complementary. CLOAK lives in the developer's workflow, not the network egress.
- **Not a secret scanner from scratch.** `cloak scan` wraps `detect-secrets` (Yelp's open-source scanner — years of regex/entropy tuning come for free) and layers your policy's `secret_rules` on top. The reuse is intentional and disclosed.
- **Not magic for content the LLM has already seen.** Once code is sent, it's sent. CLOAK helps before paste, not after.

## Quickstart

> The PyPI package is named `cloak-cli` (the simpler `cloak` name was already taken).
> The command on your `$PATH` is still just `cloak`.

```bash
# Install:
pip install cloak-cli

# Or from source:
git clone https://github.com/newtophilly/cloak.git
cd cloak
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# First-time setup in a repo (one prompt, ~10 seconds):
cd your-repo
cloak policy init        # detects Python/JS/TS, scaffolds .cloakpolicy

# Then:
cloak scan .
cloak context . --copy                            # safe redacted markdown to clipboard
cloak obfuscate ./src --out ./src.cloaked --verify "pytest"
```

### A real example

```bash
# 1. About to ask Claude for help on a sensitive file? Redact first:
$ cloak context src/pricing.py --copy
# Pasted into Claude: signatures + docstrings, bodies replaced with `...`,
# proprietary tables (UPPER_SNAKE = {...}) replaced with `... `.

# 2. Shipping a contractor a working module?
$ cloak obfuscate src/payments --out /tmp/payments.cloaked --verify "pytest tests/payments"
# Output is transformed AND verified — if your tests don't pass, exit 1.
# A cloak-manifest.json with sha256s + rename map sits in the output dir.

# 3. CI guardrail:
$ cloak scan . --json   # exits 1 if any secrets, JSON for parsing.
```

### Try it on the included examples

The repo ships [`examples/`](examples/) with one Python and one JS project, each with its own `.cloakpolicy`. Clone, install, and run end-to-end against either in 30 seconds:

```bash
cd examples/python-pricing-engine
cloak scan .
cloak context . --copy
cloak obfuscate . --out /tmp/pricing.cloaked --verify "pytest"
```

See [examples/README.md](examples/README.md) for the full walkthrough.

### Use as a pre-commit hook

Drop `cloak scan` into `.pre-commit-config.yaml` to block commits that introduce secrets:

```yaml
repos:
  - repo: https://github.com/newtophilly/cloak
    rev: v0.2.1
    hooks:
      - id: cloak-scan
```

Then `pre-commit install` and you're done. See [pre-commit.com](https://pre-commit.com) for general setup.

## How `.cloakpolicy` works

The policy lives in a `.cloakpolicy` YAML file at the repo root. It's checked into git, versioned with your code, and reviewed via the same PR process as everything else. Authority = whoever has merge access.

```yaml
version: 1

# Paths CLOAK treats with extra care
sensitive_paths:
  - "src/pricing/**"
  - "src/auth/**"

# Names that must NEVER be renamed by `cloak obfuscate`
public_api:
  - "QuoteEngine.calculate_quote"
  - "PaymentGateway.*"

# Custom secret-detection rules layered on top of the built-in scanner
secret_rules:
  - id: internal_api_endpoint
    pattern: 'https?://internal\..*\.corp\.example'
    severity: high

# Default behavior of `cloak context`
context_defaults:
  keep_docstrings: true
  redact_function_bodies: true
  alias_enums: false        # set true to behave like --strict by default

# Default behavior of `cloak obfuscate`
obfuscate_defaults:
  rename_private: true
  rename_public_api: false
  encode_strings: false
  profile: standard
```

A full annotated example is at [`.cloakpolicy.example`](.cloakpolicy.example).

## Documentation

- [`docs/BUILD_PLAN.md`](docs/BUILD_PLAN.md) — current state, what's shipped, known v1 limits, what's not yet built
- [`docs/research/`](docs/research/) — the Phase 0 validation experiment that informed CLOAK's redaction strategy (a fake industrial-automation pricing engine + the LLM responses + our PASS/CONDITIONAL-PASS evaluations)

## Integrations

CLOAK is designed to be called as a subprocess from other developer tools and AI agents. It runs cleanly headless: stable JSON output (`--json`), predictable exit codes, no interactive prompts.

- **[fob](https://fob.sh)** — local AI workspace. When a fob project has a `.cloakpolicy`, fob can route context packets through `cloak context` to redact code before sending to an LLM. CLOAK works fine without fob; this is value-added, not load-bearing.
- **AI agents (Codex, Claude, custom)** — see [`docs/AGENT_INTEGRATION.md`](docs/AGENT_INTEGRATION.md) for the agent-readable integration spec: when to call CLOAK, JSON output contracts, exit codes, and common patterns.

## Status

What works today: `cloak scan`, `cloak context`, `cloak obfuscate` for both Python and JS/TS, plus `cloak policy init` for first-time setup and pre-commit-hook integration.

What's known to not yet work / has documented v1 limits: cross-file rename in `obfuscate` (per-file only — `--verify` catches breakage), JS/TS shorthand-property and destructuring rename (deliberately skipped to avoid silently changing object shapes), `cloak eval` regression harness (not started).

The full breakdown — what's shipped, the v1 gaps named honestly, and what's not started — lives in [docs/BUILD_PLAN.md](docs/BUILD_PLAN.md).

## Contributing

Issues and PRs welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style, and how to report security issues.

## License

[Apache 2.0](LICENSE).
