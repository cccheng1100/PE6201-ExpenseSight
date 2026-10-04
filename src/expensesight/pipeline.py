"""Rules-first decision pipeline and safety validator."""
from __future__ import annotations

from .contracts import (
    Claim,
    Decision,
    DecisionType,
    ReviewAbstention,
    ReviewNote,
    ReviewWarning,
)
from .rules import run_rules
from .triage import triage_rule_findings


def _totals(claim: Claim) -> tuple[float, float]:
    reimbursable = sum(item.reimbursable_rmb for item in claim.transport_legs)
    reimbursable += sum(item.reimbursable_rmb for item in claim.hotel_stays)
    reimbursable += sum(item.reimbursable_rmb for item in claim.other_expenses)
    if claim.meal_allowance:
        reimbursable += claim.meal_allowance.total_rmb

    deduction = sum(item.deduction_rmb for item in claim.transport_legs)
    deduction += sum(item.deduction_rmb for item in claim.hotel_stays)
    deduction += sum(item.deduction_rmb for item in claim.other_expenses)
    return reimbursable, deduction


def run_pipeline(
    claim: Claim,
    previous_claims: list[Claim] | None = None,
    review_notes: list[ReviewNote] | None = None,
    model_warnings: list[ReviewWarning] | None = None,
    model_abstentions: list[ReviewAbstention] | None = None,
    route_warnings: list[ReviewWarning] | None = None,
) -> Decision:
    """Run rules and combine advisory warnings without allowing them to return a claim."""
    findings = run_rules(claim, previous_claims)
    triaged = triage_rule_findings(findings)
    failures = triaged.return_reasons
    reimbursable, deduction = _totals(claim)

    if failures:
        # A deterministic return is terminal for this pass. Advisory review is
        # intentionally excluded so the orchestration layer can skip the LLM
        # call and present one unambiguous employee action.
        return Decision(
            claim_id=claim.claim_id,
            action=DecisionType.RETURN_TO_EMPLOYEE,
            return_reasons=failures,
            review_notes=[],
            review_warnings=[],
            abstentions=[],
            evidence_brief=[finding.description for finding in failures],
            total_reimbursable_rmb=reimbursable,
            total_deduction_rmb=deduction,
        )

    advisory_warnings = triaged.review_warnings + (model_warnings or []) + (route_warnings or [])
    notes = triaged.review_notes + (review_notes or [])
    return Decision(
        claim_id=claim.claim_id,
        action=DecisionType.PROCEED_TO_HUMAN,
        return_reasons=[],
        review_notes=notes,
        review_warnings=advisory_warnings,
        abstentions=model_abstentions or [],
        evidence_brief=[warning.explanation for warning in advisory_warnings if warning.explanation],
        total_reimbursable_rmb=reimbursable,
        total_deduction_rmb=deduction,
    )
