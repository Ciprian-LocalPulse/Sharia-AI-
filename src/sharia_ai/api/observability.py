"""Request logging, rate limiting, and lightweight metrics."""

from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from threading import Lock

logger = logging.getLogger("sharia_ai.api")


@dataclass
class ApiMetrics:
    total_requests: int = 0
    rate_limited_requests: int = 0
    status_counts: dict[str, int] = field(default_factory=dict)

    def snapshot(self) -> dict[str, object]:
        return {
            "total_requests": self.total_requests,
            "rate_limited_requests": self.rate_limited_requests,
            "status_counts": dict(self.status_counts),
        }


class FixedWindowRateLimiter:
    def __init__(self, requests_per_minute: int):
        self.requests_per_minute = max(1, requests_per_minute)
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str, now: float | None = None) -> bool:
        current = time.monotonic() if now is None else now
        window_start = current - 60.0
        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] < window_start:
                hits.popleft()
            if len(hits) >= self.requests_per_minute:
                return False
            hits.append(current)
            return True


metrics = ApiMetrics()
