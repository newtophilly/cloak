# CLAUDE_CODE_BUILD_PLAN.md

## CLOAK Build Brief

CLOAK is a local Shadow-AI governance tool for developers and engineering teams.

Positioning:
CLOAK gives teams an enforceable policy for what source code is allowed to leave a developer's machine and reach an LLM. It prevents sensitive source from being sent to LLMs, generates safe AI-ready context, and creates verified obfuscated copies for sharing with contractors and third parties.

The market problem is "Shadow AI": leadership tells engineers not to paste code into ChatGPT/Claude, but they do it anyway because they have deadlines. CLOAK is the sanctioned path — a CLI a CTO can mandate that lets developers participate in AI workflows without leaking IP or secrets.

Do not claim that plaintext source can be made impossible for AI to understand. Real protection comes from blocking, redacting, encrypting, compiling, or never sending the source. CLOAK is a governance and friction tool, not an unbreakable cipher.

## MVP Commands

Build these first:

```bash
cloak scan ./repo
cloak context ./repo --out safe-context.md
cloak obfuscate ./repo --out ./repo.cloaked --verify "pytest"
```

## Architecture

```text
cloak/
  cli.py
  config.py
  filesystem.py
  policy.py
  scan/
    scanner.py
    secrets.py
    report.py
  context/
    generator.py
    python_adapter.py
    js_adapter.py
  obfuscate/
    python_obfuscator.py
    js_obfuscator.py
    manifest.py
  verify.py
  templates/
  tests/
```

## Phase 1: CLI Foundation

Implement:
- Python package scaffold.
- CLI with subcommands: `scan`, `context`, `obfuscate`.
- Path walking with `.cloakignore`.
- `.cloakpolicy` loading.
- JSON and terminal output modes.
- No git assumptions.

Suggested stack:
- Python 3.11+
- `typer` or `argparse`
- `pathspec` for ignore files
- `rich` optional for terminal output
- `pytest` for tests

## Phase 2: Scanner

Implement `cloak scan`.

Detect:
- API keys and tokens.
- `.env` style secrets.
- Private keys.
- Hardcoded endpoints.
- Suspicious auth headers.
- Sensitive comments: TODOs, credentials, proprietary notes.
- Large pasted code blocks if scanning markdown.

Output:
- Severity.
- File path.
- Line number.
- Rule id.
- Redacted preview.
- Suggested action.

Do not print raw secrets.

## Phase 3: Safe Context Generator

Implement `cloak context`.

For Python:
- File tree.
- Imports.
- Function/class names.
- Signatures.
- Docstrings only if policy allows.
- Redacted function bodies.
- Error/stack trace redaction helper.

For JS/TS:
- Imports/exports.
- Function/class signatures.
- Type/interface names.
- Redacted implementation bodies.

Output should be a markdown file designed for pasting into an LLM without leaking proprietary logic.

## Phase 4: Python Obfuscator

Implement `cloak obfuscate` for Python first.

Features:
- Copy repo to output directory.
- Preserve ignored files behavior.
- Strip comments.
- Optional docstring stripping.
- Rename local/private identifiers safely.
- Do not rename public exported API by default.
- Encode safe string literals.
- Generate `cloak-manifest.json`.
- Run syntax verification.
- Run user-supplied `--verify` command inside output directory.

Avoid unsafe transforms:
- Do not mutate strings that look like secrets.
- Do not rename magic methods.
- Do not rename imported external symbols.
- Do not flatten control flow in MVP.

## Phase 5: JS/TS Obfuscator

Implement after Python works.

Preferred approach:
- Use Babel parser/generator or wrap a known JS obfuscator.
- Strip comments.
- Rename local/private identifiers.
- Encode string literals.
- Preserve module imports/exports unless aggressive mode is enabled.
- Run user-supplied verify command.

## Phase 6: Eval Harness

Add later:

```bash
cloak eval ./repo.cloaked
```

Run prompt-based checks:
- Refactor test.
- Logic extraction test.
- Secret leak test.

This is a benchmark only, not a guarantee.

## Gemini Ideas Integration

