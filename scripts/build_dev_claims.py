"""Build 20 model-visible development claims, separate from holdout cases."""
from __future__ import annotations

import json
from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "dev" / "dev_claims.json"
MANIFEST = ROOT / "data" / "dev" / "dev_case_manifest.json"
CITIES = ["Nanjing", "Hefei", "Wuhan", "Changsha", "Chengdu", "Hangzhou", "Jinan", "Kunming"]


def leg(case_id: str, number: int, origin: str, destination: str, day: date, amount: float = 320.0) -> dict:
    return {
        "leg_id": f"{case_id}-L{number}", "transport": "rail",
        "depart_city": origin, "arrive_city": destination,
        "depart_date": day.isoformat(), "arrive_date": day.isoformat(),
        "cabin": "economy", "amount_rmb": amount, "deduction_rmb": 0,
        "reimbursable_rmb": amount,
        "ticket_desc": (
            f"Rail ticket passenger Dev Employee {case_id[-3:]}, {origin} to {destination}, "
            f"travel date {day.isoformat()}, fare RMB {amount:.0f}, ticket no. TKT-{case_id}-{number}."
        ),
    }


def hotel(case_id: str, city: str, check_in: date, nights: int = 2, rate: float = 340.0, sequence: int = 1) -> dict:
    amount = nights * rate
    return {
        "city": city, "check_in": check_in.isoformat(),
        "check_out": (check_in + timedelta(days=nights)).isoformat(),
        "nights": nights,
        "amount_rmb": amount, "deduction_rmb": 0, "reimbursable_rmb": amount,
        "folio_desc": (
            f"Hotel folio guest Dev Employee {case_id[-3:]}, {city} Project Hotel, "
            f"{nights} nights at RMB {rate:.0f} per night."
        ),
        "invoice_desc": (
            f"VAT invoice for accommodation, amount RMB {amount:.0f}, "
            f"invoice no. INV-{case_id}-H{sequence}."
        ),
    }


def approval(case_id: str, start: date, end: date, cities: list[str]) -> dict:
    return {
        "approval_id": f"PA-{case_id}", "approved_on": (start - timedelta(days=5)).isoformat(),
        "valid_from": start.isoformat(), "valid_to": end.isoformat(),
        "destination_cities": cities, "estimated_total_rmb": 4000,
        "special_request": "",
    }


def base_claim(index: int) -> dict:
    case_id = f"DEV-{index:03d}"
    origin = CITIES[index % len(CITIES)]
    destination = CITIES[(index + 3) % len(CITIES)]
    start = date(2026, ((index - 1) % 9) + 1, ((index * 2) % 18) + 2)
    end = start + timedelta(days=2)
    return {
        "claim_id": case_id, "employee_id": f"DEV-E{index:03d}",
        "employee_name": f"Dev Employee {index:03d}", "grade": "G2",
        "transport_legs": [leg(case_id, 1, origin, destination, start), leg(case_id, 2, destination, origin, end, 300)],
        "hotel_stays": [hotel(case_id, destination, start)],
        "meal_allowance": {"days": 3, "city_tier": "other", "daily_rate": 80, "total_rmb": 240},
        "other_expenses": [], "pre_approval": approval(case_id, start, end, [destination]),
        "has_travel_application": True, "submitted_on": (end + timedelta(days=6)).isoformat(),
        "special_notes": "", "employee_note": f"Project visit to {destination}.",
    }


def make_complex(claim: dict, *, gap: bool = False, unapproved: bool = False) -> None:
    case_id = claim["claim_id"]
    first = claim["transport_legs"][0]
    origin, city_b = first["depart_city"], first["arrive_city"]
    city_c = next(city for city in CITIES if city not in {origin, city_b})
    gap_city = next(city for city in reversed(CITIES) if city not in {origin, city_b, city_c})
    start = date.fromisoformat(first["depart_date"])
    claim["transport_legs"] = [
        leg(case_id, 1, origin, city_b, start),
        leg(case_id, 2, gap_city if gap else city_b, city_c, start + timedelta(days=1), 240),
        leg(case_id, 3, city_c, origin, start + timedelta(days=2), 330),
    ]
    claim["hotel_stays"] = [
        hotel(case_id, city_b, start, 1, sequence=1),
        hotel(case_id, city_c, start + timedelta(days=1), 1, sequence=2),
    ]
    claim["pre_approval"] = approval(case_id, start, start + timedelta(days=2), [city_b] if unapproved else [city_b, city_c])


