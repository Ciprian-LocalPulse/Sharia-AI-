"""FastAPI service layer for Sharia-AI."""

from __future__ import annotations

import logging
import secrets
import time
from typing import Annotated, Any
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field, field_validator

from ..nlp.riba_detector import HybridContractScreener
from ..pipelines.compliance_pipeline import ShariaCompliancePipeline, asdict_safe
from ..screening.equity_screener import CompanyFinancials, EquityScreener
from ..utils.config import config
from ..zakat.zakat_calculator import ZakatAssets, ZakatCalculator
from .audit import AuditEvent, SQLiteAuditStore
from .observability import FixedWindowRateLimiter, logger, metrics

app = FastAPI(
    title=config.api_title,
    version=config.api_version,
    description=(
        "Open-source toolkit for Sharia-compliant fintech screening. "
        "This API is a decision-support tool and does not replace a qualified Sharia board."
    ),
)

if not logging.getLogger().handlers:  # pragma: no cover
    logging.basicConfig(level=logging.INFO)

if config.cors_allowed_origins:  # pragma: no cover
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(config.cors_allowed_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type", "X-API-Key", "X-Request-ID"],
    )

_equity_screener = EquityScreener()
_contract_screener = HybridContractScreener()
_rate_limiter = FixedWindowRateLimiter(config.rate_limit_per_minute)
_audit_store = SQLiteAuditStore(config.audit_log_path)
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

FiniteNonNegative = Annotated[float, Field(ge=0.0, allow_inf_nan=False)]
FinitePositive = Annotated[float, Field(gt=0.0, allow_inf_nan=False)]


