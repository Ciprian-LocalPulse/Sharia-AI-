# مرجع الواجهة البرمجية

**المؤلف: Ciprian Ștefan Pleșca**

## واجهة برمجة REST (FastAPI)

التشغيل المحلي:

```bash
uvicorn sharia_ai.api.main:app --reload
```

توثيق تفاعلي يُولَّد تلقائيًا (Swagger UI): `http://localhost:8000/docs`

### `GET /health`

فحص سريع لحالة الخدمة.

```json
{ "status": "ok", "service": "Sharia-AI Compliance Toolkit API", "version": "0.1.0" }
```

### `POST /screening/equity`

**نص الطلب:**
```json
{
  "name": "مجموعة النور للتجزئة",
  "sector": "retail",
  "market_cap": 50000000,
  "interest_bearing_debt": 12000000,
  "cash_and_interest_bearing_deposits": 8000000,
  "accounts_receivable": 15000000,
  "total_revenue": 40000000,
  "haram_revenue": 500000
}
```

**الاستجابة:** `is_compliant` (منطقية)، `purification_ratio` (عدد
عشري)، وقائمة `checks[]` مفصّلة بكل قاعدة تم التحقق منها (`rule`،
`passed`، `value`، `threshold`، `detail`).

### `POST /screening/contract`

**نص الطلب:**
```json
{ "text": "يُسدد القرض بفائدة سنوية قدرها خمسة بالمئة." }
```

**الاستجابة:** `has_concerns` (منطقية)، `categories_found[]` (`riba` |
`gharar` | `maysir`)، `flags[]` تحتوي `sentence`، `category`،
`matched_term`، `confidence`.

### `POST /zakat/calculate`

**نص الطلب:**
```json
{
  "cash_and_equivalents": 2000000,
  "receivables_collectible": 1000000,
  "trade_inventory_value": 3000000,
  "short_term_liabilities": 800000
}
```

اختياري: `gold_price_per_gram`، `silver_price_per_gram` (وإلا تُستخدم
القيم الافتراضية من `utils/config.py`، القابلة للتهيئة عبر متغيرات
البيئة `SHARIA_AI_GOLD_PRICE_PER_GRAM` / `SHARIA_AI_SILVER_PRICE_PER_GRAM`).

**الاستجابة:** `net_zakatable_wealth`، `nisab_threshold_used`،
`nisab_metal`، `meets_nisab`، `zakat_due`، `breakdown` (تفصيل حسب نوع
الأصل).

### `POST /compliance/report`

يشغّل خط المعالجة الكامل (الأسهم + العقود + الزكاة) ويُعيد تقريرًا
مُجمَّعًا، مطابقًا للبنية التي ينتجها
`ShariaCompliancePipeline.run().to_json()`.

**نص الطلب:**
```json
{
  "company": { "...": "راجع مخطط CompanyFinancialsIn" },
  "contracts": { "contract1.txt": "نص العقد بالعربية..." },
  "zakat_assets": { "cash_and_equivalents": 2000000 }
}
```

---

## واجهة برمجة بايثون (استخدام مباشر، دون خادم)

### `sharia_ai.screening.equity_screener`

```python
EquityScreener(thresholds: ScreeningThresholds | None = None)
    .screen(company: CompanyFinancials) -> ScreeningResult
    .screen_batch(companies: list[CompanyFinancials]) -> list[ScreeningResult]
```

### `sharia_ai.nlp.riba_detector`

```python
LexicalRibaDetector(lexicon: dict | None = None)
    .analyze(contract_text: str) -> DetectionReport

HybridContractScreener(lexical_detector=None, ml_classifier=None)
    .analyze(contract_text: str) -> DetectionReport
```

### `sharia_ai.zakat.zakat_calculator`

```python
ZakatCalculator(gold_price_per_gram: float, silver_price_per_gram: float, use_lower_nisab: bool = True)
    .calculate(assets: ZakatAssets) -> ZakatResult
```

### `sharia_ai.pipelines.compliance_pipeline`

```python
ShariaCompliancePipeline(equity_screener=None, contract_screener=None, zakat_calculator=None)
    .run(company, contracts=None, zakat_assets=None) -> CompanyComplianceReport
```

`CompanyComplianceReport.to_json(indent=2) -> str` — تصدير كامل، جاهز
للأرشفة لأغراض التدقيق.
