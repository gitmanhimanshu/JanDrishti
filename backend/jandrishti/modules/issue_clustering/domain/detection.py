"""
Duplicate detection scoring.

Pure functions over plain data: no ORM, no I/O. That keeps the tuning of the
thresholds honest, because the whole thing can be exercised in tests with a
handful of dictionaries.

The scoring blends the signals section 19 lists -- proximity, category, title
similarity and recency. Deliberately *not* included as an automatic decider:
anything about whether an allegation is true. Clustering answers "is this the
same pothole", never "is this claim correct".
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from jandrishti.shared.domain.value_objects import GeoPoint
from jandrishti.shared.infrastructure.text import similarity

# Above this, merge automatically. Between the two, propose and ask a human.
# Below the lower bound, do nothing.
AUTO_MERGE_THRESHOLD = 0.82
REVIEW_THRESHOLD = 0.62

# Below this much textual overlap, two reports are not about the same thing
# however close together they were filed. See the damping rule in
# `score_candidate`.
MIN_TEXT_OVERLAP = 0.30

W_DISTANCE = 0.45
W_TEXT = 0.35
W_CATEGORY = 0.15
W_RECENCY = 0.05


@dataclass(frozen=True, slots=True)
class Candidate:
    problem_id: int
    title: str
    description: str
    category_id: int | None
    latitude: float | None
    longitude: float | None
    created_at: datetime
    cluster_id: int | None = None


@dataclass(frozen=True, slots=True)
class MatchScore:
    candidate: Candidate
    score: float
    distance_metres: float | None
    title_similarity: float

    @property
    def should_auto_merge(self) -> bool:
        return self.score >= AUTO_MERGE_THRESHOLD

    @property
    def needs_review(self) -> bool:
        return REVIEW_THRESHOLD <= self.score < AUTO_MERGE_THRESHOLD


def distance_component(distance_m: float | None, radius_m: float) -> float:
    """1.0 on top of each other, falling to 0 at the radius.

    None means one of the reports has no coordinates, which is common for a
    report filed from a desktop. That is not evidence of *difference*, so it
    scores a neutral middle value rather than zero.
    """
    if distance_m is None:
        return 0.5
    if distance_m >= radius_m:
        return 0.0
    return 1.0 - (distance_m / radius_m)


def recency_component(a: datetime, b: datetime, window_days: int) -> float:
    """Reports close in time are likelier to be the same event."""
    gap_days = abs((a - b).days)
    if gap_days >= window_days:
        return 0.0
    return 1.0 - (gap_days / window_days)


def score_candidate(
    *,
    new_title: str,
    new_description: str,
    new_category_id: int | None,
    new_point: GeoPoint | None,
    new_created_at: datetime,
    candidate: Candidate,
    radius_metres: float,
    window_days: int,
) -> MatchScore:
    distance_m: float | None = None
    if new_point and candidate.latitude is not None and candidate.longitude is not None:
        distance_m = new_point.distance_m(GeoPoint(candidate.latitude, candidate.longitude))

    title_sim = similarity(new_title, candidate.title)
    # The description is a weaker signal than the title -- people write very
    # different prose about the same pothole -- so it contributes at a discount.
    body_sim = similarity(new_description[:500], candidate.description[:500])
    text_component = max(title_sim, 0.6 * title_sim + 0.4 * body_sim)

    category_component = (
        1.0 if new_category_id and new_category_id == candidate.category_id else 0.0
    )

    score = (
        W_DISTANCE * distance_component(distance_m, radius_metres)
        + W_TEXT * text_component
        + W_CATEGORY * category_component
        + W_RECENCY * recency_component(new_created_at, candidate.created_at, window_days)
    )

    # Two guards against the failure modes that matter most here.

    # Far apart is not the same pothole, however similarly worded. Without
    # this, "streetlight not working" in two different cities merges.
    if distance_m is not None and distance_m > radius_metres * 2:
        score *= 0.3

    # Same place is not the same problem. Distance and category together carry
    # 0.60 of the weight, which would otherwise be enough to merge a garbage
    # complaint into a pothole report filed from the same street corner. A
    # duplicate has to actually be *about* the same thing, so a report with
    # almost no textual overlap is damped below the review threshold.
    if text_component < MIN_TEXT_OVERLAP:
        score *= 0.5

    return MatchScore(
        candidate=candidate,
        score=round(min(score, 1.0), 4),
        distance_metres=distance_m,
        title_similarity=title_sim,
    )


def best_match(scores: list[MatchScore]) -> MatchScore | None:
    return max(scores, key=lambda s: s.score) if scores else None
