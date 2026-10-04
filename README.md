# ExpenseSight

ExpenseSight is a human-in-the-loop travel-expense pre-review prototype for finance reviewers in large enterprises that digitise expense reimbursement.

## Current status

This repository contains the completed executable prototype and frozen Holdout evaluation:

- deterministic policy checks;
- a decision validator with only two business outcomes;
- candidate claim and ground-truth datasets kept in separate files;
- expense lines and one-sentence OCR attachment descriptions stored separately;
- review triage with `Review Note`, `Warning`, and `Return Reason` outputs;
- unit tests for return boundaries, output contracts, and provenance (43 tests passing);
- an OpenRouter adapter for validated LLM review flags and interfaces for optional route facts;
- a provider-neutral offline evaluation harness for rules-only and hybrid runs;
- strict model-output validation that prevents an LLM from returning a claim;
- code-specific oneOf output schemas and taxonomy-aware post-call validation;
- configuration- and input-hash-aware resume support in the generation script;
- configuration-, taxonomy-, and input-hash validation during offline Hybrid scoring;
- dataset component hashes so results cannot silently mix different data versions.

The default model is `google/gemini-3.5-flash-lite` through OpenRouter, using
temperature 0 and strict structured JSON outputs. All 16 model-eligible Dev
claims were run under the same `semantic-review-v1` configuration fingerprint.
That run remains the historical Dev checkpoint. Pre-holdout human business
review subsequently refined the claim schema and two semantic boundaries. The
active `semantic-review-v2` fingerprint completed a fresh 16-call Dev
revalidation and is frozen for Holdout. The human-reviewed 50-case dataset is
now frozen independently as `holdout-v1`. All 34 model-eligible Holdout calls
completed under the frozen configuration and the final Hybrid result is saved.

`holdout-v1` contains 15 clean cases, 19 warning-review cases, and 16
deterministic-return cases. Its separate descriptor locks claims, ground truth,
manifest, and policy by SHA-256.

## Safety design

The prototype's safety properties form one design rather than a collection of
prompt instructions.

**Decision boundary.** Only a deterministic, policy-confirmed rule failure may
produce `RETURN_TO_EMPLOYEE`. All other cases produce `PROCEED_TO_HUMAN`,
including LLM findings, route anomalies, unclear evidence, unverified exceptions,
and low-confidence analysis. The prototype never approves, rejects, pays, or
modifies a financial amount.

**Employee text is data, not authority.** Employee notes and attachment text
cannot issue instructions to the review system. An ordinary explanation such as
"the hotel exceeded the cap but additional approval is attached" is checked as
a business claim and is not suspicious by itself. Only explicit attempts to
bypass policy, suppress findings, fabricate facts, expose hidden instructions,
or force an outcome raise the `PROMPT_INJECTION_TEXT` Warning.

**Output contract.** Strict JSON Schemas and post-call validation prevent the
model from returning a claim, authorising payment, or inventing evidence. Every
finding carries an entity and evidence references so a reviewer can verify it.

## Quick start and offline reproduction

Requires Python 3.11 or later. Use `requirements-lock.txt` for the exact
dependency set used in the final reproduction; `requirements.txt` retains
compatible ranges for normal development. No API key or paid call is required
for the commands below.

```text
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS or Linux: source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python scripts/validate_candidate_data.py
python scripts/validate_dev_data.py
python -m unittest discover -s tests -v
python scripts/run_evaluation.py --dataset holdout --configuration rules_only --output rules_only_reproduced.json
python scripts/run_evaluation.py --dataset holdout --configuration hybrid --model-outputs evals/results/model_outputs_holdout-v1_semantic-review-v2.json --output hybrid_reproduced.json
```

Both evaluation commands verify the frozen dataset component hashes before
scoring. The Hybrid command additionally requires the matching metadata file
and verifies the model configuration, review assets, taxonomy contract, and
per-claim input hashes.
The reproduced result files should have these SHA-256 hashes:

- Rules-only: `72e27ceb6f56ace84a20c14cf86a61e8ae81822b908a032bdb565f56b3f0fdd9`
- Hybrid: `971708f2ccb6e24304e26ddd0b593b7567ae99ca069073983d3b95f6a8a3b57f`

Dataset-building scripts remain available for development, but they are not
part of final Holdout reproduction and must not be used to edit `holdout-v1`.

To display three representative final cases offline:

```text
python scripts/show_demo_cases.py
```

## Optional live semantic review

Copy `.env.example` to `.env` and add a local `OPENROUTER_API_KEY`. The real
`.env` is ignored by Git. The live-generation command is deliberately a dry
run unless `--execute-live` is provided:

```text
python scripts/generate_model_outputs.py --dataset dev
python scripts/generate_model_outputs.py --dataset dev --claim-id DEV-001 --execute-live
```

The second command makes one paid request. A complete Dev run omits
`--claim-id`, generates validated outputs for model-eligible claims only, and
can then be scored with:

