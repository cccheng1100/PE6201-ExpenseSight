"""Compatibility entry point for the candidate rules-only diagnostic run."""
from __future__ import annotations

from run_evaluation import run_evaluation


if __name__ == "__main__":
    result, output = run_evaluation(configuration="rules_only")
    import json

    print(json.dumps(result["metrics"], indent=2))
    print(f"Saved diagnostic result to {output}")
