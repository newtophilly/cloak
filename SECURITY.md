# Security policy

## Supported versions

CLOAK is alpha software. The latest published `0.x.y` release on PyPI is the only supported version. Older releases will not receive security backports.

| Version | Supported          |
|---------|--------------------|
| 0.2.x   | :white_check_mark: |
| < 0.2   | :x:                |

## Reporting a vulnerability

**Please do not file public GitHub issues for security vulnerabilities.** Open a private security advisory at https://github.com/newtophilly/cloak/security/advisories/new with:

- A clear description of the vulnerability and its impact.
- Reproduction steps or a minimal proof-of-concept.
- Affected versions, if you can identify them.
- Any suggested mitigations.

We aim to acknowledge new advisories within **3 business days** and to release a fix or coordinated disclosure within **30 days** for high-severity issues.

## Scope

In scope:
- Bugs in CLOAK that cause it to **leak source code that the policy was supposed to redact**, including: secrets that should have been caught by `cloak scan`, function bodies that escape `cloak context` redaction, identifiers that should have been renamed by `cloak obfuscate`.
- Vulnerabilities in CLOAK's CLI that allow code execution, privilege escalation, or unintended file writes outside the user-supplied output directory.
- Vulnerabilities in our published distribution: tampering with the PyPI artifact, the GitHub release, or the `cloak-manifest.json` audit trail.

Out of scope (not vulnerabilities by CLOAK's design):
- An LLM successfully reasoning about code from a redacted view. CLOAK is friction tooling, not unbreakable protection. See README "What CLOAK is NOT."
- An obfuscated copy still being human-readable enough for a motivated reader to understand. Same caveat.
- Dependency vulnerabilities from upstream packages we use (`detect-secrets`, `tree-sitter`, etc.) — please report those upstream.

## Disclosure timeline expectations

For accepted reports we aim for:
- Day 0: Acknowledgement.
- Day 1–7: Initial assessment + severity rating.
- Day 7–30: Patch developed, tests added, release prepared.
- Day 30: Coordinated public disclosure (CVE if applicable, GitHub Security Advisory published, release notes updated).

If a fix takes longer than 30 days, we'll coordinate a revised disclosure date with the reporter.
