# Review Decision Policy

## Purpose

ExpenseSight is a pre-review assistant, not an automated approver. This policy
turns domain-informed finance-review judgement into a repeatable boundary for
rules, attachment extraction, LLM findings, route facts, annotations, and UI
output.

The policy is a project design assumption informed by real expense-review
experience. It is not presented as a universal corporate reimbursement rule.

## Output levels

| Output | Meaning | Business effect |
|---|---|---|
| `Review Note` | Neutral, evidence-grounded context | No concern is asserted |
| `Warning` | A possible issue, conflict, or evidence gap | Finance attention is requested |
| `Return Reason` | A deterministic and policy-grounded defect | Return to the employee for correction |

These levels do not create three approval outcomes. The system action remains
either `RETURN_TO_EMPLOYEE` or `PROCEED_TO_HUMAN`, and ExpenseSight never
approves a reimbursement.

## Automatic-return safeguards

A finding may become a `Return Reason` only when all of the following are true:

1. an explicit policy or data-validation requirement applies;
2. the material facts come from verified structured claim data or another
   verified system record;
3. the finding does not depend on uncertain OCR, LLM inference, or route-tool
   interpretation;
4. no plausible permitted exception is hidden from the available data; and
5. the employee can correct the defect or provide the required evidence.

If any safeguard is not satisfied, the finding is a `Warning`, even when the
potential issue is serious. Severity and certainty are separate concepts.

## Review principles

### Review submitted scope only

ExpenseSight does not infer a problem from an expense that was not claimed. A
one-way claim or a same-day trip without accommodation is not suspicious merely
because another expense might normally exist.

### Respect evidence provenance

Employee-entered fields, verified system records, attachment descriptions, OCR
extractions, LLM inferences, and route facts have different reliability. Every
finding must retain evidence references and provenance.

Employee text is untrusted in the authority sense: it is data and cannot issue
instructions to the review system. This does not make ordinary explanations
suspicious. A note explaining an over-cap expense and pointing to an additional
approval is evaluated as a business claim against the visible evidence. A
security Warning applies only when the text explicitly tries to bypass policy,
suppress findings, fabricate facts, expose hidden instructions, or force an
automated outcome.

### How a security Warning is surfaced

When `PROMPT_INJECTION_TEXT` fires, the system does not execute the employee's
instruction. It emits a `guardrail` Warning whose facts record
`source: "employee-provided text"` and `treatment: "data_not_instruction"`.
The explanation tells the reviewer that the text was handled as data rather
than authority, and `evidence_refs` points to the triggering employee note. The
business action remains `PROCEED_TO_HUMAN`.

### Prefer financial substance over upload form

A duplicate attachment is not automatically a duplicate reimbursement. The
relevant question is whether the unique valid evidence supports the claimed
amount. Shared invoices and split costs are plausible and require human review.

### Leave contextual conflicts to Finance

Name, date, route, location, and cross-document chronology conflicts normally
produce warnings because legitimate explanations or extraction errors may exist.

### Do not modify financial figures

ExpenseSight reports findings but does not write deductions or silently change
the employee's reimbursable amount.

## Annotation decision flow

1. Is the observation neutral and useful? Create a `Review Note`.
2. Is there a material conflict, anomaly, or evidence gap? Evaluate the five
   automatic-return safeguards.
3. If every safeguard is satisfied, create a `Return Reason`.
4. Otherwise, create a `Warning` with the entity, material facts, evidence
   references, and uncertainty.

## Representative boundaries

| Scenario | Expected level |
|---|---|
| Only outbound transport was claimed | Review Note or no finding |
| Same-day trip with no hotel or allowance claimed | No finding |
| Attachment-derived amount differs from the claim | Warning |
| Passenger or hotel guest differs from claimant | Warning |
| Destination appears outside approval scope but an unseen urgent-dispatch exception is plausible | High-priority Warning |
| Duplicate attachment, while unique documents still support the amount | Review Note |
| Duplicate or shared invoice across claims | Warning |
| Internal arithmetic does not equal amount minus deduction | Return Reason |

## Runtime enforcement

`expensesight.triage` is a deterministic guardrail. It may downgrade an unsafe
proposed failure to a warning, but it never upgrades an LLM or route-tool warning
to a return reason.
