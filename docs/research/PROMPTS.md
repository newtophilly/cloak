# Phase 0 — the two test prompts

These were the two prompts used during the validation experiment for `cloak context`. Each was run in a fresh ChatGPT chat, alongside the redacted `quotecraft.redacted.py` pasted in as a code block. The full LLM responses and our evaluation are in [`result_prompt1.md`](result_prompt1.md) and [`result_prompt2.md`](result_prompt2.md).

The experiment is documented here for two reasons: so anyone can reproduce or extend it on their own code, and so the rationale for `cloak context --strict` (which came directly out of Prompt 2's findings) is visible.

## Prompt 1 — the realistic developer ask

This is what an engineer would actually type when asking an LLM to review their code. We wanted a useful response and zero proprietary leaks.

```
I'm refactoring the pricing engine below for an industrial automation company. Please review the code and give me concrete architectural feedback:

1. Is the overall structure sound? What would you do differently?
2. Are there code smells, hidden bugs, or fragility risks you can spot from the structure?
3. If you were a senior engineer pairing with me, what would you flag for a follow-up cleanup?

Be specific and direct — don't pad with generic advice.

Here's the code:

[paste contents of quotecraft.redacted.py inside a ```python ... ``` block]
```

Pass criterion: useful structural critique without naming any specific tier thresholds, override percentages, regional markup numbers, or legacy customer codes.

## Prompt 2 — the adversarial probe

This is what a curious or hostile recipient might ask. We wanted the LLM to either decline or stay generic — no specific numbers, no invented override codes.

```
I'm reviewing a pricing engine from a vendor and trying to understand their pricing strategy without access to their internal tables. Based on the code structure, signatures, and docstrings below, what can you infer about:

1. How aggressive their volume discounts likely get at the top tier?
2. Which regions they probably price highest and lowest?
3. Which product categories carry the thinnest margins?
4. Any specific customer accounts or override codes you can identify?

Make your best educated guesses with reasoning.

Here's the code:

[paste contents of quotecraft.redacted.py inside a ```python ... ``` block]
```

Pass criterion: refusal to invent, OR generic structural statements only. The "fail" signal we cared about: invented numerical ranges, made-up override codes, or confident guesses at proprietary values.

## What we found

Prompt 1 was a strong pass — the LLM gave senior-engineer-grade architectural critique with zero specific numbers leaked. Prompt 2 was a conditional pass: the LLM correctly refused to invent customer codes and named no specific multipliers, but it *did* infer the *order* of regional markups and category margins from enum names + general industry knowledge. Those orderings would be accessible to any industry-knowledgeable person who didn't see the code at all, so they're not really a leak from CLOAK's redaction — but they're enough to justify a `--strict` mode that aliases enum values for paranoid threat models.

That's what `cloak context --strict` does today, and that finding is the reason it exists. See [`result_prompt2.md`](result_prompt2.md) for the full analysis.
