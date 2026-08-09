"""
main.py — واجهة برمجية REST (FastAPI) لمجموعة أدوات Sharia-AI.

تكشف ثلاث فئات من نقاط النهاية (endpoints):
    POST /screening/equity      — فرز الامتثال لشركة معينة
    POST /screening/contract    — كشف الربا/الغرر/الميسر في نص عربي
    POST /zakat/calculate       — حساب الزكاة على أصول مُصرَّح بها
    POST /compliance/report     — تقرير مُجمَّع (خط المعالجة الكامل)

التشغيل المحلي:
    pip install -r requirements.txt
    uvicorn sharia_ai.api.main:app --reload

توثيق تفاعلي يُولَّد تلقائيًا: http://localhost:8000/docs

المؤلف: Ciprian Ștefan Pleșca
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from ..nlp.riba_detector import HybridContractScreener
from ..pipelines.compliance_pipeline import ShariaCompliancePipeline, asdict_safe
from ..screening.equity_screener import CompanyFinancials, EquityScreener
from ..utils.config import config
from ..zakat.zakat_calculator import ZakatAssets, ZakatCalculator

app = FastAPI(
    title=config.api_title,
    version=config.api_version,
    description=(
        "مجموعة أدوات مفتوحة المصدر للبيانات والذكاء الاصطناعي من أجل "
        "الامتثال في التقنية المالية المتوافقة مع الشريعة. أداة فرز أولي/"
        "مساعدة — لا تحل محل رأي هيئة رقابة شرعية معتمدة."
    ),
)

_equity_screener = EquityScreener()
_contract_screener = HybridContractScreener()


# ---------- مخططات Pydantic ----------

class CompanyFinancialsIn(BaseModel):
    name: str
    sector: str = Field(..., description="مفتاح القطاع، راجع screening/rules.py -> EXCLUDED_SECTORS")
    market_cap: float
    interest_bearing_debt: float
    cash_and_interest_bearing_deposits: float
    accounts_receivable: float
    total_revenue: float
    haram_revenue: float = 0.0


class ContractTextIn(BaseModel):
    text: str = Field(..., description="نص تعاقدي باللغة العربية")


class ZakatAssetsIn(BaseModel):
    cash_and_equivalents: float = 0.0
    receivables_collectible: float = 0.0
    trade_inventory_value: float = 0.0
    investments_market_value: float = 0.0
    gold_silver_value: float = 0.0
    short_term_liabilities: float = 0.0
    gold_price_per_gram: float | None = None
    silver_price_per_gram: float | None = None


class ComplianceReportIn(BaseModel):
    company: CompanyFinancialsIn
    contracts: dict[str, str] | None = None
    zakat_assets: ZakatAssetsIn | None = None


# ---------- نقاط النهاية (Endpoints) ----------

@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": config.api_title, "version": config.api_version}


@app.post("/screening/equity")
def screen_equity(payload: CompanyFinancialsIn) -> dict:
    company = CompanyFinancials(**payload.model_dump())
    result = _equity_screener.screen(company)
    return {
        "company": result.company,
        "is_compliant": result.is_compliant,
        "purification_ratio": result.purification_ratio,
        "checks": [c.__dict__ for c in result.checks],
    }


@app.post("/screening/contract")
def screen_contract(payload: ContractTextIn) -> dict:
    report = _contract_screener.analyze(payload.text)
    return {
        "has_concerns": report.has_concerns,
        "categories_found": [c.value for c in report.categories_found],
        "flags": [
            {
                "sentence": f.sentence,
                "category": f.category.value,
                "matched_term": f.matched_term,
                "confidence": f.confidence,
            }
            for f in report.flags
        ],
    }


@app.post("/zakat/calculate")
def calculate_zakat(payload: ZakatAssetsIn) -> dict:
    gold_price = payload.gold_price_per_gram or config.gold_price_per_gram
    silver_price = payload.silver_price_per_gram or config.silver_price_per_gram

    calculator = ZakatCalculator(
        gold_price_per_gram=gold_price,
        silver_price_per_gram=silver_price,
    )
    assets = ZakatAssets(
        cash_and_equivalents=payload.cash_and_equivalents,
        receivables_collectible=payload.receivables_collectible,
        trade_inventory_value=payload.trade_inventory_value,
        investments_market_value=payload.investments_market_value,
        gold_silver_value=payload.gold_silver_value,
        short_term_liabilities=payload.short_term_liabilities,
    )
    result = calculator.calculate(assets)
    return result.__dict__


@app.post("/compliance/report")
def compliance_report(payload: ComplianceReportIn) -> dict:
    zakat_calculator = None
    zakat_assets = None
    if payload.zakat_assets is not None:
        gold_price = payload.zakat_assets.gold_price_per_gram or config.gold_price_per_gram
        silver_price = payload.zakat_assets.silver_price_per_gram or config.silver_price_per_gram
        zakat_calculator = ZakatCalculator(gold_price, silver_price)
        zakat_assets = ZakatAssets(
            cash_and_equivalents=payload.zakat_assets.cash_and_equivalents,
            receivables_collectible=payload.zakat_assets.receivables_collectible,
            trade_inventory_value=payload.zakat_assets.trade_inventory_value,
            investments_market_value=payload.zakat_assets.investments_market_value,
            gold_silver_value=payload.zakat_assets.gold_silver_value,
            short_term_liabilities=payload.zakat_assets.short_term_liabilities,
        )

    pipeline = ShariaCompliancePipeline(zakat_calculator=zakat_calculator)

    try:
        company = CompanyFinancials(**payload.company.model_dump())
    except TypeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    report = pipeline.run(company=company, contracts=payload.contracts, zakat_assets=zakat_assets)
    return asdict_safe(report)
