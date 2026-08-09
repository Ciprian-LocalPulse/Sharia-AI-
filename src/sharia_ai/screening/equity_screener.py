"""
equity_screener.py — Screening de conformitate Sharia pentru acțiuni/companii.

Aplică un proces în două etape, aliniat metodologiilor AAOIFI / DJIM / FTSE Shariah:

    1. Screening calitativ (de business): compania nu trebuie să opereze
       predominant într-un sector exclus, iar venitul din surse haram
       nu trebuie să depășească pragul configurat.
    2. Screening cantitativ (financiar): rate de îndatorare, lichiditate
       purtătoare de dobândă și creanțe raportate la capitalizarea bursieră.

Rezultatul este un `ScreeningResult` explicabil (fiecare regulă e
raportată individual), nu doar un verdict binar — esențial pentru
audit și pentru comitetele Sharia care trebuie să poată justifica decizia.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .rules import EXCLUDED_SECTORS, ScreeningThresholds


@dataclass
class CompanyFinancials:
    """Date financiare minime necesare pentru screening cantitativ."""

    name: str
    sector: str  # cheie din EXCLUDED_SECTORS, sau "other"
    market_cap: float
    interest_bearing_debt: float
    cash_and_interest_bearing_deposits: float
    accounts_receivable: float
    total_revenue: float
    haram_revenue: float = 0.0  # venit din activități secundare non-permise (ex: venit din dobândă incidental)


@dataclass
class RuleCheck:
    """Rezultatul unei singure verificări de conformitate."""

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
        status = "CONFORM" if self.is_compliant else "NECONFORM"
        lines = [f"[{status}] {self.company}"]
        for c in self.checks:
            mark = "OK " if c.passed else "FAIL"
            lines.append(f"  ({mark}) {c.rule}: {c.detail}")
        if self.purification_ratio > 0:
            lines.append(
                f"  -> Rată de purificare a dividendului recomandată: "
                f"{self.purification_ratio:.4%} din venitul distribuit"
            )
        return "\n".join(lines)


class EquityScreener:
    """Motor de screening configurabil pe bază de praguri."""

    def __init__(self, thresholds: ScreeningThresholds | None = None):
        self.thresholds = thresholds or ScreeningThresholds()

    def screen(self, company: CompanyFinancials) -> ScreeningResult:
        checks: list[RuleCheck] = []

        # --- 1. Screening sectorial (business) ---
        sector_excluded = company.sector in EXCLUDED_SECTORS
        checks.append(
            RuleCheck(
                rule="Activitate sectorială",
                passed=not sector_excluded,
                value=None,
                threshold=None,
                detail=(
                    f"Sector exclus: {EXCLUDED_SECTORS.get(company.sector, '-')}"
                    if sector_excluded
                    else f"Sector '{company.sector}' nu figurează pe lista de excludere"
                ),
            )
        )

        # --- 2. Venit haram secundar ---
        haram_ratio = self._safe_div(company.haram_revenue, company.total_revenue)
        checks.append(
            RuleCheck(
                rule="Venit din surse neconforme",
                passed=haram_ratio <= self.thresholds.max_haram_revenue_ratio,
                value=haram_ratio,
                threshold=self.thresholds.max_haram_revenue_ratio,
                detail=f"{haram_ratio:.2%} din venitul total (prag {self.thresholds.max_haram_revenue_ratio:.0%})",
            )
        )

        # --- 3. Datorie purtătoare de dobândă / capitalizare bursieră ---
        debt_ratio = self._safe_div(company.interest_bearing_debt, company.market_cap)
        checks.append(
            RuleCheck(
                rule="Îndatorare purtătoare de dobândă",
                passed=debt_ratio <= self.thresholds.max_debt_to_market_cap,
                value=debt_ratio,
                threshold=self.thresholds.max_debt_to_market_cap,
                detail=f"{debt_ratio:.2%} din cap. bursieră (prag {self.thresholds.max_debt_to_market_cap:.0%})",
            )
        )

        # --- 4. Numerar + depozite purtătoare de dobândă / capitalizare bursieră ---
        cash_ratio = self._safe_div(
            company.cash_and_interest_bearing_deposits, company.market_cap
        )
        checks.append(
            RuleCheck(
                rule="Lichiditate purtătoare de dobândă",
                passed=cash_ratio <= self.thresholds.max_cash_interest_to_market_cap,
                value=cash_ratio,
                threshold=self.thresholds.max_cash_interest_to_market_cap,
                detail=f"{cash_ratio:.2%} din cap. bursieră (prag {self.thresholds.max_cash_interest_to_market_cap:.0%})",
            )
        )

        # --- 5. Creanțe / capitalizare bursieră ---
        recv_ratio = self._safe_div(company.accounts_receivable, company.market_cap)
        checks.append(
            RuleCheck(
                rule="Creanțe comerciale",
                passed=recv_ratio <= self.thresholds.max_receivables_to_market_cap,
                value=recv_ratio,
                threshold=self.thresholds.max_receivables_to_market_cap,
                detail=f"{recv_ratio:.2%} din cap. bursieră (prag {self.thresholds.max_receivables_to_market_cap:.0%})",
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
