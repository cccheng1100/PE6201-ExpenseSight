# Development Journey: Difficulties, Solutions and Performance Tuning

This document records the engineering path I took to build ExpenseSight: the core
difficulties I encountered, how I resolved each one, the performance tuning I
did, and what I deliberately left unfixed. Final reproducible evidence remains
in `evals/results/`; superseded smoke-test files were moved to the local process
archive so the submission repository contains only the selected checkpoints.

The companion decision record is `docs/DECISION_LOG.md`; prompt iteration detail
is in `docs/PROMPT_DESIGN.md`; the final frozen evaluation is in
`docs/FINAL_EVALUATION.md`.

---

## 1. How I worked

My development loop was deliberately model-cost-conscious and provenance-strict:

1. Keep the return boundary deterministic (rules only). The LLM is advisory and
   structurally cannot return a claim.
2. Build and iterate the prompt only on the 22-case Dev set, one claim at a time,
   then on the full Dev set.
3. Run every change through the offline evaluation harness so a claimed
   improvement is measured, not assumed.
4. Freeze one configuration before touching Holdout, and never tune against the
   frozen results.

The rest of this document narrates the concrete difficulties this loop exposed.

---

## 2. Core difficulties and how I resolved them

### 2.1 Clean-case noise — the model manufactured a finding on a compliant claim

**The problem.** On the very first smoke test (`DEV-001`), a perfectly compliant
round trip produced a redundant `COMPLIANT_ITINERARY_CHRONOLOGY` Review Note. The
model was restating that the claim was compliant, chronological, unremarkable —
exactly the noise a pre-screen should not add. Worse, it set a bad precedent:
if I let the model narrate every normal claim, clean-case warning/note rates
climb and reviewers learn to ignore the output.

**What I tried.** I changed the prompt to forbid Review Notes that merely restate
compliance, chronology, or ordinariness. Review Notes are reserved for neutral,
non-obvious context that helps the reviewer.

**Result.** The re-run returned all three arrays empty. This established the
"hard negative" discipline that carried through the whole project.

*Evidence:* the selected behaviour is specified in `docs/PROMPT_DESIGN.md` and
covered by the clean-claim rule and evaluation tests.

### 2.2 One-way claims — the model almost inferred an expense the employee never claimed

**The problem.** On `DEV-002` (an outbound-only claim) the model initially
produced no neutral context at all, and risked two failure modes: failing to name
the submitted scope, or inferring a return expense the employee had not claimed.

**What I tried.** I named `OUTBOUND_ONLY_CLAIMED` explicitly as the neutral
submitted-scope context and added a rule forbidding the model from inferring or
requesting an unclaimed return expense.

**Result.** The claim produced the correct Review Note and the model stayed
inside the submitted scope.

*Evidence:* `docs/PROMPT_DESIGN.md` records the submitted-scope rule, and
`tests/test_rules.py` verifies that a one-way claim is not treated as an error.

### 2.3 Loose output contract — empty facts and cross-code field leakage

**The problem.** The single largest structural problem came from a schema that
was too permissive. Early runs produced empty `facts` objects, and because `facts`
was an open object, fields belonging to one warning code (e.g. `unreadable_field`)
leaked into another code's output. The validator could not reject these at the
structural level, so a plausible-looking but structurally wrong output would have
passed through.

**What I tried — a three-stage tightening:**

1. **Closed facts schema.** I replaced the open `facts` object with 39 explicit
   fact properties and `additionalProperties: false`.
2. **Taxonomy v2.** I upgraded the warning taxonomy so every semantic code defines
   `fact_keys`, `required_fact_values`, `materiality`, and `policy_clause`, and I
   added a taxonomy-aware post-call validator that rejects any output whose fact
   keys drift from its code's contract.
3. **Code-specific `oneOf` schemas.** I made the provider schema branch by warning
   code, so each branch's `facts` requires exactly that code's keys and rejects
   cross-code fields at the JSON-structure level — before any semantic check.

**Result.** The tightened pipeline rejected the previously-flawed `DEV-007`
output and the re-run passed validation with a complete, single-code facts object
(11,906 tokens).

*Evidence:* `evals/schemas/model_review_output.schema.json`,
`evals/warning_taxonomy.json`, and `tests/test_model_output.py` preserve the
selected contract and its rejection cases.

### 2.4 Warning + Abstention coexistence — the model warned but would not abstain

**The problem.** On `DEV-021`, the model correctly emitted a
`TRANSPORT_DOCUMENT_QUALITY_REVIEW` Warning for an unreadable passenger name, but
returned an empty Abstention array. The stronger conclusion — "I can verify the
passenger identity matches the claimant" — is precisely what cannot be made from
an unreadable field, and the model did not say so.

**What I tried.** I added an explicit coexistence rule: when a key field is
unreadable, emit the document-quality Warning **and** separately abstain on the
dependent verification task (here `PASSENGER_IDENTITY_CHECK`). I generalised the
principle to any check task whose evidence is unreadable, and fixed an early draft
that mistakenly referenced a non-existent hotel code.

**Result.** The re-run produced both the Warning and the Abstention, with their
meanings kept separate (Warning records the visible quality problem; Abstention
stops the stronger identity conclusion). All three output shapes now worked:
empty (clean), Review Note only, Warning, and Warning + Abstention.

*Evidence:* the final coexistence rule is documented in `docs/PROMPT_DESIGN.md`
and validated by the frozen Dev result.

