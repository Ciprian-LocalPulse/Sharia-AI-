"""
rules.py — Praguri de conformitate Sharia pentru screening de echitate.

Sursă metodologică (rezumat, nu reproducere textuală):
    - AAOIFI Shari'ah Standard No. 21 (Financial Paper - Shares/Bonds)
    - Dow Jones Islamic Market (DJIM) Index Methodology
    - FTSE Shariah Global Equity Index Series — Ground Rules

Aceste praguri sunt CONFIGURABILE. Ele reprezintă interpretări comune,
nu o fatwa. Orice utilizare instituțională trebuie validată de un
comitet Sharia acreditat (Sharia Supervisory Board) înainte de a fi
folosită în decizii de investiție reale.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ScreeningThresholds:
    """Praguri procentuale (exprimate ca fracție, ex: 0.33 = 33%)."""

    # Screening de business (activitate primară — excludere sectorială)
    max_haram_revenue_ratio: float = 0.05  # venit din activități interzise / venit total

    # Screening financiar (rate financiare)
    max_debt_to_market_cap: float = 0.33          # datorie purtătoare de dobândă / capitalizare bursieră
    max_cash_interest_to_market_cap: float = 0.33  # numerar + depozite purtătoare de dobândă / cap. bursieră
    max_receivables_to_market_cap: float = 0.49    # creanțe + numerar / cap. bursieră (unele metodologii: activ total)

    # Purificare venit (dividend purification) — venit non-permis / venit total
    purification_threshold: float = 0.05


# Sectoare de activitate excluse implicit (haram prin natura activității).
# Lista este intenționat editabilă — companiile își pot extinde/restrânge
# taxonomia în funcție de comitetul Sharia propriu.
EXCLUDED_SECTORS = {
    "alcohol": "Producție/distribuție de băuturi alcoolice",
    "gambling": "Jocuri de noroc și pariuri (maysir)",
    "conventional_banking": "Bănci și instituții financiare convenționale (bazate pe dobândă/riba)",
    "conventional_insurance": "Asigurări convenționale (non-Takaful)",
    "pork": "Producție/procesare carne de porc și derivate",
    "adult_entertainment": "Divertisment pentru adulți / pornografie",
    "tobacco": "Producție de tutun (interpretare majoritară: haram/makruh sever)",
    "weapons_controversial": "Armament controversat / neconvențional",
    "media_immoral": "Media care promovează conținut imoral ca activitate primară",
}

# Nisab de referință (praguri clasice, în grame de metal — valoarea monetară
# se calculează dinamic pe baza prețului curent al metalului).
NISAB_GOLD_GRAMS = 85.0     # ~85g aur (echivalent 20 mithqal)
NISAB_SILVER_GRAMS = 595.0  # ~595g argint (echivalent 200 dirham)

ZAKAT_RATE = 0.025  # 2.5% asupra activelor eligibile care depășesc Nisab, deținute 1 an lunar (hawl)
