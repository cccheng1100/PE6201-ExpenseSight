from __future__ import annotations

import unittest
from pathlib import Path
import sys


SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from expensesight.evaluation import evidence_reference_is_valid, evaluate_records


class EvaluationTests(unittest.TestCase):
    def test_evidence_reference_validation(self) -> None:
        claim = {
            "employee_name": "A",
            "transport_legs": [{"amount_rmb": 100}],
            "attachments": [{"attachment_id": "ATT-1", "ocr_description": "x"}],
        }
        self.assertTrue(evidence_reference_is_valid("employee_name", claim))
        self.assertTrue(evidence_reference_is_valid("transport_legs[0].amount_rmb", claim))
        self.assertTrue(evidence_reference_is_valid("attachments[ATT-1].ocr_description", claim))
        self.assertFalse(evidence_reference_is_valid("transport_legs[3].amount_rmb", claim))
        self.assertFalse(evidence_reference_is_valid("transport_legs[0].missing", claim))
        self.assertFalse(evidence_reference_is_valid("attachments[ATT-1].missing", claim))
        self.assertFalse(evidence_reference_is_valid("secret_field", claim))
        previous = {"C0": {"claim_id": "C0", "employee_name": "B"}}
        self.assertTrue(
            evidence_reference_is_valid("previous_claims[C0].employee_name", claim, previous)
        )
        self.assertFalse(
            evidence_reference_is_valid("previous_claims[FAKE].employee_name", claim, previous)
        )

    def test_wording_is_not_used_but_material_facts_are_diagnosed(self) -> None:
        claims = [{"claim_id": "C1", "employee_name": "A", "attachments": []}]
        ground_truth = [{
            "claim_id": "C1",
            "expected_action": "PROCEED_TO_HUMAN",
            "expected_return_reasons": [],
            "expected_review_notes": [],
            "expected_warnings": [{
                "warning_code": "NAME_MISMATCH",
                "entity_ref": "attachments",
                "expected_facts": {"claim_employee": "A", "document_name": "B"},
            }],
        }]
        predictions = [{
            "claim_id": "C1",
            "action": "PROCEED_TO_HUMAN",
            "return_reasons": [],
            "review_notes": [],
            "warnings": [{
                "warning_code": "NAME_MISMATCH",
                "entity_ref": "attachments",
                "facts": {"claim_employee": "A", "document_name": "B"},
                "evidence_refs": ["employee_name", "attachments"],
                "explanation": "Different wording is irrelevant.",
            }],
            "abstentions": [],
        }]
        result = evaluate_records(claims, ground_truth, predictions)
        self.assertEqual(result["metrics"]["warning_recall"], 1.0)
        self.assertEqual(result["metrics"]["warning_fact_recall_diagnostic"], 1.0)
        self.assertEqual(result["metrics"]["evidence_reference_validity"], 1.0)


if __name__ == "__main__":
    unittest.main()
