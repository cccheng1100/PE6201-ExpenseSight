"""Show three representative frozen Holdout decisions without making API calls.

The command re-runs the real deterministic pipeline and injects only the saved,
validated semantic output from the final Holdout run. It never reads ground
truth and never contacts a model provider.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from expensesight.io import claim_from_dict  # noqa: E402
from expensesight.model_output import parse_model_review_output  # noqa: E402
from expensesight.pipeline import run_pipeline  # noqa: E402


CLAIMS_PATH = ROOT / "data" / "holdout" / "holdout_claims.json"
MODEL_OUTPUTS_PATH = (
    ROOT / "evals" / "results" / "model_outputs_holdout-v1_semantic-review-v2.json"
)
DEFAULT_CASES = ["CAND-005", "CAND-040", "CAND-004"]


def _money(value: float) -> str:
    return f"RMB {value:,.2f}"


def _show_claim(claim_raw: dict, decision, *, model_used: bool) -> None:
    print(f"\n{'=' * 68}\n{claim_raw['claim_id']} | {decision.action.value}")
    print(f"Employee grade: {claim_raw['grade']}")
    routes = [
        f"{leg['depart_city']} -> {leg['arrive_city']} ({leg['depart_date']})"
        for leg in claim_raw["transport_legs"]
    ]
    print("Route: " + ("; ".join(routes) if routes else "None"))
    print(f"Hotel stays: {len(claim_raw['hotel_stays'])}")
    print(f"Employee note: {claim_raw.get('employee_note') or 'None'}")
    print(f"Semantic model output used: {'yes' if model_used else 'no'}")
    print(f"Reimbursable total: {_money(decision.total_reimbursable_rmb)}")

    if decision.return_reasons:
        print("Return Reasons:")
        for item in decision.return_reasons:
            print(f"  - {item.rule_code}: {item.description}")
    else:
        print("Return Reasons: none")

    if decision.review_warnings:
        print("Warnings:")
        for item in decision.review_warnings:
            print(f"  - {item.warning_code} [{item.entity_ref}]: {item.explanation}")
    else:
        print("Warnings: none")

    if decision.abstentions:
        print("Abstentions:")
        for item in decision.abstentions:
            print(f"  - {item.task_code} [{item.entity_ref}]: {item.reason}")
    else:
        print("Abstentions: none")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Display saved final decisions for representative Holdout cases."
    )
    parser.add_argument(
        "--claim-id",
        action="append",
        help="Case to display; repeat for several. Defaults to the three demo cases.",
    )
    args = parser.parse_args()

    claims_raw = json.loads(CLAIMS_PATH.read_text(encoding="utf-8"))
    saved_outputs = {
        item["claim_id"]: item
        for item in json.loads(MODEL_OUTPUTS_PATH.read_text(encoding="utf-8"))
    }
    selected = args.claim_id or DEFAULT_CASES
    known_ids = {item["claim_id"] for item in claims_raw}
    unknown = [claim_id for claim_id in selected if claim_id not in known_ids]
    if unknown:
        raise ValueError(f"Unknown Holdout claim IDs: {unknown}")

    decisions = {}
    previous = []
    for raw in claims_raw:
        claim = claim_from_dict(raw)
        saved = saved_outputs.get(claim.claim_id)
        model_review = (
            parse_model_review_output(saved, expected_claim_id=claim.claim_id)
            if saved is not None
            else None
        )
        decisions[claim.claim_id] = run_pipeline(
            claim,
            previous_claims=previous,
            review_notes=model_review.review_notes if model_review else None,
            model_warnings=model_review.warnings if model_review else None,
            model_abstentions=model_review.abstentions if model_review else None,
        )
        previous.append(claim)

    print("ExpenseSight final Holdout demonstration (offline, saved outputs)")
    print("PROCEED_TO_HUMAN means human review, not automatic approval.")
    for claim_id in selected:
        raw = next(item for item in claims_raw if item["claim_id"] == claim_id)
        _show_claim(raw, decisions[claim_id], model_used=claim_id in saved_outputs)


if __name__ == "__main__":
    main()