def finalize_attachments(claim: dict) -> None:
    attachments: list[dict] = []

    def add(document_type: str, entity_ref: str, description: str) -> None:
        if description.strip():
            attachments.append({
                "attachment_id": f"{claim['claim_id']}-ATT-{len(attachments) + 1:02d}",
                "document_type": document_type, "linked_expense_refs": [entity_ref],
                "ocr_description": description,
            })

    for index, item in enumerate(claim["transport_legs"]):
        add("transport_ticket", f"transport_legs[{index}]", item.pop("ticket_desc", ""))
    for index, item in enumerate(claim["hotel_stays"]):
        add("hotel_folio", f"hotel_stays[{index}]", item.pop("folio_desc", ""))
        add("hotel_invoice", f"hotel_stays[{index}]", item.pop("invoice_desc", ""))
    for index, item in enumerate(claim["other_expenses"]):
        add("other_invoice", f"other_expenses[{index}]", item.pop("invoice_desc", ""))
    for extra in claim.pop("_extra_attachments", []):
        add(extra["document_type"], extra["entity_ref"], extra["ocr_description"])
    claim["attachments"] = attachments


def build_claims() -> tuple[list[dict], list[dict]]:
    claims = [base_claim(index) for index in range(1, 23)]
    by_id = {claim["claim_id"]: claim for claim in claims}

    by_id["DEV-002"]["transport_legs"] = by_id["DEV-002"]["transport_legs"][:1]
    c = by_id["DEV-003"]
    start = date.fromisoformat(c["transport_legs"][0]["depart_date"])
    origin, destination = c["transport_legs"][0]["depart_city"], c["transport_legs"][0]["arrive_city"]
    c["transport_legs"] = [leg("DEV-003", 1, origin, destination, start, 100), leg("DEV-003", 2, destination, origin, start, 100)]
    c["hotel_stays"], c["meal_allowance"] = [], None
    c["pre_approval"] = approval("DEV-003", start, start, [destination])
    c = by_id["DEV-004"]
    checkout = date.fromisoformat(c["hotel_stays"][0]["check_out"])
    c["hotel_stays"][0]["invoice_desc"] = (
        f"VAT invoice for accommodation, issue date {(checkout - timedelta(days=1)).isoformat()}, "
        f"checkout date {checkout.isoformat()}, amount RMB {c['hotel_stays'][0]['amount_rmb']:.0f}, invoice no. INV-DEV-004-H1."
    )
    c = by_id["DEV-005"]
    c["_extra_attachments"] = [{"document_type": "transport_ticket", "entity_ref": "transport_legs[0]", "ocr_description": deepcopy(c["transport_legs"][0]["ticket_desc"])}]
    make_complex(by_id["DEV-006"])

    c = by_id["DEV-007"]
    c["transport_legs"][0]["ticket_desc"] = c["transport_legs"][0]["ticket_desc"].replace("Dev Employee 007", "Dev Employee 071")
    c = by_id["DEV-008"]
    c["hotel_stays"][0]["folio_desc"] = c["hotel_stays"][0]["folio_desc"].replace("Dev Employee 008", "Dev Employee 081")
    c = by_id["DEV-009"]
    first = c["transport_legs"][0]
    first["ticket_desc"] = first["ticket_desc"].replace(first["depart_date"], (date.fromisoformat(first["depart_date"]) - timedelta(days=2)).isoformat())
    make_complex(by_id["DEV-010"])
    c = by_id["DEV-010"]
    arrival, destination = date.fromisoformat(c["transport_legs"][0]["arrive_date"]), c["transport_legs"][0]["arrive_city"]
    c["hotel_stays"] = [hotel("DEV-010", destination, arrival - timedelta(days=1), 3)]
    approved_cities = [c["transport_legs"][0]["arrive_city"], c["transport_legs"][1]["arrive_city"]]
    c["pre_approval"] = approval("DEV-010", arrival - timedelta(days=1), arrival + timedelta(days=2), approved_cities)
    c = by_id["DEV-011"]
    destination = c["transport_legs"][0]["arrive_city"]
    day = date.fromisoformat(c["transport_legs"][0]["depart_date"]) + timedelta(days=1)
    ride = leg("DEV-011", 3, f"{destination} Riverside Restaurant", f"{destination} Central Mall", day, 72)
    ride.update({"transport": "rideshare", "cabin": None, "ticket_desc": f"Rideshare receipt from {destination} Riverside Restaurant to {destination} Central Mall, fare RMB 72, ticket no. TKT-DEV-011-3."})
    c["transport_legs"].append(ride)
    c["employee_note"] = f"Meetings at {destination} Q Company; no meeting schedule is attached."
    make_complex(by_id["DEV-012"], gap=True)
    by_id["DEV-012"]["special_notes"] = "No connecting local-transport document is attached."
    c = by_id["DEV-013"]
    c["other_expenses"] = [{"category": "printing", "description": "Project drawing printing", "amount_rmb": 280, "deduction_rmb": 0, "reimbursable_rmb": 280, "invoice_desc": "VAT invoice for restaurant dining, amount RMB 280, invoice no. INV-DEV-013-O1."}]
    make_complex(by_id["DEV-014"], unapproved=True)

    by_id["DEV-015"]["transport_legs"][0]["reimbursable_rmb"] += 20
    c = by_id["DEV-016"]
    stay = c["hotel_stays"][0]
    stay.update({"amount_rmb": 1040, "reimbursable_rmb": 1040, "folio_desc": "Hotel folio, two nights at RMB 520 per night.", "invoice_desc": "VAT invoice for accommodation, amount RMB 1040, invoice no. INV-DEV-016-H1."})
    by_id["DEV-017"]["meal_allowance"]["total_rmb"] = 320
    c = by_id["DEV-018"]
    c["other_expenses"] = [{"category": "parking", "description": "Site parking", "amount_rmb": -60, "deduction_rmb": 0, "reimbursable_rmb": -60, "invoice_desc": "Parking receipt, amount RMB 60, invoice no. INV-DEV-018-O1."}]
    by_id["DEV-019"]["hotel_stays"][0]["nights"] = 3
    make_complex(by_id["DEV-020"])
    c = by_id["DEV-020"]
    depart = date.fromisoformat(c["transport_legs"][0]["depart_date"])
    c["transport_legs"][0]["arrive_date"] = (depart - timedelta(days=1)).isoformat()

    # Two additional abstention cases exercise different missing-evidence modes.
    c = by_id["DEV-021"]
    first = c["transport_legs"][0]
    first["ticket_desc"] = (
        f"Rail ticket passenger name unreadable due to damaged scan, "
        f"{first['depart_city']} to {first['arrive_city']}, travel date "
        f"{first['depart_date']}, fare RMB {first['amount_rmb']:.0f}, "
        "ticket no. TKT-DEV-021-1."
    )
    c = by_id["DEV-022"]
    city = c["hotel_stays"][0]["city"]
    c["hotel_stays"][0]["folio_desc"] = (
        f"Hotel folio guest Dev Employee 022 at {city} Remote Airport Hotel, "
        f"address: North Airport Industrial Zone, {city}; two nights at RMB 340 per night."
    )
    c["special_notes"] = f"Declared meeting location: {city} Q Company, Central Business District."

    for claim in claims:
        finalize_attachments(claim)
    complex_ids = {"DEV-006", "DEV-010", "DEV-012", "DEV-014", "DEV-020"}
    manifest = [{"claim_id": c["claim_id"], "origin": "development_synthetic", "case_tags": ["complex_multi_leg"] if c["claim_id"] in complex_ids else ["simple_or_single_itinerary"], "status": "development_editable"} for c in claims]
    return claims, manifest


def main() -> None:
    claims, manifest = build_claims()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(claims, indent=2), encoding="utf-8")
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote {len(claims)} development claims to {OUTPUT}")


if __name__ == "__main__":
    main()
