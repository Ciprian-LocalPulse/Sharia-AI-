# المساهمة

**المؤلف: Ciprian Ștefan Pleșca**

تم نقل دليل المساهمة الكامل إلى
[`docs/contributing.md`](./docs/contributing.md) للحفاظ على جذر
المشروع نظيفًا ومتوافقًا مع بنية التوثيق القياسية.

باختصار:

1. Fork + فرع مخصّص لكل تعديل.
2. `pip install -e ".[dev]"` لبيئة التطوير.
3. `ruff check src tests && mypy src && pytest --cov=sharia_ai` قبل الإيداع.
4. يجب أن يكون أي تعديل على عتبات الفرز أو معجم معالجة اللغة الطبيعية
   مصحوبًا بمصدر منهجي واختبار انحدار (يشمل حالة سلبية، لمنع
   الإيجابيات الكاذبة).
5. افتح طلب سحب (Pull Request) يصف بوضوح المشكلة التي تم حلّها.

راجع [`docs/contributing.md`](./docs/contributing.md) للتفاصيل الكاملة
و[`CODE_OF_CONDUCT.md`](./CODE_OF_CONDUCT.md) لقواعد المجتمع.
