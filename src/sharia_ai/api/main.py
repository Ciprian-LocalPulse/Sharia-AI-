"""
main.py — واجهة برمجية REST (FastAPI) لمجموعة أدوات Sharia-AI، جاهزة
للإنتاج: مصادقة عبر مفتاح API، تحديد معدّل الطلبات، CORS مُهيَّأ صراحةً،
تسجيل منظَّم (JSON)، سجلّ تدقيق دائم (SQLite)، وحدود حجم للمُدخلات.

تكشف أربع فئات من نقاط النهاية (endpoints)، جميعها تحت البادئة /v1:
    POST /v1/screening/equity      — فرز الامتثال لشركة معينة
    POST /v1/screening/contract    — كشف الربا/الغرر/الميسر في نص عربي
    POST /v1/zakat/calculate       — حساب الزكاة على أصول مُصرَّح بها
    POST /v1/compliance/report     — تقرير مُجمَّع (خط المعالجة الكامل)
    GET  /v1/audit/recent          — آخر إدخالات سجلّ التدقيق (يتطلّب مصادقة)
    GET  /health                   — فحص صحة الخدمة (بدون مصادقة، لأدوات orchestration)

التشغيل المحلي:
    pip install -r requirements.txt
    uvicorn sharia_ai.api.main:app --reload

توثيق تفاعلي يُولَّد تلقائيًا: http://localhost:8000/docs

المؤلف: Ciprian Ștefan Pleșca
"""

from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from ..audit.audit_log import AuditLog
from ..nlp.riba_detector import HybridContractScreener
from ..pipelines.compliance_pipeline import ShariaCompliancePipeline, asdict_safe
from ..screening.equity_screener import CompanyFinancials, EquityScreener
from ..utils.config import config
from ..utils.logging_setup import configure_logging, get_logger, log_with_fields
from ..zakat.zakat_calculator import ZakatAssets, ZakatCalculator
from .security import client_identifier, enforce_rate_limit, require_api_key

configure_logging(config.log_level)
logger = get_logger("sharia_ai.api")

_equity_screener = EquityScreener()
_contract_screener = HybridContractScreener()
_audit_log = AuditLog(config.audit_db_path) if config.audit_enabled else None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    log_with_fields(
        logger,
        20,
        "بدء تشغيل الخدمة",
        environment=config.environment,
        require_api_key=config.require_api_key,
        audit_enabled=config.audit_enabled,
    )
    yield
    log_with_fields(logger, 20, "إيقاف تشغيل الخدمة")


app = FastAPI(
    title=config.api_title,
    version=config.api_version,
    description=(
        "مجموعة أدوات مفتوحة المصدر للبيانات والذكاء الاصطناعي من أجل "
        "الامتثال في التقنية المالية المتوافقة مع الشريعة. أداة فرز أولي/"
        "مساعدة — لا تحل محل رأي هيئة رقابة شرعية معتمدة."
    ),
    lifespan=lifespan,
)

# --- CORS: صريح، بلا "*" افتراضي غير آمن. فارغ = بلا أصول مسموحة عبر المتصفح. ---
if config.cors_allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["X-API-Key", "Content-Type"],
    )


# --- وسيط: معرِّف طلب + تسجيل منظَّم لكل استجابة ---
@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start = time.monotonic()
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = round((time.monotonic() - start) * 1000, 2)
        log_with_fields(
            logger,
            40,
            "استثناء غير مُعالَج أثناء تنفيذ الطلب",
            request_id=request_id,
            path=request.url.path,
            method=request.method,
            duration_ms=duration_ms,
        )
        raise
    duration_ms = round((time.monotonic() - start) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    log_with_fields(
        logger,
        20,
        "تم تنفيذ الطلب",
        request_id=request_id,
        path=request.url.path,
        method=request.method,
        status_code=response.status_code,
        duration_ms=duration_ms,
        client=client_identifier(request),
    )
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """يمنع تسرّب تفاصيل الاستثناء الداخلي (stack trace) إلى المستخدم
    النهائي، مع تسجيل كامل التفاصيل داخليًا."""
    log_with_fields(
        logger,
        40,
        "خطأ داخلي غير متوقّع",
        path=request.url.path,
        error_type=type(exc).__name__,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "حدث خطأ داخلي غير متوقّع. تم تسجيل الحادثة للمراجعة."},
    )


# ---------- مخططات Pydantic ----------

class CompanyFinancialsIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=300)
    sector: str = Field(..., description="مفتاح القطاع، راجع screening/rules.py -> EXCLUDED_SECTORS")
    market_cap: float = Field(..., gt=0, description="القيمة السوقية، يجب أن تكون أكبر من صفر")
    interest_bearing_debt: float = Field(..., ge=0)
    cash_and_interest_bearing_deposits: float = Field(..., ge=0)
    accounts_receivable: float = Field(..., ge=0)
    total_revenue: float = Field(..., ge=0)
    haram_revenue: float = Field(default=0.0, ge=0)


