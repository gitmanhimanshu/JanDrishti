"""
Credibility scoring (spec 31).

The rule this file exists to enforce: *support is a signal, not proof*. Ranking
experiences purely by support would turn a platform for professional judgement
into a popularity contest, so support is capped at a minority of the score and
sits alongside verification, evidence, specificity and discussion.

Pure functions, no ORM -- every weight here is directly unit-testable.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# Weights sum to 1.0. Support is deliberately the smallest large component.
W_VERIFICATION = 0.25
W_RELEVANCE = 0.20
W_EVIDENCE = 0.15
W_SPECIFICITY = 0.20
W_SUPPORT = 0.12
W_DISCUSSION = 0.08


@dataclass(frozen=True, slots=True)
class CredibilityInputs:
    author_verified: bool
    author_category: str
    domain_matches_category: bool
    years_of_experience: int
    evidence_count: int
    linked_problem_count: int
    support_count: int
    comment_count: int
    has_root_cause: bool
    has_implementation: bool
    has_expected_impact: bool
    has_cost_estimate: bool


def _saturate(value: float, midpoint: float) -> float:
    """Diminishing returns in [0, 1). Twice the input is never twice the score."""
    if value <= 0:
        return 0.0
    return value / (value + midpoint)


def verification_component(inputs: CredibilityInputs) -> float:
    """A verified professional claim raises the floor, and never to certainty."""
    if not inputs.author_verified:
        return 0.15
    base = 0.75
    if inputs.author_category in {
        "GOVERNMENT_EMPLOYEE",
        "RETIRED_GOVERNMENT_EMPLOYEE",
        "DOMAIN_EXPERT",
    }:
        base = 0.9
    experience_bonus = min(inputs.years_of_experience / 40.0, 1.0) * 0.1
    return min(base + experience_bonus, 1.0)


def specificity_component(inputs: CredibilityInputs) -> float:
    """Actionability. A recommendation without an implementation path is an opinion."""
    filled = sum(
        (
            inputs.has_root_cause,
            inputs.has_implementation,
            inputs.has_expected_impact,
            inputs.has_cost_estimate,
        )
    )
    return filled / 4.0


def compute_credibility(inputs: CredibilityInputs) -> float:
    """Blended score in [0, 100]."""
    score = (
        W_VERIFICATION * verification_component(inputs)
        + W_RELEVANCE * (1.0 if inputs.domain_matches_category else 0.35)
        + W_EVIDENCE * _saturate(inputs.evidence_count, 3.0)
        + W_SPECIFICITY * specificity_component(inputs)
        + W_SUPPORT * _saturate(math.log1p(max(inputs.support_count, 0)), 3.0)
        + W_DISCUSSION * _saturate(inputs.comment_count, 8.0)
    )
    # Being tied to real reported problems is corroboration, so it lifts the
    # score modestly rather than being a weight of its own.
    relevance_lift = 1.0 + min(inputs.linked_problem_count, 5) * 0.02
    return round(min(score * relevance_lift, 1.0) * 100, 2)
