"""Build development annotations independently from development claims."""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "evals" / "dev_ground_truth.json"


def warning(code: str, category: str, entity: str, facts: dict, evidence: list[str], clause: str | None = None, materiality: str = "material") -> dict:
    return {"warning_code": code, "category": category, "entity_ref": entity, "expected_facts": facts, "evidence_refs": evidence, "materiality": materiality, "policy_clause": clause}


def note(code: str, category: str, entity: str, facts: dict, evidence: list[str], text: str) -> dict:
    return {"note_code": code, "category": category, "entity_ref": entity, "expected_facts": facts, "evidence_refs": evidence, "text": text}


def abstention(task: str, entity: str, reason: str, missing: list[str]) -> dict:
    return {"task_code": task, "entity_ref": entity, "reason": reason, "missing_evidence_refs": missing}


def record(index: int) -> dict:
    return {
        "claim_id": f"DEV-{index:03d}", "expected_action": "PROCEED_TO_HUMAN",
        "expected_return_reasons": [], "expected_review_notes": [],
        "expected_warnings": [], "expected_abstentions": [],
        "annotation_note": "", "status": "development_editable",
    }


def build_annotations() -> list[dict]:
    items = [record(index) for index in range(1, 23)]
    by_id = {item["claim_id"]: item for item in items}

    by_id["DEV-001"]["annotation_note"] = "Ordinary compliant claim; no warning should be produced."
    by_id["DEV-002"]["expected_review_notes"] = [note("OUTBOUND_ONLY_CLAIMED", "itinerary", "transport_legs", {"claimed_direction": "outbound_only"}, ["transport_legs"], "Only outbound transport was submitted; do not infer an unclaimed return expense.")]
    by_id["DEV-003"]["annotation_note"] = (
        "A same-day round trip does not require accommodation. No unclaimed "
        "hotel or allowance expense is inferred, and no Review Note is needed."
    )
    by_id["DEV-004"]["expected_review_notes"] = [note("INVOICE_ISSUED_DURING_STAY", "invoice", "hotel_stays[0]", {"relationship": "invoice issue date precedes checkout date"}, ["attachments", "hotel_stays[0].check_out"], "The invoice was issued during the stay; prepaid or early settlement may be valid.")]
    by_id["DEV-005"]["expected_review_notes"] = [note("DUPLICATE_ATTACHMENT_IGNORED", "attachment", "transport_legs[0]", {"duplicate_attachment_count": 1, "unique_documents_support_claim": True}, ["attachments"], "The repeated upload is ignored and does not imply duplicate reimbursement.")]
    by_id["DEV-006"]["annotation_note"] = "Coherent three-leg itinerary; ordinary round-trip-only logic is insufficient but no issue exists."

    def set_warnings(case_id: str, warnings: list[dict], annotation: str) -> None:
        by_id[case_id]["expected_warnings"] = warnings
        by_id[case_id]["annotation_note"] = annotation

    set_warnings("DEV-007", [warning("TRANSPORT_PASSENGER_MISMATCH", "transport", "transport_legs[0]", {"relationship": "ticket passenger differs from claimant"}, ["employee_name", "attachments"], "Section 7 — Required Attachments")], "Cross-document identity comparison.")
    set_warnings("DEV-008", [warning("HOTEL_GUEST_MISMATCH", "accommodation", "hotel_stays[0]", {"relationship": "folio guest differs from claimant"}, ["employee_name", "attachments"], "Section 7 — Required Attachments")], "Cross-document guest comparison.")
    set_warnings("DEV-009", [warning("TRANSPORT_DATE_MISMATCH", "transport", "transport_legs[0]", {"relationship": "ticket travel date differs from claimed departure date"}, ["transport_legs[0].depart_date", "attachments"])], "Structured date versus attachment date.")
    set_warnings("DEV-010", [warning("ITINERARY_CHRONOLOGY_CONFLICT", "itinerary", "hotel_stays[0]", {"relationship": "hotel check-in precedes arrival at destination"}, ["hotel_stays[0].check_in", "transport_legs[0].arrive_date", "transport_legs[0].arrive_city"])], "Cross-document chronology conflict.")
    set_warnings("DEV-011", [warning("POSSIBLE_NON_BUSINESS_TRIP", "transport", "transport_legs[2]", {"origin_type": "restaurant", "destination_type": "shopping_centre"}, ["attachments", "employee_note"])], "Route endpoints justify a warning, but the final business-purpose conclusion lacks meeting evidence.")
    by_id["DEV-011"]["expected_abstentions"] = [abstention("BUSINESS_PURPOSE_CONCLUSION", "transport_legs[2]", "The available claim does not include a meeting schedule or verified route context.", ["meeting_schedule", "verified_route_context"])]
    set_warnings("DEV-012", [warning("MULTI_LEG_LOCATION_GAP", "itinerary", "transport_legs[1]", {"relationship": "previous arrival differs from next departure", "connecting_document": "missing"}, ["transport_legs[0].arrive_city", "transport_legs[1].depart_city", "special_notes"], "Section 6 — Multi-Leg Itinerary Consistency")], "Requires continuity reasoning across three segments.")
    set_warnings("DEV-013", [
        warning("OTHER_EXPENSE_REVIEW", "rule_review", "other_expenses[0]", {"category": "printing"}, ["other_expenses[0].description", "attachments"], "Section 7 — Required Attachments"),
        warning("INVOICE_SERVICE_MISMATCH", "invoice", "other_expenses[0]", {"claimed_service": "printing", "invoice_service": "restaurant dining"}, ["other_expenses[0].description", "attachments"]),
    ], "Other expenses always reach a human; semantic review should also identify the service mismatch.")
    set_warnings("DEV-014", [warning("APPROVAL_SCOPE_MISMATCH", "approval", "pre_approval", {"relationship": "itinerary includes an unapproved destination"}, ["pre_approval.destination_cities", "transport_legs"], "Section 2 — Pre-Approval", "high")], "Serious approval mismatch remains a warning because exceptions may exist outside the visible claim.")

    returns = {
        15: "AMOUNT_ARITHMETIC_MISMATCH", 16: "HOTEL_OVER_CAP_NOT_DEDUCTED",
        17: "ALLOWANCE_ARITHMETIC_MISMATCH", 18: "INVALID_NEGATIVE_AMOUNT",
        19: "HOTEL_NIGHTS_MISMATCH", 20: "TRANSPORT_DATE_ORDER_INVALID",
    }
    for index, code in returns.items():
        item = by_id[f"DEV-{index:03d}"]
        item["expected_action"] = "RETURN_TO_EMPLOYEE"
        item["expected_return_reasons"] = [code]
        item["annotation_note"] = "Deterministic return based only on verified structured claim fields."

    set_warnings("DEV-021", [warning(
        "TRANSPORT_DOCUMENT_QUALITY_REVIEW", "attachment", "transport_legs[0]",
        {"unreadable_field": "passenger_name", "cause": "damaged_scan"},
        ["attachments"], "Section 7 — Required Attachments",
    )], "The unreadable passenger field is itself reviewable, but identity matching must abstain.")
    by_id["DEV-021"]["expected_abstentions"] = [abstention(
        "PASSENGER_IDENTITY_CHECK", "transport_legs[0]",
        "The passenger name is unreadable, so it cannot be compared with the claimant.",
        ["readable_passenger_name"],
    )]

    set_warnings("DEV-022", [warning(
        "HOTEL_LOCATION_REVIEW", "accommodation", "hotel_stays[0]",
        {"hotel_area": "airport industrial zone", "business_area": "central business district"},
        ["attachments", "special_notes"],
    )], "Textual locations justify review, but exact distance and route reasonableness require external facts.")
    by_id["DEV-022"]["expected_abstentions"] = [abstention(
        "ROUTE_DISTANCE_CHECK", "hotel_stays[0]",
        "No verified route distance or travel-time facts are available.",
        ["verified_route_distance", "verified_route_time"],
    )]
    return items


def main() -> None:
    annotations = build_annotations()
    OUTPUT.write_text(json.dumps(annotations, indent=2), encoding="utf-8")
    print(f"Wrote {len(annotations)} development annotations to {OUTPUT}")


if __name__ == "__main__":
    main()
