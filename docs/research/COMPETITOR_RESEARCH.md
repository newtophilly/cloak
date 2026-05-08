# CLOAK Competitive Landscape

**Research date:** 2026-05-08
**Method:** Multi-angle web search across direct competitors, repo-to-LLM packaging tools, secrets scanners, code obfuscators, enterprise LLM DLP, and browser/IDE extensions. Fresh search; not from training data.

## TL;DR

**No direct competitor exists with CLOAK's exact combination** (local CLI + in-repo YAML policy + signature-preserving context generation + test-verified obfuscation). The niche is genuinely unoccupied today.

**Two real durability threats are visible:** (1) OpenAI's Privacy Filter (released April 2026) and GitGuardian's `ggshield ai-hook` are pushing the secret/PII-redaction floor toward "free, built-in, everywhere" — meaning `cloak scan` is commodity within ~12 months. (2) `cyberchitta/llm-context.py` and `repomix` are one feature-PR away from being 60-70% overlap competitors.

**Defensible CLOAK value sits squarely in `cloak context` (with policy + strict mode) and `cloak obfuscate --verify` (test-gated obfuscation is genuinely unique).** Lead positioning here. Do not differentiate on scan.

---

## Section 1: Direct Competitors

**Verdict: none.** ~15 tools overlap on one or two of CLOAK's three commands; none combines all four of (a) local CLI, (b) in-repo YAML policy, (c) signature-preserving context view that keeps docstrings/enums, (d) test-verified obfuscation.

| Tool | What overlaps | What's missing |
|---|---|---|
| **cyberchitta/llm-context.py** (300 stars) | YAML+Markdown rules in `.llm-context/rules/`, signature extraction via `lc-outlines` for 15+ languages, MCP + clipboard | No redaction, no secret scanning, no obfuscation, no test verification |
| **repomix `--compress`** (~16k stars) | Tree-sitter signature extraction, ~70% token reduction, preserves docstrings, secretlint detection | Detection-only secret handling (no redaction transform), no obfuscation, no policy file beyond exclusions, no strict mode |
| **cc-redact** (ShindouMihou) | `.redactcc` glob policy, type-preserving redaction for env/yaml/json/toml, runs as Claude Code hook | Operates on data files, not source code; no signature view; no obfuscation; locked to Claude Code |
| **Biip** (HN Show) | CLI explicitly for "share code with LLM" use case | Env-var config (no policy file), no signatures, no obfuscation, generic regex only |
| **llm-redactor** (WangYihang, 5 stars) | Egress proxy + CLI prepend, gitleaks-compatible 100+ secret types | No policy, no signatures, no obfuscation, secrets-only |
| **Safe-Paste** | Scans pasted content, replaces secrets with placeholders | No CLI for repos, no policy, no signatures, no obfuscation |
| **CodeContexter** (Sekinal, Rust) | gitignore-respecting, auto-redacts secrets, Markdown/JSON/XML out | No policy beyond gitignore, no signature mode, no obfuscation |
| **masked-ai** (cado-security) | Python SDK + CLI for masking before LLM calls | Archived Nov 2024, generic PII, no source-code awareness |
| **llmshield** (brainpolo, 8 stars) | PII redaction with reversible mapping for round-trips | Library only, generic PII, no source-code semantics |
| **Mask My Code** (web app) | Closest in spirit — obfuscates identifiers before sharing with LLMs | Browser-only, no policy, no test verification, no signature view, no repo-wide |

**The `obfuscate --verify "pytest"` pattern (transform → run user-supplied tests → succeed-or-fail) appears unique in the open-source LLM-privacy space.** Even heavyweight obfuscators (PyArmor, javascript-obfuscator, Intensio-Obfuscator) don't run user tests as a correctness gate. Academic CodeCipher (arxiv 2410.05797) is research-stage with no released CLI.

---

## Section 2: Adjacent Landscape

