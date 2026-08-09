"""
equity_screener.py — فرز الامتثال الشرعي للأسهم/الشركات.

يطبّق عملية على مرحلتين، متوافقة مع منهجيات AAOIFI / DJIM / FTSE Shariah:

    1. الفرز النوعي (النشاط التجاري): يجب ألا تعمل الشركة بشكل غالب في
       قطاع مستبعَد، ويجب ألا يتجاوز الدخل من مصادر حرام العتبة المُهيَّأة.
    2. الفرز الكمي (المالي): نسب المديونية، السيولة التي تحمل فائدة،
       والذمم المدينة منسوبة إلى القيمة السوقية.

النتيجة هي `ScreeningResult` قابل للتفسير (يُبلَّغ عن كل قاعدة بشكل
فردي)، وليس مجرد حكم ثنائي — أمر ضروري للتدقيق ولهيئات الرقابة الشرعية
التي يجب أن تكون قادرة على تبرير قرارها.

المؤلف: Ciprian Ștefan Pleșca
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .rules import EXCLUDED_SECTORS, ScreeningThresholds


@dataclass
class CompanyFinancials:
    """البيانات المالية الدنيا اللازمة للفرز الكمي."""

    name: str
    sector: str  # مفتاح من EXCLUDED_SECTORS، أو "other"
    market_cap: float
    interest_bearing_debt: float
    cash_and_interest_bearing_deposits: float
    accounts_receivable: float
    total_revenue: float
    haram_revenue: float = 0.0  # دخل من أنشطة ثانوية غير مسموحة (مثل دخل الفائدة العرضي)


@dataclass
class RuleCheck:
    """نتيجة فحص امتثال واحد."""

    rule: str
    passed: bool
    value: Optional[float]
    threshold: Optional[float]
    detail: str


@dataclass
class ScreeningResult:
    company: str
    is_compliant: bool
    checks: list[RuleCheck] = field(default_factory=list)
    purification_ratio: float = 0.0

    def summary(self) -> str:
        status = "متوافق" if self.is_compliant else "غير متوافق"
        lines = [f"[{status}] {self.company}"]
        for c in self.checks:
            mark = "نجح" if c.passed else "فشل"
            lines.append(f"  ({mark}) {c.rule}: {c.detail}")
        if self.purification_ratio > 0:
            lines.append(
                f"  -> نسبة التنقية الموصى بها للأرباح الموزّعة: "
                f"{self.purification_ratio:.4%} من الدخل الموزَّع"
            )
        return "\n".join(lines)


class EquityScreener:
    """محرك فرز قابل للتهيئة استنادًا إلى عتبات."""

    def __init__(self, thresholds: ScreeningThresholds | None = None):
        self.thresholds = thresholds or ScreeningThresholds()

    def screen(self, company: CompanyFinancials) -> ScreeningResult:
        checks: list[RuleCheck] = []

        # --- 1. الفرز القطاعي (النشاط التجاري) ---
        sector_excluded = company.sector in EXCLUDED_SECTORS
        checks.append(
            RuleCheck(
                rule="النشاط القطاعي",
                passed=not sector_excluded,
                value=None,
                threshold=None,
                detail=(
                    f"قطاع مستبعَد: {EXCLUDED_SECTORS.get(company.sector, '-')}"
                    if sector_excluded
                    else f"القطاع '{company.sector}' لا يظهر في قائمة الاستبعاد"
                ),
            )
        )

        # --- 2. الدخل الحرام الثانوي ---
        haram_ratio = self._safe_div(company.haram_revenue, company.total_revenue)
        checks.append(
            RuleCheck(
                rule="الدخل من مصادر غير متوافقة",
                passed=haram_ratio <= self.thresholds.max_haram_revenue_ratio,
                value=haram_ratio,
                threshold=self.thresholds.max_haram_revenue_ratio,
                detail=f"{haram_ratio:.2%} من إجمالي الدخل (العتبة {self.thresholds.max_haram_revenue_ratio:.0%})",
            )
        )

        # --- 3. الديون التي تحمل فائدة / القيمة السوقية ---
        debt_ratio = self._safe_div(company.interest_bearing_debt, company.market_cap)
        checks.append(
            RuleCheck(
                rule="المديونية التي تحمل فائدة",
                passed=debt_ratio <= self.thresholds.max_debt_to_market_cap,
                value=debt_ratio,
                threshold=self.thresholds.max_debt_to_market_cap,
                detail=f"{debt_ratio:.2%} من القيمة السوقية (العتبة {self.thresholds.max_debt_to_market_cap:.0%})",
            )
        )

        # --- 4. النقد + الودائع التي تحمل فائدة / القيمة السوقية ---
        cash_ratio = self._safe_div(
            company.cash_and_interest_bearing_deposits, company.market_cap
        )
        checks.append(
            RuleCheck(
                rule="السيولة التي تحمل فائدة",
                passed=cash_ratio <= self.thresholds.max_cash_interest_to_market_cap,
                value=cash_ratio,
                threshold=self.thresholds.max_cash_interest_to_market_cap,
                detail=f"{cash_ratio:.2%} من القيمة السوقية (العتبة {self.thresholds.max_cash_interest_to_market_cap:.0%})",
            )
        )

        # --- 5. الذمم المدينة / القيمة السوقية ---
        recv_ratio = self._safe_div(company.accounts_receivable, company.market_cap)
        checks.append(
            RuleCheck(
                rule="الذمم المدينة التجارية",
                passed=recv_ratio <= self.thresholds.max_receivables_to_market_cap,
                value=recv_ratio,
                threshold=self.thresholds.max_receivables_to_market_cap,
                detail=f"{recv_ratio:.2%} من القيمة السوقية (العتبة {self.thresholds.max_receivables_to_market_cap:.0%})",
            )
        )

        is_compliant = all(c.passed for c in checks)

        result = ScreeningResult(
            company=company.name,
            is_compliant=is_compliant,
            checks=checks,
            purification_ratio=haram_ratio if is_compliant and haram_ratio > 0 else 0.0,
        )
        return result

    def screen_batch(self, companies: list[CompanyFinancials]) -> list[ScreeningResult]:
        return [self.screen(c) for c in companies]

    @staticmethod
    def _safe_div(numerator: float, denominator: float) -> float:
        if not denominator:
            return 0.0
        return numerator / denominator
