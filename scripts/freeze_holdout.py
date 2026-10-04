"""Freeze the business-reviewed candidate data as immutable Holdout v1.

The editable candidate files remain available for regeneration. This script
copies their reviewed content into separate Holdout paths, changes only review
status fields, and records exact component hashes. It never calls a model.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DESCRIPTOR = ROOT / "evals" / "dataset_versions" / "candidate-v1.json"
CLAIMS_SOURCE = ROOT / "data" / "candidate_holdout_claims.json"
GROUND_TRUTH_SOURCE = ROOT / "evals" / "candidate_holdout_ground_truth.json"
MANIFEST_SOURCE = ROOT / "data" / "candidate_case_manifest.json"
POLICY = ROOT / "data" / "policies" / "travel_policy.md"

CLAIMS_OUTPUT = ROOT / "data" / "holdout" / "holdout_claims.json"
GROUND_TRUTH_OUTPUT = ROOT / "evals" / "holdout_ground_truth.json"
MANIFEST_OUTPUT = ROOT / "data" / "holdout" / "holdout_case_manifest.json"
DESCRIPTOR_OUTPUT = ROOT / "evals" / "dataset_versions" / "holdout-v1.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_candidate_descriptor() -> dict:
    descriptor = json.loads(SOURCE_DESCRIPTOR.read_text(encoding="utf-8"))
    for component in descriptor["components"].values():
        path = ROOT / component["path"]
        if sha256(path) != component["sha256"]:
            raise ValueError(f"Candidate component changed after review: {component['path']}")
    return descriptor


def main() -> None:
    source_descriptor = verify_candidate_descriptor()
    claims = json.loads(CLAIMS_SOURCE.read_text(encoding="utf-8"))
    ground_truth = json.loads(GROUND_TRUTH_SOURCE.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST_SOURCE.read_text(encoding="utf-8"))

    claim_ids = [item["claim_id"] for item in claims]
    if len(claims) != 50 or claim_ids != [item["claim_id"] for item in ground_truth]:
        raise ValueError("Reviewed candidate claims and ground truth are not an ordered 50-case set")
    if claim_ids != [item["claim_id"] for item in manifest]:
        raise ValueError("Reviewed candidate manifest does not match claim order")

    for item in ground_truth:
        item["status"] = "frozen_holdout"
    for item in manifest:
        item["status"] = "frozen_holdout"

    CLAIMS_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    CLAIMS_OUTPUT.write_text(json.dumps(claims, ensure_ascii=False, indent=2), encoding="utf-8")
    GROUND_TRUTH_OUTPUT.write_text(json.dumps(ground_truth, ensure_ascii=False, indent=2), encoding="utf-8")
    MANIFEST_OUTPUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    components = {
        "claims": CLAIMS_OUTPUT,
        "ground_truth": GROUND_TRUTH_OUTPUT,
        "case_manifest": MANIFEST_OUTPUT,
        "policy": POLICY,
    }
    descriptor = {
        "dataset_name": "holdout",
        "dataset_version": "holdout-v1",
        "status": "frozen_holdout",
        "frozen_on": "2026-10-03",
        "business_review": "completed_by_project_author",
        "claim_count": 50,
        "label_distribution": {
            "clean_pass": sum(item["expected_action"] == "PROCEED_TO_HUMAN" and not item["expected_warnings"] for item in ground_truth),
            "warning_review": sum(item["expected_action"] == "PROCEED_TO_HUMAN" and bool(item["expected_warnings"]) for item in ground_truth),
            "return_required": sum(item["expected_action"] == "RETURN_TO_EMPLOYEE" for item in ground_truth),
        },
        "subsets": {
            "complex_multi_leg": sum("complex_multi_leg" in item["case_tags"] for item in manifest),
            "security_test": sum("security_test" in item["case_tags"] for item in manifest),
            "primary_financial": sum("security_test" not in item["case_tags"] for item in manifest),
        },
        "components": {
            name: {"path": path.relative_to(ROOT).as_posix(), "sha256": sha256(path)}
            for name, path in components.items()
        },
        "source_candidate": {
            "dataset_version": source_descriptor["dataset_version"],
            "descriptor_sha256": sha256(SOURCE_DESCRIPTOR),
        },
        "review_decisions": [
            "Attachment-only and plausibly exceptional findings remain advisory.",
            "Hotel form data excludes an employee-entered nightly-rate field.",
            "Same-day round trips do not produce a Review Note merely for absent hotel or allowance claims.",
            "Explicit automated-review manipulation is a separate security-test Warning; ordinary employee explanations are not.",
        ],
        "freeze_rule": "Any change to a frozen component requires a new Holdout version; Holdout v1 must never be edited in place.",
    }
    DESCRIPTOR_OUTPUT.write_text(json.dumps(descriptor, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Frozen {len(claims)} reviewed cases as {DESCRIPTOR_OUTPUT}")


if __name__ == "__main__":
    main()
