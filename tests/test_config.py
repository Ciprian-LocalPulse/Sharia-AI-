import importlib
import os
import unittest
from dataclasses import FrozenInstanceError


class TestAppConfigDefaults(unittest.TestCase):
    def setUp(self):
        # ensure a clean environment for each test, then reload the module
        # so that AppConfig field defaults (evaluated at class-definition
        # time via os.getenv) reflect the current environment.
        self._env_backup = {}
        for key in (
            "SHARIA_AI_GOLD_PRICE_PER_GRAM",
            "SHARIA_AI_SILVER_PRICE_PER_GRAM",
            "SHARIA_AI_CURRENCY",
            "SHARIA_AI_RATE_LIMIT_PER_MINUTE",
        ):
            self._env_backup[key] = os.environ.pop(key, None)

        import sharia_ai.utils.config as config_module

        self.config_module = importlib.reload(config_module)

    def tearDown(self):
        for key, value in self._env_backup.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        import sharia_ai.utils.config as config_module

        importlib.reload(config_module)

    def test_default_gold_price(self):
        self.assertAlmostEqual(self.config_module.config.gold_price_per_gram, 75.0)

    def test_default_silver_price(self):
        self.assertAlmostEqual(self.config_module.config.silver_price_per_gram, 0.95)

    def test_default_currency(self):
        self.assertEqual(self.config_module.config.default_currency, "USD")

    def test_api_title_and_version_are_set(self):
        self.assertEqual(
            self.config_module.config.api_title, "Sharia-AI Compliance Toolkit API"
        )
        self.assertEqual(self.config_module.config.api_version, "0.1.0")

    def test_config_is_frozen(self):
        with self.assertRaises(FrozenInstanceError):
            self.config_module.config.gold_price_per_gram = 100.0


class TestAppConfigFromEnv(unittest.TestCase):
    def setUp(self):
        self._env_backup = {
            "SHARIA_AI_GOLD_PRICE_PER_GRAM": os.environ.get("SHARIA_AI_GOLD_PRICE_PER_GRAM"),
            "SHARIA_AI_SILVER_PRICE_PER_GRAM": os.environ.get(
                "SHARIA_AI_SILVER_PRICE_PER_GRAM"
            ),
            "SHARIA_AI_CURRENCY": os.environ.get("SHARIA_AI_CURRENCY"),
            "SHARIA_AI_RATE_LIMIT_PER_MINUTE": os.environ.get(
                "SHARIA_AI_RATE_LIMIT_PER_MINUTE"
            ),
        }

    def tearDown(self):
        for key, value in self._env_backup.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        import sharia_ai.utils.config as config_module

        importlib.reload(config_module)

    def test_env_overrides_gold_price(self):
        os.environ["SHARIA_AI_GOLD_PRICE_PER_GRAM"] = "80.5"
        import sharia_ai.utils.config as config_module

        reloaded = importlib.reload(config_module)
        self.assertAlmostEqual(reloaded.config.gold_price_per_gram, 80.5)

    def test_env_overrides_currency(self):
        os.environ["SHARIA_AI_CURRENCY"] = "AED"
        import sharia_ai.utils.config as config_module

        reloaded = importlib.reload(config_module)
        self.assertEqual(reloaded.config.default_currency, "AED")

    def test_invalid_env_float_falls_back_to_default(self):
        os.environ["SHARIA_AI_GOLD_PRICE_PER_GRAM"] = "not-a-number"
        import sharia_ai.utils.config as config_module

        reloaded = importlib.reload(config_module)
        self.assertAlmostEqual(reloaded.config.gold_price_per_gram, 75.0)

    def test_env_overrides_rate_limit(self):
        os.environ["SHARIA_AI_RATE_LIMIT_PER_MINUTE"] = "42"
        import sharia_ai.utils.config as config_module

        reloaded = importlib.reload(config_module)
        self.assertEqual(reloaded.config.rate_limit_per_minute, 42)

    def test_invalid_env_int_falls_back_to_default(self):
        os.environ["SHARIA_AI_RATE_LIMIT_PER_MINUTE"] = "not-a-number"
        import sharia_ai.utils.config as config_module

        reloaded = importlib.reload(config_module)
        self.assertEqual(reloaded.config.rate_limit_per_minute, 120)


if __name__ == "__main__":
    unittest.main()
