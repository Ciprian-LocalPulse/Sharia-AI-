import json
import unittest

from sharia_ai.pipelines.compliance_pipeline import ShariaCompliancePipeline, asdict_safe
from sharia_ai.screening.equity_screener import CompanyFinancials
from sharia_ai.zakat.zakat_calculator import ZakatAssets, ZakatCalculator


def _compliant_company(name: str = "شركة الاختبار") -> CompanyFinancials:
    return CompanyFinancials(
        name=name,
        sector="other",
        market_cap=1_000_000.0,
        interest_bearing_debt=100_000.0,
        cash_and_interest_bearing_deposits=100_000.0,
        accounts_receivable=100_000.0,
        total_revenue=500_000.0,
        haram_revenue=0.0,
    )


def _non_compliant_company(name: str = "شركة مقامرة") -> CompanyFinancials:
    return CompanyFinancials(
        name=name,
        sector="gambling",
        market_cap=1_000_000.0,
        interest_bearing_debt=100_000.0,
        cash_and_interest_bearing_deposits=100_000.0,
        accounts_receivable=100_000.0,
        total_revenue=500_000.0,
        haram_revenue=0.0,
    )


class TestShariaCompliancePipelineRun(unittest.TestCase):
    def setUp(self):
        self.pipeline = ShariaCompliancePipeline()

    def test_run_with_only_equity_data(self):
        report = self.pipeline.run(company=_compliant_company())
        self.assertEqual(report.company_name, "شركة الاختبار")
        self.assertIsNotNone(report.equity_screening)
        self.assertTrue(report.equity_screening.is_compliant)
        self.assertIsNone(report.contract_screening)
        self.assertIsNone(report.zakat)
        self.assertEqual(report.overall_status, "متوافق (خاضع لمراجعة هيئة الرقابة الشرعية)")

    def test_run_flags_excluded_sector_as_non_compliant(self):
        report = self.pipeline.run(company=_non_compliant_company())
        self.assertFalse(report.equity_screening.is_compliant)
        self.assertEqual(report.overall_status, "غير متوافق — فشل في فرز الأسهم")

    def test_run_with_contracts_no_high_confidence_flags(self):
        contracts = {"عقد نظيف": "هذا عقد بيع عادي بلا أي شروط إشكالية"}
        report = self.pipeline.run(company=_compliant_company(), contracts=contracts)
        self.assertIsNotNone(report.contract_screening)
        self.assertIn("عقد نظيف", report.contract_screening)
        self.assertEqual(report.overall_status, "متوافق (خاضع لمراجعة هيئة الرقابة الشرعية)")

    def test_run_with_contracts_high_confidence_flags_requires_review(self):
        contracts = {"عقد قرض": "هذا القرض بفايده مركبه على المبلغ الاصلي"}
        report = self.pipeline.run(company=_compliant_company(), contracts=contracts)
        self.assertTrue(report.contract_screening["عقد قرض"].has_concerns)
        self.assertEqual(
            report.overall_status, "يتطلب مراجعة — تم اكتشاف بنود تعاقدية عالية الخطورة"
        )

    def test_run_with_zakat_assets_and_calculator(self):
        calculator = ZakatCalculator(gold_price_per_gram=75.0, silver_price_per_gram=0.9)
        pipeline = ShariaCompliancePipeline(zakat_calculator=calculator)
        assets = ZakatAssets(cash_and_equivalents=10_000.0)
        report = pipeline.run(company=_compliant_company(), zakat_assets=assets)
        self.assertIsNotNone(report.zakat)
        self.assertTrue(report.zakat.meets_nisab)
        self.assertAlmostEqual(report.zakat.zakat_due, 250.0)

    def test_run_without_zakat_calculator_ignores_zakat_assets(self):
        # no zakat_calculator was configured on the pipeline
        assets = ZakatAssets(cash_and_equivalents=10_000.0)
        report = self.pipeline.run(company=_compliant_company(), zakat_assets=assets)
        self.assertIsNone(report.zakat)

    def test_generated_at_utc_is_iso_format(self):
        report = self.pipeline.run(company=_compliant_company())
        # should not raise
        from datetime import datetime

        datetime.fromisoformat(report.generated_at_utc)

    def test_empty_contracts_dict_treated_as_no_contracts(self):
        report = self.pipeline.run(company=_compliant_company(), contracts={})
        self.assertIsNone(report.contract_screening)


class TestAsdictSafe(unittest.TestCase):
    def setUp(self):
        self.pipeline = ShariaCompliancePipeline()

    def test_converts_report_to_plain_dict(self):
        report = self.pipeline.run(company=_compliant_company())
        result = asdict_safe(report)
        self.assertIsInstance(result, dict)
        self.assertEqual(result["company_name"], "شركة الاختبار")
        self.assertIsInstance(result["equity_screening"], dict)

    def test_enum_values_converted_to_plain_values(self):
        contracts = {"عقد": "قرض بفايده مركبه"}
        report = self.pipeline.run(company=_compliant_company(), contracts=contracts)
        result = asdict_safe(report)
        flags = result["contract_screening"]["عقد"]["flags"]
        self.assertGreater(len(flags), 0)
        for flag in flags:
            self.assertIsInstance(flag["category"], str)

    def test_result_is_json_serializable(self):
        contracts = {"عقد": "قرض بفايده مركبه"}
        report = self.pipeline.run(company=_compliant_company(), contracts=contracts)
        result = asdict_safe(report)
        # should not raise
        serialized = json.dumps(result, ensure_ascii=False)
        self.assertIsInstance(serialized, str)


class TestCompanyComplianceReportToJson(unittest.TestCase):
    def test_to_json_returns_valid_json_string(self):
        pipeline = ShariaCompliancePipeline()
        report = pipeline.run(company=_compliant_company())
        json_str = report.to_json()
        parsed = json.loads(json_str)
        self.assertEqual(parsed["company_name"], "شركة الاختبار")
        self.assertEqual(parsed["overall_status"], report.overall_status)

    def test_to_json_respects_indent(self):
        pipeline = ShariaCompliancePipeline()
        report = pipeline.run(company=_compliant_company())
        compact_lines = report.to_json(indent=None).count("\n")
        indented_lines = report.to_json(indent=2).count("\n")
        self.assertGreaterEqual(indented_lines, compact_lines)


if __name__ == "__main__":
    unittest.main()
