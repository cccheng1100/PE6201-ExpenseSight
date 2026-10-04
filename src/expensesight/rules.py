"""Deterministic rules for the ExpenseSight baseline."""
from __future__ import annotations

from datetime import date

from .contracts import (
    CabinClass,
    Claim,
    CityTier,
    Grade,
    RuleFinding,
    TransportType,
)
from .parsing import extract_document_amount, extract_document_ids


HOTEL_CAP = {
    ("junior", CityTier.TIER1): 450.0,
    ("junior", CityTier.OTHER): 380.0,
    ("senior", CityTier.TIER1): 550.0,
    ("senior", CityTier.OTHER): 450.0,
}

TIER1_CITIES = {"Beijing", "Shanghai", "Guangzhou", "Shenzhen", "北京", "上海", "广州", "深圳"}


def _finding(
    code: str,
    description: str,
    clause: str,
    severity: str,
    entity: str,
    *evidence: str,
    evidence_source: str = "structured_claim",
    evidence_reliability: str = "verified",
    plausible_exception: bool = False,
    employee_actionable: bool = True,
) -> RuleFinding:
    return RuleFinding(
        code, description, clause, severity, entity, list(evidence),
        evidence_source, evidence_reliability, plausible_exception,
        employee_actionable,
    )


def _attachments(claim: Claim, entity_ref: str, document_type: str | None = None):
    return [
        item for item in claim.attachments
        if entity_ref in item.linked_expense_refs
        and (document_type is None or item.document_type == document_type)
    ]


def _attachment_ref(attachment_id: str) -> str:
    return f"attachments[{attachment_id}].ocr_description"


def _fingerprint(text: str) -> str:
    return " ".join((text or "").lower().split())


def _grade_group(grade: Grade) -> str:
    return "junior" if grade in (Grade.G1, Grade.G2) else "senior"


def _city_tier(city: str) -> CityTier:
    return CityTier.TIER1 if city in TIER1_CITIES else CityTier.OTHER


def _has_exception_evidence(claim: Claim) -> bool:
    return bool(
        (claim.pre_approval and claim.pre_approval.special_request.strip())
        or claim.special_notes.strip()
    )


def check_arithmetic(claim: Claim) -> list[RuleFinding]:
    findings: list[RuleFinding] = []
    groups = [
        ("transport_legs", claim.transport_legs),
        ("hotel_stays", claim.hotel_stays),
        ("other_expenses", claim.other_expenses),
    ]
    for group_name, items in groups:
        for index, item in enumerate(items):
            if min(item.amount_rmb, item.deduction_rmb, item.reimbursable_rmb) < 0:
                findings.append(_finding(
                    "INVALID_NEGATIVE_AMOUNT",
                    "Billed, deduction, and reimbursable amounts must not be negative.",
                    "Data validation", "fail", f"{group_name}[{index}]",
                    f"{group_name}[{index}].amount_rmb",
                    f"{group_name}[{index}].deduction_rmb",
                    f"{group_name}[{index}].reimbursable_rmb",
                ))
            if item.deduction_rmb > item.amount_rmb + 0.01:
                findings.append(_finding(
                    "DEDUCTION_EXCEEDS_AMOUNT",
                    "Employee deduction exceeds the billed amount.",
                    "Data validation", "fail", f"{group_name}[{index}]",
                    f"{group_name}[{index}].amount_rmb",
                    f"{group_name}[{index}].deduction_rmb",
                ))
            if abs((item.amount_rmb - item.deduction_rmb) - item.reimbursable_rmb) > 0.01:
                findings.append(_finding(
                    "AMOUNT_ARITHMETIC_MISMATCH",
                    "Reimbursable amount does not equal billed amount minus employee deduction.",
                    "Data validation",
                    "fail",
                    f"{group_name}[{index}]",
                    f"{group_name}[{index}].amount_rmb",
                    f"{group_name}[{index}].deduction_rmb",
                    f"{group_name}[{index}].reimbursable_rmb",
                ))
    if claim.meal_allowance and abs(
        claim.meal_allowance.days * claim.meal_allowance.daily_rate
        - claim.meal_allowance.total_rmb
    ) > 0.01:
        findings.append(_finding(
            "ALLOWANCE_ARITHMETIC_MISMATCH",
            "Allowance total does not equal eligible days multiplied by the daily rate.",
            "Data validation", "fail", "meal_allowance",
            "meal_allowance.days", "meal_allowance.daily_rate", "meal_allowance.total_rmb",
        ))

    for index, stay in enumerate(claim.hotel_stays):
        calendar_nights = (stay.check_out - stay.check_in).days
        if calendar_nights != stay.nights:
            findings.append(_finding(
                "HOTEL_NIGHTS_MISMATCH",
                "Declared hotel nights do not match check-in and check-out dates.",
                "Data validation", "fail", f"hotel_stays[{index}]",
                f"hotel_stays[{index}].check_in", f"hotel_stays[{index}].check_out",
                f"hotel_stays[{index}].nights",
            ))

    for index, leg in enumerate(claim.transport_legs):
        if leg.arrive_date < leg.depart_date:
            findings.append(_finding(
                "TRANSPORT_DATE_ORDER_INVALID",
                "Transport arrival date is earlier than departure date.",
                "Data validation", "fail", f"transport_legs[{index}]",
                f"transport_legs[{index}].depart_date", f"transport_legs[{index}].arrive_date",
            ))
    return findings


