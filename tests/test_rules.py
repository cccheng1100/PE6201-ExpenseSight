from __future__ import annotations

import unittest
from datetime import date
from pathlib import Path
import sys


SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from expensesight.contracts import (
    Attachment,
    CabinClass,
    Claim,
    Grade,
    HotelStay,
    PreApproval,
    ReviewNote,
    ReviewWarning,
    TransportLeg,
    TransportType,
    DecisionType,
)
from expensesight.pipeline import run_pipeline


def base_claim(claim_id: str = "TEST-001") -> Claim:
    return Claim(
        claim_id=claim_id,
        employee_id="SYN-E001",
        employee_name="Synthetic Employee",
        grade=Grade.G2,
        transport_legs=[
            TransportLeg(
                leg_id=f"{claim_id}-L1",
                transport=TransportType.RAIL,
                depart_city="Guangzhou",
                arrive_city="Shanghai",
                depart_date=date(2026, 3, 10),
                arrive_date=date(2026, 3, 10),
                cabin=CabinClass.ECONOMY,
                amount_rmb=500,
                reimbursable_rmb=500,
                ticket_desc="Rail ticket, fare RMB 500, ticket no. SYN-001-A",
            )
        ],
        hotel_stays=[
            HotelStay(
                city="Shanghai",
                check_in=date(2026, 3, 10),
                check_out=date(2026, 3, 11),
                nights=1,
                amount_rmb=420,
                reimbursable_rmb=420,
                folio_desc="One night in Shanghai",
                invoice_desc="Invoice no. SYN-INV-001, amount RMB 420",
            )
        ],
        attachments=[
            Attachment("ATT-T1", "transport_ticket", ["transport_legs[0]"], "Rail ticket, fare RMB 500, ticket no. SYN-001-A"),
            Attachment("ATT-HF1", "hotel_folio", ["hotel_stays[0]"], "One night in Shanghai"),
            Attachment("ATT-HI1", "hotel_invoice", ["hotel_stays[0]"], "Invoice no. SYN-INV-001, amount RMB 420"),
        ],
        pre_approval=PreApproval(
            approval_id="PA-001",
            approved_on=date(2026, 3, 1),
            valid_from=date(2026, 3, 10),
            valid_to=date(2026, 3, 11),
            destination_cities=["Shanghai"],
        ),
        submitted_on=date(2026, 3, 15),
    )