### Repo-to-LLM packaging tools — largest overlap zone

- **repomix** — `--compress` mode is closest single feature to `cloak context`. Detects secrets via secretlint but does not redact. Token-reduction framing, not privacy.
- **llm-context.py** — most architecturally similar to CLOAK (YAML+Markdown rules + signature outlining). **Zero privacy/redaction features**, but the project most likely to add CLOAK-style features in 12 months.
- **gitingest, code2prompt, files-to-prompt** — pure dump tools, no signature mode, no redaction.
- **aider's repo map** — built-in, tree-sitter, signatures only. Not standalone, no privacy features.

**None of these have privacy as their primary frame.** Most are explicitly "send everything (or signatures) to the LLM."

### Secrets scanners

- **gitleaks, trufflehog, detect-secrets** — pure secret-finding, no LLM context generation. Confirmed boundary.
- **GitGuardian `ggshield secret scan ai-hook`** (April 2026) — installs hooks into Claude Code, Cursor, VS Code+Copilot to scan prompts/tool-uses/outputs in real time and block secrets pre-submission. **This is the closest "live LLM-aware" secret tool** and owns the "block at the boundary" lane.

`cloak scan` is genuinely commodity. Do not differentiate on it.

### Code obfuscators

- **PyArmor, javascript-obfuscator, Intensio-Obfuscator, pyminifier, JScrambler, PreEmptive Dotfuscator** — all distribution/IP-protection tools, designed for shipping bytecode/minified output. None has an LLM-friendly mode. None runs user tests as a verification gate. None has a YAML policy file.
- **Mask My Code** (web app) — closest in spirit; in-browser obfuscation before sharing with ChatGPT/Gemini/Copilot. Browser-only, no policy, no verification.

### Enterprise LLM data security platforms

