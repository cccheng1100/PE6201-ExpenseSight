"""JSON conversion helpers for ExpenseSight claim files."""
from __future__ import annotations

from datetime import date
from typing import Any

from .contracts import (
    Attachment,
    CabinClass,
    Claim,
    CityTier,
    Grade,
    HotelStay,
    MealAllowance,
    OtherExpense,
    PreApproval,
    TransportLeg,
    TransportType,
)


def _date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def claim_from_dict(raw: dict[str, Any]) -> Claim:
    legs = [
        TransportLeg(
            leg_id=item["leg_id"],
            transport=TransportType(item["transport"]),
            depart_city=item["depart_city"],
            arrive_city=item["arrive_city"],
            depart_date=_date(item["depart_date"]),
            arrive_date=_date(item["arrive_date"]),
            cabin=CabinClass(item["cabin"]) if item.get("cabin") else None,
            amount_rmb=float(item.get("amount_rmb", 0)),
            deduction_rmb=float(item.get("deduction_rmb", 0)),
            reimbursable_rmb=float(item.get("reimbursable_rmb", 0)),
            ticket_desc=item.get("ticket_desc", ""),
        )
        for item in raw.get("transport_legs", [])
    ]
    stays = [
        HotelStay(
            city=item["city"],
            check_in=_date(item["check_in"]),
            check_out=_date(item["check_out"]),
            nights=int(item["nights"]),
            amount_rmb=float(item.get("amount_rmb", 0)),
            deduction_rmb=float(item.get("deduction_rmb", 0)),
            reimbursable_rmb=float(item.get("reimbursable_rmb", 0)),
            folio_desc=item.get("folio_desc", ""),
            invoice_desc=item.get("invoice_desc", ""),
        )
        for item in raw.get("hotel_stays", [])
    ]
    meal_raw = raw.get("meal_allowance")
    meal = None
    if meal_raw:
        meal = MealAllowance(
            days=int(meal_raw["days"]),
            city_tier=CityTier(meal_raw["city_tier"]),
            daily_rate=float(meal_raw["daily_rate"]),
            total_rmb=float(meal_raw.get("total_rmb", 0)),
        )
    others = [
        OtherExpense(
            category=item["category"],
            description=item["description"],
            amount_rmb=float(item.get("amount_rmb", 0)),
            deduction_rmb=float(item.get("deduction_rmb", 0)),
            reimbursable_rmb=float(item.get("reimbursable_rmb", 0)),
            invoice_desc=item.get("invoice_desc", ""),
        )
        for item in raw.get("other_expenses", [])
    ]
    approval_raw = raw.get("pre_approval")
    approval = None
    if approval_raw:
        approval = PreApproval(
            approval_id=approval_raw["approval_id"],
            approved_on=_date(approval_raw["approved_on"]),
            valid_from=_date(approval_raw["valid_from"]),
            valid_to=_date(approval_raw["valid_to"]),
            destination_cities=list(approval_raw.get("destination_cities", [])),
            estimated_total_rmb=float(approval_raw.get("estimated_total_rmb", 0)),
            special_request=approval_raw.get("special_request", ""),
        )
    attachments = [
        Attachment(
            attachment_id=item["attachment_id"],
            document_type=item["document_type"],
            linked_expense_refs=list(item.get("linked_expense_refs", [])),
            ocr_description=item.get("ocr_description", ""),
        )
        for item in raw.get("attachments", [])
    ]
    return Claim(
        claim_id=raw["claim_id"],
        employee_id=raw["employee_id"],
        employee_name=raw["employee_name"],
        grade=Grade(raw["grade"]),
        transport_legs=legs,
        hotel_stays=stays,
        meal_allowance=meal,
        other_expenses=others,
        attachments=attachments,
        pre_approval=approval,
        has_travel_application=bool(raw.get("has_travel_application", True)),
        submitted_on=_date(raw.get("submitted_on")),
        special_notes=raw.get("special_notes", ""),
        employee_note=raw.get("employee_note", ""),
    )
