from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DevelopmentDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.claims = json.loads((ROOT / "data" / "dev" / "dev_claims.json").read_text(encoding="utf-8"))
        cls.ground_truth = json.loads((ROOT / "evals" / "dev_ground_truth.json").read_text(encoding="utf-8"))
        cls.taxonomy = json.loads((ROOT / "evals" / "warning_taxonomy.json").read_text(encoding="utf-8"))

    def test_dev_ids_are_separate_from_holdout(self) -> None:
        holdout = json.loads((ROOT / "data" / "candidate_holdout_claims.json").read_text(encoding="utf-8"))
        self.assertFalse(
            {item["claim_id"] for item in self.claims}
            & {item["claim_id"] for item in holdout}
        )

    def test_dev_distribution_is_6_10_6(self) -> None:
        clean = sum(item["expected_action"] == "PROCEED_TO_HUMAN" and not item["expected_warnings"] for item in self.ground_truth)
        warnings = sum(item["expected_action"] == "PROCEED_TO_HUMAN" and bool(item["expected_warnings"]) for item in self.ground_truth)
        returns = sum(item["expected_action"] == "RETURN_TO_EMPLOYEE" for item in self.ground_truth)
        self.assertEqual((clean, warnings, returns), (6, 10, 6))

    def test_warning_taxonomy_covers_all_dev_labels(self) -> None:
        codes = {item["code"] for item in self.taxonomy["codes"]}
        expected = {
            warning["warning_code"]
            for case in self.ground_truth
            for warning in case["expected_warnings"]
        }
        self.assertTrue(expected <= codes)

    def test_semantic_warning_taxonomy_has_output_contracts(self) -> None:
        semantic_codes = [
            item for item in self.taxonomy["codes"]
            if item["owner"] in {"semantic_model", "semantic_model_or_route_layer"}
        ]
        self.assertTrue(semantic_codes)
        for item in semantic_codes:
            self.assertIn("fact_keys", item)
            self.assertIn("required_fact_values", item)
            self.assertIn(item["materiality"], {"material", "high", "guardrail"})
            self.assertIn("policy_clause", item)
            self.assertTrue(set(item["required_fact_values"]) <= set(item["fact_keys"]))

    def test_dev_contains_expected_abstention(self) -> None:
        self.assertEqual(
            sum(len(item.get("expected_abstentions", [])) for item in self.ground_truth),
            3,
        )


if __name__ == "__main__":
    unittest.main()
