"""
security.py — طبقة الأمان الأساسية للواجهة البرمجية REST:
    1. مصادقة عبر مفتاح API ثابت (header: X-API-Key)، مقارنة بزمن ثابت
       (`hmac.compare_digest`) لتفادي هجمات القياس الزمني (timing attack).
    2. تحديد معدّل الطلبات (rate limiting) بخوارزمية "نافذة ثابتة"
       (fixed-window) في الذاكرة — كافٍ لعملية واحدة (single-process)،
       قابل للاستبدال بـ Redis في نشر متعدد العمليات/الحاويات.

كلا الآليتين قابلتان للتعطيل عبر الإعدادات (مفيد للتطوير المحلي أو
الاختبارات)، لكن الافتراضي الآمن هو التفعيل.

المؤلف: Ciprian Ștefan Pleșca
"""

from __future__ import annotations

import hmac
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader

from ..utils.config import config

_API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def _constant_time_in(candidate: str, valid_keys: frozenset[str] | tuple[str, ...]) -> bool:
    """يقارن `candidate` بكل مفتاح صالح باستخدام مقارنة بزمن ثابت،
    لتفادي تسريب معلومات عبر توقيت الاستجابة."""
    matched = False
    for key in valid_keys:
        if hmac.compare_digest(candidate, key):
            matched = True
    return matched


async def require_api_key(api_key: str | None = Security(_API_KEY_HEADER)) -> str:
    """اعتمادية FastAPI (dependency) تفرض وجود مفتاح API صالح.

    تُعطَّل تلقائيًا إذا:
        - `config.require_api_key` هو False، أو
        - لا توجد أي مفاتيح مُهيَّأة في `config.api_keys` (وضع تطوير محلي)
          — في هذه الحالة يُسجَّل تحذير صريح بدلاً من فشل صامت.
    """
    if not config.require_api_key or not config.api_keys:
        return "unauthenticated-dev-mode"

    if api_key is None or not _constant_time_in(api_key, config.api_keys):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="مفتاح API مفقود أو غير صالح (رأس X-API-Key).",
        )
    return api_key


class FixedWindowRateLimiter:
    """محدِّد معدّل بسيط بنافذة زمنية ثابتة، آمن للتزامن (thread-safe)
    عبر قفل واحد. يُحدَّد كل عميل بمعرِّفه (مفتاح API إن وُجد، وإلا
    عنوان IP)."""

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, client_id: str) -> bool:
        now = time.monotonic()
        with self._lock:
            bucket = self._hits[client_id]
            cutoff = now - self.window_seconds
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= self.max_requests:
                return False
            bucket.append(now)
            return True

    def reset(self) -> None:
        """يمسح كل الحالة الداخلية — مفيد بين الاختبارات."""
        with self._lock:
            self._hits.clear()


rate_limiter = FixedWindowRateLimiter(
    max_requests=config.rate_limit_requests,
    window_seconds=config.rate_limit_window_seconds,
)


def client_identifier(request: Request) -> str:
    """يستخدم مفتاح API إن وُجد (لتحديد أدق)، وإلا عنوان IP للعميل."""
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"key:{api_key}"
    client = request.client
    return f"ip:{client.host}" if client else "ip:unknown"


async def enforce_rate_limit(request: Request) -> None:
    """اعتمادية FastAPI تفرض حد معدّل الطلبات لكل عميل."""
    client_id = client_identifier(request)
    if not rate_limiter.allow(client_id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"تم تجاوز حد معدّل الطلبات "
                f"({config.rate_limit_requests} طلب/{config.rate_limit_window_seconds} ثانية)."
            ),
            headers={"Retry-After": str(config.rate_limit_window_seconds)},
        )