All of these are network/proxy/SaaS plays. **None ships a developer CLI with in-repo policy.** Same problem (don't leak code to LLMs), fundamentally different delivery model:

- **Lasso Security, Polymer, Nightfall AI, Cyera, Cyberhaven, Prisma AIRS, Cisco AI Defense, Netskope GenAI, Privacera** — all gateway/endpoint/SaaS-layer DLP. Enterprise-monetizable. They don't *want* the developer-CLI market; that's the same reason the gap exists.

### Browser/IDE extensions and PII libraries

- **Microsoft Presidio** — open-source PII detection/anonymization SDK. Often wrapped by other tools. Could underlie part of `cloak scan` but doesn't compete.
- **OpenAI Privacy Filter** (April 2026) — open-weight 1.5B-param model, Apache 2.0, runs locally. PII-focused with "secret" category. **Not source-code-aware**, but its existence pushes the floor of decent local PII redaction toward zero cost.
- **SafePaste / SafePaste AI / Redactify** — Chrome extensions and macOS apps for paste-time redaction. Not CLI, not repo-aware.

---

## Section 3: White Space Verdict

**The white space is real but narrow.** What's empty:

- Local CLI for source-code-aware redaction (not generic PII)
- In-repo YAML policy, gitops model — `.cloakpolicy` is genuinely novel terminology + pattern
- Two-tier (default vs `--strict`) policy with semantic reasoning about enum names + docstrings
- **Test-verified obfuscation** (running user's own pytest/jest/go test as correctness gate) — unique
- Honest "governance + friction" framing (most tools either oversell as uncrackable or are gateway plays)

**Why it stayed empty:**

1. **Hard to monetize as SaaS** — local CLI doesn't fit gateway/seat/usage billing, where the funded competitors live.
2. **The user is the developer, not the buyer.** Enterprise security teams want network/endpoint enforcement, not a CLI any dev can skip. CLOAK's "merge access = policy access" is the opposite of what most enterprise security teams want.
3. **The market is split** — repo-packaging tools optimize for token cost, security tools optimize for blocking. The "share-with-LLM-but-redact-with-policy" use case sits between them.
4. **Test-verified obfuscation is genuinely hard engineering** — most obfuscators don't bother because their target user (shipping a binary) doesn't expect tests to keep passing.

**Honest caveat:** `cyberchitta/llm-context.py` is one good weekend away from being a 60-70% overlap competitor. Worth tracking.

---

## Section 4: Durability Threats (12-24 months)

**High probability:**

1. **OpenAI Privacy Filter expansion (April 2026)** — released, 1.5B params, "secret" category included. Doesn't currently do source-code AST work; if a v2 ships with code-awareness, the redaction layer of CLOAK becomes free. Biggest threat to `cloak scan` and the redaction-text portion of `cloak context`.
2. **GitGuardian ggshield ai-hook** — already shipping with native hooks for Claude Code/Cursor/VS Code+Copilot. If they extend hooks to scan for *proprietary patterns* (not just secrets), they consume CLOAK's `scan` use case entirely.
3. **Anthropic native redaction in Claude Code** — open issue #29434 for built-in PII/secret redaction. If Anthropic ships it, marginal value of an external tool drops sharply *for that audience*. CLOAK's "works with any LLM, any flow" matters here.
4. **`cyberchitta/llm-context.py` adds redaction** — same maintainer, similar architecture, larger user base. Most realistic open-source competitor in next 12 months.
5. **`repomix` adds privacy mode** — they have `--compress` and secretlint. Adding `--redact-bodies` is one PR away. They have user base + maintainer velocity.

**Medium probability:**

6. **Pipelock** (open-source agent firewall, May 2026) — DLP, redaction, MCP scanning. Not per-repo CLI today. If they pivot toward dev-side enforcement, overlapping.
7. **Velum Labs** (YC P26) — currently data-warehouse focused. If they expand to source-code-aware DLP, adjacent.
8. **YC W26/S26 wave** — densely populated in this neighborhood. Expect a Show HN within 6 months copying parts of the idea.

**Low probability:**

9. **Academic CodeCipher** library release — different technical approach (token-confusion), same use case.
10. **LangChain/LlamaIndex absorbing redaction primitives** — mostly aimed at RAG, not pre-LLM-paste.

---

## Strategic Implications

The single most defensible piece of CLOAK is **`cloak obfuscate --verify`**. Test-gated obfuscation is unique.

`cloak scan` is commodity within 12 months (OpenAI Privacy Filter + ggshield ai-hook will eat it). Build it for parity, not differentiation.

`cloak context` overlaps today with repomix `--compress` and llm-context.py — defensibility there comes from the redaction policy + strict mode, not from signature extraction (which is a solved problem).

**Lead positioning on:**
1. `cloak obfuscate --verify` — test-gated, unique
2. `.cloakpolicy` in-repo gitops governance pattern — unique
3. Two-tier redaction with --strict — unique to the LLM-privacy CLI space

**Watch:** `cyberchitta/llm-context.py` and `repomix` maintainer activity. These are the canaries.

---

## Sources

Direct candidates: cc-redact, llm-redactor, Biip (HN), Redactify (HN), llmshield, masked-ai, Safe-Paste, SafePaste AI, Mask My Code, llm-code-lens.

Repo-to-LLM packaging: Repomix, llm-context.py, gitingest, CodeContexter, tldr-code, Aider repo map, Annotated-AST-For-LLM.

Secrets scanners: gitleaks, trufflehog, GitGuardian ggshield ai-hook.

Obfuscators: PyArmor, javascript-obfuscator, Intensio-Obfuscator, CodeCipher (arxiv).

Enterprise LLM DLP: Lasso, Nightfall, Cyberhaven, Prisma AIRS, Cisco AI Defense, Pipelock, Velum Labs.

PII libraries / browser extensions: Microsoft Presidio, OpenAI Privacy Filter, Anthropic Claude Code redaction issue #29434, SafeDep VET.

YC: W26 batch surveys (TheVCcorner, TechCrunch).
