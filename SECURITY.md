# Security policy

CLOAK is early-stage software (pre-1.0), maintained by a single person. The latest release on PyPI (`cloak-cli`) is the one that gets security attention; older releases will not get backports.

## Reporting a vulnerability

**Please don't file public GitHub issues for security vulnerabilities.** Open a private security advisory at https://github.com/newtophilly/cloak/security/advisories/new and include:

- What the vulnerability is and what it lets an attacker do.
- Reproduction steps or a minimal proof-of-concept.
- Which version(s) you found it in.
- Any mitigation you'd suggest.

I'll respond as soon as I can. Realistic expectation: a few days for an acknowledgement, longer for a fix depending on severity and how busy I am. If I'm slow, that's solo-maintainer life — feel free to nudge me on the advisory thread.

## What counts as a vulnerability

In scope (these are real bugs and I want to know about them):

- CLOAK leaks code that the policy was supposed to redact — secrets that `cloak scan` should have caught, function bodies that escape `cloak context` redaction, identifiers that should have been renamed by `cloak obfuscate`.
- The CLI does something it shouldn't — runs unintended code, writes outside the user-supplied output directory, etc.
- The published distribution (PyPI artifact, GitHub release, `cloak-manifest.json`) is tampered with or has been compromised.

Not in scope (CLOAK doesn't claim to prevent these):

- An LLM successfully reasoning about a redacted view. CLOAK is friction tooling, not unbreakable protection. See "What CLOAK is NOT" in the README.
- An obfuscated copy still being human-readable enough for a motivated reader. Same caveat.
- Vulnerabilities in upstream packages (`detect-secrets`, `tree-sitter`, `typer`, etc.). Report those upstream — but if the upstream bug means CLOAK leaks something, that's in scope here too.

## Coordinated disclosure

Default: I'd like to fix it privately, ship a release, then publicly disclose. If we agree a public disclosure date, I'll keep to it. If a fix is taking longer than expected, I'll talk to you about extending the embargo rather than letting it slip silently.