class RuleBoundaryTests(unittest.TestCase):
    def test_clean_claim_proceeds(self):
        decision = run_pipeline(base_claim())
        self.assertEqual(decision.action, DecisionType.PROCEED_TO_HUMAN)
        self.assertEqual(decision.return_reasons, [])

    def test_each_hotel_stay_uses_total_divided_by_nights_for_cap_check(self):
        claim = base_claim()
        claim.hotel_stays = [
            HotelStay("Shanghai", date(2026, 3, 10), date(2026, 3, 11), 1, 300, 0, 300, "folio A", "Invoice no. A-1, amount RMB 300"),
            HotelStay("Shanghai", date(2026, 3, 11), date(2026, 3, 12), 1, 580, 0, 580, "folio B", "Invoice no. B-1, amount RMB 580"),
        ]
        claim.pre_approval.valid_to = date(2026, 3, 12)
        decision = run_pipeline(claim)
        self.assertEqual(decision.action, DecisionType.RETURN_TO_EMPLOYEE)
        self.assertIn("HOTEL_OVER_CAP_NOT_DEDUCTED", [item.rule_code for item in decision.return_reasons])

    def test_one_way_claim_is_not_treated_as_an_error(self):
        claim = base_claim()
        decision = run_pipeline(claim)
        self.assertNotIn("ITINERARY_NOT_CLOSED", [item.rule_code for item in decision.return_reasons])

    def test_unapproved_destination_without_visible_exception_warns(self):
        claim = base_claim()
        claim.transport_legs[0].arrive_city = "Hangzhou"
        decision = run_pipeline(claim)
        self.assertEqual(decision.action, DecisionType.PROCEED_TO_HUMAN)
        self.assertIn("APPROVAL_SCOPE_MISMATCH", [item.warning_code for item in decision.review_warnings])

    def test_unapproved_destination_with_unverified_exception_goes_to_human(self):
        claim = base_claim()
        claim.transport_legs[0].arrive_city = "Hangzhou"
        claim.special_notes = "Supervisor signed a paper change request; Finance should verify it."
        decision = run_pipeline(claim)
        self.assertEqual(decision.action, DecisionType.PROCEED_TO_HUMAN)
        self.assertIn("APPROVAL_SCOPE_MISMATCH", [item.warning_code for item in decision.review_warnings])

    def test_document_amount_mismatch_warns_when_extraction_is_uncertain(self):
        claim = base_claim()
        claim.transport_legs[0].amount_rmb = 675
        claim.transport_legs[0].reimbursable_rmb = 675
        claim.attachments[0].ocr_description = "Electronic ticket, fare RMB 650, ticket no. SYN-001-A"
        decision = run_pipeline(claim)
        self.assertEqual(decision.action, DecisionType.PROCEED_TO_HUMAN)
        self.assertIn("TRANSPORT_DOCUMENT_AMOUNT_MISMATCH", [item.warning_code for item in decision.review_warnings])

    def test_duplicate_ticket_across_expense_lines_warns(self):
        claim = base_claim()
        duplicate = TransportLeg(
            leg_id="TEST-001-L2",
            transport=TransportType.RAIL,
            depart_city="Shanghai",
            arrive_city="Guangzhou",
            depart_date=date(2026, 3, 11),
            arrive_date=date(2026, 3, 11),
            cabin=CabinClass.ECONOMY,
            amount_rmb=500,
            reimbursable_rmb=500,
            ticket_desc="Rail ticket, fare RMB 500, ticket no. SYN-001-A",
        )
        claim.transport_legs.append(duplicate)
        claim.attachments.append(Attachment(
            "ATT-T2", "transport_ticket", ["transport_legs[1]"],
            "Rail ticket, fare RMB 500, ticket no. SYN-001-A",
        ))
        decision = run_pipeline(claim)
        self.assertEqual(decision.action, DecisionType.PROCEED_TO_HUMAN)
        self.assertIn("DUPLICATE_DOCUMENT_SUPPORT_REVIEW", [item.warning_code for item in decision.review_warnings])

    def test_duplicate_attachment_on_same_expense_is_a_review_note(self):
        claim = base_claim()
        claim.attachments.append(Attachment(
            "ATT-T1-COPY", "transport_ticket", ["transport_legs[0]"],
            claim.attachments[0].ocr_description,
        ))
        decision = run_pipeline(claim)
        self.assertEqual(decision.action, DecisionType.PROCEED_TO_HUMAN)
        self.assertIn("DUPLICATE_ATTACHMENT_IGNORED", [item.note_code for item in decision.review_notes])
        self.assertNotIn("DUPLICATE_DOCUMENT_SUPPORT_REVIEW", [item.warning_code for item in decision.review_warnings])

    def test_structured_arithmetic_mismatch_returns(self):
        claim = base_claim()
        claim.transport_legs[0].reimbursable_rmb = 525
        decision = run_pipeline(claim)
        self.assertEqual(decision.action, DecisionType.RETURN_TO_EMPLOYEE)
        self.assertIn("AMOUNT_ARITHMETIC_MISMATCH", [item.rule_code for item in decision.return_reasons])

    def test_deterministic_return_short_circuits_advisory_output(self):
        claim = base_claim()
        claim.transport_legs[0].reimbursable_rmb = 525
        warning = ReviewWarning(
            warning_code="POSSIBLE_NON_BUSINESS_TRIP",
            category="transport",
            entity_ref="transport_legs[0]",
            evidence_refs=["transport_legs[0]"],
            explanation="This advisory output must be ignored after a deterministic return.",
        )
        decision = run_pipeline(claim, model_warnings=[warning])
        self.assertEqual(decision.action, DecisionType.RETURN_TO_EMPLOYEE)
        self.assertEqual(decision.review_warnings, [])
        self.assertEqual(decision.review_notes, [])
        self.assertEqual(decision.abstentions, [])

    def test_model_warning_cannot_return_a_claim(self):
        claim = base_claim()
        warning = ReviewWarning(
            warning_code="POSSIBLE_NON_BUSINESS_TRIP",
            category="transport",
            entity_ref="transport_legs[0]",
            evidence_refs=["transport_legs[0].ticket_desc"],
            explanation="Route may not match the declared business purpose.",
        )
        decision = run_pipeline(claim, model_warnings=[warning])
        self.assertEqual(decision.action, DecisionType.PROCEED_TO_HUMAN)
        self.assertIn(warning, decision.review_warnings)

    def test_review_note_does_not_create_a_warning_or_change_action(self):
        claim = base_claim()
        note = ReviewNote(
            note_code="OUTBOUND_ONLY_CLAIMED",
            category="itinerary",
            entity_ref="transport_legs",
            evidence_refs=["transport_legs"],
            text="Only outbound transport was claimed.",
        )
        decision = run_pipeline(claim, review_notes=[note])
        self.assertEqual(decision.action, DecisionType.PROCEED_TO_HUMAN)
        self.assertEqual(decision.review_notes, [note])
        self.assertEqual(decision.review_warnings, [])

    def test_historical_invoice_duplicate_warns(self):
        previous = base_claim("PREV-001")
        current = base_claim("CURR-001")
        current.attachments[2].ocr_description = previous.attachments[2].ocr_description
        decision = run_pipeline(current, previous_claims=[previous])
        self.assertEqual(decision.action, DecisionType.PROCEED_TO_HUMAN)
        self.assertIn("SHARED_OR_DUPLICATE_INVOICE_REVIEW", [item.warning_code for item in decision.review_warnings])


if __name__ == "__main__":
    unittest.main()
