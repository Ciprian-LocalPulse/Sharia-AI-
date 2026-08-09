import unittest

from sharia_ai.zakat.zakat_calculator import ZakatAssets, ZakatCalculator


class TestZakatCalculator(unittest.TestCase):
    def setUp(self):
        # Preturi ipotetice pentru teste deterministe
        self.calc = ZakatCalculator(gold_price_per_gram=75.0, silver_price_per_gram=0.9)

    def test_below_nisab_owes_nothing(self):
        assets = ZakatAssets(cash_and_equivalents=100.0)
        result = self.calc.calculate(assets)
        self.assertFalse(result.meets_nisab)
        self.assertEqual(result.zakat_due, 0.0)

    def test_above_nisab_calculates_2_5_percent(self):
        assets = ZakatAssets(cash_and_equivalents=10_000.0)
        result = self.calc.calculate(assets)
        self.assertTrue(result.meets_nisab)
        self.assertAlmostEqual(result.zakat_due, 250.0)  # 2.5% of 10000

    def test_liabilities_are_deducted(self):
        assets = ZakatAssets(cash_and_equivalents=10_000.0, short_term_liabilities=4_000.0)
        result = self.calc.calculate(assets)
        self.assertAlmostEqual(result.net_zakatable_wealth, 6_000.0)
        self.assertAlmostEqual(result.zakat_due, 150.0)

    def test_uses_lower_nisab_by_default(self):
        # argint: 595g * 0.9 = 535.5 ; aur: 85g * 75 = 6375 -> argintul e mai mic
        nisab_value, metal = self.calc._nisab_threshold()
        self.assertEqual(metal, "argint")
        self.assertAlmostEqual(nisab_value, 535.5)

    def test_negative_net_wealth_clamped_to_zero(self):
        assets = ZakatAssets(cash_and_equivalents=100.0, short_term_liabilities=500.0)
        result = self.calc.calculate(assets)
        self.assertEqual(result.net_zakatable_wealth, 0.0)
        self.assertFalse(result.meets_nisab)


if __name__ == "__main__":
    unittest.main()
