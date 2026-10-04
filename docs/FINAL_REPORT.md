# ExpenseSight: Human-in-the-Loop Travel Expense Pre-Review

## 1. Problem and intended user

I built ExpenseSight for finance reviewers in large enterprises that digitise expense reimbursement. Travel claims in these organisations may contain pre-approvals, several transport legs, hotel deductions, allowances, receipts and free-text explanations. A reviewer must decide whether a claim contains a confirmed policy failure that should be returned to the employee, or whether it should continue to finance with the important evidence highlighted. Manual review is slow and inconsistent, but a fully automated rejection system would create a more serious risk: an uncertain model judgement could send an employee into an unnecessary correction cycle.

I therefore address one bounded question: can a hybrid rules-and-LLM system increase the recall of material review issues while keeping false returns at zero? `PROCEED_TO_HUMAN` is not approval. ExpenseSight never approves, rejects, pays or changes a claimed amount. The closest commercial alternative is SAP Concur Travel & Expense, which provides configurable approval workflows and automated policy checks. ExpenseSight does not replace that platform; it tests a narrower semantic review layer for inconsistencies spread across an itinerary, an attachment summary and an employee explanation, without transferring decision authority to the model.

## 2. Product and technical design

The input is a synthetic travel claim containing structured expense fields, a pre-approval, employee-provided notes and separate one-sentence OCR descriptions of supporting documents. I designed the pipeline to apply deterministic rules first. Only a verified structured failure—such as an arithmetic mismatch, an invalid date order or an unreduced hotel cap excess—can create `RETURN_TO_EMPLOYEE`. Those cases short-circuit before model review.

All other claims remain `PROCEED_TO_HUMAN`. A Gemini 3.5 Flash-Lite call through OpenRouter may then produce three advisory objects: a neutral Review Note, a material Warning, or a task-scoped Abstention when required evidence is unavailable. A strict JSON Schema excludes both an action field and return reasons. Post-call validation checks warning codes, categories, material facts and evidence references before an output can enter the pipeline. Employee text is always data, not authority. This is part of the overall safety design, not a separate feature. A normal explanation such as “the excess was separately approved; see attachment” is checked against visible evidence and is not suspicious by itself. An explicit instruction to ignore policy or force approval is instead surfaced as a `guardrail` Warning whose facts record `treatment: data_not_instruction`, signalling that the claim needs human review without obeying the instruction.

This separation is the main safety control. It reflects the NIST AI Risk Management Framework's emphasis on valid and reliable, accountable and transparent, explainable and interpretable systems, while leaving threshold decisions to human judgement in their context of use ([NIST AI RMF 1.0](https://www.nist.gov/itl/ai-risk-management-framework)). In ExpenseSight, every finding includes an entity and visible evidence path so a finance reviewer can verify it rather than trust an unexplained score.

## 3. Data and evaluation method

I used 50 synthetic final cases: 15 clean cases, 19 warning-review cases and 16 deterministic-return cases. Thirty-five began as generated templates and 15 were derived from finance-review experience, but all names, suppliers, identifiers and amounts are synthetic. I reviewed every case and label in business language before freezing `holdout-v1`. Claims, hidden ground truth and the case manifest are stored separately. Runtime code never loads ground truth. SHA-256 descriptors lock the claims, labels, manifest and policy; changing any component requires a new dataset version.

I developed the prompt on a separate 22-case Dev set with different identifiers. The final `semantic-review-v2` fingerprint fixed the model, prompts, policy context, warning taxonomy, schema and pipeline contract before Holdout evaluation. The 16 deterministic-return Holdout cases required no model call; each of the other 34 cases received one validated call. After freezing, I changed neither prompts nor labels.

Rules-only and Hybrid configurations were compared on exactly the same ordered Holdout. The primary measures were material-issue recall and false-return rate, because recall alone can be “won” by flagging everything. I also measured return precision and recall, warning precision and recall, unsupported-warning rate, clean-case warning rate and evidence-reference validity. Complex multi-leg journeys were reported separately, as was one security test, so security behaviour was not presented as financial-policy accuracy.