class ContractTextIn(BaseModel):
    text: str = Field(..., min_length=1, description="نص تعاقدي باللغة العربية")

    @field_validator("text")
    @classmethod
    def _enforce_max_length(cls, value: str) -> str:
        if len(value) > config.max_contract_text_chars:
            raise ValueError(
                f"النص يتجاوز الحد الأقصى المسموح ({config.max_contract_text_chars} حرفًا)."
            )
        return value


class ZakatAssetsIn(BaseModel):
    cash_and_equivalents: float = Field(default=0.0, ge=0)
    receivables_collectible: float = Field(default=0.0, ge=0)
    trade_inventory_value: float = Field(default=0.0, ge=0)
    investments_market_value: float = Field(default=0.0, ge=0)
    gold_silver_value: float = Field(default=0.0, ge=0)
    short_term_liabilities: float = Field(default=0.0, ge=0)
    gold_price_per_gram: float | None = Field(default=None, gt=0)
    silver_price_per_gram: float | None = Field(default=None, gt=0)


class ComplianceReportIn(BaseModel):
    company: CompanyFinancialsIn
    contracts: dict[str, str] | None = None
    zakat_assets: ZakatAssetsIn | None = None

    @field_validator("contracts")
    @classmethod
    def _enforce_contracts_limit(cls, value: dict[str, str] | None) -> dict[str, str] | None:
        if value is None:
            return value
        for text in value.values():
            if len(text) > config.max_contract_text_chars:
                raise ValueError(
                    f"أحد نصوص العقود يتجاوز الحد الأقصى المسموح "
                    f"({config.max_contract_text_chars} حرفًا)."
                )
        return value


# ---------- نقاط النهاية (Endpoints) ----------

@app.get("/health")
def health() -> dict:
    """فحص صحة بدون مصادقة، مخصَّص لأدوات orchestration (Docker/K8s)."""
    return {"status": "ok", "service": config.api_title, "version": config.api_version}


@app.post("/v1/screening/equity", dependencies=[Depends(enforce_rate_limit)])
def screen_equity(
    payload: CompanyFinancialsIn,
    request: Request,
    api_key: str = Depends(require_api_key),
) -> dict:
    company = CompanyFinancials(**payload.model_dump())
    result = _equity_screener.screen(company)
    response = {
        "company": result.company,
        "is_compliant": result.is_compliant,
        "purification_ratio": result.purification_ratio,
        "checks": [c.__dict__ for c in result.checks],
    }
    if _audit_log is not None:
        _audit_log.record(
            event_type="equity_screening",
            subject=result.company,
            outcome_summary="متوافق" if result.is_compliant else "غير متوافق",
            payload=response,
            client_id=client_identifier(request),
        )
    return response


@app.post("/v1/screening/contract", dependencies=[Depends(enforce_rate_limit)])
def screen_contract(
    payload: ContractTextIn,
    request: Request,
    api_key: str = Depends(require_api_key),
) -> dict:
    report = _contract_screener.analyze(payload.text)
    response = {
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
    if _audit_log is not None:
        _audit_log.record(
            event_type="contract_screening",
            subject=f"contract:{len(payload.text)}chars",
            outcome_summary="concerns_found" if report.has_concerns else "clean",
            payload=response,
            client_id=client_identifier(request),
        )
    return response


@app.post("/v1/zakat/calculate", dependencies=[Depends(enforce_rate_limit)])
def calculate_zakat(
    payload: ZakatAssetsIn,
    request: Request,
    api_key: str = Depends(require_api_key),
) -> dict:
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
    response = result.__dict__
    if _audit_log is not None:
        _audit_log.record(
            event_type="zakat_calculation",
            subject=f"zakat:{client_identifier(request)}",
            outcome_summary=f"due={result.zakat_due}",
            payload=response,
            client_id=client_identifier(request),
        )
    return response


@app.post("/v1/compliance/report", dependencies=[Depends(enforce_rate_limit)])
def compliance_report(
    payload: ComplianceReportIn,
    request: Request,
    api_key: str = Depends(require_api_key),
) -> dict:
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
    response = asdict_safe(report)
    if _audit_log is not None:
        _audit_log.record(
            event_type="compliance_report",
            subject=company.name,
            outcome_summary=report.overall_status,
            payload=response,
            client_id=client_identifier(request),
        )
    return response


@app.get("/v1/audit/recent")
def audit_recent(
    limit: int = 50,
    event_type: str | None = None,
    api_key: str = Depends(require_api_key),
) -> dict:
    """يُعيد آخر إدخالات سجلّ التدقيق — يتطلّب مصادقة دائمًا (بيانات
    حسّاسة قد تحتوي معلومات عن شركات/عقود حقيقية)."""
    if _audit_log is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="سجلّ التدقيق معطَّل في هذه النشرة (SHARIA_AI_AUDIT_ENABLED=false).",
        )
    limit = max(1, min(limit, 500))
    entries = _audit_log.fetch_recent(limit=limit, event_type=event_type)
    return {
        "total_entries": _audit_log.count(),
        "returned": len(entries),
        "entries": [entry.__dict__ for entry in entries],
    }
