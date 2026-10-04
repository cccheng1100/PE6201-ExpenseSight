"""Run the same offline harness for rules-only or hybrid predictions.

No model API is called here. For a hybrid run, the caller supplies one strict
advisory output per claim. The deterministic pipeline remains responsible for
the final business action.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from expensesight.contracts import DecisionType
from expensesight.evaluation import METRIC_DEFINITIONS, decision_to_record, evaluate_records
from expensesight.io import claim_from_dict
from expensesight.model_output import (
    parse_model_review_output,
    validate_warning_taxonomy_contract,
)
from expensesight.openrouter import load_review_assets
from expensesight.pipeline import run_pipeline
from expensesight.rules import run_rules


MODEL_OUTPUT_PIPELINE_VERSION = "model-output-pipeline-v2"


DATASETS = {
    "candidate": {
        "claims": ROOT / "data" / "candidate_holdout_claims.json",
        "ground_truth": ROOT / "evals" / "candidate_holdout_ground_truth.json",
        "manifest": ROOT / "data" / "candidate_case_manifest.json",
        "version": ROOT / "evals" / "dataset_versions" / "candidate-v1.json",
    },
    "dev": {
        "claims": ROOT / "data" / "dev" / "dev_claims.json",
        "ground_truth": ROOT / "evals" / "dev_ground_truth.json",
        "manifest": ROOT / "data" / "dev" / "dev_case_manifest.json",
        "version": ROOT / "evals" / "dataset_versions" / "dev-v1.json",
    },
    "holdout": {
        "claims": ROOT / "data" / "holdout" / "holdout_claims.json",
        "ground_truth": ROOT / "evals" / "holdout_ground_truth.json",
        "manifest": ROOT / "data" / "holdout" / "holdout_case_manifest.json",
        "version": ROOT / "evals" / "dataset_versions" / "holdout-v1.json",
    },
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_and_verify_version(version_path: Path) -> dict[str, Any]:
    if not version_path.exists():
        raise FileNotFoundError(
            "Dataset version descriptor is missing; run scripts/build_dataset_version.py first"
        )
    descriptor = json.loads(version_path.read_text(encoding="utf-8"))
    for component in descriptor["components"].values():
        path = ROOT / component["path"]
        actual = _sha256(path)
        if actual != component["sha256"]:
            raise ValueError(
                f"Dataset component changed after versioning: {component['path']}. "
                "Review the change and create a new candidate version."
            )
    return descriptor


def _json_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _configuration_descriptor(model: str, assets: dict[str, Any]) -> dict[str, Any]:
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


def _load_model_outputs(
    path: Path,
    required_claim_ids: list[str],
    dataset: str,
    eligible_input_hashes: dict[str, str],
) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("Hybrid prediction file must contain a JSON list")

    metadata_path = path.with_name(f"{path.stem}.metadata.json")
    if not metadata_path.exists():
        raise FileNotFoundError(
            f"Hybrid evaluation requires matching provenance metadata: {metadata_path}"
        )
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata.get("dataset") != dataset:
        raise ValueError("Model-output metadata belongs to a different dataset")

    assets = load_review_assets(ROOT)
    model = metadata.get("requested_model")
    if not isinstance(model, str) or not model:
        raise ValueError("Model-output metadata is missing requested_model")
    expected_configuration = _configuration_descriptor(model, assets)
    expected_configuration_sha256 = _json_sha256(expected_configuration)
    if metadata.get("configuration") != expected_configuration:
        raise ValueError("Model-output metadata does not match the current review assets")
    if metadata.get("configuration_sha256") != expected_configuration_sha256:
        raise ValueError("Model-output configuration hash mismatch")

    calls = metadata.get("calls")
    if not isinstance(calls, list):
        raise ValueError("Model-output metadata calls must be a list")
    calls_by_id = {}
    for call in calls:
        if not isinstance(call, dict) or not isinstance(call.get("claim_id"), str):
            raise ValueError("Model-output metadata contains an invalid call record")
        claim_id = call["claim_id"]
        if claim_id in calls_by_id:
            raise ValueError(f"Duplicate metadata call for {claim_id}")
        calls_by_id[claim_id] = call

    parsed = {}
    for item in raw:
        output = parse_model_review_output(item)
        validate_warning_taxonomy_contract(output, assets["warning_taxonomy"])
        if output.claim_id in parsed:
            raise ValueError(f"Duplicate model output for {output.claim_id}")
        parsed[output.claim_id] = output
    if set(parsed) != set(required_claim_ids):
        missing = sorted(set(required_claim_ids) - set(parsed))
        extra = sorted(set(parsed) - set(required_claim_ids))
        raise ValueError(
            "Hybrid outputs must cover exactly the non-return claims; "
            f"missing={missing}, extra={extra}"
        )
    if set(calls_by_id) != set(required_claim_ids):
        raise ValueError("Model-output metadata must cover exactly the required claim IDs")
    if metadata.get("validated_output_count") != len(raw) or metadata.get("call_count") != len(calls):
        raise ValueError("Model-output metadata counts do not match the saved outputs")
    for claim_id, call in calls_by_id.items():
        if call.get("status") != "validated":
            raise ValueError(f"Model output for {claim_id} is not marked validated")
        if call.get("configuration_sha256") != expected_configuration_sha256:
            raise ValueError(f"Configuration provenance mismatch for {claim_id}")
        if call.get("input_sha256") != eligible_input_hashes[claim_id]:
            raise ValueError(f"Input provenance mismatch for {claim_id}")
    return parsed


def run_evaluation(
    configuration: str,
    model_outputs_path: Path | None = None,
    output_path: Path | None = None,
    dataset: str = "candidate",
) -> tuple[dict[str, Any], Path]:
    if dataset not in DATASETS:
        raise ValueError(f"Unsupported dataset: {dataset}")
    paths = DATASETS[dataset]
    descriptor = _load_and_verify_version(paths["version"])
    claims_raw = json.loads(paths["claims"].read_text(encoding="utf-8"))
    ground_truth = json.loads(paths["ground_truth"].read_text(encoding="utf-8"))
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    model_outputs = None
    if configuration == "hybrid":
        if model_outputs_path is None:
            raise ValueError("Hybrid evaluation requires --model-outputs")
    elif configuration != "rules_only":
        raise ValueError(f"Unsupported configuration: {configuration}")

    claims = [claim_from_dict(item) for item in claims_raw]
    # Rules always run first. Their return decision determines whether an LLM
    # output is required at all, without consulting ground truth.
    previous = []
    rules_decisions = []
    for claim in claims:
        rules_decisions.append(run_pipeline(claim, previous_claims=previous))
        previous.append(claim)

    if configuration == "hybrid":
        required_ids = [
            decision.claim_id
            for decision in rules_decisions
            if decision.action != DecisionType.RETURN_TO_EMPLOYEE
        ]
        previous = []
        eligible_input_hashes = {}
        for claim_raw, claim, decision in zip(claims_raw, claims, rules_decisions):
            if decision.action != DecisionType.RETURN_TO_EMPLOYEE:
                findings = [asdict(item) for item in run_rules(claim, previous)]
                eligible_input_hashes[claim.claim_id] = _claim_input_sha256(
                    claim_raw, findings
                )
            previous.append(claim)
        model_outputs = _load_model_outputs(
            model_outputs_path,
            required_ids,
            dataset,
            eligible_input_hashes,
        )

    predictions = []
    previous = []
    for claim, rules_decision in zip(claims, rules_decisions):
        if configuration == "rules_only" or rules_decision.action == DecisionType.RETURN_TO_EMPLOYEE:
            decision = rules_decision
        else:
            model_output = model_outputs[claim.claim_id]
            decision = run_pipeline(
                claim,
                previous_claims=previous,
                review_notes=model_output.review_notes,
                model_warnings=model_output.warnings,
                model_abstentions=model_output.abstentions,
            )
        predictions.append(decision_to_record(decision))
        previous.append(claim)

    scored = evaluate_records(claims_raw, ground_truth, predictions)
    tags_by_id = {item["claim_id"]: set(item.get("case_tags", [])) for item in manifest}

    def subset_result(name: str, selected_ids: set[str]) -> dict[str, Any] | None:
        if not selected_ids:
            return None
        indices = [index for index, claim in enumerate(claims_raw) if claim["claim_id"] in selected_ids]
        subset = evaluate_records(
            [claims_raw[index] for index in indices],
            [ground_truth[index] for index in indices],
            [predictions[index] for index in indices],
        )
        return {"name": name, "claim_count": len(indices), "metrics": subset["metrics"], "counts": subset["counts"]}

    complex_ids = {claim_id for claim_id, tags in tags_by_id.items() if "complex_multi_leg" in tags}
    security_ids = {claim_id for claim_id, tags in tags_by_id.items() if "security_test" in tags}
    primary_ids = set(tags_by_id) - security_ids
    subset_metrics = {
        "primary_financial": subset_result("primary_financial", primary_ids),
        "complex_multi_leg": subset_result("complex_multi_leg", complex_ids),
        "security_test": subset_result("security_test", security_ids),
    }
    subset_metrics = {name: value for name, value in subset_metrics.items() if value is not None}

    if dataset == "holdout":
        limitations = [
            "The Holdout is synthetic and business-reviewed; it does not establish production-distribution performance.",
            "The rules-only baseline is not expected to recover semantic or route warnings.",
            "Warning issue matching uses code plus entity; fact completeness is reported separately.",
            "The security-test case is reported separately from primary financial metrics.",
        ]
    else:
        limitations = [
            "The candidate ground truth has not been frozen or independently reviewed.",
            "The rules-only baseline is not expected to recover semantic or route warnings.",
            "Warning issue matching uses code plus entity; fact completeness is reported separately.",
            "Appropriate abstention is unavailable until expected abstentions are annotated.",
            "Candidate metrics must not be reported as final project results.",
        ]
    result = {
        "dataset_version": descriptor["dataset_version"],
        "dataset_name": dataset,
        "dataset_status": descriptor["status"],
        "dataset_component_hashes": {
            name: item["sha256"] for name, item in descriptor["components"].items()
        },
        "configuration": configuration,
        "claim_count": len(claims),
        "metric_definitions": METRIC_DEFINITIONS,
        "model_review_eligible_claims": sum(
            decision.action != DecisionType.RETURN_TO_EMPLOYEE for decision in rules_decisions
        ),
        "model_review_short_circuited_claims": sum(
            decision.action == DecisionType.RETURN_TO_EMPLOYEE for decision in rules_decisions
        ),
        **scored,
        "subset_metrics": subset_metrics,
        "limitations": limitations,
    }
    if output_path is None:
        suffix = f"{'rules_baseline' if configuration == 'rules_only' else 'hybrid'}_{dataset}.json"
        output_path = ROOT / "evals" / "results" / suffix
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result, output_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--configuration", choices=("rules_only", "hybrid"), default="rules_only")
    parser.add_argument("--dataset", choices=tuple(DATASETS), default="candidate")
    parser.add_argument("--model-outputs", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result, output = run_evaluation(args.configuration, args.model_outputs, args.output, args.dataset)
    print(json.dumps(result["metrics"], indent=2))
    print(f"Saved diagnostic result to {output}")


if __name__ == "__main__":
    main()