Use:
- Control-flow flattening only in `--profile aggressive`.
- Fragmented string reconstruction only for non-secret literals.
- "Test Suite from Hell" as `cloak eval`.

Skip for v1:
- Dead-code noise.
- Custom DSL.
- Claims that obfuscation equals true security.

## Done Criteria

MVP is done when:
- `cloak scan` finds secrets without leaking them.
- `cloak context` creates useful safe markdown.
- `cloak obfuscate` transforms Python code and preserves tests.
- Verification failure blocks success.
- README clearly says CLOAK provides privacy tooling and obfuscation friction, not impossible-to-break protection.

## Adjustments (added 2026-05-08)

Refinements to apply during implementation. These override the phase descriptions above where they conflict.

### Scanner (Phase 2)
- Do not roll our own secrets engine. Wrap `detect-secrets` or `gitleaks` and layer CLOAK-specific rules on top (proprietary endpoints, internal tokens, sensitive comments). Years of regex/entropy tuning come for free.

### Safe Context Generator (Phase 3) — elevated priority
- Treat `context` as a co-equal flagship feature, not a stepping stone to `obfuscate`. The "safe LLM context from a repo" use case has a wider market than obfuscation and is what most security-conscious devs actually want.
- Add a `--dry-run`/diff mode so users can preview what gets included vs. redacted before generating.

### Python tooling (Phases 3 & 4) — share infrastructure
- Collapse `context/python_adapter.py` and `obfuscate/python_obfuscator.py` infra into a shared `cloak/python/` package: one parser/walker, multiple visitors. They are reading the same AST with different output strategies.
- Use `libcst` over the stdlib `ast` module — preserves formatting, comments, and is round-trippable.

### Python Obfuscator (Phase 4) — safety adjustments
- "Rename local/private identifiers safely" requires real scope analysis: closures, nested classes, `nonlocal`, `__all__`, dunder leakage, `getattr`-by-string lookups. Plan weeks of work here, not days.
- Default to **fail-closed**: if scope analysis cannot prove a rename safe, skip the rename and log. Never break code in pursuit of obfuscation density.
- "Encode safe string literals" is a footgun — strings are often SQL, log keys, feature-flag names, regex patterns asserted on by tests. Default this **off**; require opt-in per-rule, not per-profile.
- Add a `--dry-run` mode that shows the rename map and string-encoding plan before writing the output directory.

### JS/TS Obfuscator (Phase 5) — depend, don't rebuild
- Do not build a Babel pipeline ourselves. Depend on `javascript-obfuscator` (mature, configurable) and run it via a Node sidecar from the Python CLI. Our value is the policy layer, ignore-file integration, and verify loop — not parser plumbing.

### Eval Harness (Phase 6) — signal, not gate
- LLM-prompt-based "did obfuscation hold" checks are non-deterministic and provider-dependent. Pin the model + prompts so runs are comparable.
- Report `cloak eval` results as a *signal* in CI/output, never as a pass/fail gate on `obfuscate`. Do not let users mistake it for a security guarantee.

### Phase 0 — Alpha validation experiment (DONE 2026-05-08)

Status: **PASS** with one product finding.

Sample: `phase0/quotecraft.py` (fake industrial-automation pricing engine with proprietary tier discounts, regional markups, margin floors, legacy customer overrides, and bundle stacking rules in function bodies + module-level tables).

Test: redacted bodies + tables, kept imports/classes/signatures/docstrings/enum names. Ran two prompts against ChatGPT (web). See `phase0/result_prompt1.md` and `phase0/result_prompt2.md`.

**Prompt 1 (realistic dev ask) — strong PASS.** LLM produced senior-engineer-grade architectural critique (concrete bug pattern identified, prioritized cleanup list, target architecture sketch) with zero leaks of any proprietary number, threshold, percentage, or customer code.

**Prompt 2 (adversarial probe) — conditional PASS.** LLM refused to invent customer/override codes and named no specific multipliers, floors, or rates. It did correctly infer the *ordering* of regional markups and category margins — but those inferences come from enum names + general industrial-economics knowledge, not from the redacted code itself. Operationally, the leaked information is too imprecise to drive a competitor's counter-quote.

