import os
import tempfile
import unittest

from tests._reload_utils import reload_chain, restore_env, snapshot_env

try:
    from fastapi.testclient import TestClient

    _FASTAPI_AVAILABLE = True
except ImportError:
    _FASTAPI_AVAILABLE = False

_TEST_API_KEY = "test-key-abc123"


def _company_payload(**overrides):
    payload = {
        "name": "شركة الاختبار",
        "sector": "other",
        "market_cap": 1_000_000.0,
        "interest_bearing_debt": 100_000.0,
        "cash_and_interest_bearing_deposits": 100_000.0,
        "accounts_receivable": 100_000.0,
        "total_revenue": 500_000.0,
        "haram_revenue": 0.0,
    }
    payload.update(overrides)
    return payload


@unittest.skipUnless(
    _FASTAPI_AVAILABLE, "fastapi/httpx not installed — install requirements.txt to run API tests"
)
class _AuthenticatedApiTestCase(unittest.TestCase):
    """قاعدة مشتركة: تهيّئ بيئة اختبار بمفتاح API صالح، معدّل طلبات
    مرتفع (لتفادي تداخل بين الاختبارات)، وقاعدة تدقيق مؤقّتة."""

    def setUp(self):
        self._env_snapshot = snapshot_env()
        _fd, self._tmp_db_path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(_fd)

        os.environ["SHARIA_AI_API_KEYS"] = _TEST_API_KEY
        os.environ["SHARIA_AI_REQUIRE_API_KEY"] = "true"
        os.environ["SHARIA_AI_RATE_LIMIT_REQUESTS"] = "1000"
        os.environ["SHARIA_AI_RATE_LIMIT_WINDOW_SECONDS"] = "60"
        os.environ["SHARIA_AI_AUDIT_DB_PATH"] = self._tmp_db_path
        os.environ["SHARIA_AI_AUDIT_ENABLED"] = "true"

        self.main_module = reload_chain()
        self.client = TestClient(self.main_module.app)
        self.auth_headers = {"X-API-Key": _TEST_API_KEY}

    def tearDown(self):
        restore_env(self._env_snapshot)
        reload_chain()
        try:
            os.unlink(self._tmp_db_path)
        except OSError:
            pass


class TestHealthEndpoint(_AuthenticatedApiTestCase):
    def test_health_returns_ok_without_auth(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "ok")
        self.assertIn("service", body)
        self.assertIn("version", body)

    def test_health_response_includes_request_id_header(self):
        response = self.client.get("/health")
        self.assertIn("X-Request-ID", response.headers)


class TestAuthenticationEnforcement(_AuthenticatedApiTestCase):
    def test_missing_api_key_returns_401(self):
        response = self.client.post("/v1/screening/equity", json=_company_payload())
        self.assertEqual(response.status_code, 401)

    def test_wrong_api_key_returns_401(self):
        response = self.client.post(
            "/v1/screening/equity",
            json=_company_payload(),
            headers={"X-API-Key": "wrong-key"},
        )
        self.assertEqual(response.status_code, 401)

    def test_correct_api_key_returns_200(self):
        response = self.client.post(
            "/v1/screening/equity", json=_company_payload(), headers=self.auth_headers
        )
        self.assertEqual(response.status_code, 200)


class TestScreenEquityEndpoint(_AuthenticatedApiTestCase):
    def test_compliant_company_returns_true(self):
        response = self.client.post(
            "/v1/screening/equity", json=_company_payload(), headers=self.auth_headers
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["is_compliant"])
        self.assertEqual(body["company"], "شركة الاختبار")
        self.assertIsInstance(body["checks"], list)
        self.assertEqual(len(body["checks"]), 5)

    def test_excluded_sector_returns_false(self):
        response = self.client.post(
            "/v1/screening/equity",
            json=_company_payload(sector="gambling"),
            headers=self.auth_headers,
        )
        body = response.json()
        self.assertFalse(body["is_compliant"])

    def test_missing_required_field_returns_422(self):
        payload = _company_payload()
        del payload["market_cap"]
        response = self.client.post(
            "/v1/screening/equity", json=payload, headers=self.auth_headers
        )
        self.assertEqual(response.status_code, 422)

    def test_zero_market_cap_rejected_by_validation(self):
        response = self.client.post(
            "/v1/screening/equity",
            json=_company_payload(market_cap=0.0),
            headers=self.auth_headers,
        )
        self.assertEqual(response.status_code, 422)

    def test_negative_debt_rejected_by_validation(self):
        response = self.client.post(
            "/v1/screening/equity",
            json=_company_payload(interest_bearing_debt=-1.0),
            headers=self.auth_headers,
        )
        self.assertEqual(response.status_code, 422)

    def test_screening_writes_audit_entry(self):
        self.client.post(
            "/v1/screening/equity", json=_company_payload(), headers=self.auth_headers
        )
        audit_response = self.client.get("/v1/audit/recent", headers=self.auth_headers)
        self.assertEqual(audit_response.status_code, 200)
        body = audit_response.json()
        self.assertGreaterEqual(body["total_entries"], 1)
        self.assertEqual(body["entries"][0]["event_type"], "equity_screening")


