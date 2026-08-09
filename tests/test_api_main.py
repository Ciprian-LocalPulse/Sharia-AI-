import unittest

try:
    from fastapi.testclient import TestClient

    from sharia_ai.api.main import app

    _FASTAPI_AVAILABLE = True
except ImportError:
    _FASTAPI_AVAILABLE = False


@unittest.skipUnless(
    _FASTAPI_AVAILABLE, "fastapi/httpx not installed — install requirements.txt to run API tests"
)
class TestHealthEndpoint(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_returns_ok(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "ok")
        self.assertIn("service", body)
        self.assertIn("version", body)


@unittest.skipUnless(_FASTAPI_AVAILABLE, "fastapi/httpx not installed")
class TestScreenEquityEndpoint(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def _payload(self, **overrides):
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

    def test_compliant_company_returns_true(self):
        response = self.client.post("/screening/equity", json=self._payload())
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["is_compliant"])
        self.assertEqual(body["company"], "شركة الاختبار")
        self.assertIsInstance(body["checks"], list)
        self.assertEqual(len(body["checks"]), 5)

    def test_excluded_sector_returns_false(self):
        response = self.client.post(
            "/screening/equity", json=self._payload(sector="gambling")
        )
        body = response.json()
        self.assertFalse(body["is_compliant"])

    def test_missing_required_field_returns_422(self):
        payload = self._payload()
        del payload["market_cap"]
        response = self.client.post("/screening/equity", json=payload)
        self.assertEqual(response.status_code, 422)


@unittest.skipUnless(_FASTAPI_AVAILABLE, "fastapi/httpx not installed")
class TestScreenContractEndpoint(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_clean_contract_has_no_concerns(self):
        response = self.client.post(
            "/screening/contract", json={"text": "هذا عقد بيع عادي بلا أي شروط"}
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertFalse(body["has_concerns"])
        self.assertEqual(body["flags"], [])

    def test_riba_contract_flags_riba_category(self):
        response = self.client.post(
            "/screening/contract",
            json={"text": "هذا القرض بفايده مركبه على المبلغ الاصلي"},
        )
        body = response.json()
        self.assertTrue(body["has_concerns"])
        self.assertIn("riba", body["categories_found"])
        self.assertGreater(len(body["flags"]), 0)


@unittest.skipUnless(_FASTAPI_AVAILABLE, "fastapi/httpx not installed")
class TestZakatCalculateEndpoint(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_above_nisab_returns_zakat_due(self):
        response = self.client.post(
            "/zakat/calculate",
            json={
                "cash_and_equivalents": 10_000.0,
                "gold_price_per_gram": 75.0,
                "silver_price_per_gram": 0.9,
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["meets_nisab"])
        self.assertAlmostEqual(body["zakat_due"], 250.0)

    def test_below_nisab_returns_zero_due(self):
        response = self.client.post(
            "/zakat/calculate",
            json={"cash_and_equivalents": 10.0},
        )
        body = response.json()
        self.assertFalse(body["meets_nisab"])
        self.assertEqual(body["zakat_due"], 0.0)

    def test_uses_config_default_prices_when_omitted(self):
        response = self.client.post("/zakat/calculate", json={"cash_and_equivalents": 1000.0})
        self.assertEqual(response.status_code, 200)


@unittest.skipUnless(_FASTAPI_AVAILABLE, "fastapi/httpx not installed")
class TestComplianceReportEndpoint(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def _company_payload(self, **overrides):
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

    def test_full_report_with_all_sections(self):
        response = self.client.post(
            "/compliance/report",
            json={
                "company": self._company_payload(),
                "contracts": {"عقد": "هذا عقد بيع عادي"},
                "zakat_assets": {"cash_and_equivalents": 10_000.0},
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["company_name"], "شركة الاختبار")
        self.assertIsNotNone(body["equity_screening"])
        self.assertIsNotNone(body["contract_screening"])
        self.assertIsNotNone(body["zakat"])

    def test_report_without_optional_sections(self):
        response = self.client.post(
            "/compliance/report",
            json={"company": self._company_payload()},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIsNone(body["contract_screening"])
        self.assertIsNone(body["zakat"])

    def test_non_compliant_company_overall_status(self):
        response = self.client.post(
            "/compliance/report",
            json={"company": self._company_payload(sector="gambling")},
        )
        body = response.json()
        self.assertEqual(body["overall_status"], "غير متوافق — فشل في فرز الأسهم")


if __name__ == "__main__":
    unittest.main()