```text
python scripts/run_evaluation.py --dataset dev --configuration hybrid --model-outputs <output-file>
```

Use `--resume` to reuse already-validated outputs in the output file and only
call the remaining claims. Reuse is allowed only when the model, prompt files,
policy, taxonomy, output schema, pipeline contract, and per-claim input hash all
match. Legacy or mixed-configuration outputs are deliberately not reused.

## Repository safety

- Keep the real `.env` local; `.env` and `.env.*` are ignored, with only
  `.env.example` allowed into version control.
- Do not commit API keys, raw employee data, local virtual environments,
  caches, logs, or temporary directories.
- All submitted employee, supplier, invoice, approval, and expense identifiers
  in this repository are synthetic.
- Final Holdout evaluation is complete. Do not make another live Holdout call
  or tune prompts against the frozen results.

## Dev evaluation results (single configuration, not final)

The following results are from the 22-case Dev set using
`google/gemini-3.5-flash-lite`. All 16 model-eligible claims were generated and
validated under one configuration fingerprint. This is the selected Dev result,
not a final holdout result.

| Metric | Rules-only | Hybrid |
|---|---:|---:|
| false_return_rate | 0.0 | 0.0 |
| return_precision | 1.0 | 1.0 |
| return_recall | 1.0 | 1.0 |
| warning_recall | 0.182 | 1.0 |
| warning_precision | 1.0 | 0.917 |
| unsupported_warning_rate | 0.0 | 0.083 |
| clean_case_warning_rate | 0.0 | 0.0 |
| material_issue_recall | 0.471 | 1.0 |
| evidence_reference_validity | 0.964 | 0.982 |
| appropriate_abstention | 0.0 | 1.0 |

The hybrid layer finds every annotated material issue while preserving zero
false returns and zero clean-case warnings. One extra hotel-location warning on
the already-problematic `DEV-011` case lowers warning precision to 0.917. The
lower-priority fact-completeness diagnostic is 0.364 and Review Note recall is
1.0. The deviation is reported transparently rather than triggering another
Dev-tuning cycle.

## Final Holdout results

| Metric | Rules-only | Hybrid |
|---|---:|---:|
| false_return_rate | 0.0 | 0.0 |
| return_precision | 1.0 | 1.0 |
| return_recall | 1.0 | 1.0 |
| warning_recall | 0.400 | 1.0 |
| warning_precision | 1.0 | 0.870 |
| unsupported_warning_rate | 0.0 | 0.130 |
| clean_case_warning_rate | 0.0 | 0.133 |
| material_issue_recall | 0.667 | 1.0 |
| evidence_reference_validity | 0.985 | 0.990 |

The Hybrid system found all annotated material issues and preserved zero false
returns. Three unsupported hotel-cap warnings caused two clean cases to be
flagged; these frozen-test errors are retained and analysed in
`docs/FINAL_EVALUATION.md`, not used for further prompt tuning.

Strict full-path evidence validation also identified one frozen deterministic
reference to an omitted optional field (`other_expenses[0].invoice_desc`). The
finding itself remains supported by the visible expense and attachments, but
that specific path is not model-visible. It is disclosed rather than rewritten
after the Holdout run.

## Repository map

```text
data/       Policy, candidate model-visible claims, and data documentation
docs/       Product, architecture, and decision records
evals/      Candidate ground truth and evaluation documentation
scripts/    Separate claim-building, annotation-building, and validation tools
src/        Runtime contracts, deterministic rules, and decision pipeline
tests/      Automated boundary and rule tests
```

The separately submitted written report and video-recording materials are not
part of this source repository. The `docs/` directory contains only technical
documentation needed to understand, audit, and reproduce the implementation.

## Documentation

The suggested reading path is:

| Document | What it covers |
|---|---|
| [`docs/PRODUCT.md`](docs/PRODUCT.md) | Persona, inputs, outputs, and achieved metrics |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Architecture diagram and data flow |
| [`docs/REAL_WORLD_GROUNDING.md`](docs/REAL_WORLD_GROUNDING.md) | Finance-review practice and the design trade-offs it created |
| [`docs/DEVELOPMENT_JOURNEY.md`](docs/DEVELOPMENT_JOURNEY.md) | Difficulties, fixes, tuning decisions, and limitations |
| [`docs/DECISION_LOG.md`](docs/DECISION_LOG.md) | Confirmed design and evaluation decisions |
| [`docs/PROMPT_DESIGN.md`](docs/PROMPT_DESIGN.md) | Prompt architecture and iteration history |
| [`docs/REVIEW_DECISION_POLICY.md`](docs/REVIEW_DECISION_POLICY.md) | Warning-versus-return boundary |
| [`docs/FINAL_EVALUATION.md`](docs/FINAL_EVALUATION.md) | Frozen Holdout results and error analysis |
| [`docs/EVALUATION_HARNESS.md`](docs/EVALUATION_HARNESS.md) | Evaluation and provenance controls |
