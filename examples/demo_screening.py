"""
demo_screening.py — عرض توضيحي شامل لمجموعة أدوات Sharia-AI.

المؤلف: Ciprian Ștefan Pleșca

التشغيل:
    PYTHONPATH=src python3 examples/demo_screening.py
"""

from sharia_ai.pipelines.compliance_pipeline import ShariaCompliancePipeline
from sharia_ai.screening.equity_screener import CompanyFinancials
from sharia_ai.zakat.zakat_calculator import ZakatAssets, ZakatCalculator

# 1. تعريف شركة افتراضية لفرز الأسهم
company = CompanyFinancials(
    name="مجموعة النور للتجزئة",
    sector="retail",
    market_cap=50_000_000,
    interest_bearing_debt=12_000_000,
    cash_and_interest_bearing_deposits=8_000_000,
    accounts_receivable=15_000_000,
    total_revenue=40_000_000,
    haram_revenue=500_000,  # دخل عرضي من ودائع تحمل فائدة
)

# 2. عقود باللغة العربية لتحليلها بحثًا عن بنود إشكالية
contracts = {
    "عقد_توريد.txt": (
        "يلتزم الطرف الأول بتوريد البضاعة المتفق عليها خلال ثلاثين يومًا. "
        "في حال التأخير، يُطبق سعر الفائدة المتفق عليه على المبلغ المتبقي."
    ),
    "اتفاقية_شراكة.txt": (
        "يتفق الطرفان على تقاسم الأرباح والخسائر بنسب محددة سلفًا "
        "بناءً على رأس المال المستثمر من كل طرف."
    ),
}

# 3. أصول لحساب زكاة الشركة
zakat_assets = ZakatAssets(
    cash_and_equivalents=2_000_000,
    receivables_collectible=1_000_000,
    trade_inventory_value=3_000_000,
    short_term_liabilities=800_000,
)
zakat_calculator = ZakatCalculator(gold_price_per_gram=75.0, silver_price_per_gram=0.95)

# 4. تشغيل خط المعالجة الكامل
pipeline = ShariaCompliancePipeline(zakat_calculator=zakat_calculator)
report = pipeline.run(company=company, contracts=contracts, zakat_assets=zakat_assets)

print("=" * 70)
print(f"تقرير الامتثال — {report.company_name}")
print(f"تاريخ الإنشاء: {report.generated_at_utc}")
print(f"الحالة العامة: {report.overall_status}")
print("=" * 70)

print("\n--- فرز الأسهم ---")
print(report.equity_screening.summary())

print("\n--- فرز العقود ---")
for doc_name, detection in (report.contract_screening or {}).items():
    print(f"\n[{doc_name}]")
    print(detection.summary())

print("\n--- حساب الزكاة ---")
print(report.zakat.summary())

print("\n--- تصدير JSON (مقتطف) ---")
print(report.to_json()[:500] + "...")
