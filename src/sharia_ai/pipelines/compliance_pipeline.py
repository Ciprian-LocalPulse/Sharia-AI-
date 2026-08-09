"""
compliance_pipeline.py — التنسيق الشامل لتدفق الامتثال الشرعي لشركة
واحدة: فرز الأسهم + فرز العقود + (اختياري) حساب الزكاة، مُجمَّعة في
تقرير موحّد، قابل للتصدير (dict/JSON).

هذه هي الطبقة التي تُبنى عليها الواجهة البرمجية (راجع api/main.py) وأي
تكامل خارجي (لوحة تحكم، نظام تخطيط موارد المؤسسات، نظام تدقيق).

المؤلف: Ciprian Ștefan Pleșca
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
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
    """يحوّل التقرير (بما في ذلك التعدادات والكائنات المتداخلة) إلى قاموس قابل للتسلسل."""

    def convert(obj):
        if isinstance(obj, dict):
            return {str(k): convert(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [convert(v) for v in obj]
        if hasattr(obj, "__dataclass_fields__"):
            return {k: convert(v) for k, v in asdict(obj, dict_factory=dict).items()}
        if hasattr(obj, "value") and not isinstance(obj, (int, float, str)):
            # تعداد (Enum)
            return obj.value
        return obj

    return convert(report)


class ShariaCompliancePipeline:
    """نقطة التنسيق المركزية — تُنشئ وتشغّل جميع الوحدات."""

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
            return "غير متوافق — فشل في فرز الأسهم"

        if contract_results:
            high_confidence_flags = [
                f
                for report in contract_results.values()
                for f in report.flags
                if f.confidence >= 0.85
            ]
            if high_confidence_flags:
                return "يتطلب مراجعة — تم اكتشاف بنود تعاقدية عالية الخطورة"

        return "متوافق (خاضع لمراجعة هيئة الرقابة الشرعية)"
