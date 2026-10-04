from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "generate_model_outputs",
    ROOT / "scripts" / "generate_model_outputs.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ResumeValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.output = [{
            "claim_id": "DEV-001",
            "review_notes": [],
            "warnings": [],
            "abstentions": [],
        }]
        self.taxonomy = {"codes": []}
        self.configuration_sha256 = "config-1"
        self.input_hashes = {"DEV-001": "input-1"}

    def _fake_output_path(
        self,
        call: dict,
        *,
        top_config: str = "config-1",
        dataset: str = "dev",
    ):
        contents = {
            "outputs.json": json.dumps(self.output),
            "outputs.metadata.json": json.dumps({
            "dataset": dataset,
            "configuration_sha256": top_config,
            "calls": [call],
            }),
        }

        class FakePath:
            stem = "outputs"

            def __init__(self, name: str) -> None:
                self.name = name

            def exists(self) -> bool:
                return self.name in contents

            def read_text(self, encoding: str = "utf-8") -> str:
                return contents[self.name]

            def with_name(self, name: str):
                return FakePath(name)

        return FakePath("outputs.json")

    def test_resume_reuses_only_matching_configuration_and_input(self) -> None:
        output_path = self._fake_output_path({
            "claim_id": "DEV-001",
            "status": "validated",
            "configuration_sha256": "config-1",
            "input_sha256": "input-1",
        })
        outputs, calls, completed = MODULE._load_validated_outputs(
            output_path,
            "dev",
            self.taxonomy,
            self.configuration_sha256,
            self.input_hashes,
        )
        self.assertEqual(outputs, self.output)
        self.assertEqual(len(calls), 1)
        self.assertEqual(completed, {"DEV-001"})

    def test_resume_rejects_legacy_or_changed_configuration(self) -> None:
        output_path = self._fake_output_path({
            "claim_id": "DEV-001",
            "status": "validated",
            "configuration_sha256": "config-1",
            "input_sha256": "input-1",
        }, top_config="legacy-config")
        outputs, calls, completed = MODULE._load_validated_outputs(
            output_path,
            "dev",
            self.taxonomy,
            self.configuration_sha256,
            self.input_hashes,
        )
        self.assertEqual((outputs, calls, completed), ([], [], set()))

    def test_resume_rejects_changed_claim_input(self) -> None:
        output_path = self._fake_output_path({
            "claim_id": "DEV-001",
            "status": "validated",
            "configuration_sha256": "config-1",
            "input_sha256": "old-input",
        })
        outputs, calls, completed = MODULE._load_validated_outputs(
            output_path,
            "dev",
            self.taxonomy,
            self.configuration_sha256,
            self.input_hashes,
        )
        self.assertEqual((outputs, calls, completed), ([], [], set()))

    def test_resume_rejects_output_from_another_dataset(self) -> None:
        output_path = self._fake_output_path({
            "claim_id": "DEV-001",
            "status": "validated",
            "configuration_sha256": "config-1",
            "input_sha256": "input-1",
        }, dataset="candidate")
        outputs, calls, completed = MODULE._load_validated_outputs(
            output_path,
            "dev",
            self.taxonomy,
            self.configuration_sha256,
            self.input_hashes,
        )
        self.assertEqual((outputs, calls, completed), ([], [], set()))


if __name__ == "__main__":
    unittest.main()
