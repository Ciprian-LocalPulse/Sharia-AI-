"""
demo_screening.py — Demonstrație end-to-end a toolkit-ului Sharia-AI.

Rulare:
    PYTHONPATH=src python3 examples/demo_screening.py
"""

from sharia_ai.pipelines.compliance_pipeline import ShariaCompliancePipeline
from sharia_ai.screening.equity_screener import CompanyFinancials
from sharia_ai.zakat.zakat_calculator import ZakatAssets, ZakatCalculator

# 1. Definim o companie fictivă pentru screening de echitate
company = CompanyFinancials(
    name="Al-Noor Retail Group",
    sector="retail",
    market_cap=50_000_000,
    interest_bearing_debt=12_000_000,
    cash_and_interest_bearing_deposits=8_000_000,
    accounts_receivable=15_000_000,
    total_revenue=40_000_000,
    haram_revenue=500_000,  # venit incidental din depozite purtătoare de dobândă
)

# 2. Contracte în arabă de analizat pentru clauze problematice
contracts = {
    "contract_furnizare.txt": (
        "يلتزم الطرف الأول بتوريد البضاعة المتفق عليها خلال ثلاثين يومًا. "
        "في حال التأخير، يُطبق سعر الفائدة المتفق عليه على المبلغ المتبقي."
    ),
    "acord_parteneriat.txt": (
        "يتفق الطرفان على تقاسم الأرباح والخسائر بنسب محددة سلفًا "
        "بناءً على رأس المال المستثمر من كل طرف."
    ),
}

# 3. Active pentru calculul Zakat al companiei
zakat_assets = ZakatAssets(
    cash_and_equivalents=2_000_000,
    receivables_collectible=1_000_000,
    trade_inventory_value=3_000_000,
    short_term_liabilities=800_000,
)
zakat_calculator = ZakatCalculator(gold_price_per_gram=75.0, silver_price_per_gram=0.95)

# 4. Rulăm pipeline-ul complet
pipeline = ShariaCompliancePipeline(zakat_calculator=zakat_calculator)
report = pipeline.run(company=company, contracts=contracts, zakat_assets=zakat_assets)

print("=" * 70)
print(f"RAPORT DE CONFORMITATE — {report.company_name}")
print(f"Generat: {report.generated_at_utc}")
print(f"Status general: {report.overall_status}")
print("=" * 70)

print("\n--- Screening de echitate ---")
print(report.equity_screening.summary())

print("\n--- Screening de contracte ---")
for doc_name, detection in (report.contract_screening or {}).items():
    print(f"\n[{doc_name}]")
    print(detection.summary())

print("\n--- Calcul Zakat ---")
print(report.zakat.summary())

print("\n--- Export JSON (fragment) ---")
print(report.to_json()[:500] + "...")
