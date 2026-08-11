"""Configurable Sharia screening methodology primitives."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import Enum


class DecisionState(str, Enum):
    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


@dataclass(frozen=True)
class Methodology:
    identifier: str
    version: str
    effective_date: date
    source_reference: str
    thresholds: dict[str, float]
    explanation: str

    def threshold_for(self, rule: str) -> float:
        try:
            return self.thresholds[rule]
        except KeyError as exc:
            raise KeyError(f"methodology {self.identifier} has no threshold for {rule}") from exc


@dataclass(frozen=True)
class RuleEvaluation:
    methodology: str
    methodology_version: str
    rule: str
    value: float | None
    threshold: float | None
    decision: DecisionState
    evidence: str
    confidence: float
    data_quality: str
    timestamp_utc: datetime

    @classmethod
    def from_threshold(
        cls,
        methodology: Methodology,
        rule: str,
        value: float | None,
        evidence: str,
        confidence: float = 1.0,
        data_quality: str = "HIGH",
    ) -> RuleEvaluation:
        threshold = methodology.threshold_for(rule)
        if value is None:
            decision = DecisionState.INSUFFICIENT_DATA
        elif value <= threshold:
            decision = DecisionState.COMPLIANT
        else:
            decision = DecisionState.NON_COMPLIANT
        return cls(
            methodology=methodology.identifier,
            methodology_version=methodology.version,
            rule=rule,
            value=value,
            threshold=threshold,
            decision=decision,
            evidence=evidence,
            confidence=confidence,
            data_quality=data_quality,
            timestamp_utc=datetime.now(timezone.utc),
        )
