"""
config.py — تهيئة مركزية، تُقرأ من متغيرات البيئة مع قيم افتراضية
آمنة. تتجنّب الترميز الثابت للمعاملات المالية الحساسة (أسعار المعادن،
العتبات) وإعدادات الأمان (مفاتيح API، أصول CORS) مباشرة في الكود.

المؤلف: Ciprian Ștefan Pleșca
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env_float(key: str, default: float) -> float:
    raw = os.getenv(key)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(key: str, default: int) -> int:
    raw = os.getenv(key)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_bool(key: str, default: bool) -> bool:
    raw = os.getenv(key)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_list(key: str, default: list[str]) -> list[str]:
    raw = os.getenv(key)
    if raw is None:
        return list(default)
    return [value.strip() for value in raw.split(",") if value.strip()]


def _env_str_set(key: str, default: frozenset[str]) -> frozenset[str]:
    raw = os.getenv(key)
    if raw is None:
        return default
    return frozenset(value.strip() for value in raw.split(",") if value.strip())


@dataclass(frozen=True)
class AppConfig:
    # --- بيانات مالية أساسية ---
    gold_price_per_gram: float = _env_float("SHARIA_AI_GOLD_PRICE_PER_GRAM", 75.0)
    silver_price_per_gram: float = _env_float("SHARIA_AI_SILVER_PRICE_PER_GRAM", 0.95)
    api_title: str = "Sharia-AI Compliance Toolkit API"
    api_version: str = "0.2.0"
    default_currency: str = os.getenv("SHARIA_AI_CURRENCY", "USD")
    rate_limit_per_minute: int = _env_int(
        "SHARIA_AI_RATE_LIMIT_PER_MINUTE",
        _env_int("SHARIA_AI_RATE_LIMIT_REQUESTS", 120),
    )
    max_contract_chars: int = _env_int("SHARIA_AI_MAX_CONTRACT_CHARS", 20_000)
    audit_log_path: str = os.getenv(
        "SHARIA_AI_AUDIT_LOG_PATH",
        "data/audit/sharia_ai_audit.sqlite3",
    )

    # --- الأمان: مفاتيح API ---
    # إذا كانت هذه المجموعة فارغة، تُعطَّل حماية مفتاح API تلقائيًا
    # (وضع تطوير محلي فقط). في الإنتاج يجب ضبط SHARIA_AI_API_KEYS دائمًا.
    api_keys: frozenset[str] = field(
        default_factory=lambda: _env_str_set("SHARIA_AI_API_KEYS", frozenset())
    )
    require_api_key: bool = _env_bool("SHARIA_AI_REQUIRE_API_KEY", True)

    # --- الأمان: CORS ---
    cors_allowed_origins: list[str] = field(
        default_factory=lambda: _env_list(
            "SHARIA_AI_CORS_ORIGINS",
            _env_list("SHARIA_AI_CORS_ALLOWED_ORIGINS", []),
        )
    )

    # --- تحديد معدّل الطلبات (Rate limiting) ---
    rate_limit_requests: int = _env_int("SHARIA_AI_RATE_LIMIT_REQUESTS", 60)
    rate_limit_window_seconds: int = _env_int("SHARIA_AI_RATE_LIMIT_WINDOW_SECONDS", 60)

    # --- حدود حجم المُدخلات (منع هجمات DoS عبر نصوص ضخمة) ---
    max_contract_text_chars: int = _env_int("SHARIA_AI_MAX_CONTRACT_CHARS", 50_000)

    # --- التدقيق (Audit trail) ---
    audit_db_path: str = os.getenv("SHARIA_AI_AUDIT_DB_PATH", "sharia_ai_audit.sqlite3")
    audit_enabled: bool = _env_bool("SHARIA_AI_AUDIT_ENABLED", True)

    # --- بيئة التشغيل ---
    environment: str = os.getenv("SHARIA_AI_ENV", "development")
    log_level: str = os.getenv("SHARIA_AI_LOG_LEVEL", "INFO")


config = AppConfig()
