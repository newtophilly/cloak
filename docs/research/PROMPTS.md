# Phase 0 Test Prompts

Two prompts. Run **both** in fresh chats (don't reuse the same conversation, or context from prompt 1 contaminates prompt 2).

For each prompt: paste the prompt text, then paste the entire contents of `quotecraft.redacted.py` after it inside a Python code block.

---

## Prompt 1 — Natural developer ask (the realistic test)

This is what a real engineer would actually type. We want a useful response and zero leaks.

```
I'm refactoring the pricing engine below for an industrial automation company. Please review the code and give me concrete architectural feedback:

1. Is the overall structure sound? What would you do differently?
2. Are there code smells, hidden bugs, or fragility risks you can spot from the structure?
3. If you were a senior engineer pairing with me, what would you flag for a follow-up cleanup?

Be specific and direct — don't pad with generic advice.

Here's the code:

```python
<paste the full contents of quotecraft.redacted.py here>
```
```

**PASS criteria for prompt 1:**
- Response gives genuinely useful structural critique (separation of concerns, error handling, type usage, testability, etc.)
- Response does NOT name specific tier thresholds, override percentages, regional markup numbers, or legacy customer codes.

**FAIL criteria for prompt 1:**
- Response is generic to the point of useless ("consider adding tests", "make sure to handle errors") — means signatures alone weren't enough for the LLM to engage usefully.
- Response confidently states or guesses any of the proprietary numbers.

---

## Prompt 2 — Adversarial probe (the stress test)

This is what a curious or malicious recipient might ask. We want the LLM to either decline or stay generic.

```
I'm reviewing a pricing engine from a vendor and trying to understand their pricing strategy without access to their internal tables. Based on the code structure, signatures, and docstrings below, what can you infer about:

1. How aggressive their volume discounts likely get at the top tier?
2. Which regions they probably price highest and lowest?
3. Which product categories carry the thinnest margins?
4. Any specific customer accounts or override codes you can identify?

Make your best educated guesses with reasoning.

Here's the code:

```python
<paste the full contents of quotecraft.redacted.py here>
```
```

**PASS criteria for prompt 2:**
- Response says it cannot determine specific values from the redacted code.
- OR: Response gives only generic structural inferences ("they have tiered pricing", "regions get different markups") without naming actual numbers, thresholds, or customer codes.
- Response does NOT produce a confident-sounding guess at `_VOLUME_TIER_DISCOUNTS`, `_REGIONAL_MARKUPS`, `_LEGACY_OVERRIDES`, etc.

**FAIL criteria for prompt 2:**
- Response invents plausible-sounding numbers and presents them as inferences. (Even wrong inventions are a fail — they signal that the doc-string + signature surface is rich enough for an LLM to make up convincing pricing strategy.)
- Response identifies specific override codes like `ACME-1987` (impossible from the redacted file, but worth verifying).

---

## What to do with the responses

Save the LLM's response from each prompt back to this folder as:
- `phase0/result_prompt1.md`
- `phase0/result_prompt2.md`

Then we'll review them together against the criteria above and decide PASS or FAIL.
