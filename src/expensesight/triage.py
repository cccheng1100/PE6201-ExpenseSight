"""Deterministic review-boundary guardrails.

Triage does not decide whether a business explanation is true. It prevents an
uncertain, inferred, or plausibly exceptional finding from becoming an
automatic return action.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .contracts import ReviewNote, ReviewWarning, RuleFinding


RETURN_SOURCES = {"structured_claim", "verified_system_record"}


@dataclass
class TriageResult:
    return_reasons: list[RuleFinding] = field(default_factory=list)
    review_notes: list[ReviewNote] = field(default_factory=list)
    review_warnings: list[ReviewWarning] = field(default_factory=list)


def is_return_eligible(finding: RuleFinding) -> bool:
    """Return True only when all automatic-return safeguards are satisfied."""
    return bool(
        finding.severity == "fail"
        and finding.policy_clause.strip()
        and finding.evidence_source in RETURN_SOURCES
        and finding.evidence_reliability == "verified"
        and not finding.plausible_exception
        and finding.employee_actionable
    )


def _as_warning(finding: RuleFinding) -> ReviewWarning:
    reason = ""
    if finding.severity == "fail" and not is_return_eligible(finding):
        reason = " Automatic return was suppressed by the review-boundary policy."
    return ReviewWarning(
        warning_code=finding.rule_code,
        category="rule_review",
        entity_ref=finding.entity_ref,
        facts={
            "evidence_source": finding.evidence_source,
            "evidence_reliability": finding.evidence_reliability,
            "plausible_exception": finding.plausible_exception,
        },
        evidence_refs=finding.evidence_refs,
        policy_clause=finding.policy_clause,
        explanation=f"{finding.description}{reason}".strip(),
    )


def _as_note(finding: RuleFinding) -> ReviewNote:
    return ReviewNote(
        note_code=finding.rule_code,
        category="rule_note",
        entity_ref=finding.entity_ref,
        facts={"evidence_source": finding.evidence_source},
        evidence_refs=finding.evidence_refs,
        text=finding.description,
    )


def triage_rule_findings(findings: list[RuleFinding]) -> TriageResult:
    """Split rule findings into return reasons and human-review warnings."""
    result = TriageResult()
    for finding in findings:
        if finding.severity == "note":
            result.review_notes.append(_as_note(finding))
        elif is_return_eligible(finding):
            result.return_reasons.append(finding)
        else:
            result.review_warnings.append(_as_warning(finding))
    return result
