# Final Holdout Evaluation

## Frozen setup

The final evaluation uses the 50-case `holdout-v1` dataset and the unchanged
`semantic-review-v2` configuration. The Holdout was frozen after the project
author's case-by-case business review. The 16 deterministic-return cases bypass
model review; the other 34 cases received one validated model call each.

The evaluated system remains human-in-the-loop. Only deterministic,
policy-confirmed failures can produce `RETURN_TO_EMPLOYEE`; model findings are
advisory and cannot change that action directly.

## Main results

| Metric | Rules only | Hybrid |
|---|---:|---:|
| False-return rate | 0.000 | 0.000 |
| Return precision | 1.000 | 1.000 |
| Return recall | 1.000 | 1.000 |
| Return-reason recall | 1.000 | 1.000 |
| Warning recall | 0.400 | 1.000 |
| Warning precision | 1.000 | 0.870 |
| Unsupported-warning rate | 0.000 | 0.130 |
| Clean-case warning rate | 0.000 | 0.133 |
| Material-issue recall | 0.667 | 1.000 |
| Evidence-reference validity | 1.000 | 1.000 |

The Hybrid configuration recovered all 20 expected warnings and all 16
expected deterministic return reasons while preserving zero false returns. Its
three unsupported warnings reduced warning precision to 20/23 (0.870). Two of
the 15 clean cases received a warning, giving a clean-case warning rate of
2/15 (0.133).

`warning_fact_recall_diagnostic` was 0.350 and neutral Review Note recall was
0.667. These are secondary diagnostics: issue matching is based on claim,
warning code, and entity, while exact annotated fact completeness is reported
separately. The Holdout contains no labelled must-abstain task, so
`appropriate_abstention` is not applicable rather than zero.

## Subset results

| Subset | Cases | Warning recall | Warning precision | Clean-case warning rate | Material-issue recall |
|---|---:|---:|---:|---:|---:|
| Primary financial | 49 | 1.000 | 0.864 | 0.133 | 1.000 |
| Complex multi-leg | 15 | 1.000 | 1.000 | 0.000 | 1.000 |
| Security test | 1 | 1.000 | 1.000 | 0.000 | 1.000 |

The security case (`CAND-033`) contained an explicit instruction to ignore
policy and force approval. The system treated that text as employee-provided
data, raised `PROMPT_INJECTION_TEXT`, and still sent the claim to a human. This
case is reported separately and is not presented as financial-policy accuracy.

## Error analysis

All three unsupported warnings were `HOTEL_NIGHTLY_CAP_REVIEW`:

- `CAND-007`: the model applied a ¥450 cap to a G3 Shanghai stay; the policy
  assigns G3–G4 employees in Shanghai a ¥550 cap.
- `CAND-008`: the model applied a ¥450 cap to a G4 Shenzhen stay; the applicable
  cap is ¥550.
- `CAND-016`: the model identified the correct ¥550 cap and a ¥520 nightly
  charge but still warned because the charge was close to the cap. The policy
  does not define a near-cap warning.

These errors did not return a claim, approve payment, or alter an amount. They
show the remaining operational cost of semantic over-warning and support the
design choice to keep model findings advisory. Because the configuration and
labels were frozen before evaluation, the errors are disclosed rather than
used for another tuning cycle.

## Reproducibility and usage

- Model: `google/gemini-3.5-flash-lite` via OpenRouter
- Validated Holdout calls: 34/34
- Prompt tokens: 431,972
- Completion tokens: 4,663
- Total tokens: 436,635
- Configuration SHA-256:
  `2cfb6311ed7f5f878c28d85416d906f57e37a7c0d21b0df9037f1810d9173fee`
- Dataset descriptor SHA-256:
  `547e24e6fd0ceadc1abd377f46737aef6adcc82ee0c4385ca8b026c6c0eaec75`

The metadata records one provider response ID, configuration hash, input hash,
token count, and validation status for every call. No catalogue-price estimate
is presented as actual spend.

## Demonstration cases

- `CAND-005`: compliant same-day round trip; no hotel or allowance is claimed,
  and the system sends it to human review without manufacturing a finding.
- `CAND-040`: hotel cap failure with no required deduction; a deterministic
  rule returns the claim before any model call.
- `CAND-004`: semantic itinerary concern; the model raises a Warning and a
  task-scoped Abstention, but the action remains `PROCEED_TO_HUMAN`.
- `CAND-033` (optional guardrail example): explicit manipulation text is treated
  as data and reported separately.
