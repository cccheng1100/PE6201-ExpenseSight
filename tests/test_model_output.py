from __future__ import annotations

import unittest
from pathlib import Path
import sys


SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from expensesight.model_output import (
    ModelOutputValidationError,
    parse_model_review_output,
    validate_warning_taxonomy_contract,
)


class ModelOutputTests(unittest.TestCase):
    def warning_taxonomy(self) -> dict:
        return {
            "codes": [{
                "code": "HOTEL_GUEST_MISMATCH",
                "owner": "semantic_model",
                "fact_keys": ["relationship", "claim_employee", "folio_guest"],
                "required_fact_values": {
                    "relationship": "folio guest differs from claimant"
                },
                "materiality": "material",
                "policy_clause": "Section 7",
            }]
        }

    def valid_output(self) -> dict:
        return {
            "claim_id": "CAND-001",
            "review_notes": [],
            "warnings": [{
                "warning_code": "HOTEL_GUEST_MISMATCH",
                "category": "accommodation",
                "entity_ref": "hotel_stays[0]",
                "facts": {"claim_employee": "A", "folio_guest": "B"},
                "evidence_refs": ["employee_name", "attachments"],
                "policy_clause": "Section 7",
                "materiality": "material",
                "explanation": "The names differ and require human verification."
            }],
            "abstentions": [],
        }

    def test_accepts_strict_advisory_output(self) -> None:
        parsed = parse_model_review_output(self.valid_output(), "CAND-001")
        self.assertEqual(parsed.warnings[0].warning_code, "HOTEL_GUEST_MISMATCH")

    def test_rejects_model_selected_action(self) -> None:
        raw = self.valid_output()
        raw["action"] = "RETURN_TO_EMPLOYEE"
        with self.assertRaises(ModelOutputValidationError):
            parse_model_review_output(raw)

    def test_rejects_model_return_reason(self) -> None:
        raw = self.valid_output()
        raw["return_reasons"] = ["SOME_REASON"]
        with self.assertRaises(ModelOutputValidationError):
            parse_model_review_output(raw)

    def test_rejects_wrong_claim_id(self) -> None:
        with self.assertRaises(ModelOutputValidationError):
            parse_model_review_output(self.valid_output(), "CAND-002")

    def test_warning_taxonomy_contract_accepts_exact_fields(self) -> None:
        raw = self.valid_output()
        raw["warnings"][0]["facts"]["relationship"] = "folio guest differs from claimant"
        parsed = parse_model_review_output(raw, "CAND-001")
        validate_warning_taxonomy_contract(parsed, self.warning_taxonomy())

    def test_warning_taxonomy_contract_rejects_missing_or_cross_code_facts(self) -> None:
        raw = self.valid_output()
        raw["warnings"][0]["facts"]["unreadable_field"] = "guest_name"
        parsed = parse_model_review_output(raw, "CAND-001")
        with self.assertRaises(ModelOutputValidationError):
            validate_warning_taxonomy_contract(parsed, self.warning_taxonomy())

    def test_warning_taxonomy_contract_rejects_metadata_drift(self) -> None:
        raw = self.valid_output()
        raw["warnings"][0]["facts"]["relationship"] = "folio guest differs from claimant"
        raw["warnings"][0]["materiality"] = "high"
        parsed = parse_model_review_output(raw, "CAND-001")
        with self.assertRaises(ModelOutputValidationError):
            validate_warning_taxonomy_contract(parsed, self.warning_taxonomy())


if __name__ == "__main__":
    unittest.main()
