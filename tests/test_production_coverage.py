import unittest
from typing import Any
from unittest.mock import patch

from fastapi import HTTPException

from sharia_ai.api.main import CompanyFinancialsIn, ComplianceReportIn, compliance_report
from sharia_ai.nlp.riba_detector import (
    ConcernCategory,
    DetectionReport,
    Flag,
    HybridContractScreener,
    LexicalRibaDetector,
)
from sharia_ai.pipelines.compliance_pipeline import ShariaCompliancePipeline, asdict_safe
from sharia_ai.screening.equity_screener import CompanyFinancials, EquityScreener
from sharia_ai.zakat.zakat_calculator import ZakatAssets, ZakatCalculator


class FakeClassifier:
    def predict(self, sentence: str) -> list[tuple[ConcernCategory, float]]:
        if sentence:
            return [(ConcernCategory.UNKNOWN_CLAUSE, 0.42)]
        return []


def _company(**overrides: Any) -> CompanyFinancials:
    payload: dict[str, Any] = {
        "name": "شركة الاختبار",
        "sector": "retail",
        "market_cap": 1_000_000.0,
        "interest_bearing_debt": 100_000.0,
        "cash_and_interest_bearing_deposits": 100_000.0,
        "accounts_receivable": 100_000.0,
        "total_revenue": 500_000.0,
        "haram_revenue": 0.0,
    }
    payload.update(overrides)
    return CompanyFinancials(**payload)


class TestSummariesAndBranches(unittest.TestCase):
    def test_detection_report_summary_empty_short_and_long_flags(self):
        empty = DetectionReport(text_length_chars=0, flags=[])
        self.assertIn("فرز", empty.summary())

        short = DetectionReport(
            text_length_chars=10,
            flags=[Flag("قرض بفائدة", ConcernCategory.RIBA, "فائدة", 0.9)],
        )
        self.assertIn("RIBA", short.summary())

        long_sentence = "قرض بفائدة " * 20
        long = DetectionReport(
            text_length_chars=len(long_sentence),
            flags=[Flag(long_sentence, ConcernCategory.RIBA, "فائدة", 0.9)],
        )
        self.assertIn("...", long.summary())

    def test_equity_summary_and_batch(self):
        screener = EquityScreener()
        compliant = _company(haram_revenue=10_000.0)
        non_compliant = _company(sector="gambling")

        summary = screener.screen(compliant).summary()
        self.assertIn("2.0000%", summary)

        failed_summary = screener.screen(non_compliant).summary()
        self.assertIn("غير متوافق", failed_summary)

        batch = screener.screen_batch([compliant, non_compliant])
        self.assertEqual([r.is_compliant for r in batch], [True, False])

    def test_lexical_detector_custom_empty_term_and_no_sequence_match(self):
        detector = LexicalRibaDetector(
            {
                "": (ConcernCategory.RIBA, 1.0),
                "قرض فائدة": (ConcernCategory.RIBA, 0.8),
            }
        )
        report = detector.analyze("هذا قرض عادي بدون الكلمة الثانية")
        self.assertFalse(report.has_concerns)

    def test_hybrid_screener_adds_ml_flags(self):
        screener = HybridContractScreener(ml_classifier=FakeClassifier())
        report = screener.analyze("بند يحتاج مراجعة.")
        self.assertTrue(report.has_concerns)
        self.assertIn(ConcernCategory.UNKNOWN_CLAUSE, report.categories_found)

    def test_pipeline_handles_none_inside_contract_mapping(self):
        pipeline = ShariaCompliancePipeline()
        report = pipeline.run(company=_company(), contracts={"فارغ": ""})
        self.assertEqual(report.overall_status, "متوافق (خاضع لمراجعة هيئة الرقابة الشرعية)")

    def test_asdict_safe_converts_direct_enum_value(self):
        self.assertEqual(asdict_safe(ConcernCategory.RIBA), "riba")

    def test_zakat_summary_and_nisab_branches(self):
        lower_gold = ZakatCalculator(
            gold_price_per_gram=0.1,
            silver_price_per_gram=1.0,
        )
        value, metal = lower_gold._nisab_threshold()
        self.assertEqual((value, metal), (8.5, "ذهب"))

        gold_only = ZakatCalculator(
            gold_price_per_gram=75.0,
            silver_price_per_gram=0.1,
            use_lower_nisab=False,
        )
        value, metal = gold_only._nisab_threshold()
        self.assertEqual((value, metal), (6375.0, "ذهب"))

        due = gold_only.calculate(ZakatAssets(cash_and_equivalents=10_000.0))
        self.assertIn("2.5%", due.summary(currency="AED"))

        not_due = gold_only.calculate(ZakatAssets(cash_and_equivalents=10.0))
        self.assertIn("0", not_due.summary())


class TestApiDefensiveBranch(unittest.TestCase):
    def test_compliance_report_converts_company_type_error_to_http_422(self):
        payload = ComplianceReportIn(
            company=CompanyFinancialsIn(
                name="شركة الاختبار",
                sector="other",
                market_cap=1_000_000.0,
                interest_bearing_debt=100_000.0,
                cash_and_interest_bearing_deposits=100_000.0,
                accounts_receivable=100_000.0,
                total_revenue=500_000.0,
            )
        )

        fake_request = MagicMock()
        fake_request.headers = {}
        fake_request.client.host = "127.0.0.1"

        with (
            patch("sharia_ai.api.main.CompanyFinancials", side_effect=TypeError("bad")),
            self.assertRaises(HTTPException) as raised,
        ):
            compliance_report(payload, fake_request, api_key="test")

        self.assertEqual(raised.exception.status_code, 422)


if __name__ == "__main__":
    unittest.main()
