# ExpenseSight Demo Script (5–6 minutes)

Run this before recording to confirm the three saved cases:

```text
python scripts/show_demo_cases.py
```

The command is offline. It re-runs deterministic rules and uses the already
validated final Holdout outputs; it makes no paid API call.

## 0:00–0:35 — Problem and promise

**Screen:** README title and Safety boundary.

**Say:**

“Hello, I am Jin Cheng. ExpenseSight is a human-in-the-loop travel-expense
pre-review prototype for finance teams in large enterprises that digitise
expense reimbursement. A claim may combine approvals, several journey legs, hotel
deductions, allowances, receipts and employee explanations. My goal is not to
automate approval. It is to find more review issues while avoiding unnecessary
returns to employees.”

## 0:35–1:15 — Architecture and safety boundary

**Screen:** `docs/ARCHITECTURE.md`, then briefly show the model output schema.

**Say:**

“The pipeline deliberately separates authority. Deterministic rules check
arithmetic, dates and explicit policy limits. Only a verified rule failure can
return a claim. All uncertain or semantic findings remain Review Notes,
Warnings or task-scoped Abstentions, and the action stays Proceed to Human.
The model schema has no action field and no return-reasons field, so the model
cannot cross this boundary. Employee and attachment text is treated as data,
not as system instructions.”

## 1:15–2:00 — Case 1: normal same-day trip

**Screen:** Run `python scripts/show_demo_cases.py --claim-id CAND-005`.

**Say:**

“This is a compliant same-day rail round trip. There is no hotel or meal
allowance because none is needed. Earlier in development, absence of those
items could create unnecessary commentary. After business review, the frozen
system produces no Return Reason, Warning or Abstention. Proceed to Human means
the finance reviewer continues the normal workflow; it does not mean automatic
payment.”

## 2:00–2:50 — Case 2: confirmed deterministic failure

**Screen:** Run `python scripts/show_demo_cases.py --claim-id CAND-040`.

**Say:**

“This case contains a hotel amount above the applicable cap without the
required employee deduction. The deterministic rule identifies
HOTEL_OVER_CAP_NOT_DEDUCTED and returns the claim. Notice that semantic model
output used is ‘no’. This is intentional: once a confirmed, employee-actionable
failure exists, the pipeline short-circuits and avoids both ambiguity and an
unnecessary paid call.”

## 2:50–3:50 — Case 3: semantic concern with uncertainty

**Screen:** Run `python scripts/show_demo_cases.py --claim-id CAND-004`.

**Say:**

“Here, a local transport leg runs from a restaurant to a shopping mall while
the declared business destination is a company. A deterministic rule cannot
conclude business purpose from those facts. The semantic layer raises a
POSSIBLE_NON_BUSINESS_TRIP Warning and also abstains from a final business-
purpose conclusion because meeting records are unavailable. Despite the
concern, the action remains Proceed to Human. This shows why semantic review is
useful and why it must remain advisory.”

## 3:50–4:55 — Final evaluation

**Screen:** `docs/FINAL_EVALUATION.md`, Main results and Subset results tables.

**Say:**

“I developed the prompt on a separate 22-case Dev set, then froze the model,
prompts, schema, taxonomy, policy and 50-case Holdout before final evaluation.
Rules-only already had zero false returns and perfect deterministic return
recall, but found only 40 percent of expected Warnings. Hybrid preserved zero
false returns and increased Warning recall and overall material-issue recall to
100 percent. On the 15 complex multi-leg cases, Warning precision and recall
were both 100 percent. The separate security case also passed: an explicit
instruction to ignore policy was treated as employee data, not obeyed.”

## 4:55–5:35 — Critique and conclusion

**Screen:** Error analysis in `docs/FINAL_EVALUATION.md`.

**Say:**

“The result is not perfect. The model produced three unsupported hotel-cap
Warnings. Two used the wrong grade-and-city cap, and one warned merely because
an amount was close to the limit. Warning precision was therefore 87 percent,
and two of 15 clean cases were over-flagged. These errors did not return a
claim, change money or approve payment, but they would consume reviewer time.
I retained them rather than tuning on the frozen test set. My conclusion is
that the hybrid design adds meaningful semantic coverage, while deterministic
rules and human review remain necessary safeguards. Thank you.”
