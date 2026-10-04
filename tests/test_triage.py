from __future__ import annotations

import unittest
from pathlib import Path
import sys


SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from expensesight.contracts import RuleFinding
from expensesight.triage import is_return_eligible, triage_rule_findings


def finding(**overrides) -> RuleFinding:
    values = {
        "rule_code": "TEST_FINDING",
        "description": "Test finding.",
        "policy_clause": "Test policy clause",
        "severity": "fail",
        "entity_ref": "claim",
        "evidence_refs": ["claim"],
        "evidence_source": "structured_claim",
        "evidence_reliability": "verified",
        "plausible_exception": False,
        "employee_actionable": True,
    }
    values.update(overrides)
    return RuleFinding(**values)


class ReviewBoundaryTests(unittest.TestCase):
    def test_verified_structured_failure_is_return_eligible(self):
        item = finding()
        self.assertTrue(is_return_eligible(item))
        result = triage_rule_findings([item])
        self.assertEqual(result.return_reasons, [item])
        self.assertEqual(result.review_warnings, [])

    def test_uncertain_attachment_extraction_is_downgraded_to_warning(self):
        item = finding(
            evidence_source="attachment_extraction",
            evidence_reliability="uncertain",
        )
        result = triage_rule_findings([item])
        self.assertEqual(result.return_reasons, [])
        self.assertEqual(result.review_warnings[0].warning_code, "TEST_FINDING")

    def test_plausible_exception_is_downgraded_to_warning(self):
        item = finding(plausible_exception=True)
        result = triage_rule_findings([item])
        self.assertEqual(result.return_reasons, [])
        self.assertTrue(result.review_warnings[0].facts["plausible_exception"])

    def test_non_actionable_finding_cannot_return_employee(self):
        item = finding(employee_actionable=False)
        self.assertFalse(is_return_eligible(item))

    def test_warning_never_becomes_return_reason(self):
        item = finding(severity="warn")
        result = triage_rule_findings([item])
        self.assertEqual(result.return_reasons, [])
        self.assertEqual(len(result.review_warnings), 1)


if __name__ == "__main__":
    unittest.main()
