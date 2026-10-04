"""Reusable offline evaluation logic for rules-only and hybrid runs."""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .contracts import Decision, DecisionType


METRIC_DEFINITIONS = {
    "false_return_rate": "Share of claims that should proceed to human review but were incorrectly returned.",
    "return_precision": "Share of predicted returns that were expected returns.",
    "return_recall": "Share of expected return cases correctly returned.",
    "return_reason_recall": "Share of expected deterministic return reasons recovered.",
    "warning_recall": "Share of expected warning issues detected, matched by claim, code, and entity.",
    "warning_precision": "Share of predicted warning issues that match an expected issue.",
    "warning_fact_recall_diagnostic": "Share of expected warnings whose annotated material facts are all present and equal.",
    "unsupported_warning_rate": "Share of predicted warnings with no matching expected issue.",
    "clean_case_warning_rate": "Share of clean non-return cases that received at least one warning.",
    "review_note_recall_diagnostic": "Share of expected neutral review notes recovered.",
    "material_issue_recall": "Share of expected return reasons and warnings recovered together.",
    "evidence_reference_validity": "Share of cited evidence paths that point to model-visible claim data or prior-claim context.",
    "appropriate_abstention": "Share of annotated task-specific abstentions produced when required evidence is insufficient.",
}


def safe_div(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def _issue_key(claim_id: str, code: str, entity_ref: str) -> tuple[str, str, str]:
    return claim_id, code, entity_ref


def _fact_subset_matches(expected: dict[str, Any], predicted: dict[str, Any]) -> bool:
    """Require all annotated material facts to be present and equal.

    This is a diagnostic stricter than issue matching. It keeps wording out of
    scoring while showing whether a model returned the annotated fact payload.
    """
    return all(key in predicted and predicted[key] == value for key, value in expected.items())


def _root_name(reference: str) -> str:
    return reference.split(".", 1)[0].split("[", 1)[0]


def evidence_reference_is_valid(reference: str, claim: dict[str, Any]) -> bool:
    """Check that an evidence reference points to model-visible or prior-claim data."""
    if reference.startswith("previous_claims"):
        return True
    root = _root_name(reference)
    if root not in claim:
        return False
    if "[" not in reference:
        return True

    prefix, remainder = reference.split("[", 1)
    selector = remainder.split("]", 1)[0]
    collection = claim.get(prefix)
    if not isinstance(collection, list):
        return False
    if selector.isdigit():
        return int(selector) < len(collection)
    if prefix == "attachments":
        return any(item.get("attachment_id") == selector for item in collection)
    return False


def decision_to_record(decision: Decision) -> dict[str, Any]:
    return {
        "claim_id": decision.claim_id,
        "action": decision.action.value,
        "return_reasons": [
            {
                "return_code": item.rule_code,
                "entity_ref": item.entity_ref,
                "evidence_refs": list(item.evidence_refs),
            }
            for item in decision.return_reasons
        ],
        "review_notes": [asdict(item) for item in decision.review_notes],
        "warnings": [asdict(item) for item in decision.review_warnings],
        "abstentions": [asdict(item) for item in decision.abstentions],
    }


def evaluate_records(
    claims: list[dict[str, Any]],
    ground_truth: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Score aligned predictions without comparing natural-language wording."""
    claim_by_id = {item["claim_id"]: item for item in claims}
    gt_by_id = {item["claim_id"]: item for item in ground_truth}
    pred_by_id = {item["claim_id"]: item for item in predictions}
    expected_ids = list(claim_by_id)
    if set(expected_ids) != set(gt_by_id) or set(expected_ids) != set(pred_by_id):
        raise ValueError("Claims, ground truth, and predictions must contain the same claim IDs")

    expected_return_cases: set[str] = set()
    predicted_return_cases: set[str] = set()
    expected_return_keys: set[tuple[str, str]] = set()
    predicted_return_keys: set[tuple[str, str]] = set()
    expected_warning_keys: set[tuple[str, str, str]] = set()
    predicted_warning_keys: set[tuple[str, str, str]] = set()
    fact_complete_warning_keys: set[tuple[str, str, str]] = set()
    expected_note_keys: set[tuple[str, str, str]] = set()
    predicted_note_keys: set[tuple[str, str, str]] = set()
    evidence_total = 0
    evidence_valid = 0
    abstention_keys: set[tuple[str, str, str]] = set()
    expected_abstention_keys: set[tuple[str, str, str]] = set()
    clean_ids: set[str] = set()
    cases: list[dict[str, Any]] = []

    for claim_id in expected_ids:
        claim = claim_by_id[claim_id]
        expected = gt_by_id[claim_id]
        predicted = pred_by_id[claim_id]
        expected_return = expected["expected_action"] == DecisionType.RETURN_TO_EMPLOYEE.value
        predicted_return = predicted["action"] == DecisionType.RETURN_TO_EMPLOYEE.value
        if expected_return:
            expected_return_cases.add(claim_id)
        if predicted_return:
            predicted_return_cases.add(claim_id)

        for code in expected.get("expected_return_reasons", []):
            expected_return_keys.add((claim_id, code))
        for item in predicted.get("return_reasons", []):
            predicted_return_keys.add((claim_id, item["return_code"]))

        expected_warnings = expected.get("expected_warnings", [])
        if not expected_return and not expected_warnings:
            clean_ids.add(claim_id)
        if not expected_return:
            for item in expected_warnings:
                expected_warning_keys.add(_issue_key(
                    claim_id, item["warning_code"], item["entity_ref"]
                ))
            for item in predicted.get("warnings", []):
                key = _issue_key(claim_id, item["warning_code"], item["entity_ref"])
                predicted_warning_keys.add(key)
                matching_expected = next(
                    (
                        candidate for candidate in expected_warnings
                        if candidate["warning_code"] == item["warning_code"]
                        and candidate["entity_ref"] == item["entity_ref"]
                    ),
                    None,
                )
                if matching_expected and _fact_subset_matches(
                    matching_expected.get("expected_facts", {}), item.get("facts", {})
                ):
                    fact_complete_warning_keys.add(key)

        for item in expected.get("expected_review_notes", []):
            expected_note_keys.add(_issue_key(claim_id, item["note_code"], item["entity_ref"]))
        for item in predicted.get("review_notes", []):
            predicted_note_keys.add(_issue_key(claim_id, item["note_code"], item["entity_ref"]))

        for item in predicted.get("return_reasons", []) + predicted.get("warnings", []) + predicted.get("review_notes", []):
            for reference in item.get("evidence_refs", []):
                evidence_total += 1
                evidence_valid += int(evidence_reference_is_valid(reference, claim))

        for item in predicted.get("abstentions", []):
            abstention_keys.add((claim_id, item["task_code"], item["entity_ref"]))
        for item in expected.get("expected_abstentions", []):
            expected_abstention_keys.add((claim_id, item["task_code"], item["entity_ref"]))

        cases.append({
            "claim_id": claim_id,
            "expected_action": expected["expected_action"],
            "predicted_action": predicted["action"],
            "predicted_return_reasons": [item["return_code"] for item in predicted.get("return_reasons", [])],
            "predicted_review_notes": [item["note_code"] for item in predicted.get("review_notes", [])],
            "predicted_warnings": [item["warning_code"] for item in predicted.get("warnings", [])],
            "predicted_abstentions": [item["task_code"] for item in predicted.get("abstentions", [])],
        })

    correct_return_cases = expected_return_cases & predicted_return_cases
    false_return_cases = predicted_return_cases - expected_return_cases
    matched_returns = expected_return_keys & predicted_return_keys
    matched_warnings = expected_warning_keys & predicted_warning_keys
    unsupported_warnings = predicted_warning_keys - expected_warning_keys
    matched_notes = expected_note_keys & predicted_note_keys
    clean_with_warning = {claim_id for claim_id, _, _ in predicted_warning_keys if claim_id in clean_ids}
    expected_issue_count = len(expected_return_keys) + len(expected_warning_keys)
    matched_issue_count = len(matched_returns) + len(matched_warnings)
    matched_abstentions = expected_abstention_keys & abstention_keys

    return {
        "metrics": {
            "false_return_rate": safe_div(len(false_return_cases), len(claims) - len(expected_return_cases)),
            "return_precision": safe_div(len(correct_return_cases), len(predicted_return_cases)),
            "return_recall": safe_div(len(correct_return_cases), len(expected_return_cases)),
            "return_reason_recall": safe_div(len(matched_returns), len(expected_return_keys)),
            "warning_recall": safe_div(len(matched_warnings), len(expected_warning_keys)),
            "warning_precision": safe_div(len(matched_warnings), len(predicted_warning_keys)),
            "warning_fact_recall_diagnostic": safe_div(len(fact_complete_warning_keys), len(expected_warning_keys)),
            "unsupported_warning_rate": safe_div(len(unsupported_warnings), len(predicted_warning_keys)),
            "clean_case_warning_rate": safe_div(len(clean_with_warning), len(clean_ids)),
            "review_note_recall_diagnostic": safe_div(len(matched_notes), len(expected_note_keys)),
            "material_issue_recall": safe_div(matched_issue_count, expected_issue_count),
            "evidence_reference_validity": safe_div(evidence_valid, evidence_total),
            "appropriate_abstention": (
                safe_div(len(matched_abstentions), len(expected_abstention_keys))
                if expected_abstention_keys else None
            ),
        },
        "counts": {
            "claims": len(claims),
            "clean_cases": len(clean_ids),
            "expected_returns": len(expected_return_cases),
            "predicted_returns": len(predicted_return_cases),
            "false_returns": len(false_return_cases),
            "expected_return_reasons": len(expected_return_keys),
            "matched_return_reasons": len(matched_returns),
            "expected_warnings": len(expected_warning_keys),
            "matched_warnings": len(matched_warnings),
            "fact_complete_warnings": len(fact_complete_warning_keys),
            "unsupported_warnings": len(unsupported_warnings),
            "expected_review_notes": len(expected_note_keys),
            "matched_review_notes": len(matched_notes),
            "evidence_references": evidence_total,
            "valid_evidence_references": evidence_valid,
            "abstentions": len(abstention_keys),
            "expected_abstentions": len(expected_abstention_keys),
        },
        "cases": cases,
    }
