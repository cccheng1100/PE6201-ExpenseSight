import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from expensesight.openrouter import (  # noqa: E402
    OpenRouterClient,
    _structured_output_schema,
    build_messages,
    load_review_assets,
)


class OpenRouterAdapterTests(unittest.TestCase):
    def test_material_fact_schema_is_explicit_and_inlined(self):
        schema = load_review_assets(ROOT)["output_schema"]
        prepared = _structured_output_schema(schema)
        warning_facts = prepared["properties"]["warnings"]["items"]["properties"]["facts"]
        note_facts = prepared["properties"]["review_notes"]["items"]["properties"]["facts"]

        self.assertNotIn("$defs", prepared)
        self.assertNotIn("$ref", warning_facts)
        self.assertFalse(warning_facts["additionalProperties"])
        self.assertIn("relationship", warning_facts["properties"])
        self.assertIn("claimed_direction", note_facts["properties"])
        materiality = prepared["properties"]["warnings"]["items"]["properties"]["materiality"]
        self.assertEqual(materiality["enum"], ["material", "high", "guardrail"])

    def test_warning_taxonomy_creates_code_specific_schema_branches(self):
        schema = load_review_assets(ROOT)["output_schema"]
        taxonomy = {
            "codes": [{
                "code": "TRANSPORT_PASSENGER_MISMATCH",
                "owner": "semantic_model",
                "fact_keys": ["relationship", "claim_employee", "ticket_passenger"],
                "materiality": "material",
                "policy_clause": "Section 7 — Required Attachments",
            }]
        }
        prepared = _structured_output_schema(schema, taxonomy)
        branches = prepared["properties"]["warnings"]["items"]["oneOf"]
        self.assertEqual(len(branches), 1)
        branch = branches[0]
        self.assertEqual(
            branch["properties"]["warning_code"]["enum"],
            ["TRANSPORT_PASSENGER_MISMATCH"],
        )
        self.assertEqual(
            set(branch["properties"]["facts"]["required"]),
            {"relationship", "claim_employee", "ticket_passenger"},
        )
        self.assertFalse(branch["properties"]["facts"]["additionalProperties"])
        self.assertIn("policy_clause", branch["required"])

    def test_build_messages_replaces_all_markers(self):
        messages = build_messages(
            system_prompt="system",
            request_template="{{POLICY_CONTEXT}}\n{{WARNING_TAXONOMY}}\n"
            "{{DETERMINISTIC_FINDINGS_JSON}}\n{{CLAIM_JSON}}",
            policy_context="policy",
            warning_taxonomy={"codes": []},
            deterministic_findings=[],
            claim={"claim_id": "DEV-001"},
        )
        self.assertEqual(messages[0], {"role": "system", "content": "system"})
        self.assertIn('"claim_id": "DEV-001"', messages[1]["content"])
        self.assertNotIn("{{", messages[1]["content"])

    @patch("expensesight.openrouter.requests.post")
    def test_review_uses_schema_and_validates_claim_id(self, post):
        model_output = {
            "claim_id": "DEV-001",
            "review_notes": [],
            "warnings": [],
            "abstentions": [],
        }
        response = Mock()
        response.status_code = 200
        response.json.return_value = {
            "id": "response-1",
            "model": "google/gemini-3.5-flash-lite",
            "choices": [{"message": {"content": json.dumps(model_output)}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }
        post.return_value = response

        client = OpenRouterClient("test-key", max_retries=0)
        result = client.review(
            claim_id="DEV-001",
            messages=[{"role": "user", "content": "review"}],
            output_schema={"type": "object", "properties": {}},
        )

        self.assertEqual(result.output.claim_id, "DEV-001")
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["response_format"]["type"], "json_schema")
        self.assertNotIn("action", payload["response_format"]["json_schema"]["schema"])


if __name__ == "__main__":
    unittest.main()