class TestScreenContractEndpoint(_AuthenticatedApiTestCase):
    def test_clean_contract_has_no_concerns(self):
        response = self.client.post(
            "/v1/screening/contract",
            json={"text": "هذا عقد بيع عادي بلا أي شروط"},
            headers=self.auth_headers,
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertFalse(body["has_concerns"])
        self.assertEqual(body["flags"], [])

    def test_riba_contract_flags_riba_category(self):
        response = self.client.post(
            "/v1/screening/contract",
            json={"text": "هذا القرض بفايده مركبه على المبلغ الاصلي"},
            headers=self.auth_headers,
        )
        body = response.json()
        self.assertTrue(body["has_concerns"])
        self.assertIn("riba", body["categories_found"])
        self.assertGreater(len(body["flags"]), 0)

    def test_oversized_contract_text_rejected(self):
        os.environ["SHARIA_AI_MAX_CONTRACT_CHARS"] = "10"
        main_module = reload_chain()
        client = TestClient(main_module.app)
        response = client.post(
            "/v1/screening/contract",
            json={"text": "نص طويل جدًا يتجاوز الحد الأقصى المسموح به لعدد الأحرف"},
            headers=self.auth_headers,
        )
        self.assertEqual(response.status_code, 422)

    def test_empty_contract_text_rejected(self):
        response = self.client.post(
            "/v1/screening/contract", json={"text": ""}, headers=self.auth_headers
        )
        self.assertEqual(response.status_code, 422)


class TestZakatCalculateEndpoint(_AuthenticatedApiTestCase):
    def test_above_nisab_returns_zakat_due(self):
        response = self.client.post(
            "/v1/zakat/calculate",
            json={
                "cash_and_equivalents": 10_000.0,
                "gold_price_per_gram": 75.0,
                "silver_price_per_gram": 0.9,
            },
            headers=self.auth_headers,
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["meets_nisab"])
        self.assertAlmostEqual(body["zakat_due"], 250.0)

    def test_below_nisab_returns_zero_due(self):
        response = self.client.post(
            "/v1/zakat/calculate",
            json={"cash_and_equivalents": 10.0},
            headers=self.auth_headers,
        )
        body = response.json()
        self.assertFalse(body["meets_nisab"])
        self.assertEqual(body["zakat_due"], 0.0)

    def test_uses_config_default_prices_when_omitted(self):
        response = self.client.post(
            "/v1/zakat/calculate",
            json={"cash_and_equivalents": 1000.0},
            headers=self.auth_headers,
        )
        self.assertEqual(response.status_code, 200)

    def test_negative_asset_value_rejected(self):
        response = self.client.post(
            "/v1/zakat/calculate",
            json={"cash_and_equivalents": -500.0},
            headers=self.auth_headers,
        )
        self.assertEqual(response.status_code, 422)


class TestComplianceReportEndpoint(_AuthenticatedApiTestCase):
    def test_full_report_with_all_sections(self):
        response = self.client.post(
            "/v1/compliance/report",
            json={
                "company": _company_payload(),
                "contracts": {"عقد": "هذا عقد بيع عادي"},
                "zakat_assets": {"cash_and_equivalents": 10_000.0},
            },
            headers=self.auth_headers,
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["company_name"], "شركة الاختبار")
        self.assertIsNotNone(body["equity_screening"])
        self.assertIsNotNone(body["contract_screening"])
        self.assertIsNotNone(body["zakat"])

    def test_report_without_optional_sections(self):
        response = self.client.post(
            "/v1/compliance/report",
            json={"company": _company_payload()},
            headers=self.auth_headers,
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIsNone(body["contract_screening"])
        self.assertIsNone(body["zakat"])

    def test_non_compliant_company_overall_status(self):
        response = self.client.post(
            "/v1/compliance/report",
            json={"company": _company_payload(sector="gambling")},
            headers=self.auth_headers,
        )
        body = response.json()
        self.assertEqual(body["overall_status"], "غير متوافق — فشل في فرز الأسهم")

    def test_explicit_null_contracts_is_accepted(self):
        response = self.client.post(
            "/v1/compliance/report",
            json={"company": _company_payload(), "contracts": None},
            headers=self.auth_headers,
        )
        self.assertEqual(response.status_code, 200)

    def test_oversized_contract_in_report_rejected(self):
        response = self.client.post(
            "/v1/compliance/report",
            json={
                "company": _company_payload(),
                "contracts": {"عقد": "س" * 100_000},
            },
            headers=self.auth_headers,
        )
        self.assertEqual(response.status_code, 422)


class TestRateLimiting(_AuthenticatedApiTestCase):
    def test_requests_beyond_limit_return_429(self):
        os.environ["SHARIA_AI_RATE_LIMIT_REQUESTS"] = "2"
        os.environ["SHARIA_AI_RATE_LIMIT_WINDOW_SECONDS"] = "60"
        main_module = reload_chain()
        client = TestClient(main_module.app)

        for _ in range(2):
            response = client.post(
                "/v1/zakat/calculate",
                json={"cash_and_equivalents": 1000.0},
                headers=self.auth_headers,
            )
            self.assertEqual(response.status_code, 200)

        blocked = client.post(
            "/v1/zakat/calculate",
            json={"cash_and_equivalents": 1000.0},
            headers=self.auth_headers,
        )
        self.assertEqual(blocked.status_code, 429)
        self.assertIn("Retry-After", blocked.headers)


class TestAuditEndpoint(_AuthenticatedApiTestCase):
    def test_audit_recent_requires_api_key(self):
        response = self.client.get("/v1/audit/recent")
        self.assertEqual(response.status_code, 401)

    def test_audit_recent_filters_by_event_type(self):
        self.client.post(
            "/v1/zakat/calculate",
            json={"cash_and_equivalents": 1000.0},
            headers=self.auth_headers,
        )
        self.client.post(
            "/v1/screening/equity", json=_company_payload(), headers=self.auth_headers
        )
        response = self.client.get(
            "/v1/audit/recent",
            params={"event_type": "zakat_calculation"},
            headers=self.auth_headers,
        )
        body = response.json()
        self.assertGreaterEqual(body["returned"], 1)
        for entry in body["entries"]:
            self.assertEqual(entry["event_type"], "zakat_calculation")

    def test_audit_recent_disabled_returns_503(self):
        os.environ["SHARIA_AI_AUDIT_ENABLED"] = "false"
        main_module = reload_chain()
        client = TestClient(main_module.app)
        response = client.get("/v1/audit/recent", headers=self.auth_headers)
        self.assertEqual(response.status_code, 503)


class TestUnhandledExceptionHandling(_AuthenticatedApiTestCase):
    def test_unexpected_exception_returns_500_without_leaking_details(self):
        from unittest.mock import patch

        no_raise_client = TestClient(self.main_module.app, raise_server_exceptions=False)
        with patch.object(
            self.main_module,
            "_equity_screener",
            **{"screen.side_effect": RuntimeError("boom - internal secret detail")},
        ):
            response = no_raise_client.post(
                "/v1/screening/equity", json=_company_payload(), headers=self.auth_headers
            )
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("boom", response.text)
        self.assertNotIn("secret", response.text)


class TestLifespanLogging(_AuthenticatedApiTestCase):
    def test_app_startup_and_shutdown_via_context_manager(self):
        with TestClient(self.main_module.app) as client:
            response = client.get("/health")
            self.assertEqual(response.status_code, 200)


class TestCorsConfiguredExplicitly(unittest.TestCase):
    def setUp(self):
        self._env_snapshot = snapshot_env()
        os.environ["SHARIA_AI_CORS_ORIGINS"] = "https://example.com"
        os.environ.pop("SHARIA_AI_API_KEYS", None)
        os.environ["SHARIA_AI_REQUIRE_API_KEY"] = "false"
        self.main_module = reload_chain()
        self.client = TestClient(self.main_module.app)

    def tearDown(self):
        restore_env(self._env_snapshot)
        reload_chain()

    def test_cors_preflight_allows_configured_origin(self):
        response = self.client.options(
            "/v1/zakat/calculate",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "POST",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers.get("access-control-allow-origin"), "https://example.com"
        )


class TestDevModeWithoutApiKeysConfigured(unittest.TestCase):
    """عندما لا تُهيَّأ أي مفاتيح API، يجب أن تُتاح الواجهة البرمجية دون
    مصادقة (وضع تطوير محلي فقط) — سلوك موثَّق صراحةً، وليس عطلًا صامتًا."""

    def setUp(self):
        self._env_snapshot = snapshot_env()
        _fd, self._tmp_db_path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(_fd)
        os.environ.pop("SHARIA_AI_API_KEYS", None)
        os.environ["SHARIA_AI_REQUIRE_API_KEY"] = "true"
        os.environ["SHARIA_AI_AUDIT_DB_PATH"] = self._tmp_db_path
        self.main_module = reload_chain()
        self.client = TestClient(self.main_module.app)

    def tearDown(self):
        restore_env(self._env_snapshot)
        reload_chain()
        try:
            os.unlink(self._tmp_db_path)
        except OSError:
            pass

    def test_request_without_key_succeeds_in_dev_mode(self):
        response = self.client.post("/v1/screening/equity", json=_company_payload())
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
