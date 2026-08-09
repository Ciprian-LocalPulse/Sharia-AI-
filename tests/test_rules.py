import unittest

from sharia_ai.screening.rules import (
    EXCLUDED_SECTORS,
    NISAB_GOLD_GRAMS,
    NISAB_SILVER_GRAMS,
    ZAKAT_RATE,
    ScreeningThresholds,
)


class TestScreeningThresholds(unittest.TestCase):
    def test_default_values(self):
        thresholds = ScreeningThresholds()
        self.assertAlmostEqual(thresholds.max_haram_revenue_ratio, 0.05)
        self.assertAlmostEqual(thresholds.max_debt_to_market_cap, 0.33)
        self.assertAlmostEqual(thresholds.max_cash_interest_to_market_cap, 0.33)
        self.assertAlmostEqual(thresholds.max_receivables_to_market_cap, 0.49)
        self.assertAlmostEqual(thresholds.purification_threshold, 0.05)

    def test_is_frozen_dataclass(self):
        thresholds = ScreeningThresholds()
        with self.assertRaises(Exception):
            thresholds.max_debt_to_market_cap = 0.5

    def test_can_override_thresholds(self):
        thresholds = ScreeningThresholds(max_debt_to_market_cap=0.4)
        self.assertAlmostEqual(thresholds.max_debt_to_market_cap, 0.4)
        # unrelated fields keep their defaults
        self.assertAlmostEqual(thresholds.max_haram_revenue_ratio, 0.05)


class TestExcludedSectors(unittest.TestCase):
    def test_contains_expected_keys(self):
        expected_keys = {
            "alcohol",
            "gambling",
            "conventional_banking",
            "conventional_insurance",
            "pork",
            "adult_entertainment",
            "tobacco",
            "weapons_controversial",
            "media_immoral",
        }
        self.assertEqual(set(EXCLUDED_SECTORS.keys()), expected_keys)

    def test_all_values_are_non_empty_strings(self):
        for key, description in EXCLUDED_SECTORS.items():
            self.assertIsInstance(description, str)
            self.assertTrue(description.strip(), msg=f"empty description for {key}")

    def test_other_is_not_excluded(self):
        self.assertNotIn("other", EXCLUDED_SECTORS)


class TestNisabAndZakatConstants(unittest.TestCase):
    def test_nisab_gold_grams(self):
        self.assertAlmostEqual(NISAB_GOLD_GRAMS, 85.0)

    def test_nisab_silver_grams(self):
        self.assertAlmostEqual(NISAB_SILVER_GRAMS, 595.0)

    def test_zakat_rate(self):
        self.assertAlmostEqual(ZAKAT_RATE, 0.025)


if __name__ == "__main__":
    unittest.main()
