"""Build deterministic version descriptors for development and candidate data."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATASETS = {
    "candidate": {
        "version": "candidate-v1",
        "status": "candidate_not_frozen",
        "output": ROOT / "evals" / "dataset_versions" / "candidate-v1.json",
        "components": {
            "claims": ROOT / "data" / "candidate_holdout_claims.json",
            "ground_truth": ROOT / "evals" / "candidate_holdout_ground_truth.json",
            "case_manifest": ROOT / "data" / "candidate_case_manifest.json",
            "policy": ROOT / "data" / "policies" / "travel_policy.md",
        },
    },
    "dev": {
        "version": "dev-v1",
        "status": "development_editable",
        "output": ROOT / "evals" / "dataset_versions" / "dev-v1.json",
        "components": {
            "claims": ROOT / "data" / "dev" / "dev_claims.json",
            "ground_truth": ROOT / "evals" / "dev_ground_truth.json",
            "case_manifest": ROOT / "data" / "dev" / "dev_case_manifest.json",
            "policy": ROOT / "data" / "policies" / "travel_policy.md",
        },
    },
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_descriptor(name: str, config: dict) -> Path:
    components = config["components"]
    claims = json.loads(components["claims"].read_text(encoding="utf-8"))
    ground_truth = json.loads(components["ground_truth"].read_text(encoding="utf-8"))
    descriptor = {
        "dataset_name": name,
        "dataset_version": config["version"],
        "status": config["status"],
        "claim_count": len(claims),
        "label_distribution": {
            "clean_pass": sum(item["expected_action"] == "PROCEED_TO_HUMAN" and not item["expected_warnings"] for item in ground_truth),
            "warning_review": sum(item["expected_action"] == "PROCEED_TO_HUMAN" and bool(item["expected_warnings"]) for item in ground_truth),
            "return_required": sum(item["expected_action"] == "RETURN_TO_EMPLOYEE" for item in ground_truth),
        },
        "components": {
            component_name: {"path": path.relative_to(ROOT).as_posix(), "sha256": sha256(path)}
            for component_name, path in components.items()
        },
        "freeze_rule": "Any component change requires a new dataset version before comparison.",
    }
    output = config["output"]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(descriptor, indent=2), encoding="utf-8")
    return output


def main() -> None:
    for name, config in DATASETS.items():
        output = build_descriptor(name, config)
        print(f"Wrote {name} dataset descriptor to {output}")


if __name__ == "__main__":
    main()
