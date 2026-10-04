"""Core data contracts for ExpenseSight.

The claim schema intentionally follows the earlier prototype while the output
contract enforces the latest two-outcome safety boundary.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any


class Grade(str, Enum):
    G1 = "G1"
    G2 = "G2"
    G3 = "G3"
    G4 = "G4"


class TransportType(str, Enum):
    FLIGHT = "flight"
    RAIL = "rail"
    INTERCITY_BUS = "intercity_bus"
    TAXI = "taxi"
    RIDESHARE = "rideshare"


class CabinClass(str, Enum):
    ECONOMY = "economy"
    BUSINESS = "business"
    FIRST_RAIL = "first_rail"
    BUSINESS_RAIL = "business_rail"


class CityTier(str, Enum):
    TIER1 = "tier1"
    OTHER = "other"


class DecisionType(str, Enum):
    RETURN_TO_EMPLOYEE = "RETURN_TO_EMPLOYEE"
    PROCEED_TO_HUMAN = "PROCEED_TO_HUMAN"


@dataclass
class TransportLeg:
    leg_id: str
    transport: TransportType
    depart_city: str
    arrive_city: str
    depart_date: date
    arrive_date: date
    cabin: CabinClass | None = None
    amount_rmb: float = 0.0
    deduction_rmb: float = 0.0
    reimbursable_rmb: float = 0.0
    ticket_desc: str = ""


@dataclass
class HotelStay:
    city: str
    check_in: date
    check_out: date
    nights: int
    amount_rmb: float = 0.0
    deduction_rmb: float = 0.0
    reimbursable_rmb: float = 0.0
    folio_desc: str = ""
    invoice_desc: str = ""


@dataclass
class MealAllowance:
    days: int
    city_tier: CityTier
    daily_rate: float
    total_rmb: float = 0.0


@dataclass
class OtherExpense:
    category: str
    description: str
    amount_rmb: float = 0.0
    deduction_rmb: float = 0.0
    reimbursable_rmb: float = 0.0
    invoice_desc: str = ""


@dataclass
class PreApproval:
    approval_id: str
    approved_on: date
    valid_from: date
    valid_to: date
    destination_cities: list[str] = field(default_factory=list)
    estimated_total_rmb: float = 0.0
    special_request: str = ""


@dataclass
class Attachment:
    attachment_id: str
    document_type: str
    linked_expense_refs: list[str] = field(default_factory=list)
    ocr_description: str = ""


@dataclass
class Claim:
    claim_id: str
    employee_id: str
    employee_name: str
    grade: Grade
    transport_legs: list[TransportLeg] = field(default_factory=list)
    hotel_stays: list[HotelStay] = field(default_factory=list)
    meal_allowance: MealAllowance | None = None
    other_expenses: list[OtherExpense] = field(default_factory=list)
    attachments: list[Attachment] = field(default_factory=list)
    pre_approval: PreApproval | None = None
    has_travel_application: bool = True
    submitted_on: date | None = None
    special_notes: str = ""
    employee_note: str = ""


@dataclass
class RuleFinding:
    rule_code: str
    description: str
    policy_clause: str
    severity: str
    entity_ref: str
    evidence_refs: list[str] = field(default_factory=list)
    evidence_source: str = "structured_claim"
    evidence_reliability: str = "verified"
    plausible_exception: bool = False
    employee_actionable: bool = True


@dataclass
class ReviewNote:
    note_code: str
    category: str
    entity_ref: str
    facts: dict[str, Any] = field(default_factory=dict)
    evidence_refs: list[str] = field(default_factory=list)
    text: str = ""


@dataclass
class ReviewWarning:
    warning_code: str
    category: str
    entity_ref: str
    facts: dict[str, Any] = field(default_factory=dict)
    evidence_refs: list[str] = field(default_factory=list)
    policy_clause: str | None = None
    materiality: str = "material"
    explanation: str = ""
    abstained: bool = False


@dataclass
class ReviewAbstention:
    task_code: str
    entity_ref: str
    reason: str
    missing_evidence_refs: list[str] = field(default_factory=list)


@dataclass
class Decision:
    claim_id: str
    action: DecisionType
    return_reasons: list[RuleFinding] = field(default_factory=list)
    review_notes: list[ReviewNote] = field(default_factory=list)
    review_warnings: list[ReviewWarning] = field(default_factory=list)
    abstentions: list[ReviewAbstention] = field(default_factory=list)
    evidence_brief: list[str] = field(default_factory=list)
    total_reimbursable_rmb: float = 0.0
    total_deduction_rmb: float = 0.0
