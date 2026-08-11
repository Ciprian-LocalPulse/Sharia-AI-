"""Human review workflow for Sharia-sensitive findings."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4


class ReviewStatus(str, Enum):
    PENDING = "PENDING"
    IN_REVIEW = "IN_REVIEW"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    ESCALATED = "ESCALATED"


@dataclass(frozen=True)
class ReviewFinding:
    category: str
    evidence: str
    source: str
    rule: str
    confidence: float


@dataclass
class Review:
    finding: ReviewFinding
    reviewer_id: str | None = None
    status: ReviewStatus = ReviewStatus.PENDING
    comments: list[str] = field(default_factory=list)
    review_id: str = field(default_factory=lambda: str(uuid4()))
    created_at_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def transition(self, status: ReviewStatus, reviewer_id: str, comment: str | None = None) -> None:
        if self.status in {ReviewStatus.ACCEPTED, ReviewStatus.REJECTED}:
            raise ValueError("finalized reviews cannot transition")
        self.status = status
        self.reviewer_id = reviewer_id
        if comment:
            self.comments.append(comment)
        self.updated_at_utc = datetime.now(timezone.utc)
