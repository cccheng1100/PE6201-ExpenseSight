# Evaluation

## Candidate ground truth

`candidate_holdout_ground_truth.json` is kept separate from model-visible claims. Each record contains:

- `expected_action`;
- `expected_return_reasons`;
- `expected_review_notes`;
- `expected_warnings`;
- annotation evidence and notes.

## Warning matching

Natural-language wording is not compared verbatim. A predicted warning matches an expected warning when the warning code, entity reference, and material facts refer to the same issue.

Review notes are neutral context rather than issue labels. Their diagnostic recall
may be reported, but they are not included in material-issue recall.

## Required metrics

- **Material-issue recall** — how many expected Return Reasons and Warnings were found.
- **False-return rate** — how many claims that should proceed were incorrectly returned.
- **Return precision** — how many system returns were expected returns.
- **Return recall** — how many expected return cases were correctly returned.
- **Warning recall** — how many expected warning issues were detected.
- **Warning precision** — how many produced warnings matched an expected issue.
- **Unsupported-warning rate** — how many produced warnings lacked a matching expected issue.
- **Clean-case warning rate** — how many normal cases received at least one Warning.
- **Evidence-reference validity** — how many cited paths point to visible input evidence.
- **Appropriate abstention** — how many annotated evidence-insufficient tasks received the expected task-scoped Abstention.

These definitions are also embedded in every generated result JSON so a reader
does not need to consult this document to interpret the numbers.

Warning metrics are calculated on non-return cases because the three evaluation
groups are mutually exclusive. Return-required cases are assessed with return
metrics even if the runtime also discovers advisory findings.

## Mutually exclusive evaluation groups

- `clean_pass`: no return reason and no warning; used to measure false returns and false or unsupported warnings.
- `warning_review`: one or more warnings but no deterministic return reason; used to measure issue-level warning recall and precision.
- `return_required`: one or more deterministic return reasons; used to measure return precision, return recall, and reason recall.

The groups are derived from the frozen expected labels. They do not add a third system action, and `clean_pass` does not mean automatic reimbursement approval.

## Complex multi-leg subset

A simple round trip is excluded. The subset contains journeys that require continuity reasoning across segments, for example an intermediate destination, an open chain, or a gap between a previous arrival location and the next departure location.

The final evaluation must compare rules-only and hybrid configurations on the same frozen holdout.

## Harness status

The repository now contains one offline harness used by both configurations:

- `scripts/run_evaluation.py --configuration rules_only` runs deterministic rules;
- `scripts/run_evaluation.py --dataset dev --configuration rules_only` runs the editable Dev baseline;
- `scripts/run_evaluation.py --dataset dev --configuration hybrid --model-outputs <file>` adds validated advisory model outputs to the same rule pipeline;
- `scripts/run_evaluation.py --dataset holdout --configuration rules_only` scores the frozen Rules-only baseline;
- `scripts/run_evaluation.py --dataset holdout --configuration hybrid --model-outputs <file>` scores final Hybrid outputs without changing labels;
- `evals/schemas/model_review_output.schema.json` defines the provider-neutral model contract;
- `evals/dataset_versions/holdout-v1.json` records and verifies exact frozen component hashes.

The model contract deliberately contains no `action` or `return_reasons` field.
Only deterministic rules can produce `RETURN_TO_EMPLOYEE`.

Issue matching uses `warning_code + entity_ref`; natural-language wording is
ignored. Material-fact completeness is reported separately, so a warning can
be recognised without rewarding a response that omits the annotated facts.

## Development set versus holdout

The 50 reviewed cases are frozen as the final `holdout-v1`, the agreed
evaluation size. They were not split into 20/30 merely to create a Dev label.
Prompt construction and iteration used the separate 22-case development set
under `data/dev`, with different claim IDs and no copied Holdout cases.

## Candidate versus frozen results

`candidate-v1` remains the editable, versioned source snapshot. After business
review, `scripts/freeze_holdout.py` copied it into separate paths and created
`holdout-v1` with status `frozen_holdout`. Any change to claims, ground truth,
manifest, or policy now requires a new Holdout version; v1 is never edited in
place. Rules-only Holdout results are in
`evals/results/rules_only_holdout-v1.json`; the final Hybrid result is
`evals/results/hybrid_holdout-v1_semantic-review-v2.json`. All 34 eligible calls
completed under the frozen configuration. Detailed interpretation and error
analysis are in `docs/FINAL_EVALUATION.md`.
