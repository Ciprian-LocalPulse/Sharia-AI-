# البنية المعمارية

**المؤلف: Ciprian Ștefan Pleșca**

## فلسفة التصميم

بُنِيَ Sharia-AI على أربعة مبادئ، مرتّبة بهذا الترتيب من حيث الأولوية:

1. **قابلية التفسير قبل الدقة الخام.** درجة امتثال بلا تبرير قاعدة
   بقاعدة عديمة الفائدة لهيئة رقابة شرعية يجب أن تبرر قراراتها. لذلك
   يكشف كل نتيجة (`ScreeningResult`، `DetectionReport`، `ZakatResult`)
   عن كل فحص فردي، وليس مجرد حكم مُجمَّع.
2. **العمل دون اتصال بالإنترنت كخيار افتراضي.** تعمل المؤسسات المالية
   غالبًا في بيئات معزولة (air-gapped) أو بمتطلبات صارمة لبقاء
   البيانات ضمن حدود جغرافية معينة. تستخدم النواة (`screening`،
   `nlp`، `zakat`، `pipelines`) فقط مكتبة بايثون القياسية — لا اعتماد
   خارجي إلزامي للمنطق الأساسي.
3. **قابلية التوسع دون إعادة الكتابة.** تتصل طبقات تعلّم الآلة (مثل
   مصنّف تحويلي للعربية) عبر واجهات (`Protocol`)، وليس عبر وراثة
   جامدة — راجع `RibaClassifierProtocol`.
4. **التهيئة، لا الترميز الثابت.** جميع العتبات المالية (نسب
   المديونية، النصاب، معدّل الزكاة) معاملات، وليست ثوابت مُدمجة في
   المنطق — راجع `screening/rules.py` و`data/rules/aaoifi_thresholds.yaml`.

## مخطط المكوّنات

```
                        ┌─────────────────────────┐
                        │  واجهة برمجية REST (FastAPI) │
                        │      api/main.py        │
                        └────────────┬────────────┘
                                     │
                        ┌────────────▼────────────┐
                        │  ShariaCompliancePipeline│
                        │  pipelines/compliance_   │
                        │  pipeline.py             │
                        └───┬──────────┬───────────┘
             ┌──────────────┘          └──────────────┐
             │                                          │
   ┌─────────▼─────────┐                    ┌──────────▼──────────┐
   │  EquityScreener     │                    │ HybridContractScreener│
   │  screening/          │                    │ nlp/riba_detector.py │
   │  equity_screener.py  │                    └──────────┬──────────┘
   └─────────┬─────────┘                                  │
             │                                  ┌──────────▼──────────┐
             │                                  │ LexicalRibaDetector │
             │                                  │ (حتمي،              │
             │                                  │  غير متصل بالإنترنت)│
             │                                  └──────────┬──────────┘
             │                                              │ (اختياري)
             │                                  ┌──────────▼──────────┐
             │                                  │ RibaClassifierProtocol│
             │                                  │ (نموذج تعلّم آلة خارجي،│
             │                                  │  مثل AraBERT)        │
             │                                  └──────────────────────┘
   ┌─────────▼─────────┐
   │  ZakatCalculator    │
   │  zakat/zakat_        │
   │  calculator.py       │
   └───────────────────┘
```

## مسار طلب الامتثال

1. يبني العميل (واجهة برمجية، سكريبت، دفتر ملاحظات) كائن
   `CompanyFinancials`.
2. تستدعي `ShariaCompliancePipeline.run()` دالة `EquityScreener.screen()`،
   التي تطبّق بالتتابع قواعد الاستبعاد القطاعي والنسب المالية الأربع من
   `ScreeningThresholds`.
3. إذا تم توفير عقود، يمرّ كل مستند عبر `HybridContractScreener`، التي
   تشغّل أولًا `LexicalRibaDetector` (حتمي)، وإذا كانت مُهيَّأة، تجمّع
   أيضًا نتائج مصنّف تعلّم آلة خارجي.
4. إذا تم توفير أصول، تحسب `ZakatCalculator` صافي الثروة الخاضعة
   للزكاة، وعتبة النصاب (ذهب/فضة، قابلة للتهيئة)، والمبلغ المستحق.
5. تُجمَّع النتائج في `CompanyComplianceReport`، قابل للتسلسل مباشرة
   بصيغة JSON عبر `to_json()`.

## قابلية التوسع لمعالجة اللغة الطبيعية

المحرك المعجمي (`LexicalRibaDetector`) بسيط وحتمي عمدًا — مناسب كمرشّح
أول ضمن خط معالجة منظَّم، حيث تُعتبر قابلية التدقيق بنفس أهمية معدّل
الاستدعاء. للحصول على تغطية دلالية أعمق (إعادة الصياغة، الصيغ غير
المباشرة للفائدة إلخ)، المشروع جاهز لدمج نموذج تحويلي عبر
`RibaClassifierProtocol`:

```python
from sharia_ai.nlp.riba_detector import ConcernCategory, RibaClassifierProtocol

class AraBertRibaClassifier:
    def __init__(self, model_path: str):
        # تحميل النموذج المُدرَّب (مثل transformers.AutoModelForSequenceClassification)
        ...

    def predict(self, sentence: str) -> list[tuple[ConcernCategory, float]]:
        # تشغيل الاستدلال وربط قيم logit بـ (الفئة، الدرجة)
        ...

from sharia_ai.nlp.riba_detector import HybridContractScreener, LexicalRibaDetector

screener = HybridContractScreener(
    lexical_detector=LexicalRibaDetector(),
    ml_classifier=AraBertRibaClassifier("path/to/model"),
)
```

لا حاجة لتعديل أي كود من `pipelines` أو `api` للاستفادة من هذا الترقية
— تضمن واجهة `Protocol` التوافقية.

## التهيئة الخارجية (YAML ← العتبات)

للتكامل مع أنظمة تهيئة خارجية (لوحة تدقيق، سياسات CI/CD)، يعكس
`data/rules/aaoifi_thresholds.yaml` القيم من `screening/rules.py`. مثال
على أداة تحميل (يتطلب `pyyaml`، إضافة اختيارية):

```python
import yaml
from sharia_ai.screening.rules import ScreeningThresholds

with open("data/rules/aaoifi_thresholds.yaml", encoding="utf-8") as f:
    raw = yaml.safe_load(f)

thresholds = ScreeningThresholds(
    max_haram_revenue_ratio=raw["business_screening"]["max_haram_revenue_ratio"],
    max_debt_to_market_cap=raw["financial_ratios"]["max_debt_to_market_cap"],
    max_cash_interest_to_market_cap=raw["financial_ratios"]["max_cash_interest_to_market_cap"],
    max_receivables_to_market_cap=raw["financial_ratios"]["max_receivables_to_market_cap"],
    purification_threshold=raw["purification"]["purification_threshold"],
)
```

## اعتبارات الأمان وخصوصية البيانات

- لا تحتفظ الأدوات بالبيانات افتراضيًا — كل استدعاء عديم الحالة (stateless).
- للتكامل مع بيانات مالية حقيقية، يوصى بتشغيل الواجهة البرمجية داخل
  محيط شبكة المؤسسة (وليس مكشوفًا للعموم دون مصادقة/تفويض إضافيين —
  راجع `docs/roadmap.md`، عنصر "مصادقة الواجهة البرمجية").
- يحتوي معجم معالجة اللغة الطبيعية فقط على مصطلحات مالية/قانونية عامة
  — لا يعالج أو يخزّن بيانات شخصية.
