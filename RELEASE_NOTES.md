# Sharia-AI v0.2.0

## Codex hardening update - 2026-08-11

### Before

- API, audit logging, and rule tests existed, but the current working tree had failing tests.
- API-key client identifiers could include the full API key in derived log/rate-limit identity.
- SQLite audit tests were unstable on Windows because connections left the database file locked.
- Financial data provenance, methodology decisions, and human Sharia review were not modeled as explicit reusable contracts.

### Implemented

- Added tamper-evident hash-chain fields to the API SQLite audit store and readiness reporting for hash-chain validity.
- Restored `/v1/audit/recent` as a metadata-only endpoint: counts, event types, and chain validity only; no payload, subject, or request ID disclosure.
- Added `Retry-After` on API rate-limit responses.
- Added financial provenance and freshness models under `sharia_ai.data`.
- Added provider abstraction under `sharia_ai.data.providers`.
- Added methodology primitives under `sharia_ai.policies`, including `COMPLIANT`, `NON_COMPLIANT`, `REVIEW_REQUIRED`, and `INSUFFICIENT_DATA`.
- Added human review workflow primitives under `sharia_ai.governance`.
- Replaced API-key client identifiers with SHA-256 fingerprints truncated to 12 hex characters.
- Removed accidental `src/sharia_ai/api/main.py.backup`.
- Corrected corrupted Arabic string assertions in tests so they validate real Unicode output.

### Verification

- Tests: `175 passed`.
- Coverage: `96%`.
- Ruff: passed with `--no-cache`.
- Mypy: passed with cache redirected outside the repository.
- Wheel build: passed with `--no-isolation`; isolated build could not run because network access to PyPI was blocked.
- Secret scan: no production source returns `key:{full_api_key}` after the fix.
- Docker: Docker CLI exists, but Docker Desktop daemon was not running; image build could not be completed.
- Compose: validation currently requires a local `.env`; using `.env.example` as a fallback was intentionally not committed because it can create unsafe deployments with example credentials.

### Known limitations

- PostgreSQL, Redis, RBAC, frontend, trained Arabic NLP models, and live market-data providers are still not implemented.
- SQLite remains the local audit store.
- The NLP layer remains deterministic with adapter-ready architecture work still pending.
- This release remains a hardened research/compliance toolkit, not a full enterprise SaaS platform.

هذا الإصدار يُحوِّل الواجهة البرمجية REST من نموذج أولي (prototype) بلا حماية إلى خدمة جاهزة لنشر أوّلي مسؤول، عبر إضافة طبقة أمان ومراقبة وتدقيق كاملة، دون تغيير منطق الفرز/الحساب الأساسي (يبقى متوافقًا سلوكيًا مع v0.1.0).

## أبرز التغييرات

- **مصادقة إلزامية افتراضيًا** عبر مفتاح API (`X-API-Key`)، مع وضع تطوير محلي صريح وموثَّق عند عدم ضبط أي مفتاح.
- **تحديد معدّل الطلبات** لكل عميل، لمنع إساءة الاستخدام والاستنزاف.
- **CORS صريح** بلا أصول مفتوحة افتراضيًا.
- **تسجيل JSON منظَّم** + **سجلّ تدقيق دائم (SQLite)** لكل قرار امتثال — إغلاق فجوة إنتاجية جوهرية كانت موجودة في v0.1.0.
- **حدود صارمة على حجم المُدخلات** لمنع هجمات DoS عبر نصوص عقود ضخمة.
- API مُصدَّر تحت `/v1/*`.
- استعادة CI/Dependabot اللذين كانا غائبين عن شجرة العمل رغم وجودهما في تاريخ Git.
- `.env.example`، `docker-compose.yml` بوحدة تخزين دائمة، و`SECURITY.md` جديد.

## التحقق

- `python -m pytest --cov=sharia_ai --cov-report=term-missing --cov-fail-under=100` → **156 اختبارًا، تغطية 100%**
- `python -m ruff check .` → نظيف
- `python -m mypy src` → نظيف

## خطوة إلزامية قبل النشر

اضبط `SHARIA_AI_API_KEYS` بمفتاح عشوائي آمن (`python -c "import secrets; print(secrets.token_urlsafe(32))"`) قبل أي نشر خارج جهاز التطوير المحلي — وإلا ستُعطَّل المصادقة تلقائيًا. راجع [`SECURITY.md`](./SECURITY.md) و[`.env.example`](./.env.example).

## ما هو خارج نطاق هذا الإصدار (موثَّق عمدًا في SECURITY.md)

- لا صلاحيات متدرّجة (RBAC) — مفتاح API واحد بصلاحية كاملة.
- تحديد معدّل الطلبات في الذاكرة فقط (غير مشترك بين نسخ متعددة).
- سجلّ التدقيق SQLite محلي (غير موزَّع).

## تنبيه

هذه الأداة تساعد في الفرز الأولي والتدقيق التقني، ولا تصدر فتوى ولا تغني عن مراجعة هيئة رقابة شرعية معتمدة.
