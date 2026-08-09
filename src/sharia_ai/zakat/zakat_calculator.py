"""
zakat_calculator.py — محرك حساب الزكاة للأصول المؤسسية/الشخصية السائلة،
متوافق مع التفسير الكلاسيكي السائد (2.5% على الأصول المؤهَّلة التي
تتجاوز عتبة النصاب، محتفَظ بها لمدة حول قمري).

هذه الوحدة **لا** تصدر فتوى ولا تحل محل مستشار شرعي مؤهَّل للحالات
المعقّدة (مثل زكاة المخزون التجاري، الأصول المختلطة، الديون طويلة
الأجل). إنها أداة حساب مساعدة، شفافة وقابلة للتدقيق (كل خطوة من
الحساب مكشوفة).

المؤلف: Ciprian Ștefan Pleșca
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..screening.rules import NISAB_GOLD_GRAMS, NISAB_SILVER_GRAMS, ZAKAT_RATE


@dataclass
class ZakatAssets:
    """الأصول المؤهَّلة لحساب الزكاة (قيم نقدية، بنفس العملة)."""

    cash_and_equivalents: float = 0.0
    receivables_collectible: float = 0.0       # ذمم مدينة بفرص تحصيل معقولة
    trade_inventory_value: float = 0.0          # بضاعة مُعدّة للبيع، بالقيمة السوقية
    investments_market_value: float = 0.0       # أسهم/صناديق متوافقة شرعًا، بالقيمة السوقية
    gold_silver_value: float = 0.0

    short_term_liabilities: float = 0.0          # ديون مستحقة في السنة الحالية، قابلة للخصم


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
            f"صافي الثروة الخاضعة للزكاة: {self.net_zakatable_wealth:,.2f} {currency}",
            f"عتبة النصاب المستخدمة ({self.nisab_metal}): {self.nisab_threshold_used:,.2f} {currency}",
            f"عتبة النصاب مُحقَّقة: {'نعم' if self.meets_nisab else 'لا'}",
        ]
        if self.meets_nisab:
            lines.append(f"الزكاة المستحقة (2.5%): {self.zakat_due:,.2f} {currency}")
        else:
            lines.append("الزكاة المستحقة: 0 (الثروة دون عتبة النصاب)")
        return "\n".join(lines)


class ZakatCalculator:
    """حاسبة زكاة قابلة للتهيئة استنادًا إلى الأسعار الحالية للمعادن."""

    def __init__(
        self,
        gold_price_per_gram: float,
        silver_price_per_gram: float,
        use_lower_nisab: bool = True,
    ):
        """
        المعاملات:
            gold_price_per_gram: السعر الحالي للذهب لكل غرام، بالعملة المطلوبة.
            silver_price_per_gram: السعر الحالي للفضة لكل غرام.
            use_lower_nisab: إذا كانت True، تُستخدم العتبة الأقل بين
                الذهب/الفضة (التفسير السائد المُفضِّل لمستحقي الزكاة —
                عدد أكبر من المزكّين يبلغون العتبة). إذا كانت False،
                تُستخدم عتبة الذهب.
        """
        self.gold_price_per_gram = gold_price_per_gram
        self.silver_price_per_gram = silver_price_per_gram
        self.use_lower_nisab = use_lower_nisab

    def _nisab_threshold(self) -> tuple[float, str]:
        gold_nisab = NISAB_GOLD_GRAMS * self.gold_price_per_gram
        silver_nisab = NISAB_SILVER_GRAMS * self.silver_price_per_gram

        if self.use_lower_nisab:
            if silver_nisab <= gold_nisab:
                return silver_nisab, "فضة"
            return gold_nisab, "ذهب"
        return gold_nisab, "ذهب"

    def calculate(self, assets: ZakatAssets) -> ZakatResult:
        breakdown = {
            "نقد_وما_يعادله": assets.cash_and_equivalents,
            "ذمم_مدينة_قابلة_للتحصيل": assets.receivables_collectible,
            "مخزون_تجاري": assets.trade_inventory_value,
            "استثمارات_متوافقة": assets.investments_market_value,
            "ذهب_وفضة": assets.gold_silver_value,
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
