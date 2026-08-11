import asyncio
import unittest
from unittest.mock import MagicMock

from fastapi import HTTPException

from sharia_ai.api import security as security_module
from sharia_ai.api.security import (
    FixedWindowRateLimiter,
    _constant_time_in,
    client_identifier,
    enforce_rate_limit,
    require_api_key,
)


class TestConstantTimeIn(unittest.TestCase):
    def test_matching_key_returns_true(self):
        self.assertTrue(_constant_time_in("abc", frozenset({"abc", "def"})))

    def test_non_matching_key_returns_false(self):
        self.assertFalse(_constant_time_in("xyz", frozenset({"abc", "def"})))

    def test_empty_key_set_returns_false(self):
        self.assertFalse(_constant_time_in("abc", frozenset()))


class TestRequireApiKey(unittest.TestCase):
    def setUp(self):
        self._original_require = security_module.config.require_api_key
        self._original_keys = security_module.config.api_keys

    def tearDown(self):
        object.__setattr__(security_module.config, "require_api_key", self._original_require)
        object.__setattr__(security_module.config, "api_keys", self._original_keys)

    def test_dev_mode_bypasses_auth_when_no_keys_configured(self):
        object.__setattr__(security_module.config, "require_api_key", True)
        object.__setattr__(security_module.config, "api_keys", frozenset())
        result = asyncio.run(require_api_key(api_key=None))
        self.assertEqual(result, "unauthenticated-dev-mode")

    def test_disabled_requirement_bypasses_auth_even_with_keys(self):
        object.__setattr__(security_module.config, "require_api_key", False)
        object.__setattr__(security_module.config, "api_keys", frozenset({"secret"}))
        result = asyncio.run(require_api_key(api_key=None))
        self.assertEqual(result, "unauthenticated-dev-mode")

    def test_missing_key_raises_401_when_enforced(self):
        object.__setattr__(security_module.config, "require_api_key", True)
        object.__setattr__(security_module.config, "api_keys", frozenset({"secret"}))
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(require_api_key(api_key=None))
        self.assertEqual(ctx.exception.status_code, 401)

    def test_wrong_key_raises_401(self):
        object.__setattr__(security_module.config, "require_api_key", True)
        object.__setattr__(security_module.config, "api_keys", frozenset({"secret"}))
        with self.assertRaises(HTTPException):
            asyncio.run(require_api_key(api_key="wrong"))

    def test_correct_key_is_returned(self):
        object.__setattr__(security_module.config, "require_api_key", True)
        object.__setattr__(security_module.config, "api_keys", frozenset({"secret"}))
        result = asyncio.run(require_api_key(api_key="secret"))
        self.assertEqual(result, "secret")


class TestFixedWindowRateLimiter(unittest.TestCase):
    def test_allows_up_to_max_requests(self):
        limiter = FixedWindowRateLimiter(max_requests=3, window_seconds=60)
        self.assertTrue(limiter.allow("client-a"))
        self.assertTrue(limiter.allow("client-a"))
        self.assertTrue(limiter.allow("client-a"))
        self.assertFalse(limiter.allow("client-a"))

    def test_different_clients_have_independent_buckets(self):
        limiter = FixedWindowRateLimiter(max_requests=1, window_seconds=60)
        self.assertTrue(limiter.allow("client-a"))
        self.assertTrue(limiter.allow("client-b"))
        self.assertFalse(limiter.allow("client-a"))

    def test_reset_clears_all_state(self):
        limiter = FixedWindowRateLimiter(max_requests=1, window_seconds=60)
        limiter.allow("client-a")
        self.assertFalse(limiter.allow("client-a"))
        limiter.reset()
        self.assertTrue(limiter.allow("client-a"))

    def test_expired_entries_are_evicted(self):
        limiter = FixedWindowRateLimiter(max_requests=1, window_seconds=60)
        limiter.allow("client-a")
        # Simulate time passing beyond the window by manipulating the bucket directly.
        bucket = limiter._hits["client-a"]
        bucket[0] -= 61
        self.assertTrue(limiter.allow("client-a"))


class TestClientIdentifier(unittest.TestCase):
    def test_uses_api_key_header_when_present(self):
        request = MagicMock()
        request.headers = {"X-API-Key": "abc123"}
        identifier = client_identifier(request)
        self.assertTrue(identifier.startswith("key:"))
        self.assertNotIn("abc123", identifier)
        self.assertEqual(identifier, client_identifier(request))

    def test_falls_back_to_client_ip(self):
        request = MagicMock()
        request.headers = {}
        request.client.host = "10.0.0.5"
        self.assertEqual(client_identifier(request), "ip:10.0.0.5")

    def test_unknown_when_no_client_info(self):
        request = MagicMock()
        request.headers = {}
        request.client = None
        self.assertEqual(client_identifier(request), "ip:unknown")


class TestEnforceRateLimit(unittest.TestCase):
    def setUp(self):
        self._original_limiter = security_module.rate_limiter
        security_module.rate_limiter = FixedWindowRateLimiter(
            max_requests=1, window_seconds=60
        )

    def tearDown(self):
        security_module.rate_limiter = self._original_limiter

    def test_first_request_passes(self):
        request = MagicMock()
        request.headers = {"X-API-Key": "k1"}
        asyncio.run(enforce_rate_limit(request))

    def test_second_request_raises_429(self):
        request = MagicMock()
        request.headers = {"X-API-Key": "k2"}
        asyncio.run(enforce_rate_limit(request))
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(enforce_rate_limit(request))
        self.assertEqual(ctx.exception.status_code, 429)
        self.assertIn("Retry-After", ctx.exception.headers)


if __name__ == "__main__":
    unittest.main()
