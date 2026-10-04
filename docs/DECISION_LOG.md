# Decision Log

## Confirmed decisions

### Human-in-the-loop boundary

- Business outcomes are limited to `RETURN_TO_EMPLOYEE` and `PROCEED_TO_HUMAN`.
- Only deterministic rule failures may return a claim.
- An LLM or external route tool may create review warnings but may not return a claim.
- Abstention is a review status, not a third business outcome.

### Evaluation labels

- `expected_action` evaluates whether the system should return the claim.
- `expected_return_reasons` evaluates deterministic return reasons.
- `expected_warnings` evaluates issue-level warning detection.
- `expected_review_notes` records neutral, evidence-grounded context separately from issues.
- Warning wording is not compared verbatim.
- A warning match requires the same warning code, entity, and material facts.
- Human authors create and review the ground truth, but runtime evaluation compares predictions with the frozen expected labels.

### Evaluation case groups

The holdout is analysed as three mutually exclusive groups derived from the expected labels; no redundant label is required in each record:

- `clean_pass`: `PROCEED_TO_HUMAN`, with no expected return reason and no expected warning. The claim conforms to the reimbursement standard and should reach the reviewer without a system concern.
- `warning_review`: `PROCEED_TO_HUMAN`, with one or more expected warnings. The system should surface the possible issue but must not return the claim automatically.
- `return_required`: `RETURN_TO_EMPLOYEE`, with one or more deterministic expected return reasons.

These are evaluation groups, not three business actions. ExpenseSight still produces only `RETURN_TO_EMPLOYEE` or `PROCEED_TO_HUMAN` and never auto-approves a reimbursement.

### Complex multi-leg definition

- An ordinary outbound-and-return journey (`A -> B -> A`) is not a complex multi-leg case.
- A complex multi-leg case requires continuity reasoning across transport segments, such as an intermediate or changed destination, an open chain, or a location gap between one segment's arrival and the next segment's departure.
- Complex multi-leg performance is reported as a dedicated evaluation subset rather than inferred from the raw number of transport lines.

### Data

- Model-visible claims and ground truth are stored separately.
- Candidate data is reviewed before it is frozen.
- Synthetic data limitations must be reported.
- Real personal data is excluded.
- Expense lines and attachments are separate. Each attachment retains one short OCR description and explicit expense references.
- Duplicate uploads are assessed by their financial effect; duplicate form alone is not a return reason.
- Hotel claims use fixed form fields for night count and total financial amounts;
  there is no employee-entered nightly-rate field. Rules derive an average
  reimbursable rate from total divided by nights, while uneven nightly prices
  remain attachment evidence and therefore cannot directly return a claim.

### Architecture

- Rules plus LLM is the core candidate system.
- Google Maps or equivalent route data is optional.
- Offline/mock route facts are required before any live integration.
- Live API pricing and cost-to-serve must be checked before use.

### Return boundary

- Attachment-derived amount differences, duplicate documents, repeated invoice identifiers, and approval-scope anomalies are warnings because extraction error or a legitimate exception may exist.
- Automatic returns are limited to verified structured defects, including arithmetic inconsistencies, invalid negative amounts, deductions above billed amounts, structured hotel-cap failures, allowance calculation failures, hotel-night inconsistencies, and impossible structured date order.
- Seriousness does not imply certainty; a high-priority warning remains advisory.

### Model review and reproducibility

- The default Dev model is `google/gemini-3.5-flash-lite` through OpenRouter,
  with temperature 0 and strict structured output.
- Semantic Warning schemas branch by warning code and are checked again against
  the versioned taxonomy before an output is saved.
- A visible document-quality problem may coexist with task-scoped Abstention
  when the unreadable evidence prevents a stronger conclusion, such as a
  passenger-identity check.
- Resume is allowed only for outputs with matching configuration and claim-input
  hashes. Structural validity alone is not sufficient provenance.
- Earlier mixed-prompt and smoke-test files are retained in the external process
  archive as iteration evidence, not as single-configuration benchmarks.
- `semantic-review-v1` is retained as a historical Dev checkpoint. It was
  superseded before Holdout after business review refined the claim schema and
  two semantic boundaries.
- Pre-holdout business review distinguishes authority from suspicion: every
  employee-provided note is data rather than an instruction, but ordinary
  exception explanations remain valid evidence leads and do not trigger a
  security Warning. `PROMPT_INJECTION_TEXT` is reserved for explicit attempts
  to bypass policy, suppress findings, invent facts, expose hidden instructions,
  or force an automated outcome.
- Because this clarification changed the active prompt and taxonomy before any
  Holdout model run, the replacement configuration was versioned and rerun on
  Dev before it became Holdout-eligible.
- All 16 `semantic-review-v2` Dev outputs were regenerated and validated. Core
  recall, safety, evidence, and abstention metrics met the stop criteria. One
  additional `HOTEL_LOCATION_REVIEW` on `DEV-011` produced warning precision
  0.917; it is retained as a disclosed limitation to avoid another round of
  Dev overfitting.
- `semantic-review-v2` is the final frozen configuration. All 34 model-eligible
  `holdout-v1` claims completed under this fingerprint. The saved Hybrid result
  is final and the three unsupported hotel-cap Warnings remain disclosed rather
  than being used for post-Holdout tuning.
