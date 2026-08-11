from datetime import date, datetime, timedelta, timezone

import pytest

from sharia_ai.data import FinancialMetric as ExportedMetric
from sharia_ai.data.models import DataQuality, FinancialMetric, FinancialProvenance, FreshnessPolicy
from sharia_ai.data.providers import FinancialDataProvider
from sharia_ai.data.providers import FinancialDataProvider as ExportedProvider
from sharia_ai.governance.review import Review, ReviewFinding, ReviewStatus
from sharia_ai.policies.methodology import DecisionState, Methodology, RuleEvaluation


def _provenance(**overrides):
    payload = {
        "source": "issuer annual report",
        "source_url": "https://example.test/report",
        "reporting_period": "FY2025",
        "currency": "USD",
        "retrieved_at_utc": datetime.now(timezone.utc),
        "normalization_method": "reported_as_is",
    }
    payload.update(overrides)
    return FinancialProvenance(**payload)


def test_financial_metric_requires_complete_provenance():
    metric = FinancialMetric("interest_bearing_debt", 100.0, _provenance())
    assert metric.provenance.source == "issuer annual report"

    with pytest.raises(ValueError, match="financial provenance missing"):
        FinancialMetric("market_cap", 10.0, _provenance(source=""))

    with pytest.raises(ValueError, match="timezone-aware"):
        FinancialMetric(
            "market_cap",
            10.0,
            _provenance(retrieved_at_utc=now_naive()),
        )

    with pytest.raises(ValueError, match="non-negative"):
        FinancialMetric("market_cap", -1.0, _provenance())


def test_freshness_policy_classifies_age():
    now = datetime.now(timezone.utc)
    policy = FreshnessPolicy(max_age_days=30)
    assert policy.assess(now - timedelta(days=10), now=now) is DataQuality.HIGH
    assert policy.assess(now - timedelta(days=45), now=now) is DataQuality.MEDIUM
    assert policy.assess(now - timedelta(days=90), now=now) is DataQuality.LOW
    assert policy.assess(now_naive(), now=now) is DataQuality.INSUFFICIENT


def test_methodology_threshold_evaluation_has_evidence_and_state():
    methodology = Methodology(
        identifier="AAOIFI",
        version="2025.1",
        effective_date=date(2025, 1, 1),
        source_reference="AAOIFI screening methodology",
        thresholds={"debt_to_market_cap": 0.33},
        explanation="Debt ratio must stay below the configured threshold.",
    )

    passed = RuleEvaluation.from_threshold(
        methodology, "debt_to_market_cap", 0.25, evidence="sourced metric ratio"
    )
    failed = RuleEvaluation.from_threshold(
        methodology, "debt_to_market_cap", 0.40, evidence="sourced metric ratio"
    )
    missing = RuleEvaluation.from_threshold(
        methodology, "debt_to_market_cap", None, evidence="provider returned no value"
    )

    assert passed.decision is DecisionState.COMPLIANT
    assert failed.decision is DecisionState.NON_COMPLIANT
    assert missing.decision is DecisionState.INSUFFICIENT_DATA
    assert failed.evidence == "sourced metric ratio"

    with pytest.raises(KeyError, match="no threshold"):
        methodology.threshold_for("unknown_rule")


def test_financial_data_provider_contract_returns_provenanced_metric():
    class StaticProvider(FinancialDataProvider):
        def get_metric(self, company_id: str, metric_name: str) -> FinancialMetric:
            assert company_id == "issuer-1"
            return FinancialMetric(metric_name, 12.0, _provenance())

    metric = StaticProvider().get_metric("issuer-1", "cash")
    assert metric.name == "cash"
    assert metric.value == 12.0
    assert ExportedMetric is FinancialMetric
    assert ExportedProvider is FinancialDataProvider

    with pytest.raises(NotImplementedError):
        super(StaticProvider, StaticProvider()).get_metric("issuer-1", "cash")


def now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def test_human_review_workflow_blocks_finalized_transitions():
    finding = ReviewFinding(
        category="RIBA",
        evidence="interest clause detected",
        source="contract",
        rule="contract.riba.lexical",
        confidence=0.92,
    )
    review = Review(finding=finding)
    review.transition(ReviewStatus.IN_REVIEW, reviewer_id="analyst-1", comment="triaged")
    review.transition(ReviewStatus.ACCEPTED, reviewer_id="sharia-1", comment="confirmed")

    assert review.status is ReviewStatus.ACCEPTED
    assert review.comments == ["triaged", "confirmed"]

    with pytest.raises(ValueError, match="finalized"):
        review.transition(ReviewStatus.REJECTED, reviewer_id="sharia-2")
