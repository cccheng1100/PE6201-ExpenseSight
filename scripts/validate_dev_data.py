"""Validate development data separation, coverage, and rule baselines."""
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
    claims_raw = json.loads((ROOT / "data" / "dev" / "dev_claims.json").read_text(encoding="utf-8"))
    gt_raw = json.loads((ROOT / "evals" / "dev_ground_truth.json").read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / "data" / "dev" / "dev_case_manifest.json").read_text(encoding="utf-8"))
    holdout_ids = {
        item["claim_id"]
        for item in json.loads((ROOT / "data" / "candidate_holdout_claims.json").read_text(encoding="utf-8"))
    }

    assert len(claims_raw) == len(gt_raw) == len(manifest) == 22
    claim_ids = [item["claim_id"] for item in claims_raw]
    assert claim_ids == [item["claim_id"] for item in gt_raw]
    assert len(set(claim_ids)) == 22
    assert not set(claim_ids) & holdout_ids
    assert all(item.startswith("DEV-") for item in claim_ids)
    assert all("expected_action" not in item for item in claims_raw)
    assert all("expected_warnings" not in item for item in claims_raw)
    assert all("attachments" in item for item in claims_raw)

    clean = sum(item["expected_action"] == "PROCEED_TO_HUMAN" and not item["expected_warnings"] for item in gt_raw)
    warning = sum(item["expected_action"] == "PROCEED_TO_HUMAN" and bool(item["expected_warnings"]) for item in gt_raw)
    returned = sum(item["expected_action"] == "RETURN_TO_EMPLOYEE" for item in gt_raw)
    assert (clean, warning, returned) == (6, 10, 6)
    assert sum("complex_multi_leg" in item["case_tags"] for item in manifest) == 5
    assert sum(len(item.get("expected_abstentions", [])) for item in gt_raw) == 3

    previous = []
    mismatches: list[str] = []
    for raw, expected in zip(claims_raw, gt_raw):
        claim = claim_from_dict(raw)
        decision = run_pipeline(claim, previous_claims=previous)
        if decision.action.value != expected["expected_action"]:
            mismatches.append(
                f"{claim.claim_id}: expected {expected['expected_action']}, rules produced {decision.action.value}"
            )
        if expected["expected_action"] == "RETURN_TO_EMPLOYEE":
            actual = {item.rule_code for item in decision.return_reasons}
            missing = set(expected["expected_return_reasons"]) - actual
            if missing:
                mismatches.append(f"{claim.claim_id}: missing return codes {sorted(missing)}")
        previous.append(claim)
    if mismatches:
        raise AssertionError("Development baseline mismatches:\n" + "\n".join(mismatches))
    print("Development validation passed: 22 separate Dev claims; distribution 6/10/6; 5 complex cases; 3 abstentions.")


if __name__ == "__main__":
    main()
