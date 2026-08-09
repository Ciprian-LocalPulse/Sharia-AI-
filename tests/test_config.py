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
        self.assertEqual(self.config_module.config.api_version, "0.2.0")

    def test_config_is_frozen(self):
        with self.assertRaises(FrozenInstanceError):
            self.config_module.config.gold_price_per_gram = 100.0

    def test_require_api_key_defaults_true(self):
        self.assertTrue(self.config_module.config.require_api_key)

    def test_api_keys_default_empty(self):
        self.assertEqual(self.config_module.config.api_keys, frozenset())

    def test_cors_origins_default_empty(self):
        self.assertEqual(self.config_module.config.cors_allowed_origins, [])

    def test_rate_limit_defaults(self):
        self.assertEqual(self.config_module.config.rate_limit_requests, 60)
        self.assertEqual(self.config_module.config.rate_limit_window_seconds, 60)

    def test_max_contract_chars_default(self):
        self.assertEqual(self.config_module.config.max_contract_text_chars, 50_000)

    def test_audit_defaults(self):
        self.assertTrue(self.config_module.config.audit_enabled)
        self.assertEqual(
            self.config_module.config.audit_db_path, "sharia_ai_audit.sqlite3"
        )


class TestAppConfigFromEnv(unittest.TestCase):
    def setUp(self):
        self._env_backup = {
            "SHARIA_AI_GOLD_PRICE_PER_GRAM": os.environ.get("SHARIA_AI_GOLD_PRICE_PER_GRAM"),
            "SHARIA_AI_SILVER_PRICE_PER_GRAM": os.environ.get(
                "SHARIA_AI_SILVER_PRICE_PER_GRAM"
            ),
            "SHARIA_AI_CURRENCY": os.environ.get("SHARIA_AI_CURRENCY"),
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


class TestAppConfigSecurityFieldsFromEnv(unittest.TestCase):
    def setUp(self):
        self._env_keys = (
            "SHARIA_AI_API_KEYS",
            "SHARIA_AI_REQUIRE_API_KEY",
            "SHARIA_AI_CORS_ORIGINS",
            "SHARIA_AI_RATE_LIMIT_REQUESTS",
            "SHARIA_AI_RATE_LIMIT_WINDOW_SECONDS",
            "SHARIA_AI_MAX_CONTRACT_CHARS",
            "SHARIA_AI_AUDIT_ENABLED",
        )
        self._env_backup = {key: os.environ.get(key) for key in self._env_keys}

    def tearDown(self):
        for key, value in self._env_backup.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        import sharia_ai.utils.config as config_module

        importlib.reload(config_module)

    def _reload(self):
        import sharia_ai.utils.config as config_module

        return importlib.reload(config_module)

    def test_api_keys_parsed_as_comma_separated_set(self):
        os.environ["SHARIA_AI_API_KEYS"] = "key-one, key-two,key-three"
        reloaded = self._reload()
        self.assertEqual(reloaded.config.api_keys, {"key-one", "key-two", "key-three"})

    def test_require_api_key_false_via_env(self):
        os.environ["SHARIA_AI_REQUIRE_API_KEY"] = "false"
        reloaded = self._reload()
        self.assertFalse(reloaded.config.require_api_key)

    def test_cors_origins_parsed_as_list(self):
        os.environ["SHARIA_AI_CORS_ORIGINS"] = "https://a.com, https://b.com"
        reloaded = self._reload()
        self.assertEqual(reloaded.config.cors_allowed_origins, ["https://a.com", "https://b.com"])

    def test_rate_limit_parsed_as_int(self):
        os.environ["SHARIA_AI_RATE_LIMIT_REQUESTS"] = "10"
        os.environ["SHARIA_AI_RATE_LIMIT_WINDOW_SECONDS"] = "5"
        reloaded = self._reload()
        self.assertEqual(reloaded.config.rate_limit_requests, 10)
        self.assertEqual(reloaded.config.rate_limit_window_seconds, 5)

    def test_invalid_int_env_falls_back_to_default(self):
        os.environ["SHARIA_AI_RATE_LIMIT_REQUESTS"] = "not-an-int"
        reloaded = self._reload()
        self.assertEqual(reloaded.config.rate_limit_requests, 60)

    def test_audit_enabled_false_via_env(self):
        os.environ["SHARIA_AI_AUDIT_ENABLED"] = "0"
        reloaded = self._reload()
        self.assertFalse(reloaded.config.audit_enabled)


if __name__ == "__main__":
    unittest.main()
