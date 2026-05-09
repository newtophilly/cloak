# CLOAK examples

Two tiny projects to demonstrate `cloak scan`, `cloak context`, and `cloak obfuscate` end to end.

Both have their own `.cloakpolicy` so you can run CLOAK against them right away.

## `python-pricing-engine/`

A simplified pricing engine: a public `calculate_total` plus private `_apply_tier` and `_apply_region` helpers, with `_TIER_DISCOUNTS` and `_REGIONAL_MARKUPS` proprietary tables. Includes pytest coverage so `--verify` has something real to check.

```bash
cd examples/python-pricing-engine

# 1. Scan for secrets / proprietary markers
cloak scan .

# 2. Generate redacted markdown safe to paste into ChatGPT/Claude
cloak context . --copy
# Bodies replaced with `...`. Tables (_TIER_DISCOUNTS, _REGIONAL_MARKUPS) replaced
# with `...`. Public API + signatures preserved.

# 3. Obfuscate, gated on the pytest suite passing
cloak obfuscate . --out /tmp/pricing.cloaked --verify "pytest"
# Private helpers renamed (_apply_tier → _a000, _apply_region → _a001).
# Public `calculate_total` preserved (it's in .cloakpolicy public_api).
# Tests pass against the obfuscated copy.
ls /tmp/pricing.cloaked/cloak-manifest.json   # audit trail with hashes + rename map
```

## `js-api-client/`

A small API client with a public `fetchJson` plus private `_buildHeaders` and `_normalizePath` helpers, and `_BASE_HEADERS` / `_TIMEOUT_MS` proprietary constants.

```bash
cd examples/js-api-client

cloak scan .
cloak context . --copy
cloak obfuscate . --out /tmp/client.cloaked
# Note: no --verify here because the example doesn't ship a Node test runner setup.
# In your real project, you'd pass --verify "npm test" or similar.
```

## What you should observe

- `cloak scan` exits 0 (no secrets in these examples) and prints a green "Clean" panel.
- `cloak context` produces markdown where signatures and class shapes survive, but bodies and proprietary tables are replaced with `...` (Python) or `/* [REDACTED BY CLOAK] */` (JS/TS).
- `cloak obfuscate` produces a transformed copy in the output dir with `_a000`/`_a001`/...  identifiers replacing the original `_names`. Public-API names listed in `.cloakpolicy` are preserved.
- The `cloak-manifest.json` in the output dir records: cloak version, source/output sha256s, the rename map, the policy snapshot, and (if `--verify` was passed) the verify command + result.

## Want to try `--verify` failing?

Edit `pricing.py` to break the math (e.g., return `subtotal` instead of the discounted total) and rerun:

```bash
cloak obfuscate . --out /tmp/pricing.cloaked --verify "pytest"
# Exit code 1, panel shows the failing pytest output.
# Output is still written for inspection but the operation is reported as failed.
```

This is the differentiator: `cloak obfuscate` only succeeds if your tests pass against the transformed copy.
