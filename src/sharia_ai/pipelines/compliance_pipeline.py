"""
compliance_pipeline.py — Orchestrarea end-to-end a fluxului de conformitate
Sharia pentru o companie: screening de echitate + screening de contracte +
(opțional) calcul Zakat, agregate într-un raport unic, exportabil (dict/JSON).

Acesta este stratul pe care se construiește API-ul (vezi api/main.py) și
orice integrare externă (dashboard, ERP, sistem de audit).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from ..nlp.riba_detector import DetectionReport, HybridContractScreener
from ..screening.equity_screener import CompanyFinancials, EquityScreener, ScreeningResult
from ..zakat.zakat_calculator import ZakatAssets, ZakatCalculator, ZakatResult


@dataclass
class CompanyComplianceReport:
    company_name: str
    generated_at_utc: str
    equity_screening: ScreeningResult | None
    contract_screening: dict[str, DetectionReport] | None
    zakat: ZakatResult | None
    overall_status: str

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(asdict_safe(self), indent=indent, ensure_ascii=False)


def asdict_safe(report: CompanyComplianceReport) -> dict:
    """Convertește raportul (inclusiv enum-uri și obiecte imbricate) într-un dict serializabil."""

    def convert(obj):
        if isinstance(obj, dict):
            return {str(k): convert(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [convert(v) for v in obj]
        if hasattr(obj, "__dataclass_fields__"):
            return {k: convert(v) for k, v in asdict(obj, dict_factory=dict).items()}
        if hasattr(obj, "value") and not isinstance(obj, (int, float, str)):
            # Enum
            return obj.value
        return obj

    return convert(report)


class ShariaCompliancePipeline:
    """Punctul central de orchestrare — instanțiază și rulează toate modulele."""

    def __init__(
        self,
        equity_screener: EquityScreener | None = None,
        contract_screener: HybridContractScreener | None = None,
        zakat_calculator: ZakatCalculator | None = None,
    ):
        self.equity_screener = equity_screener or EquityScreener()
        self.contract_screener = contract_screener or HybridContractScreener()
        self.zakat_calculator = zakat_calculator

    def run(
        self,
        company: CompanyFinancials,
        contracts: dict[str, str] | None = None,
        zakat_assets: ZakatAssets | None = None,
    ) -> CompanyComplianceReport:
        equity_result = self.equity_screener.screen(company)

        contract_results: dict[str, DetectionReport] | None = None
        if contracts:
            contract_results = {
                doc_name: self.contract_screener.analyze(text)
                for doc_name, text in contracts.items()
            }

        zakat_result = None
        if zakat_assets is not None and self.zakat_calculator is not None:
            zakat_result = self.zakat_calculator.calculate(zakat_assets)

        overall_status = self._compute_overall_status(equity_result, contract_results)

        return CompanyComplianceReport(
            company_name=company.name,
            generated_at_utc=datetime.now(timezone.utc).isoformat(),
            equity_screening=equity_result,
            contract_screening=contract_results,
            zakat=zakat_result,
            overall_status=overall_status,
        )

    @staticmethod
    def _compute_overall_status(
        equity_result: ScreeningResult,
        contract_results: dict[str, DetectionReport] | None,
    ) -> str:
        if not equity_result.is_compliant:
            return "NECONFORM — eșec la screening de echitate"

        if contract_results:
            high_confidence_flags = [
                f
                for report in contract_results.values()
                for f in report.flags
                if f.confidence >= 0.85
            ]
            if high_confidence_flags:
                return "NECESITĂ REVIZUIRE — clauze contractuale cu risc ridicat detectate"

        return "CONFORM (sub rezerva revizuirii comitetului Sharia)"
