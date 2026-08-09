import importlib
import json
import logging
import unittest

import sharia_ai.utils.logging_setup as logging_module


class TestJsonFormatter(unittest.TestCase):
    def test_format_produces_valid_json_with_expected_fields(self):
        formatter = logging_module.JsonFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="رسالة اختبار",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        self.assertEqual(parsed["level"], "INFO")
        self.assertEqual(parsed["logger"], "test.logger")
        self.assertEqual(parsed["message"], "رسالة اختبار")
        self.assertIn("timestamp", parsed)

    def test_format_includes_extra_fields(self):
        formatter = logging_module.JsonFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="msg",
            args=(),
            exc_info=None,
        )
        record.extra_fields = {"request_id": "abc-123", "status_code": 200}
        output = formatter.format(record)
        parsed = json.loads(output)
        self.assertEqual(parsed["request_id"], "abc-123")
        self.assertEqual(parsed["status_code"], 200)

    def test_format_includes_exception_when_present(self):
        formatter = logging_module.JsonFormatter()
        try:
            raise ValueError("boom")
        except ValueError:
            import sys

            record = logging.LogRecord(
                name="test.logger",
                level=logging.ERROR,
                pathname=__file__,
                lineno=1,
                msg="failure",
                args=(),
                exc_info=sys.exc_info(),
            )
        output = formatter.format(record)
        parsed = json.loads(output)
        self.assertIn("exception", parsed)
        self.assertIn("ValueError", parsed["exception"])


class TestConfigureLogging(unittest.TestCase):
    def setUp(self):
        importlib.reload(logging_module)

    def tearDown(self):
        importlib.reload(logging_module)

    def test_configure_logging_sets_root_level(self):
        logging_module.configure_logging("DEBUG")
        self.assertEqual(logging.getLogger().level, logging.DEBUG)

    def test_configure_logging_is_idempotent(self):
        logging_module.configure_logging("INFO")
        handler_count_first = len(logging.getLogger().handlers)
        logging_module.configure_logging("INFO")
        handler_count_second = len(logging.getLogger().handlers)
        self.assertEqual(handler_count_first, handler_count_second)

    def test_get_logger_returns_named_logger(self):
        logger = logging_module.get_logger("sharia_ai.test")
        self.assertEqual(logger.name, "sharia_ai.test")

    def test_log_with_fields_does_not_raise(self):
        logging_module.configure_logging("INFO")
        logger = logging_module.get_logger("sharia_ai.test")
        logging_module.log_with_fields(logger, logging.INFO, "test message", key="value")


if __name__ == "__main__":
    unittest.main()
