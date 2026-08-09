import sqlite3
import tempfile
import unittest
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import patch

from pydantic import ValidationError

try:
    from fastapi.testclient import TestClient

    from sharia_ai.api import main as api_module
    from sharia_ai.api.audit import SQLiteAuditStore
    from sharia_ai.api.main import app
    from sharia_ai.api.observability import FixedWindowRateLimiter

    _FASTAPI_AVAILABLE = True
except ImportError:
    _FASTAPI_AVAILABLE = False


def _company_payload(**overrides):
    payload = {
        "name": "AuditCo",
        "sector": "other",
        "market_cap": 1_000_000.0,
        "interest_bearing_debt": 100_000.0,
        "cash_and_interest_bearing_deposits": 100_000.0,
        "accounts_receivable": 100_000.0,
        "total_revenue": 500_000.0,
    }
    payload.update(overrides)
    return payload


@unittest.skipUnless(_FASTAPI_AVAILABLE, "fastapi/httpx not installed")
class TestProductionApiControls(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_request_id_header_is_returned(self):
        response = self.client.get("/health", headers={"X-Request-ID": "req-test"})
        self.assertEqual(response.headers["X-Request-ID"], "req-test")

    def test_v1_alias_is_available(self):
        response = self.client.post("/v1/screening/equity", json=_company_payload())
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["is_compliant"])

    def test_metrics_endpoint_returns_counters(self):
        response = self.client.get("/metrics")
        self.assertEqual(response.status_code, 200)
        self.assertIn("total_requests", response.json())

    def test_api_key_is_required_when_configured(self):
        secured_config = SimpleNamespace(api_keys=("secret",))
        with patch.object(api_module, "config", secured_config):
            response = self.client.post("/screening/equity", json=_company_payload())
            self.assertEqual(response.status_code, 401)

            allowed = self.client.post(
                "/screening/equity",
                headers={"X-API-Key": "secret"},
                json=_company_payload(),
            )
            self.assertEqual(allowed.status_code, 200)

    def test_invalid_market_cap_is_rejected(self):
        response = self.client.post(
            "/screening/equity",
            json=_company_payload(market_cap=-1.0),
        )
        self.assertEqual(response.status_code, 422)

    def test_contract_size_limit_returns_422(self):
        response = self.client.post(
            "/screening/contract",
            json={"text": "x" * (api_module.config.max_contract_chars + 1)},
        )
        self.assertEqual(response.status_code, 422)

    def test_compliance_contract_validator_rejects_bad_names_and_text(self):
        with self.assertRaises(ValidationError):
            api_module.ComplianceReportIn(
                company=_company_payload(),
                contracts={"": "valid text"},
            )

        with self.assertRaises(ValidationError):
            api_module.ComplianceReportIn(
                company=_company_payload(),
                contracts={"contract": ""},
            )

    def test_compliance_contract_validator_allows_missing_contracts(self):
        payload = api_module.ComplianceReportIn(company=_company_payload())
        self.assertIsNone(payload.contracts)

    def test_client_key_prefers_forwarded_for_and_handles_missing_client(self):
        forwarded = SimpleNamespace(
            headers={"x-forwarded-for": "203.0.113.1, 10.0.0.1"},
            client=SimpleNamespace(host="127.0.0.1"),
        )
        self.assertEqual(api_module._client_key(cast(Any, forwarded)), "203.0.113.1")

        missing = SimpleNamespace(headers={}, client=None)
        self.assertEqual(api_module._client_key(cast(Any, missing)), "unknown")

    def test_rate_limited_request_returns_429(self):
        class BlockAll:
            def allow(self, key: str) -> bool:
                return False

        with patch.object(api_module, "_rate_limiter", BlockAll()):
            response = self.client.get("/health", headers={"X-Request-ID": "blocked"})

        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json()["request_id"], "blocked")

    def test_audit_write_failure_is_logged_not_raised(self):
        class BrokenAuditStore:
            def record(self, event: object) -> None:
                raise OSError("disk full")

        request = SimpleNamespace(state=SimpleNamespace(request_id="audit-failure"))
        with patch.object(api_module, "_audit_store", BrokenAuditStore()):
            api_module._record_audit(
                cast(Any, request),
                "endpoint",
                "subject",
                "decision",
                {"ok": True},
            )

    def test_screening_writes_sqlite_audit_event(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            db_path = f"{temp_dir}/audit.sqlite3"
            with patch.object(api_module, "_audit_store", SQLiteAuditStore(db_path)):
                response = self.client.post("/screening/equity", json=_company_payload())
                self.assertEqual(response.status_code, 200)

            with sqlite3.connect(db_path) as connection:
                rows = connection.execute(
                    "SELECT endpoint, subject, decision FROM audit_events"
                ).fetchall()

        self.assertEqual(rows, [("screening.equity", "AuditCo", "compliant")])


class TestRateLimiter(unittest.TestCase):
    def test_fixed_window_rate_limiter_blocks_after_limit(self):
        limiter = FixedWindowRateLimiter(requests_per_minute=2)
        self.assertTrue(limiter.allow("client", now=10.0))
        self.assertTrue(limiter.allow("client", now=11.0))
        self.assertFalse(limiter.allow("client", now=12.0))
        self.assertTrue(limiter.allow("client", now=71.1))


if __name__ == "__main__":
    unittest.main()
