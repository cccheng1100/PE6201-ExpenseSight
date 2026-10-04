"""Validate separation, schema loading, counts, and baseline label consistency."""
from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from expensesight.io import claim_from_dict
from expensesight.pipeline import run_pipeline


def main() -> None:
    claims_raw = json.loads((ROOT / "data" / "candidate_holdout_claims.json").read_text(encoding="utf-8"))
    gt_raw = json.loads((ROOT / "evals" / "candidate_holdout_ground_truth.json").read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / "data" / "candidate_case_manifest.json").read_text(encoding="utf-8"))

    assert len(claims_raw) == 50
    assert len(gt_raw) == 50
    assert len(manifest) == 50
    claim_ids = [item["claim_id"] for item in claims_raw]
    gt_ids = [item["claim_id"] for item in gt_raw]
    assert len(set(claim_ids)) == 50
    assert claim_ids == gt_ids
    assert all("expected_action" not in claim for claim in claims_raw)
    assert all("expected_warnings" not in claim for claim in claims_raw)
    assert all("expected_review_notes" not in claim for claim in claims_raw)
    assert all("attachments" in claim for claim in claims_raw)
    assert all("case_tags" in item for item in manifest)

    clean_count = sum(
        item["expected_action"] == "PROCEED_TO_HUMAN"
        and not item["expected_warnings"]
        for item in gt_raw
    )
    warning_count = sum(
        item["expected_action"] == "PROCEED_TO_HUMAN"
        and bool(item["expected_warnings"])
        for item in gt_raw
    )
    return_count = sum(item["expected_action"] == "RETURN_TO_EMPLOYEE" for item in gt_raw)
    assert (clean_count, warning_count, return_count) == (15, 19, 16)
    assert sum("complex_multi_leg" in item["case_tags"] for item in manifest) == 15
    assert sum("security_test" in item["case_tags"] for item in manifest) == 1

    claims = [claim_from_dict(item) for item in claims_raw]
    previous = []
    mismatches: list[str] = []
    for claim, expected in zip(claims, gt_raw):
        decision = run_pipeline(claim, previous_claims=previous)
        if decision.action.value != expected["expected_action"]:
            mismatches.append(f"{claim.claim_id}: expected {expected['expected_action']}, rules produced {decision.action.value}")
        if expected["expected_action"] == "RETURN_TO_EMPLOYEE":
            actual_codes = {item.rule_code for item in decision.return_reasons}
            missing = set(expected["expected_return_reasons"]) - actual_codes
            if missing:
                mismatches.append(f"{claim.claim_id}: missing return codes {sorted(missing)}; actual {sorted(actual_codes)}")
        previous.append(claim)

    if mismatches:
        raise AssertionError("Candidate baseline mismatches:\n" + "\n".join(mismatches))
    print("Candidate validation passed: 50 separated claims and annotations; baseline actions are consistent.")


if __name__ == "__main__":
    main()
