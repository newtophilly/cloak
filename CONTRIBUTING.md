# Contributing to CLOAK

Thanks for considering a contribution. CLOAK is an alpha-stage open-source project; the easiest ways to help are issues, small focused PRs, and feedback on the build plan.

## Development setup

Requirements: Python 3.11+ and `pip`.

```bash
git clone https://github.com/newtophilly/cloak.git
cd cloak
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Code style

- Format and lint with `ruff` (`ruff format . && ruff check .`)
- Type-check with `mypy src/cloak`
- Tests with `pytest`

CI will run all three. Please keep them green before opening a PR.

## What to work on

Open issues are labeled by area (`scan`, `context`, `obfuscate`, `policy`, `cli`) and difficulty. New contributors should look for `good-first-issue`. The roadmap lives in [`docs/BUILD_PLAN.md`](docs/BUILD_PLAN.md) — read that first to understand how a piece of work fits.

## Honest positioning

CLOAK markets itself as a **governance + friction** tool, not unbreakable protection. PRs that overclaim what obfuscation achieves (in code, comments, docs, or marketing copy) will be redirected. See the README's "What CLOAK is NOT" section for the line. This is not pedantry — it's the position that distinguishes CLOAK from the dishonest end of the obfuscation market.

## Reporting security issues

Please do **not** file public issues for security vulnerabilities. Open a private security advisory at https://github.com/newtophilly/cloak/security/advisories/new with details, and we'll respond as quickly as we can.

## Commit / PR conventions

- One logical change per PR. If you find unrelated cleanup along the way, prefer a separate PR.
- Commit messages: short imperative subject (≤ 72 chars), optional body explaining *why*.
- Include tests for new behavior. Include a docs update for any user-facing change.
