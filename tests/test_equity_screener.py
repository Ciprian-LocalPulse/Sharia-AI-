import unittest

from sharia_ai.screening.equity_screener import CompanyFinancials, EquityScreener


class TestEquityScreener(unittest.TestCase):
    def setUp(self):
        self.screener = EquityScreener()

    def test_compliant_company_passes_all_checks(self):
        company = CompanyFinancials(
            name="TechCo",
            sector="technology",
            market_cap=1_000_000,
            interest_bearing_debt=200_000,   # 20% < 33%
            cash_and_interest_bearing_deposits=100_000,  # 10% < 33%
            accounts_receivable=300_000,     # 30% < 49%
            total_revenue=500_000,
            haram_revenue=0,
        )
        result = self.screener.screen(company)
        self.assertTrue(result.is_compliant)
        self.assertTrue(all(c.passed for c in result.checks))

    def test_excluded_sector_fails(self):
        company = CompanyFinancials(
            name="ConventionalBank",
            sector="conventional_banking",
            market_cap=1_000_000,
            interest_bearing_debt=0,
            cash_and_interest_bearing_deposits=0,
            accounts_receivable=0,
            total_revenue=500_000,
        )
        result = self.screener.screen(company)
        self.assertFalse(result.is_compliant)
        sector_check = next(c for c in result.checks if c.rule == "النشاط القطاعي")
        self.assertFalse(sector_check.passed)

    def test_excessive_debt_ratio_fails(self):
        company = CompanyFinancials(
            name="LeveragedCo",
            sector="retail",
            market_cap=1_000_000,
            interest_bearing_debt=500_000,  # 50% > 33%
            cash_and_interest_bearing_deposits=0,
            accounts_receivable=0,
            total_revenue=500_000,
        )
        result = self.screener.screen(company)
        self.assertFalse(result.is_compliant)

    def test_haram_revenue_ratio_triggers_purification(self):
        company = CompanyFinancials(
            name="MixedCo",
            sector="retail",
            market_cap=1_000_000,
            interest_bearing_debt=0,
            cash_and_interest_bearing_deposits=0,
            accounts_receivable=0,
            total_revenue=1_000_000,
            haram_revenue=10_000,  # 1% < 5% threshold -> still compliant but needs purification
        )
        result = self.screener.screen(company)
        self.assertTrue(result.is_compliant)
        self.assertAlmostEqual(result.purification_ratio, 0.01)

    def test_zero_market_cap_does_not_crash(self):
        company = CompanyFinancials(
            name="ZeroCap",
            sector="retail",
            market_cap=0,
            interest_bearing_debt=100,
            cash_and_interest_bearing_deposits=0,
            accounts_receivable=0,
            total_revenue=100,
        )
        result = self.screener.screen(company)
        # يجب ألا يُطلق استثناء القسمة على صفر
        self.assertIsNotNone(result)


if __name__ == "__main__":
    unittest.main()