def check_hotel_caps(claim: Claim) -> list[RuleFinding]:
    findings: list[RuleFinding] = []
    group = _grade_group(claim.grade)
    for index, stay in enumerate(claim.hotel_stays):
        cap = HOTEL_CAP[(group, _city_tier(stay.city))]
        effective_rate = stay.reimbursable_rmb / stay.nights if stay.nights else 0.0
        if effective_rate > cap + 0.01:
            findings.append(_finding(
                "HOTEL_OVER_CAP_NOT_DEDUCTED",
                f"Reimbursable hotel rate is RMB {effective_rate:.2f} per night; the applicable cap is RMB {cap:.2f}.",
                "Section 3 — Accommodation Standard",
                "fail",
                f"hotel_stays[{index}]",
                f"hotel_stays[{index}].reimbursable_rmb",
                f"hotel_stays[{index}].nights",
                f"hotel_stays[{index}].city",
            ))
        if stay.nights > 14:
            findings.append(_finding(
                "LONG_STAY_REVIEW",
                "Stay exceeds 14 consecutive nights and requires evidence of a second approval.",
                "Section 3 — Accommodation Standard",
                "warn",
                f"hotel_stays[{index}]",
                f"hotel_stays[{index}].nights",
            ))
        entity = f"hotel_stays[{index}]"
        if not _attachments(claim, entity, "hotel_folio"):
            findings.append(_finding(
                "HOTEL_FOLIO_MISSING", "Hotel folio description is missing.",
                "Section 7 — Required Attachments", "warn", f"hotel_stays[{index}]",
                "attachments",
            ))
        if not _attachments(claim, entity, "hotel_invoice"):
            findings.append(_finding(
                "HOTEL_INVOICE_MISSING", "Hotel VAT invoice description is missing.",
                "Section 7 — Required Attachments", "warn", f"hotel_stays[{index}]",
                "attachments",
            ))
    return findings


def check_approval_scope(claim: Claim) -> list[RuleFinding]:
    if claim.pre_approval is None or not claim.has_travel_application:
        return [_finding(
            "APPROVAL_EVIDENCE_MISSING",
            "No attached approved travel application is available for this claim.",
            "Section 2 — Pre-Approval",
            "warn",
            "pre_approval",
            "has_travel_application",
            "pre_approval",
        )]

    approval = claim.pre_approval
    dates: list[date] = []
    destinations: set[str] = set()
    trip_origin = claim.transport_legs[0].depart_city if claim.transport_legs else None
    for leg in claim.transport_legs:
        dates.extend((leg.depart_date, leg.arrive_date))
        if leg.transport in (TransportType.FLIGHT, TransportType.RAIL, TransportType.INTERCITY_BUS) and leg.arrive_city != trip_origin:
            destinations.add(leg.arrive_city)
    for stay in claim.hotel_stays:
        dates.extend((stay.check_in, stay.check_out))
        destinations.add(stay.city)

    out_of_window = any(d < approval.valid_from or d > approval.valid_to for d in dates)
    unapproved = sorted(city for city in destinations if city not in set(approval.destination_cities))
    if not out_of_window and not unapproved:
        return []

    details = []
    if out_of_window:
        details.append("travel dates fall outside the approval window")
    if unapproved:
        details.append(f"unapproved destinations: {', '.join(unapproved)}")
    return [_finding(
        "APPROVAL_SCOPE_MISMATCH",
        "; ".join(details),
        "Section 2 — Pre-Approval",
        "fail",
        "pre_approval",
        "pre_approval.valid_from",
        "pre_approval.valid_to",
        "pre_approval.destination_cities",
        "transport_legs",
        "hotel_stays",
        plausible_exception=True,
    )]


