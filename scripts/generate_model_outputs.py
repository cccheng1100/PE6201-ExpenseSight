"""Generate validated advisory outputs for an ExpenseSight dataset.

The command is dry-run by default. A live model call is possible only when
``--execute-live`` is supplied explicitly.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from expensesight.contracts import DecisionType  # noqa: E402
from expensesight.io import claim_from_dict  # noqa: E402
from expensesight.model_output import (  # noqa: E402
    ModelOutputValidationError,
    parse_model_review_output,
    validate_warning_taxonomy_contract,
)
from expensesight.openrouter import (  # noqa: E402
    DEFAULT_MODEL,
    OpenRouterClient,
    build_messages,
    load_review_assets,
)
from expensesight.pipeline import run_pipeline  # noqa: E402
from expensesight.rules import run_rules  # noqa: E402


DATASETS = {
    "dev": ROOT / "data" / "dev" / "dev_claims.json",
    "candidate": ROOT / "data" / "candidate_holdout_claims.json",
    "holdout": ROOT / "data" / "holdout" / "holdout_claims.json",
}

DATASET_DESCRIPTORS = {
    "holdout": ROOT / "evals" / "dataset_versions" / "holdout-v1.json",
}

MODEL_OUTPUT_PIPELINE_VERSION = "model-output-pipeline-v2"


def _json_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _configuration_descriptor(model: str, assets: dict[str, Any]) -> dict[str, Any]:
    """Describe every stable input that changes model-review behaviour."""
    return {
        "pipeline_contract": MODEL_OUTPUT_PIPELINE_VERSION,
        "model": model,
        "system_prompt_sha256": _json_sha256(assets["system_prompt"]),
        "request_template_sha256": _json_sha256(assets["request_template"]),
        "policy_context_sha256": _json_sha256(assets["policy_context"]),
        "warning_taxonomy_sha256": _json_sha256(assets["warning_taxonomy"]),
        "output_schema_sha256": _json_sha256(assets["output_schema"]),
    }


def _claim_input_sha256(claim_raw: dict[str, Any], findings: list[dict[str, Any]]) -> str:
    return _json_sha256({"claim": claim_raw, "deterministic_findings": findings})


def _eligible_reviews(dataset: str) -> list[tuple[dict[str, Any], list[dict[str, Any]]]]:
    claims_raw = json.loads(DATASETS[dataset].read_text(encoding="utf-8"))
    claims = [claim_from_dict(raw) for raw in claims_raw]
    eligible = []
    previous = []
    for raw, claim in zip(claims_raw, claims):
        decision = run_pipeline(claim, previous_claims=previous)
        if decision.action != DecisionType.RETURN_TO_EMPLOYEE:
            findings = [asdict(item) for item in run_rules(claim, previous)]
            eligible.append((raw, findings))
        previous.append(claim)
    return eligible


def _verify_dataset_descriptor(dataset: str) -> None:
    """Refuse to use a versioned dataset when any frozen component changed."""
    descriptor_path = DATASET_DESCRIPTORS.get(dataset)
    if descriptor_path is None:
        return
    descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
    if descriptor.get("dataset_name") != dataset or descriptor.get("status") != "frozen_holdout":
        raise ValueError(f"Dataset descriptor is not a frozen {dataset}: {descriptor_path}")
    for component in descriptor.get("components", {}).values():
        path = ROOT / component["path"]
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != component["sha256"]:
            raise ValueError(f"Frozen dataset component hash mismatch: {component['path']}")


def _load_validated_outputs(
    output_path: Path,
    dataset: str,
    warning_taxonomy: dict[str, Any],
    configuration_sha256: str,
    eligible_input_hashes: dict[str, str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], set[str]]:
    """Load and re-validate existing outputs for resume.

    Returns (outputs, calls, completed_ids). Only outputs that pass both
    the schema parse and the taxonomy contract are reused. Invalid entries
    are dropped so they will be re-called.
    """
    metadata_path = output_path.with_name(f"{output_path.stem}.metadata.json")
    if not output_path.exists() or not metadata_path.exists():
        return [], [], set()

    try:
        existing = json.loads(output_path.read_text(encoding="utf-8"))
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return [], [], set()

    if not isinstance(existing, list) or not isinstance(metadata, dict):
        return [], [], set()
    if metadata.get("dataset") != dataset:
        return [], [], set()
    if metadata.get("configuration_sha256") != configuration_sha256:
        return [], [], set()

    raw_calls = metadata.get("calls", [])
    if not isinstance(raw_calls, list):
        return [], [], set()
    reusable_calls: dict[str, dict[str, Any]] = {}
    for call in raw_calls:
        if not isinstance(call, dict):
            continue
        claim_id = call.get("claim_id")
        if claim_id not in eligible_input_hashes:
            continue
        if call.get("status") != "validated":
            continue
        if call.get("configuration_sha256") != configuration_sha256:
            continue
        if call.get("input_sha256") != eligible_input_hashes[claim_id]:
            continue
        reusable_calls[claim_id] = call

    outputs: list[dict[str, Any]] = []
    calls: list[dict[str, Any]] = []
    completed: set[str] = set()
    for raw in existing:
        if not isinstance(raw, dict) or "claim_id" not in raw:
            continue
        claim_id = raw["claim_id"]
        if claim_id in completed or claim_id not in reusable_calls:
            continue
        try:
            parsed = parse_model_review_output(raw, expected_claim_id=claim_id)
            validate_warning_taxonomy_contract(parsed, warning_taxonomy)
        except ModelOutputValidationError:
            continue
        outputs.append(raw)
        calls.append(reusable_calls[claim_id])
        completed.add(claim_id)

    return outputs, calls, completed


def main() -> None:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", choices=tuple(DATASETS), default="dev")
    parser.add_argument("--model", default=os.getenv("EXPENSESIGHT_MODEL", DEFAULT_MODEL))
    parser.add_argument("--claim-id", action="append", default=[])
    parser.add_argument("--execute-live", action="store_true")
    parser.add_argument("--allow-candidate", action="store_true")
    parser.add_argument("--allow-holdout", action="store_true")
    parser.add_argument("--resume", action="store_true",
                        help="Reuse already-validated outputs in the output file; only call missing claims.")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    _verify_dataset_descriptor(args.dataset)
    eligible = _eligible_reviews(args.dataset)
    if args.claim_id:
        requested = set(args.claim_id)
        eligible = [item for item in eligible if item[0]["claim_id"] in requested]
        found = {item[0]["claim_id"] for item in eligible}
        missing = sorted(requested - found)
        if missing:
            raise ValueError(f"Requested claim IDs are not model-review eligible: {missing}")

    claim_ids = [item[0]["claim_id"] for item in eligible]
    print(f"Model: {args.model}")
    print(f"Dataset: {args.dataset}")

    # Load assets and resolve output before dry-run so --resume can report status.
    assets = load_review_assets(ROOT)
    configuration = _configuration_descriptor(args.model, assets)
    configuration_sha256 = _json_sha256(configuration)

    if args.output is None:
        safe_model = args.model.replace("/", "-").replace(":", "-")
        args.output = ROOT / "evals" / "results" / f"model_outputs_{args.dataset}_{safe_model}.json"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    metadata_path = args.output.with_name(f"{args.output.stem}.metadata.json")

    outputs: list[dict[str, Any]] = []
    calls: list[dict[str, Any]] = []
    eligible_input_hashes = {
        claim_raw["claim_id"]: _claim_input_sha256(claim_raw, findings)
        for claim_raw, findings in eligible
    }

    if args.resume:
        outputs, calls, completed_ids = _load_validated_outputs(
            args.output,
            args.dataset,
            assets["warning_taxonomy"],
            configuration_sha256,
            eligible_input_hashes,
        )
        if completed_ids:
            eligible = [item for item in eligible if item[0]["claim_id"] not in completed_ids]
            print(f"Resumed: {len(completed_ids)} already-validated outputs reused, {len(eligible)} remaining to call.")
            print(f"Reused IDs: {', '.join(sorted(completed_ids))}")
        else:
            print("Resumed: no valid existing outputs found; will call all eligible claims.")

    claim_ids = [item[0]["claim_id"] for item in eligible]
    print(f"Eligible model calls: {len(claim_ids)}")
    print(f"Claim IDs: {', '.join(claim_ids)}")
    if not args.execute_live:
        print("Dry run only. Add --execute-live to make paid API calls.")
        return

    if args.dataset == "candidate" and not args.allow_candidate:
        raise ValueError(
            "Candidate data is not a frozen holdout. Add --allow-candidate only after review."
        )
    if args.dataset == "holdout" and not args.allow_holdout:
        raise ValueError(
            "Holdout model calls require explicit --allow-holdout confirmation."
        )

    api_key = os.getenv("OPENROUTER_API_KEY", "")
    client = OpenRouterClient(api_key, model=args.model)

    def write_metadata() -> None:
        metadata = {
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "dataset": args.dataset,
            "requested_model": args.model,
            "configuration": configuration,
            "configuration_sha256": configuration_sha256,
            "validated_output_count": len(outputs),
            "call_count": len(calls),
            "calls": calls,
        }
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    for index, (claim_raw, findings) in enumerate(eligible, start=1):
        claim_id = claim_raw["claim_id"]
        print(f"[{index}/{len(eligible)}] Reviewing {claim_id}")
        messages = build_messages(
            system_prompt=assets["system_prompt"],
            request_template=assets["request_template"],
            policy_context=assets["policy_context"],
            warning_taxonomy=assets["warning_taxonomy"],
            deterministic_findings=findings,
            claim=claim_raw,
        )
        review = client.review(
            claim_id=claim_id,
            messages=messages,
            output_schema=assets["output_schema"],
            warning_taxonomy=assets["warning_taxonomy"],
        )
        call_record = {
            "claim_id": claim_id,
            "model": review.model,
            "response_id": review.response_id,
            "usage": asdict(review.usage),
            "configuration_sha256": configuration_sha256,
            "input_sha256": eligible_input_hashes[claim_id],
        }
        calls.append(call_record)
        try:
            validate_warning_taxonomy_contract(review.output, assets["warning_taxonomy"])
        except ModelOutputValidationError as exc:
            call_record["status"] = "rejected"
            call_record["validation_error"] = str(exc)
            rejected_path = args.output.with_name(
                f"{args.output.stem}.{claim_id}.rejected.json"
            )
            rejected_path.write_text(
                json.dumps({
                    "claim_id": claim_id,
                    "validation_error": str(exc),
                    "raw_output": review.raw_output,
                }, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            write_metadata()
            raise
        call_record["status"] = "validated"
        outputs.append(review.raw_output)
        args.output.write_text(json.dumps(outputs, indent=2, ensure_ascii=False), encoding="utf-8")
        write_metadata()

    print(f"Saved validated model outputs to {args.output}")
    print(f"Saved call metadata to {metadata_path}")


if __name__ == "__main__":
    main()