## 4. Results

Rules-only achieved zero false returns and perfect return precision, return recall and return-reason recall. It recovered 40.0% of expected Warnings and 66.7% of all material issues. Hybrid preserved the same perfect return metrics and zero false returns while increasing Warning recall to 100% and material-issue recall to 100%. Every cited evidence reference was valid.

The improvement had a measurable cost. Hybrid produced 23 Warnings for 20 expected issues, so Warning precision was 87.0% and unsupported-warning rate was 13.0%. Two of 15 clean cases received a Warning, giving a clean-case warning rate of 13.3%. On the 15-case complex multi-leg subset, Warning recall, Warning precision and material-issue recall were all 100%. The one security case also passed: explicit text telling the reviewer to ignore policy was treated as employee data and surfaced, without changing the action.

All three unsupported Warnings were hotel-cap errors. In two cases, the model used a ¥450 limit for G3–G4 stays in Shanghai or Shenzhen, where the policy limit was ¥550. In the third, it correctly identified a ¥520 charge and a ¥550 limit but still warned because the amount was “close” to the limit, a condition not defined by policy. These errors did not return a claim or modify money, but they would still consume reviewer attention. They demonstrate why Warning precision and clean-case warning rate must be reported beside recall.

The final Holdout run made 34 validated calls, using 431,972 prompt tokens and 4,663 completion tokens, 436,635 tokens in total. At OpenRouter's 4 October 2026 list prices of US$0.30 per million input tokens and US$2.50 per million output tokens, this usage corresponds to about US$0.14. This is a reproducible estimate, not an invoice. I did not use Google Maps Routes or the OpenAI Responses API, so their project usage cost was zero.

## 5. Critique, risks and future path

The evaluation supports the architecture rather than proving production readiness. Deterministic rules reliably protect the return boundary, while the LLM adds coverage for semantic issues. However, the dataset is small and mostly synthetic; I alone reviewed the labels, so there is no inter-annotator agreement or evidence of external validity. I also had no production claim-volume or reviewer-time data, so I do not claim measured time or cash savings. The model abstained on 3 of 34 eligible claims (8.8%), but the Holdout contains no labelled must-abstain task; whether those abstentions targeted cases the model would otherwise have answered incorrectly is therefore not measurable. Exact annotated-fact recall was also only 35.0%, showing that issue detection can be correct while an evidence summary remains incomplete.

The main silent-failure risk is a plausible-looking Warning that cites visible evidence but applies the wrong policy tier, as the hotel errors demonstrate. Mitigations are to keep policy arithmetic deterministic, show the applicable policy clause and evidence to the reviewer, monitor warning precision by category, and audit a sample of both flagged and unflagged claims. Privacy risk is currently limited by synthetic data; a real deployment would require access control, retention limits and redaction before sending documents to an external model. Prompt-injection risk is reduced by treating all employee and attachment text as untrusted data and by making the output schema incapable of authorising payment or return.

The next useful evaluation would involve independently labelled, de-identified real claims and agreement measurement between finance reviewers. Future engineering could add production OCR and route facts as separately costed, privacy-reviewed components, not silently fold them into the current result. A pilot should measure reviewer time, override rate and employee rework alongside model metrics. Until that evidence exists, ExpenseSight should remain a decision-support pre-screen: rules control confirmed failures, the model supplies traceable advisory context, and a human finance reviewer owns the judgement.

## References

National Institute of Standards and Technology. *Artificial Intelligence Risk Management Framework 1.0*. https://www.nist.gov/itl/ai-risk-management-framework

OpenRouter. *Google Gemini 3.5 Flash Lite API Pricing*. Accessed 4 October 2026. https://openrouter.ai/google/gemini-3.5-flash-lite-20260721

SAP Concur. *Business Travel and Expense Management Software*. Accessed 4 October 2026. https://www.concur.com/products/travel-expense
