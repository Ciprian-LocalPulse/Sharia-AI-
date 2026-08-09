"""
_reload_utils.py — أداة اختبار داخلية فقط (ليست جزءًا من الحزمة
المُنشورة). تعيد تحميل سلسلة الوحدات المرتبطة بـ `config` (التي تُقرَأ
مرة واحدة عند استيراد الوحدة) بترتيب صحيح، حتى تعكس اختبارات الواجهة
البرمجية تغييرات متغيرات البيئة بشكل موثوق.

المؤلف: Ciprian Ștefan Pleșca
"""

from __future__ import annotations

import importlib
import os

ENV_KEYS = (
    "SHARIA_AI_GOLD_PRICE_PER_GRAM",
    "SHARIA_AI_SILVER_PRICE_PER_GRAM",
    "SHARIA_AI_CURRENCY",
    "SHARIA_AI_API_KEYS",
    "SHARIA_AI_REQUIRE_API_KEY",
    "SHARIA_AI_CORS_ORIGINS",
    "SHARIA_AI_RATE_LIMIT_REQUESTS",
    "SHARIA_AI_RATE_LIMIT_WINDOW_SECONDS",
    "SHARIA_AI_MAX_CONTRACT_CHARS",
    "SHARIA_AI_AUDIT_DB_PATH",
    "SHARIA_AI_AUDIT_ENABLED",
    "SHARIA_AI_ENV",
    "SHARIA_AI_LOG_LEVEL",
)


def snapshot_env() -> dict[str, str | None]:
    return {key: os.environ.get(key) for key in ENV_KEYS}


def restore_env(snapshot: dict[str, str | None]) -> None:
    for key, value in snapshot.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def reload_chain():
    """يعيد تحميل الوحدات بترتيب الاعتمادية الصحيح ويُعيد وحدة `main`
    المُحدَّثة (ومنها يمكن أخذ `app`)."""
    import sharia_ai.utils.config as config_module

    config_module = importlib.reload(config_module)

    import sharia_ai.utils.logging_setup as logging_module

    logging_module = importlib.reload(logging_module)

    import sharia_ai.api.security as security_module

    security_module = importlib.reload(security_module)

    import sharia_ai.audit.audit_log as audit_module

    audit_module = importlib.reload(audit_module)

    import sharia_ai.api.main as main_module

    main_module = importlib.reload(main_module)

    return main_module
