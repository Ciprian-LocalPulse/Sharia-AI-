"""
zakat_calculator.py — Motor de calcul Zakat pentru active corporative/personale
lichide, aliniat interpretării clasice majoritare (2.5% asupra activelor
eligibile care depășesc pragul Nisab, deținute pe durata unui an lunar/hawl).

Acest modul NU emite fatwa și nu înlocuiește un consilier Sharia calificat
pentru cazuri complexe (ex: zakat pe inventar comercial, active mixte,
datorii pe termen lung). Este un instrument de calcul asistat, transparent
și auditabil (fiecare pas al calculului este expus).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..screening.rules import NISAB_GOLD_GRAMS, NISAB_SILVER_GRAMS, ZAKAT_RATE


@dataclass
class ZakatAssets:
    """Activele eligibile pentru calculul Zakat (valori monetare, aceeași monedă)."""

    cash_and_equivalents: float = 0.0
    receivables_collectible: float = 0.0       # creanțe cu șanse rezonabile de încasare
    trade_inventory_value: float = 0.0          # marfă destinată vânzării, la valoare de piață
    investments_market_value: float = 0.0       # acțiuni/fonduri Sharia-compliant, la valoare de piață
    gold_silver_value: float = 0.0

    short_term_liabilities: float = 0.0          # datorii scadente în anul curent, deductibile


@dataclass
class ZakatResult:
    total_eligible_assets: float
    deductible_liabilities: float
    net_zakatable_wealth: float
    nisab_threshold_used: float
    nisab_metal: str
    meets_nisab: bool
    zakat_due: float
    breakdown: dict[str, float] = field(default_factory=dict)

    def summary(self, currency: str = "USD") -> str:
        lines = [
            f"Avere netă supusă Zakat: {self.net_zakatable_wealth:,.2f} {currency}",
            f"Prag Nisab utilizat ({self.nisab_metal}): {self.nisab_threshold_used:,.2f} {currency}",
            f"Prag Nisab atins: {'DA' if self.meets_nisab else 'NU'}",
        ]
        if self.meets_nisab:
            lines.append(f"Zakat datorat (2.5%): {self.zakat_due:,.2f} {currency}")
        else:
            lines.append("Zakat datorat: 0 (avere sub pragul Nisab)")
        return "\n".join(lines)


class ZakatCalculator:
    """Calculator Zakat configurabil pe baza prețurilor curente ale metalelor."""

    def __init__(
        self,
        gold_price_per_gram: float,
        silver_price_per_gram: float,
        use_lower_nisab: bool = True,
    ):
        """
        Args:
            gold_price_per_gram: preț curent al aurului per gram, în moneda dorită.
            silver_price_per_gram: preț curent al argintului per gram.
            use_lower_nisab: dacă True, folosește pragul mai mic dintre aur/argint
                (interpretare majoritară favorabilă beneficiarilor Zakat — mai
                mulți plătitori ating pragul). Dacă False, folosește pragul aurului.
        """
        self.gold_price_per_gram = gold_price_per_gram
        self.silver_price_per_gram = silver_price_per_gram
        self.use_lower_nisab = use_lower_nisab

    def _nisab_threshold(self) -> tuple[float, str]:
        gold_nisab = NISAB_GOLD_GRAMS * self.gold_price_per_gram
        silver_nisab = NISAB_SILVER_GRAMS * self.silver_price_per_gram

        if self.use_lower_nisab:
            if silver_nisab <= gold_nisab:
                return silver_nisab, "argint"
            return gold_nisab, "aur"
        return gold_nisab, "aur"

    def calculate(self, assets: ZakatAssets) -> ZakatResult:
        breakdown = {
            "numerar_si_echivalente": assets.cash_and_equivalents,
            "creante_incasabile": assets.receivables_collectible,
            "inventar_comercial": assets.trade_inventory_value,
            "investitii_conforme": assets.investments_market_value,
            "aur_argint": assets.gold_silver_value,
        }
        total_assets = sum(breakdown.values())
        net_wealth = max(0.0, total_assets - assets.short_term_liabilities)

        nisab_value, nisab_metal = self._nisab_threshold()
        meets_nisab = net_wealth >= nisab_value

        zakat_due = round(net_wealth * ZAKAT_RATE, 2) if meets_nisab else 0.0

        return ZakatResult(
            total_eligible_assets=total_assets,
            deductible_liabilities=assets.short_term_liabilities,
            net_zakatable_wealth=net_wealth,
            nisab_threshold_used=nisab_value,
            nisab_metal=nisab_metal,
            meets_nisab=meets_nisab,
            zakat_due=zakat_due,
            breakdown=breakdown,
        )
