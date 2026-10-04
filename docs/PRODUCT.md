# Product Summary

## Persona

A finance reviewer who performs first-pass checks on employee travel-expense claims in a large enterprise that digitises expense reimbursement.

## Input

- structured claim fields;
- transport, accommodation, allowance, and other-expense lines;
- pre-approval data;
- independent supporting attachments with short pre-extracted OCR descriptions
  and expense-line references;
- employee notes and special-circumstance notes.

The prototype does not perform OCR and does not connect to live HR, payment, or approval systems.

Accommodation form data contains stay dates, night count, total billed amount,
deduction, and total reimbursable amount. It deliberately does not ask the
employee to enter a nightly rate. Average-rate checks are derived from totals,
while uneven nightly charges must be supported by the hotel folio attachment.

## Output

- one of two business actions;
- neutral, evidence-grounded review notes;
- deterministic return reasons, when applicable;
- evidence-supported review warnings;
- relevant policy clauses;
- missing or uncertain evidence;
- task-scoped abstentions when evidence is insufficient for a named judgement;
- a concise evidence brief for Finance.

`Review Note`, `Warning`, and `Return Reason` are presentation and evaluation
levels. They do not create a third business outcome and do not allow the system
to approve a reimbursement.

An Abstention is not a pass or a failure. It records that the AI cannot reliably
complete one named review task with the available evidence. Deterministic
returns are resolved before semantic review and therefore skip the LLM call.

## Target metrics

- material-issue recall: at least 90% on the frozen holdout;
- false-return rate: reported alongside recall and targeted as low as practicable;
- return precision;
- warning precision and warning recall;
- unsupported-warning rate;
- evidence-reference validity;
- appropriate abstention.

## Achieved final Holdout metrics

- material-issue recall: `1.000` (Rules-only: `0.667`);
- false-return rate: `0.000`;
- return precision and recall: `1.000` and `1.000`;
- warning recall: `1.000` (Rules-only: `0.400`);
- warning precision: `0.870`;
- unsupported-warning rate: `0.130`;
- clean-case warning rate: `0.133`;
- evidence-reference validity: `1.000`.

The 15-case complex multi-leg subset achieved `1.000` warning precision,
warning recall, and material-issue recall. Detailed interpretation, including
the three unsupported hotel-cap warnings, is in `FINAL_EVALUATION.md`.
