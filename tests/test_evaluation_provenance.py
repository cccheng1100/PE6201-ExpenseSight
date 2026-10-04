from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import run_evaluation as evaluation_script


class EvaluationProvenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = (
            ROOT
            / "evals"
            / "results"
            / "model_outputs_holdout-v1_semantic-review-v2.json"
        )
        cls.metadata_source = cls.source.with_name(
            f"{cls.source.stem}.metadata.json"
        )
        cls.metadata = json.loads(cls.metadata_source.read_text(encoding="utf-8"))
        cls.required_ids = [call["claim_id"] for call in cls.metadata["calls"]]
        cls.input_hashes = {
            call["claim_id"]: call["input_sha256"] for call in cls.metadata["calls"]
        }

    def _fake_output_path(self, metadata: dict | None = None):
        contents = {self.source.name: self.source.read_text(encoding="utf-8")}
        if metadata is not None:
            contents[f"{self.source.stem}.metadata.json"] = json.dumps(metadata)

        class FakePath:
            stem = self.source.stem

            def __init__(self, name: str) -> None:
                self.name = name

            def exists(self) -> bool:
                return self.name in contents

            def read_text(self, encoding: str = "utf-8") -> str:
                return contents[self.name]

            def with_name(self, name: str):
                return FakePath(name)

            def __str__(self) -> str:
                return self.name

        return FakePath(self.source.name)

    def test_accepts_matching_output_and_metadata(self) -> None:
        output = self._fake_output_path(self.metadata)
        parsed = evaluation_script._load_model_outputs(
            output, self.required_ids, "holdout", self.input_hashes
        )
        self.assertEqual(set(parsed), set(self.required_ids))

    def test_rejects_tampered_input_provenance(self) -> None:
        metadata = json.loads(json.dumps(self.metadata))
        metadata["calls"][0]["input_sha256"] = "tampered"
        output = self._fake_output_path(metadata)
        with self.assertRaisesRegex(ValueError, "Input provenance mismatch"):
            evaluation_script._load_model_outputs(
                output, self.required_ids, "holdout", self.input_hashes
            )

    def test_rejects_missing_metadata(self) -> None:
        output = self._fake_output_path()
        with self.assertRaises(FileNotFoundError):
            evaluation_script._load_model_outputs(
                output, self.required_ids, "holdout", self.input_hashes
            )


if __name__ == "__main__":
    unittest.main()
