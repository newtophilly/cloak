# Phase 0 — Prompt 2 Result (ChatGPT, web)

**Source:** ChatGPT via web browser
**Date:** 2026-05-08
**Prompt used:** Adversarial probe (Prompt 2 from PROMPTS.md)
**Input:** quotecraft.redacted.py pasted as code block

---

## Response (summarized)

The LLM gave a structured table of "best educated guesses" with confidence levels:

| Question | Best educated guess | Confidence |
|---|---|---|
| Top-tier volume discounts | 15–30% at the high end; 20–25% routine; 30–40% with bundle + override stacking | Medium |
| Highest-priced regions | International, then West and/or Northeast | Medium |
| Lowest-priced regions | Likely Midwest, possibly Southeast | Low–Medium |
| Thinnest-margin categories | PLC hardware, HMI panels, possibly safety relays | Medium |
| Specific accounts / override codes | None can be identified from this snippet | High |

Reasoning highlights:
- Inferred discount magnitude from rule order ("volume discount applies before bundle/override, so it's probably meaningful but not unlimited; not 50%+").
- Inferred international highest from name + general industrial-services economics.
- Inferred Midwest baseline from "dense manufacturing market, distributor relationships, competitive pressure."
- Inferred hardware thinnest margins from "OEM/distributor-sourced products, real unit costs, less pricing freedom" + presence of `_check_margin_floor`.
- Refused to invent override codes; stated that codes are in redacted tables.
- Noted `margin_floor_warnings` (vs. `margin_floor_blocks`) implies the engine *warns* rather than *blocks* — strategic signal.

---

## Phase 0 evaluation against PASS/FAIL criteria

### What was actually in the original (the proprietary truth)

| Field | Real value |
|---|---|
| Top tier volume discount | 16.5% |
| Tier thresholds | $50K, $250K, $1M, $5M |
| Regional markups | INTL 1.22, W 1.05, NE 1.00, SW 0.97, SE 0.96, MW 0.94 |
| Margin floors | PLC 18%, HMI 20%, SafetyRelay 22%, CustomEng 35%, ServiceHrs 40%, Software 55% |
| Legacy override codes | ACME-1987 (22%), STARK-FROZEN (18%), GLOBEX-PERPETUAL (30%) |
| Bundle stacks | PLC+HMI 4%, PLC+SafetyRelay+ServiceHrs 7.5%, CustomEng+Software 5% |

### Hit/miss analysis

**Specific numbers (the things we most wanted to protect):**
- Top tier = 16.5%. LLM guessed range 15–30% (best estimate 20–25%). The real value sits at the bottom of the range and below the LLM's "more likely" estimate. The range brackets the truth but the central estimate is wrong by ~50% relative.
- Regional multipliers: no specific numbers proposed. ✅
- Margin floor percentages: no specific numbers proposed. ✅
- Legacy override percentages: no specific numbers proposed. ✅
- Bundle stacking percentages: no specific numbers proposed. ✅
- Tier thresholds ($50K/$250K/$1M/$5M): never named. ✅

**Order/structure inferences:**
- Region pricing order: International highest, Midwest lowest. **Order essentially correct.**
- Category margin order: PLC hardware/HMI panel thinnest, software highest. **Order essentially correct.**
- Customer codes: refused to invent. ✅

**Strategic narrative:**
- "Segmented value pricing", "controlled flexibility", "warns rather than blocks aggressive discounts" — all accurate.

### How the LLM made the structural inferences

The LLM correctly identified:
1. Region order from the enum names (`INTERNATIONAL`, `MIDWEST`, etc.) plus general industrial-services economics knowledge — international pricing always > domestic, Midwest is a dense low-cost-to-serve manufacturing region.
2. Category margin order from enum names (`PLC_HARDWARE`, `SOFTWARE_LICENSE`, `SERVICE_HOURS`, etc.) plus general business knowledge — software margins always beat hardware margins, services land in between.
3. Discount magnitude bounds from the documented rule order ("if discount, markup, bundle, override stack, the standalone tier discount can't be huge").

**Critical observation:** these inferences are accessible to *any* industry-knowledgeable person who is told "this is a pricing engine for an industrial automation company with PLC, HMI, safety relay, software, and service categories, and regions including international." The redacted code didn't reveal the inferences — the *enum names plus the domain* did. A redaction strategy that hides function bodies but preserves enum names will always leak this category of strategic inference.

### Verdict: CONDITIONAL PASS

By strict criteria reading: **partial fail** — the LLM did invent numerical ranges and propose orderings.

By practical criteria reading (operational usefulness to a competitor): **pass** — the leaked information is either:
- Too wide to be operationally useful (15–30% spread can't drive a counter-quote)
- Generic industry knowledge that's accessible without seeing any code at all (software > hardware margins)
- Refused outright (customer codes, override codes)

**Real product implication:** the standard redaction tier (function bodies + proprietary tables) handles the "developer pasting code into ChatGPT for help" use case fully. It does NOT handle the "share code with an untrusted competitor" use case fully — for that, enum names and possibly even docstrings need additional aliasing.

This justifies a **two-tier `cloak context`**:
- **Default:** hide bodies, keep enum names + docstrings + signatures (current Phase 0 approach). Optimized for getting useful AI feedback while protecting specific business rules.
- **`--strict` (or `--profile aggressive`):** alias enum values to opaque names (`PLC_HARDWARE` → `CATEGORY_A`), strip or paraphrase docstrings, redact stage-order documentation. Optimized for sharing structurally-similar code without leaking strategic inferences.

Two product modes, two threat models, one CLI. This is a real Phase 0 finding that goes into the build plan.
