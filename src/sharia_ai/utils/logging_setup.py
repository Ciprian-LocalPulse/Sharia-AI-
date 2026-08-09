"""
logging_setup.py — تهيئة تسجيل (logging) منظَّم بصيغة JSON، مناسب
للإنتاج (قابل للفهرسة من قِبل أدوات مثل ELK / Loki / CloudWatch).

يوفّر:
    - `configure_logging()`: يهيّئ المسجِّل الجذر مرة واحدة عند إقلاع
      التطبيق.
    - `get_logger(name)`: يُعيد مسجِّلًا فرعيًا للاستخدام في أي وحدة.

المؤلف: Ciprian Ștefan Pleșca
"""

from __future__ import annotations

import json
import logging
import sys
import time
from typing import Any

_CONFIGURED = False


class JsonFormatter(logging.Formatter):
    """يُنسّق كل سجل (log record) كسطر JSON واحد."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime_iso(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # حقول سياقية إضافية (مثال: request_id، route، status_code)
        for key, value in getattr(record, "extra_fields", {}).items():
            payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)

    @staticmethod
    def formatTime_iso(record: logging.LogRecord) -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)) + (
            f".{int(record.msecs):03d}Z"
        )


def configure_logging(level: str = "INFO") -> None:
    """يهيّئ المسجِّل الجذر بصيغة JSON. آمن للاستدعاء عدة مرات (idempotent)."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    root = logging.getLogger()
    root.setLevel(level.upper())

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(JsonFormatter())

    # إزالة أي معالِجات افتراضية لتجنّب ازدواج السجلات
    root.handlers.clear()
    root.addHandler(handler)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_with_fields(logger: logging.Logger, level: int, message: str, **fields: Any) -> None:
    """يسجّل رسالة مع حقول سياقية إضافية تُدرَج في مخرجات JSON."""
    logger.log(level, message, extra={"extra_fields": fields})
