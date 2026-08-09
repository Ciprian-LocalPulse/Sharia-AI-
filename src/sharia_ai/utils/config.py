"""
config.py — Configurare centralizată, citită din variabile de mediu cu
valori implicite sigure. Evită hardcodarea parametrilor financiari
sensibili (prețuri metal, praguri) direct în cod.
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


@dataclass(frozen=True)
class AppConfig:
    gold_price_per_gram: float = _env_float("SHARIA_AI_GOLD_PRICE_PER_GRAM", 75.0)
    silver_price_per_gram: float = _env_float("SHARIA_AI_SILVER_PRICE_PER_GRAM", 0.95)
    api_title: str = "Sharia-AI Compliance Toolkit API"
    api_version: str = "0.1.0"
    default_currency: str = os.getenv("SHARIA_AI_CURRENCY", "USD")


config = AppConfig()
