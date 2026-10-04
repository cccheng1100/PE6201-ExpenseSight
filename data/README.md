# Data

## Files

- `candidate_holdout_claims.json`: 50 model-visible candidate claims.
- `candidate_case_manifest.json`: case origin and review status; not supplied to the runtime model.
- `holdout/holdout_claims.json`: immutable model-visible `holdout-v1` copy.
- `holdout/holdout_case_manifest.json`: immutable Holdout provenance and subset tags.
- `policies/travel_policy.md`: current example-company policy.

Ground truth is stored separately under `evals/`.

## Candidate and frozen status

The candidate source contains 35 generated-and-reviewed templates and 15 cases
derived from finance-review experience. The project author completed the
business review, after which an independent copy was frozen as `holdout-v1`.
The candidate files remain editable build sources; final evaluation uses only
the files under `data/holdout` and the matching frozen descriptor.

The frozen distribution is:

- 15 `clean_pass` cases;
- 19 `warning_review` cases;
- 16 `return_required` cases;
- 15 explicitly tagged complex multi-leg cases; ordinary round trips are excluded.

One of the 19 warning cases is tagged `security_test`. It checks that an
explicit instruction embedded in employee-provided data is ignored and surfaced
for human attention. It should be reported separately rather than counted as a
financial-issue success.

Expense lines contain employee-submitted structured values. Supporting documents
are stored independently in `attachments`; every attachment retains one short
`ocr_description` and optional links to one or more expense-line references. This
supports multiple documents per expense, duplicate uploads, shared invoices, and
evidence provenance without pretending that OCR output is employee-entered data.

Hotel form fields store the stay dates, declared night count, total billed amount,
employee deduction, and total reimbursable amount. They do not store an
employee-entered nightly rate. Deterministic cap checks derive the average
reimbursable rate as total reimbursable amount divided by nights; uneven
night-by-night charges remain attachment evidence for semantic human review.

## Privacy

All names, identifiers, suppliers, invoices, approvals, addresses, and monetary values are synthetic.

## Leakage controls

- Claims do not contain expected actions or warning labels.
- Claims do not contain expected review-note labels.
- Ground truth is not loaded by the runtime pipeline.
- Outcome words are avoided in attachment descriptions.
- Final prompt tuning must use development cases, not the frozen holdout.
