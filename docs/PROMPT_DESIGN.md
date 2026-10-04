# Prompt Design

## Task boundary

The LLM performs at most one constrained semantic-review call per claim. It is
not an agent and does not need tools in the first implementation. Rules run
first. If they produce an eligible Return Reason, the orchestration layer
returns the claim without invoking the LLM. Otherwise, the LLM reads the claim,
OCR descriptions, selected policy context, warning taxonomy, and non-terminal
deterministic findings.

The LLM output cannot contain a system action or return reason. The runtime
enforces the JSON schema and validates the parsed object again before combining
advisory findings with rule results.

## Why two prompt files

The system prompt contains stable role, safety, and review definitions. The
request template contains volatile claim data. This separation makes the task
easier to audit and later supports prompt caching without mixing case data into
the stable prefix.

## Warning control

To avoid maximising recall by warning on everything:

- warnings require a concrete material fact and exact evidence reference;
- neutral hard negatives become Review Notes;
- missing evidence becomes an Abstention for a named task;
- deterministic findings are supplied so the LLM does not duplicate them;
- warning codes come from a versioned taxonomy rather than free-form labels;
- clean-case warning rate and unsupported-warning rate are measured on Dev.

## Model selection

The default model is `google/gemini-3.5-flash-lite` through OpenRouter, using
temperature 0 and strict structured JSON outputs. The choice is based on:

- prior A2 group-work comparison showing Gemini-family models had the highest
  pass rate across multi-turn tool-use tasks;
- the retiring OpenRouter listing for `gemini-2.5-flash-lite` (scheduled
  2026-10-20), which makes it unsuitable as the long-term default;
- native support for `oneOf`, `required`, `properties`, and
  `additionalProperties: false` in structured outputs.

The prompt and JSON contract remain provider-neutral. Gemini 2.5 Flash-Lite may
be used as a historical comparison if time permits before its retirement.

## Prompt iteration history

The prompt was iterated exclusively on Dev evidence. Key iterations:

1. **DEV-001 clean-case noise** — the first run emitted a redundant
   `COMPLIANT_ITINERARY_CHRONOLOGY` Review Note on an ordinary compliant
   round-trip. The prompt was updated to forbid Review Notes that merely restate
   that a claim is compliant, chronological, or unremarkable. The second run
   returned all three arrays empty.
2. **DEV-002 outbound-only hard negative** — the model initially produced no
   Review Note for a one-way claim. The prompt was updated to explicitly name
   `OUTBOUND_ONLY_CLAIMED` as the neutral submitted-scope context and to forbid
   inferring or requesting an unclaimed return expense.
3. **DEV-007 fact schema** — early runs produced empty `facts` objects because
   the schema defined facts as an open object. The schema was updated to list 39
   explicit fact properties with `additionalProperties: false`. The warning
   taxonomy was upgraded to v2, defining `fact_keys`, `required_fact_values`,
   `materiality`, and `policy_clause` for every semantic code. A taxonomy-aware
   post-call validator rejects outputs whose fact keys drift from the code
   contract.
4. **Code-specific oneOf schemas** — the provider schema now branches by warning
   code, so each branch's `facts` object requires exactly that code's keys and
   rejects cross-code fields at the structural level. This prevents fields from
   one warning code (e.g. `unreadable_field`) from leaking into another.
5. **DEV-021 abstention coexistence** — the model initially emitted only the
   `TRANSPORT_DOCUMENT_QUALITY_REVIEW` Warning without abstaining on the
   identity-check task. The prompt was updated with an explicit rule: when a
   transport document has an unreadable material field, emit the document-quality
   Warning AND separately abstain on `PASSENGER_IDENTITY_CHECK`, because the
   unreadable field makes identity verification impossible.

## Development workflow

1. Run the rules-only Dev baseline.
2. Produce structured model outputs for every model-eligible Dev claim. Claims
   already returned by deterministic rules are skipped.
3. Run the same harness in hybrid mode.
4. Inspect false warnings, missed warnings, fact completeness, evidence
   validity, and expected abstention.
5. Change the prompt or taxonomy only from Dev evidence.
6. Freeze the final prompt before any final Holdout run.

The earlier mixed-prompt result was retained in the external process archive as
an iteration diagnostic, not a benchmark. The selected `semantic-review-v1`
result is `hybrid_dev_current_config.json`, produced from a fresh 16-output run
under one configuration fingerprint. Resume may reuse an output only when its
model, prompt, policy, taxonomy, schema, pipeline contract, and claim-input
hashes match the current run.

`semantic-review-v1` is the clean Dev checkpoint. It was reopened before any
Holdout model run after human business review clarified that ordinary employee
explanations are untrusted data but are not inherently prompt-injection
attempts. The active prompt is recorded as `semantic-review-v2` and requires a
complete Dev run before Holdout evaluation. The same rule applies to any
later prompt, schema, taxonomy, policy-context, model, or pipeline-contract
change.

The complete `semantic-review-v2` Dev run passed the core safety, recall,
evidence, and abstention checks. One unsupported hotel-location warning on
`DEV-011` reduced warning precision to 0.917 without affecting false returns or
clean-case warnings. The prompt is frozen at v2; no further Dev tuning is
performed before Holdout.

## Abstention boundary

Abstention is task-scoped, not a claim-level judgement. It means required
evidence is missing, unreadable, ambiguous, or insufficient for one named
conclusion. It never means that the claim is normal. The model identifies the
missing evidence and makes neither a positive nor a negative inference for that
task. A narrower evidence-supported Warning may coexist with Abstention from a
stronger conclusion.
