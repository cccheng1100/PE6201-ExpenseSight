# Real-World Grounding: From Enterprise Finance Practice to System Design

This document explains the real-world context behind ExpenseSight's design
decisions. It is written for readers unfamiliar with Chinese corporate
reimbursement practice, so the trade-offs I made are visible rather than
invisible.

A note on evidence: I keep the actual receipts I studied locally and do not
commit them to this repository because they contain personal data and traceable
invoice identifiers. Everything below describes their relevant fields in text.
Partially redacted image studies also remain outside the submission because a
barcode, QR fragment, invoice number, or verification code can still allow a
document to be traced.

---

## 1. Where the design comes from

I spent five years as a finance professional in a large enterprise that used a
centralised ERP workflow with scanned receipts for employee travel-expense
claims. In that role I reviewed such claims day to day. That experience is the
source of the project's non-obvious review boundaries. I present those
boundaries as project assumptions rather than universal reimbursement rules.

## 2. The real workflows that shaped the design

**Urgent dispatch often precedes paperwork.** An employee may be sent to a
client site or branch office the same morning, book a train ticket on the way,
and submit the 出差审批单 (paper approval) days later. A pre-screen that
auto-rejects missing or expired pre-approval would bounce every urgent trip —
useless.

**Receipts accumulate and get batched.** Field staff can be away from the
office for weeks without easy access to a scanner or their desk. A hard 30-day
filing cutoff would reject legitimate claims; a 60-day soft reminder is a real
compromise, not a random number.

**The employee self-deducts before submission.** In practice the 核减 (deduction)
is filled in by the employee, who knows whether they stayed an extra night for a
legitimate reason. The system cannot know that context. So the rule checks
whether the reimbursable amount is still over cap **after** the employee's own
deduction — it never computes the deduction itself.

**A hotel claim needs two documents in the workflow I reviewed.** The VAT invoice
records the reimbursable service and amount, while the hotel folio (水单/消费明细)
provides the stay and charge detail. A reviewer checks that the totals agree and
that personal charges such as mini-bar or laundry are excluded. Missing folio
or invoice therefore goes to a human, not to an auto-return.

**Ride-hailing receipts do not identify the passenger.** Didi invoices and taxi
meter receipts show route, time, distance and fare — usually no passenger name.
Flagging this as missing information would be noise.

**Business class exists but is rare.** It happens when economy is sold out on an
urgent dispatch, or for medical reasons. The system does not judge the excuse;
it checks whether the paperwork exists (a `special_request` note plus a
supervisor's sign-off) and sends the rest to a human.

## 3. What real receipts look like, and what I modelled

The attachment design is grounded in seven real receipt types common in Chinese
business travel. The examples below describe them; the originals remain local.

| Receipt | What it really shows | What ExpenseSight keeps | What I omit, and why |
|---|---|---|---|
| Rail e-ticket (铁路电子客票) | Train no., route, date, seat class, price, passenger name + ID (partial), buyer org., social credit code, QR code | Train no., route, date, seat class, price, ticket no. | Passenger ID, QR code, buyer org. — privacy and not needed for pre-screening |
| Flight itinerary (航空行程单) | Itinerary no., passenger, flight, fare, airport fee, fuel surcharge, total | Flight no., route, date, cabin, **total price**, ticket no. | Fare breakdown — the policy cap applies to the total |
| Hotel folio (酒店水单) | Guest name, dates, room, nightly rate, itemised charges, total | Nights, room type, nightly rate, total, hotel name/address | Guest name, itemised extras (breakfast/mini-bar) — reviewer detail, not pre-screen |
| VAT ordinary invoice (增值税电子普通发票) | Invoice no., date, service, buyer/seller + tax IDs, bank info, amount | Invoice no., date, service type, total | Tax IDs, tax rate, QR code — accounting concern, not pre-screening |
| Ride-hailing invoice and itinerary (网约车电子发票/行程单) | Invoice no., date, service type, amount; the itinerary may contain route details | Date, route when available, fare, invoice no. | Tax fields — no passenger name exists to verify |
| Taxi receipt (出租车小票) | Date, time, distance, fare, taxi company | Date, time, distance, fare | Plate and licence details — not needed for policy checks |
| VAT special invoice (增值税专用发票) | Invoice code/no., buyer/seller tax IDs, item, tax rate, amount | Invoice no., date, service, total | Tax rate/amount breakdown — tax filing concern, not pre-screening |

## 4. The OCR simplification

A real system OCRs every receipt into ~15 structured tax fields. ExpenseSight
deliberately simulates OCR output as **one sentence per attachment**. This is a
trade-off, and I made it on purpose:

- The model needs enough context to understand the receipt, not every tax field.
- One-sentence descriptions are cheap to generate, easy to audit, and robust to
  OCR errors.
- The total in the description must match the expense line's `amount_rmb` — the
  same consistency check a real auditor performs.
- Invoice numbers are retained because duplicate detection needs them.

The omitted fields (tax rate, tax amount, itemised hotel charges, QR codes) are
accounting and tax-filing concerns, not pre-screening concerns. They are listed
as future work rather than silently dropped.

## 5. Why warn-versus-fail exists

The two-tier severity is a direct consequence of the field experience in
section 2:

| Real-world fact | Consequence in the design |
|---|---|
| Urgent dispatch often lacks paper pre-approval | Missing/expired pre-approval → `warn`, human cross-checks paper trail |
| Employee knows the context of an over-cap stay | Employee self-deduction is read, not recomputed; over-cap after deduction → `fail` |
| Receipts are sometimes late or lost while travelling | Missing receipt → `warn` with the specific item, not an auto-reject |
| Folio/invoice totals must match | Hotel cap is computed from totals; uneven nightly rates stay attachment evidence |
| Some exceptions are legitimate but need proof | Business class needs `special_request` + supervisor sign-off; presence → `warn`, absence → `fail` |
| The system cannot see the world | Only deterministic, policy-confirmed failures can return a claim; everything contextual goes to Finance |

The rule engine exists to remove the trivial, mechanical checks from Finance's
workload. Everything that requires context, empathy, or judgement about a
real-world exception is deliberately left to a human.

## 6. What this means for the evaluation

Because the design encodes real workflows, the evaluation must be read through
the same lens: a `warn` on missing pre-approval is correct behaviour in this
domain, not under-flagging; an auto-return on a missing folio would be
over-flagging. This is why the ground truth was reviewed case by case in
business language before freezing, and why the human-in-the-loop boundary is the
project's central claim rather than a feature added later.