**Phase 0 product finding — two redaction tiers, not one:**
- **Default `cloak context`** (validated by Prompt 1): hide bodies + proprietary tables; keep enum names, docstrings, signatures. Optimized for daily AI workflows where the user wants useful feedback. Sufficient for the indie dev / startup customer profile.
- **`cloak context --strict`** (justified by Prompt 2): default redaction *plus* alias enum values (`PLC_HARDWARE` → `CATEGORY_A`), strip or paraphrase docstrings, remove stage-order narrative from method docstrings. Optimized for sharing with untrusted parties. Required for the compliance / contractor customer profile.

**Honest limit to document in README:** enum names + domain context + general business knowledge produce structural inferences (e.g., "software margins probably beat hardware margins") that are difficult to suppress without making code unintelligible. CLOAK reduces leak surface; it does not eliminate informed-guesser inference.

### Parser strategy — do not pick one tool
- **`scan` and `context`** (cross-language, structural): use `tree-sitter`. Multi-language, fast, structural-only is exactly what we need for body redaction and string/comment identification.
- **Python `obfuscate`** (semantic, scope-aware renaming): use `libcst`. Tree-sitter does not give the scope information needed to prove a rename is safe; libcst is built for Python codemods and round-trips cleanly.
- Two parsers, each used for what it is best at. Do not try to unify.

### `.cloakpolicy` — first-class spec, not an afterthought
This file is the moat. Define the format precisely in Phase 1, not later.

Required directives:
- `redact:` — list of file globs, function names, or class names whose bodies must be redacted in `context` and obfuscated aggressively in `obfuscate`. Example: `redact: ["src/pricing/**", "*.auth_utils.*", "AuthService.*"]`.
- `keep_docstrings:` — boolean per scope. Default false for redacted scopes, true elsewhere.
- `secret_rules:` — additions/overrides to the underlying scanner's rule set.
- `allow_strings:` — globs/regexes of string literals safe to leave un-encoded (URLs to public docs, license headers, etc.).
- `public_api:` — names that must never be renamed by `obfuscate`. Goes beyond what `__all__` declares.

A team checks `.cloakpolicy` into their repo. Their CI runs `cloak scan --policy .cloakpolicy`. Devs running `cloak context` get the team's policy applied automatically. This is what makes CLOAK an enforceable governance tool rather than a personal toy.

### Clipboard integration — make the safe path easier than the unsafe path
- Add `--copy` (or `-c`) to `cloak context`: writes the safe markdown to stdout/file *and* puts it on the system clipboard via `pbcopy`/`xclip`/`clip.exe` (whichever is on PATH).
- This collapses the "before I paste" workflow to one command. The unsafe path (right-click → copy raw file) and the safe path should take the same number of keystrokes.

### Scanner output — "clean bill of health" mode
- Terminal output for `cloak scan` should make the success state visually unambiguous: a green "Clean — N files scanned, 0 findings" summary card. People paste right after they see green; the UI should reward correctness.
- JSON mode stays machine-readable for CI.

### Signed manifests — audit-trail for compliance buyers
The regulated/compliance customer profile (legal, healthtech, fintech) needs cryptographic evidence that a transformed copy came from a specific source.

`cloak-manifest.json` should include:
- SHA-256 hash of every source file included in the transform.
- SHA-256 hash of every output file.
- Rename map (original → obfuscated identifier).
- Policy file hash + content snapshot.
- CLOAK version.
- Timestamp.

Add an optional `cloak obfuscate --sign <key>` flag that signs the manifest with a local key. Verifying the manifest later proves the obfuscated bundle was generated from a known source under a known policy. Cheap to add at MVP, very expensive to retrofit, and it is the audit-trail story compliance buyers ask about first.

### Alpha release language target
Python/AI ecosystem first (already reflected in phase order). Rationale: deeper ecosystem for parsing/AST work, larger noisy paying audience among AI/data developers, matches the team's stronger context. JS/TS lands in Phase 5. Do not split focus before Python is solid.