def check_transport_documents(claim: Claim) -> list[RuleFinding]:
    findings: list[RuleFinding] = []
    seen_fingerprints: dict[str, tuple[str, str]] = {}
    for index, leg in enumerate(claim.transport_legs):
        entity = f"transport_legs[{index}]"
        documents = _attachments(claim, entity, "transport_ticket")
        if not documents:
            findings.append(_finding(
                "TRANSPORT_DOCUMENT_MISSING", "Transport document description is missing.",
                "Section 7 — Required Attachments", "warn", entity, "attachments",
            ))
            continue

        for document in documents:
            document_amount = extract_document_amount(document.ocr_description)
            if document_amount is not None and abs(document_amount - leg.amount_rmb) > 0.01:
                findings.append(_finding(
                    "TRANSPORT_DOCUMENT_AMOUNT_MISMATCH",
                    f"Claimed transport amount RMB {leg.amount_rmb:.2f} differs from extracted document amount RMB {document_amount:.2f}.",
                    "Section 7 — Required Attachments", "fail", entity,
                    f"{entity}.amount_rmb", _attachment_ref(document.attachment_id),
                    evidence_source="attachment_extraction",
                    evidence_reliability="uncertain",
                ))

            fingerprint = _fingerprint(document.ocr_description)
            if fingerprint and fingerprint in seen_fingerprints:
                previous_id, previous_entity = seen_fingerprints[fingerprint]
                severity = "note" if previous_entity == entity else "warn"
                code = "DUPLICATE_ATTACHMENT_IGNORED" if severity == "note" else "DUPLICATE_DOCUMENT_SUPPORT_REVIEW"
                findings.append(_finding(
                    code,
                    "A supporting transport document appears more than once; duplicate evidence must not be counted twice.",
                    "Section 10 — Duplicate Claims", severity, entity,
                    _attachment_ref(previous_id), _attachment_ref(document.attachment_id),
                    evidence_source="attachment_extraction",
                    evidence_reliability="uncertain",
                    plausible_exception=True,
                ))
            else:
                seen_fingerprints[fingerprint] = (document.attachment_id, entity)

        if leg.transport == TransportType.FLIGHT and leg.cabin == CabinClass.BUSINESS:
            findings.append(_finding(
                "HIGH_CABIN_REVIEW", "Business-class flight requires reviewer verification.",
                "Section 5 — Transport", "warn", entity, f"{entity}.cabin", "pre_approval.special_request",
            ))
        if leg.transport == TransportType.RAIL and leg.cabin in (CabinClass.FIRST_RAIL, CabinClass.BUSINESS_RAIL):
            findings.append(_finding(
                "HIGH_CABIN_REVIEW", "Rail cabin is above the default second-class standard.",
                "Section 5 — Transport", "warn", entity, f"{entity}.cabin", "pre_approval.special_request",
            ))
    return findings


def _invoice_ids(claim: Claim) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for attachment in claim.attachments:
        if attachment.document_type not in {"hotel_invoice", "other_invoice"}:
            continue
        for document_id in extract_document_ids(attachment.ocr_description):
            result.setdefault(document_id, []).append(_attachment_ref(attachment.attachment_id))
    return result


def check_exact_document_duplicates(claim: Claim, previous_claims: list[Claim]) -> list[RuleFinding]:
    findings: list[RuleFinding] = []
    current = _invoice_ids(claim)
    for document_id, refs in current.items():
        if len(refs) > 1:
            findings.append(_finding(
                "DUPLICATE_INVOICE_REVIEW", f"Invoice identifier {document_id} appears more than once in this claim.",
                "Section 10 — Duplicate Claims", "warn", "attachments", *refs,
                evidence_source="attachment_extraction", evidence_reliability="uncertain",
                plausible_exception=True,
            ))
    for previous in previous_claims:
        previous_ids = _invoice_ids(previous)
        for document_id in set(current).intersection(previous_ids):
            findings.append(_finding(
                "SHARED_OR_DUPLICATE_INVOICE_REVIEW",
                f"Invoice identifier {document_id} was already used in claim {previous.claim_id}.",
                "Section 10 — Duplicate Claims",
                "warn",
                "attachments",
                current[document_id][0],
                f"previous_claims[{previous.claim_id}]",
                evidence_source="attachment_extraction",
                evidence_reliability="uncertain",
                plausible_exception=True,
            ))
    return findings


def check_review_reminders(claim: Claim) -> list[RuleFinding]:
    findings: list[RuleFinding] = []
    if claim.submitted_on:
        latest_dates = [leg.arrive_date for leg in claim.transport_legs] + [stay.check_out for stay in claim.hotel_stays]
        if latest_dates and (claim.submitted_on - max(latest_dates)).days > 60:
            findings.append(_finding(
                "LATE_FILING_REVIEW", "Claim was submitted more than 60 days after the latest expense date.",
                "Section 8 — Filing Deadline", "warn", "submitted_on", "submitted_on",
            ))
    for index, expense in enumerate(claim.other_expenses):
        findings.append(_finding(
            "OTHER_EXPENSE_REVIEW",
            "Other expense requires human review of business purpose and supporting document.",
            "Section 7 — Required Attachments",
            "warn",
            f"other_expenses[{index}]",
            f"other_expenses[{index}].description",
            f"other_expenses[{index}].invoice_desc",
        ))
    return findings


def run_rules(claim: Claim, previous_claims: list[Claim] | None = None) -> list[RuleFinding]:
    previous_claims = previous_claims or []
    findings: list[RuleFinding] = []
    findings.extend(check_arithmetic(claim))
    findings.extend(check_hotel_caps(claim))
    findings.extend(check_approval_scope(claim))
    findings.extend(check_transport_documents(claim))
    findings.extend(check_exact_document_duplicates(claim, previous_claims))
    findings.extend(check_review_reminders(claim))
    return findings