def _client_key(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    if request.client is None:
        return "unknown"
    return request.client.host


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid4()))
    request.state.request_id = request_id

    if not _rate_limiter.allow(_client_key(request)):
        metrics.total_requests += 1
        metrics.rate_limited_requests += 1
        metrics.status_counts["429"] = metrics.status_counts.get("429", 0) + 1
        logger.warning("rate_limited request_id=%s path=%s", request_id, request.url.path)
        return JSONResponse(
            status_code=429,
            content={"detail": "rate limit exceeded", "request_id": request_id},
            headers={"X-Request-ID": request_id},
        )

    started = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - started) * 1000
    response.headers["X-Request-ID"] = request_id

    metrics.total_requests += 1
    status_key = str(response.status_code)
    metrics.status_counts[status_key] = metrics.status_counts.get(status_key, 0) + 1
    logger.info(
        "request request_id=%s method=%s path=%s status=%s elapsed_ms=%.2f",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


def require_api_key(api_key: str | None = Depends(_api_key_header)) -> None:
    if not config.api_keys:
        return
    if api_key and any(secrets.compare_digest(api_key, valid) for valid in config.api_keys):
        return
    raise HTTPException(status_code=401, detail="valid API key required")


def _record_audit(
    request: Request,
    endpoint: str,
    subject: str,
    decision: str,
    payload: dict[str, Any],
) -> None:
    try:
        _audit_store.record(
            AuditEvent(
                request_id=request.state.request_id,
                endpoint=endpoint,
                subject=subject,
                decision=decision,
                payload=payload,
            )
        )
    except OSError as exc:
        logger.warning("audit_write_failed request_id=%s error=%s", request.state.request_id, exc)


class CompanyFinancialsIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    sector: str = Field(..., min_length=1, max_length=80)
    market_cap: FinitePositive
    interest_bearing_debt: FiniteNonNegative
    cash_and_interest_bearing_deposits: FiniteNonNegative
    accounts_receivable: FiniteNonNegative
    total_revenue: FinitePositive
    haram_revenue: FiniteNonNegative = 0.0


class ContractTextIn(BaseModel):
    text: str = Field(..., min_length=1, max_length=config.max_contract_chars)


class ZakatAssetsIn(BaseModel):
    cash_and_equivalents: FiniteNonNegative = 0.0
    receivables_collectible: FiniteNonNegative = 0.0
    trade_inventory_value: FiniteNonNegative = 0.0
    investments_market_value: FiniteNonNegative = 0.0
    gold_silver_value: FiniteNonNegative = 0.0
    short_term_liabilities: FiniteNonNegative = 0.0
    gold_price_per_gram: FinitePositive | None = None
    silver_price_per_gram: FinitePositive | None = None


class ComplianceReportIn(BaseModel):
    company: CompanyFinancialsIn
    contracts: dict[str, str] | None = Field(default=None, max_length=25, validate_default=True)
    zakat_assets: ZakatAssetsIn | None = None

    @field_validator("contracts")
    @classmethod
    def validate_contracts(cls, value: dict[str, str] | None) -> dict[str, str] | None:
        if value is None:
            return None
        for name, text in value.items():
            if not name or len(name) > 200:
                raise ValueError("contract names must be 1-200 characters")
            if not text or len(text) > config.max_contract_chars:
                raise ValueError("contract text exceeds configured maximum length")
        return value


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": config.api_title, "version": config.api_version}


@app.get("/metrics", dependencies=[Depends(require_api_key)])
def api_metrics() -> dict:
    return metrics.snapshot()


@app.post("/v1/screening/equity", dependencies=[Depends(require_api_key)])
@app.post("/screening/equity", dependencies=[Depends(require_api_key)])
def screen_equity(payload: CompanyFinancialsIn, request: Request) -> dict:
    company = CompanyFinancials(**payload.model_dump())
    result = _equity_screener.screen(company)
    response = {
        "company": result.company,
        "is_compliant": result.is_compliant,
        "purification_ratio": result.purification_ratio,
        "checks": [c.__dict__ for c in result.checks],
    }
    _record_audit(
        request,
        "screening.equity",
        result.company,
        "compliant" if result.is_compliant else "non_compliant",
        response,
    )
    return response


@app.post("/v1/screening/contract", dependencies=[Depends(require_api_key)])
@app.post("/screening/contract", dependencies=[Depends(require_api_key)])
def screen_contract(payload: ContractTextIn, request: Request) -> dict:
    report = _contract_screener.analyze(payload.text)
    response = {
        "has_concerns": report.has_concerns,
        "categories_found": [c.value for c in report.categories_found],
        "flags": [
            {
                "sentence": flag.sentence,
                "category": flag.category.value,
                "matched_term": flag.matched_term,
                "confidence": flag.confidence,
            }
            for flag in report.flags
        ],
    }
    _record_audit(
        request,
        "screening.contract",
        "contract_text",
        "concerns_found" if report.has_concerns else "no_concerns",
        {
            "text_length_chars": report.text_length_chars,
            "categories_found": response["categories_found"],
            "flag_count": len(report.flags),
        },
    )
    return response


@app.post("/v1/zakat/calculate", dependencies=[Depends(require_api_key)])
@app.post("/zakat/calculate", dependencies=[Depends(require_api_key)])
def calculate_zakat(payload: ZakatAssetsIn, request: Request) -> dict:
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
    _record_audit(
        request,
        "zakat.calculate",
        "assets",
        "zakat_due" if result.zakat_due else "no_zakat_due",
        response,
    )
    return response


@app.post("/v1/compliance/report", dependencies=[Depends(require_api_key)])
@app.post("/compliance/report", dependencies=[Depends(require_api_key)])
def compliance_report_endpoint(payload: ComplianceReportIn, request: Request) -> dict:
    return compliance_report(payload, request=request)


def compliance_report(payload: ComplianceReportIn, request: Request | None = None) -> dict:
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
    if request is not None:
        _record_audit(
            request,
            "compliance.report",
            report.company_name,
            report.overall_status,
            {
                "overall_status": report.overall_status,
                "has_contract_screening": report.contract_screening is not None,
                "has_zakat": report.zakat is not None,
                "equity_is_compliant": (
                    report.equity_screening.is_compliant if report.equity_screening else None
                ),
            },
        )
    return response
