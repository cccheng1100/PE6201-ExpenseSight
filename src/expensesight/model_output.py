"""Strict, provider-neutral contract for advisory model output.

The model is deliberately unable to choose the business action or create an
automatic return reason. It may only produce review notes, warnings, or an
explicit abstention. Deterministic rules remain the sole source of returns.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .contracts import ReviewAbstention, ReviewNote, ReviewWarning


class ModelOutputValidationError(ValueError):
    """Raised when model output does not satisfy the ExpenseSight contract."""


@dataclass
class ModelReviewOutput:
    claim_id: str
    review_notes: list[ReviewNote] = field(default_factory=list)
    warnings: list[ReviewWarning] = field(default_factory=list)
    abstentions: list[ReviewAbstention] = field(default_factory=list)


def _object(value: Any, location: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ModelOutputValidationError(f"{location} must be an object")
    return value


def _strict_keys(
    value: dict[str, Any],
    required: set[str],
    optional: set[str],
    location: str,
) -> None:
    missing = required - set(value)
    extra = set(value) - required - optional
    if missing:
        raise ModelOutputValidationError(f"{location} is missing {sorted(missing)}")
    if extra:
        raise ModelOutputValidationError(f"{location} has unsupported fields {sorted(extra)}")


def _text(value: Any, location: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise ModelOutputValidationError(f"{location} must be a non-empty string")
    return value


def _string_list(value: Any, location: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise ModelOutputValidationError(f"{location} must be a list of non-empty strings")
    return list(value)


def _list(value: Any, location: str) -> list[Any]:
    if not isinstance(value, list):
        raise ModelOutputValidationError(f"{location} must be a list")
    return value


def parse_model_review_output(raw: dict[str, Any], expected_claim_id: str | None = None) -> ModelReviewOutput:
    """Validate and convert one advisory model response.

    The strict top-level key check intentionally rejects ``action`` and
    ``return_reasons`` so a model response cannot cross the return boundary.
    """
    raw = _object(raw, "output")
    _strict_keys(raw, {"claim_id", "review_notes", "warnings", "abstentions"}, set(), "output")
    claim_id = _text(raw["claim_id"], "output.claim_id")
    if expected_claim_id is not None and claim_id != expected_claim_id:
        raise ModelOutputValidationError(
            f"output.claim_id {claim_id!r} does not match {expected_claim_id!r}"
        )

    notes: list[ReviewNote] = []
    for index, item_raw in enumerate(_list(raw["review_notes"], "output.review_notes")):
        location = f"output.review_notes[{index}]"
        item = _object(item_raw, location)
        _strict_keys(
            item,
            {"note_code", "category", "entity_ref", "facts", "evidence_refs", "text"},
            set(),
            location,
        )
        if not isinstance(item["facts"], dict):
            raise ModelOutputValidationError(f"{location}.facts must be an object")
        notes.append(ReviewNote(
            note_code=_text(item["note_code"], f"{location}.note_code"),
            category=_text(item["category"], f"{location}.category"),
            entity_ref=_text(item["entity_ref"], f"{location}.entity_ref"),
            facts=dict(item["facts"]),
            evidence_refs=_string_list(item["evidence_refs"], f"{location}.evidence_refs"),
            text=_text(item["text"], f"{location}.text"),
        ))

    warnings: list[ReviewWarning] = []
    for index, item_raw in enumerate(_list(raw["warnings"], "output.warnings")):
        location = f"output.warnings[{index}]"
        item = _object(item_raw, location)
        _strict_keys(
            item,
            {
                "warning_code", "category", "entity_ref", "facts",
                "evidence_refs", "materiality", "explanation",
            },
            {"policy_clause"},
            location,
        )
        if not isinstance(item["facts"], dict):
            raise ModelOutputValidationError(f"{location}.facts must be an object")
        clause = item.get("policy_clause")
        if clause is not None and not isinstance(clause, str):
            raise ModelOutputValidationError(f"{location}.policy_clause must be a string or null")
        warnings.append(ReviewWarning(
            warning_code=_text(item["warning_code"], f"{location}.warning_code"),
            category=_text(item["category"], f"{location}.category"),
            entity_ref=_text(item["entity_ref"], f"{location}.entity_ref"),
            facts=dict(item["facts"]),
            evidence_refs=_string_list(item["evidence_refs"], f"{location}.evidence_refs"),
            policy_clause=clause,
            materiality=_text(item["materiality"], f"{location}.materiality"),
            explanation=_text(item["explanation"], f"{location}.explanation"),
        ))

    abstentions: list[ReviewAbstention] = []
    for index, item_raw in enumerate(_list(raw["abstentions"], "output.abstentions")):
        location = f"output.abstentions[{index}]"
        item = _object(item_raw, location)
        _strict_keys(
            item,
            {"task_code", "entity_ref", "reason", "missing_evidence_refs"},
            set(),
            location,
        )
        abstentions.append(ReviewAbstention(
            task_code=_text(item["task_code"], f"{location}.task_code"),
            entity_ref=_text(item["entity_ref"], f"{location}.entity_ref"),
            reason=_text(item["reason"], f"{location}.reason"),
            missing_evidence_refs=_string_list(
                item["missing_evidence_refs"], f"{location}.missing_evidence_refs"
            ),
        ))

    return ModelReviewOutput(claim_id, notes, warnings, abstentions)


def validate_warning_taxonomy_contract(
    output: ModelReviewOutput,
    warning_taxonomy: dict[str, Any],
) -> None:
    """Reject semantic warnings that drift from their versioned taxonomy contract."""
    contracts = {
        item["code"]: item
        for item in warning_taxonomy.get("codes", [])
        if item.get("owner") in {"semantic_model", "semantic_model_or_route_layer"}
    }
    for index, warning in enumerate(output.warnings):
        location = f"output.warnings[{index}]"
        contract = contracts.get(warning.warning_code)
        if contract is None:
            raise ModelOutputValidationError(
                f"{location}.warning_code is not owned by the semantic review layer"
            )

        expected_keys = set(contract.get("fact_keys", []))
        actual_keys = set(warning.facts)
        missing = expected_keys - actual_keys
        extra = actual_keys - expected_keys
        if missing:
            raise ModelOutputValidationError(
                f"{location}.facts is missing taxonomy keys {sorted(missing)}"
            )
        if extra:
            raise ModelOutputValidationError(
                f"{location}.facts has cross-code keys {sorted(extra)}"
            )

        for key, expected_value in contract.get("required_fact_values", {}).items():
            if warning.facts.get(key) != expected_value:
                raise ModelOutputValidationError(
                    f"{location}.facts[{key!r}] does not match the taxonomy value"
                )

        if warning.materiality != contract.get("materiality"):
            raise ModelOutputValidationError(
                f"{location}.materiality does not match the taxonomy"
            )
        if warning.policy_clause != contract.get("policy_clause"):
            raise ModelOutputValidationError(
                f"{location}.policy_clause does not match the taxonomy"
            )
