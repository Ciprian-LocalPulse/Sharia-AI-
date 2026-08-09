"""
config.py — تهيئة مركزية، تُقرأ من متغيرات البيئة مع قيم افتراضية
آمنة. تتجنّب الترميز الثابت للمعاملات المالية الحساسة (أسعار المعادن،
العتبات) مباشرة في الكود.

المؤلف: Ciprian Ștefan Pleșca
"""

from __future__ import annotations

import os
from dataclasses import dataclass


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


def _env_csv(key: str) -> tuple[str, ...]:
    raw = os.getenv(key, "")
    return tuple(value.strip() for value in raw.split(",") if value.strip())


@dataclass(frozen=True)
class AppConfig:
    gold_price_per_gram: float = _env_float("SHARIA_AI_GOLD_PRICE_PER_GRAM", 75.0)
    silver_price_per_gram: float = _env_float("SHARIA_AI_SILVER_PRICE_PER_GRAM", 0.95)
    api_title: str = "Sharia-AI Compliance Toolkit API"
    api_version: str = "0.1.0"
    default_currency: str = os.getenv("SHARIA_AI_CURRENCY", "USD")
    api_keys: tuple[str, ...] = _env_csv("SHARIA_AI_API_KEYS")
    cors_allowed_origins: tuple[str, ...] = _env_csv("SHARIA_AI_CORS_ALLOWED_ORIGINS")
    rate_limit_per_minute: int = _env_int("SHARIA_AI_RATE_LIMIT_PER_MINUTE", 120)
    max_contract_chars: int = _env_int("SHARIA_AI_MAX_CONTRACT_CHARS", 20_000)
    audit_log_path: str = os.getenv(
        "SHARIA_AI_AUDIT_LOG_PATH",
        "data/audit/sharia_ai_audit.sqlite3",
    )


config = AppConfig()
