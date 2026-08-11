"""Typed financial data models.

No financial metric should enter screening without source, period, currency,
retrieval timestamp, and normalization metadata.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum


class DataQuality(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass(frozen=True)
class FinancialProvenance:
    source: str
    source_url: str | None
    reporting_period: str
    currency: str
    retrieved_at_utc: datetime
    normalization_method: str

    def validate(self) -> None:
        missing = [
            name
            for name, value in {
                "source": self.source,
                "reporting_period": self.reporting_period,
                "currency": self.currency,
                "normalization_method": self.normalization_method,
            }.items()
            if not value
        ]
        if missing:
            raise ValueError(f"financial provenance missing: {', '.join(missing)}")
        if self.retrieved_at_utc.tzinfo is None:
            raise ValueError("retrieved_at_utc must be timezone-aware")


@dataclass(frozen=True)
class FreshnessPolicy:
    max_age_days: int = 120

    def assess(self, retrieved_at_utc: datetime, now: datetime | None = None) -> DataQuality:
        if retrieved_at_utc.tzinfo is None:
            return DataQuality.INSUFFICIENT
        now = now or datetime.now(timezone.utc)
        age = now - retrieved_at_utc
        if age <= timedelta(days=self.max_age_days):
            return DataQuality.HIGH
        if age <= timedelta(days=self.max_age_days * 2):
            return DataQuality.MEDIUM
        return DataQuality.LOW


@dataclass(frozen=True)
class FinancialMetric:
    name: str
    value: float
    provenance: FinancialProvenance

    def __post_init__(self) -> None:
        if self.value < 0:
            raise ValueError("financial metric values must be non-negative")
        self.provenance.validate()