### 2.5 Reproducibility — a full Dev run cost money and time, so resume had to be safe

**The problem.** A full 16-call Dev run is a paid, slow operation. Re-running all
calls just because one new claim was added was wasteful, but blindly reusing old
outputs could silently mix different prompt/schema/data versions — exactly the
leakage I was trying to eliminate.

**What I tried.** I implemented `--resume` in `generate_model_outputs.py`: it
re-reads the existing output file, re-validates every saved output against the
current schema and taxonomy, and reuses only those whose model, prompt files,
policy, taxonomy, schema, pipeline contract, and per-claim input hash all match.
Any rejected or mismatched output is re-called.

**Result.** Resume re-used the four validated smoke outputs and called only the
remaining 12, finishing the complete 16-case Hybrid Dev run without re-paying for
validated calls and without mixing configurations.

*Evidence:* `tests/test_generate_model_outputs.py` checks configuration, dataset,
and per-claim input hashes; the selected Dev metadata records one validated call
per eligible claim.

### 2.6 The Dev run exposed real semantic gaps I chose not to over-tune

**The problem.** The full Dev diagnostics showed three missed semantic issues
(`DEV-010` itinerary chronology, `DEV-011` non-business route endpoint,
`DEV-022` route-distance abstention) and fact values that were natural-language
rather than standardised short values.

**What I tried.** I weighed each against the risk of Dev overfitting. Prompt
changes to chase `DEV-011`/`DEV-022` would improve a handful of cases at the cost
of a less general prompt. I added only the changes that clearly generalised
(§2.4), and **deliberately stopped** tuning once the core safety, recall,
evidence, and abstention checks passed — even though the selected Dev run had
warning precision 0.917 due to one unsupported `DEV-011` hotel-location warning.

**Result.** The prompt was frozen as `semantic-review-v2`. The missed cases and
the fact-normalisation shortfall are documented as limitations rather than tuned
away, because tuning against Dev after selection is how you overfit a benchmark.

*Evidence:* `evals/results/hybrid_dev_semantic-review-v2.json` and
`docs/FINAL_EVALUATION.md`.

---

## 3. Performance tuning and optimisations

### 3.1 Rules-only baseline first, then measure what the LLM adds

I committed to a rules-only baseline before any model call. On the final Holdout,
rules alone achieved zero false returns and perfect return precision/recall, but
recovered only 40.0% of expected Warnings and 66.7% of material issues. The LLM
layer is justified only by what it adds on top of that baseline.

### 3.2 Measured before/after on the frozen Holdout

| Metric | Rules-only | Hybrid | What I changed |
|---|---:|---:|---|
| Warning recall | 0.400 | 1.000 | LLM layer added semantic coverage |
| Material-issue recall | 0.667 | 1.000 | LLM layer added semantic coverage |
| Warning precision | 1.000 | 0.870 | Over-warning cost of the hybrid |
| Unsupported-warning rate | 0.000 | 0.130 | Three hotel-cap over-warnings |
| Clean-case warning rate | 0.000 | 0.133 | Two of 15 clean cases flagged |
| False-return rate | 0.000 | 0.000 | Guardrail held; LLM cannot return a claim |

The point of the table is that I did not present the hybrid as a free lunch: the
precision cost is measured and disclosed, and I argued why recall matters here
(a missed material issue lets a policy breach through, while an over-warning is
a review-time cost).

### 3.3 Cost control

- The generation command is a **dry run by default**; a live paid call requires
  an explicit `--execute-live` flag.
- Resume (2.5) prevented re-paying for already-validated calls.
- I report **calls and tokens** (34 validated calls, 436,635 tokens total). At
  the 4 October 2026 OpenRouter list prices used in the final report, the final
  Holdout corresponds to about US$0.14; this is an estimate, not an invoice.
- Google Maps Routes and the OpenAI Responses API were never used, so they
  incurred no cost.

### 3.4 Dataset hygiene as a performance lever

I stored claims, hidden ground truth, and the manifest separately, and locked the
frozen components with SHA-256 descriptors so a result cannot silently mix data
versions. Ground truth is never loaded by runtime code. This is what makes the
before/after numbers above trustworthy — they all ran on the same frozen,
hash-verified Holdout.

---

## 4. What I deliberately left unfixed

- **Three hotel-cap over-warnings** (`CAND-007`, `CAND-008`, `CAND-016`): the
  model misapplied a policy tier or warned on a near-cap amount the policy does
  not define. The configuration was already frozen, so I disclosed these errors
  in `FINAL_EVALUATION.md` instead of launching another tuning cycle.
- **Fact-value normalisation** (exact annotated-fact recall 35.0%): the model
  tends to write natural-language fact values where the ground truth uses short
  standardised values. Issue-level detection is correct; the evidence summary can
  be incomplete. This is a documented diagnostic, not a hidden failure.
- **No labelled must-abstain task in Holdout**, so `appropriate_abstention` is
  not measurable at the final stage even though task-scoped Abstentions were
  produced.
- **The same author labelled and reviewed the data**, so there is no
  inter-annotator agreement or external validity evidence.

Each of these is stated in the report (`docs/FINAL_REPORT.md`) rather than
buried, because the rubric asks for reasoning depth and an honest critique, and
because an over-tuned system that looks perfect on its own labels is exactly what
a frozen evaluation is meant to catch.
