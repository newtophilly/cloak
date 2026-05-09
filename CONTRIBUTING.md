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

Open issues are the obvious starting point if there are any. Beyond that: [`docs/BUILD_PLAN.md`](docs/BUILD_PLAN.md) lists the things that work today, the known v1 limitations, and what's not started — anything in those last two buckets is fair game for a PR.

If you're not sure whether a change is in scope, open an issue describing what you're thinking before sinking time into it. I'd rather discuss the shape of a PR up front than ask for a rewrite after the fact.

## Honest positioning

CLOAK markets itself as a **governance + friction** tool, not unbreakable protection. PRs that overclaim what obfuscation achieves (in code, comments, docs, or marketing copy) will be redirected. See the README's "What CLOAK is NOT" section for the line. This is not pedantry — it's the position that distinguishes CLOAK from the dishonest end of the obfuscation market.

## Reporting security issues

Please don't file public GitHub issues for security vulnerabilities. Open a private security advisory at https://github.com/newtophilly/cloak/security/advisories/new — full details in [SECURITY.md](SECURITY.md).

## Releasing (maintainers)

CLOAK is published to PyPI via a GitHub Actions workflow that runs on tag pushes (`v*`). PyPI authentication uses a [Trusted Publisher](https://docs.pypi.org/trusted-publishers/) — no tokens stored in the repo.

**One-time setup (first release only):**

1. Create the project on PyPI as a *pending* Trusted Publisher:
   - https://pypi.org/manage/account/publishing/
   - PyPI Project Name: `cloak-cli` (the `cloak` name was already taken; the CLI binary on `$PATH` is still `cloak`)
   - Owner: `newtophilly`
   - Repository name: `cloak`
   - Workflow filename: `release.yml`
   - Environment name: `pypi`
2. Create the `pypi` GitHub environment in this repo:
   - Settings → Environments → New environment → name `pypi`. No extra config needed.

**Per-release steps:**

1. Bump `__version__` in `src/cloak/__init__.py` (single source of truth — `pyproject.toml` reads from this file via `[tool.hatch.version]`).
2. Add a CHANGELOG entry under `[Unreleased]`, then move it under a new versioned heading.
3. Commit. Wait for `ci` to go green on `main`.
4. Tag and push: `git tag v<VERSION> && git push origin v<VERSION>`.
5. The `release` workflow builds an sdist + wheel and publishes them to PyPI.

If the first release fails, the most likely cause is a step missed in the one-time setup above (pending Trusted Publisher not registered, or the `pypi` environment doesn't exist).

## Commit / PR conventions

- One logical change per PR. If you find unrelated cleanup along the way, prefer a separate PR.
- Commit messages: short imperative subject (≤ 72 chars), optional body explaining *why*.
- Include tests for new behavior. Include a docs update for any user-facing change.
