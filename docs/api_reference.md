# Referință API

## API REST (FastAPI)

Pornire locală:

```bash
uvicorn sharia_ai.api.main:app --reload
```

Documentație interactivă auto-generată (Swagger UI): `http://localhost:8000/docs`

### `GET /health`

Verificare rapidă a stării serviciului.

```json
{ "status": "ok", "service": "Sharia-AI Compliance Toolkit API", "version": "0.1.0" }
```

### `POST /screening/equity`

**Body:**
```json
{
  "name": "Al-Noor Retail Group",
  "sector": "retail",
  "market_cap": 50000000,
  "interest_bearing_debt": 12000000,
  "cash_and_interest_bearing_deposits": 8000000,
  "accounts_receivable": 15000000,
  "total_revenue": 40000000,
  "haram_revenue": 500000
}
```

**Răspuns:** `is_compliant` (bool), `purification_ratio` (float), și lista
detaliată `checks[]` cu fiecare regulă verificată (`rule`, `passed`,
`value`, `threshold`, `detail`).

### `POST /screening/contract`

**Body:**
```json
{ "text": "يُسدد القرض بفائدة سنوية قدرها خمسة بالمئة." }
```

**Răspuns:** `has_concerns` (bool), `categories_found[]` (`riba` | `gharar`
| `maysir`), `flags[]` cu `sentence`, `category`, `matched_term`, `confidence`.

### `POST /zakat/calculate`

**Body:**
```json
{
  "cash_and_equivalents": 2000000,
  "receivables_collectible": 1000000,
  "trade_inventory_value": 3000000,
  "short_term_liabilities": 800000
}
```

Opțional: `gold_price_per_gram`, `silver_price_per_gram` (altfel se
folosesc valorile implicite din `utils/config.py`, configurabile prin
variabile de mediu `SHARIA_AI_GOLD_PRICE_PER_GRAM` / `SHARIA_AI_SILVER_PRICE_PER_GRAM`).

**Răspuns:** `net_zakatable_wealth`, `nisab_threshold_used`, `nisab_metal`,
`meets_nisab`, `zakat_due`, `breakdown` (defalcare pe tip de activ).

### `POST /compliance/report`

Rulează pipeline-ul complet (echitate + contracte + Zakat) și returnează
un raport agregat, identic cu structura produsă de
`ShariaCompliancePipeline.run().to_json()`.

**Body:**
```json
{
  "company": { "...": "vezi schema CompanyFinancialsIn" },
  "contracts": { "contract1.txt": "نص العقد بالعربية..." },
  "zakat_assets": { "cash_and_equivalents": 2000000 }
}
```

---

## API Python (utilizare directă, fără server)

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

`CompanyComplianceReport.to_json(indent=2) -> str` — export complet, gata
de arhivare pentru audit.
