# Arhitectură

## Filosofie de proiectare

Sharia-AI este construit pe patru principii, în această ordine de prioritate:

1. **Explicabilitate înaintea acurateții brute.** Un scor de conformitate
   fără justificare regulă-cu-regulă este inutil pentru un comitet Sharia
   care trebuie să-și motiveze deciziile. De aceea fiecare rezultat
   (`ScreeningResult`, `DetectionReport`, `ZakatResult`) expune fiecare
   verificare individuală, nu doar un verdict agregat.
2. **Funcționare offline ca implicit.** Instituțiile financiare operează
   frecvent în medii izolate (air-gapped) sau cu cerințe stricte de
   reziden ță a datelor. Nucleul (`screening`, `nlp`, `zakat`, `pipelines`)
   folosește exclusiv biblioteca standard Python — nicio dependență externă
   obligatorie pentru logica de bază.
3. **Extensibilitate fără rescriere.** Straturile ML (ex: un clasificator
   transformer pentru arabă) se conectează prin interfețe (`Protocol`), nu
   prin moștenire rigidă — vezi `RibaClassifierProtocol`.
4. **Configurare, nu hardcodare.** Toate pragurile financiare (rate de
   îndatorare, Nisab, rata Zakat) sunt parametri, nu constante îngropate
   în logică — vezi `screening/rules.py` și `data/rules/aaoifi_thresholds.yaml`.

## Diagrama componentelor

```
                        ┌─────────────────────────┐
                        │   API REST (FastAPI)    │
                        │      api/main.py        │
                        └────────────┬────────────┘
                                     │
                        ┌────────────▼────────────┐
                        │  ShariaCompliancePipeline│
                        │  pipelines/compliance_   │
                        │  pipeline.py             │
                        └───┬──────────┬───────────┘
             ┌──────────────┘          └──────────────┐
             │                                          │
   ┌─────────▼─────────┐                    ┌──────────▼──────────┐
   │  EquityScreener     │                    │ HybridContractScreener│
   │  screening/          │                    │ nlp/riba_detector.py │
   │  equity_screener.py  │                    └──────────┬──────────┘
   └─────────┬─────────┘                                  │
             │                                  ┌──────────▼──────────┐
             │                                  │ LexicalRibaDetector │
             │                                  │ (determinist,       │
             │                                  │  offline)           │
             │                                  └──────────┬──────────┘
             │                                              │ (opțional)
             │                                  ┌──────────▼──────────┐
             │                                  │ RibaClassifierProtocol│
             │                                  │ (model ML extern,    │
             │                                  │  ex: AraBERT)        │
             │                                  └──────────────────────┘
   ┌─────────▼─────────┐
   │  ZakatCalculator    │
   │  zakat/zakat_        │
   │  calculator.py       │
   └───────────────────┘
```

## Fluxul unei cereri de conformitate

1. Clientul (API, script, notebook) construiește un obiect `CompanyFinancials`.
2. `ShariaCompliancePipeline.run()` invocă `EquityScreener.screen()`, care
   aplică secvențial regulile de excludere sectorială și cele patru rate
   financiare din `ScreeningThresholds`.
3. Dacă sunt furnizate contracte, fiecare document este trecut prin
   `HybridContractScreener`, care rulează întâi `LexicalRibaDetector`
   (determinist) și, dacă e configurat, agregă și scorurile unui
   clasificator ML extern.
4. Dacă sunt furnizate active, `ZakatCalculator` calculează averea netă
   supusă Zakat, pragul Nisab (aur/argint, configurabil) și suma datorată.
5. Rezultatele sunt agregate într-un `CompanyComplianceReport`, serializabil
   direct în JSON prin `to_json()`.

## Extensibilitate NLP

Motorul lexical (`LexicalRibaDetector`) este intenționat simplu și
determinist — potrivit ca prim filtru într-un pipeline reglementat, unde
auditabilitatea contează la fel de mult ca recall-ul. Pentru acoperire
semantică mai profundă (parafraze, formulări indirecte de dobândă etc.),
proiectul este pregătit să integreze un model transformer prin
`RibaClassifierProtocol`:

```python
from sharia_ai.nlp.riba_detector import ConcernCategory, RibaClassifierProtocol

class AraBertRibaClassifier:
    def __init__(self, model_path: str):
        # încarcă modelul fine-tuned (ex: transformers.AutoModelForSequenceClassification)
        ...

    def predict(self, sentence: str) -> list[tuple[ConcernCategory, float]]:
        # rulează inferența și mapează logit-urile la (categorie, scor)
        ...

from sharia_ai.nlp.riba_detector import HybridContractScreener, LexicalRibaDetector

screener = HybridContractScreener(
    lexical_detector=LexicalRibaDetector(),
    ml_classifier=AraBertRibaClassifier("path/to/model"),
)
```

Niciun cod din `pipelines` sau `api` nu trebuie modificat pentru a beneficia
de acest upgrade — interfața `Protocol` garantează compatibilitatea.

## Configurare externă (YAML → praguri)

Pentru integrare cu sisteme externe de configurare (dashboard de audit,
CI/CD de politici), `data/rules/aaoifi_thresholds.yaml` oglindește valorile
din `screening/rules.py`. Exemplu de loader (necesită `pyyaml`, extra opțional):

```python
import yaml
from sharia_ai.screening.rules import ScreeningThresholds

with open("data/rules/aaoifi_thresholds.yaml", encoding="utf-8") as f:
    raw = yaml.safe_load(f)

thresholds = ScreeningThresholds(
    max_haram_revenue_ratio=raw["business_screening"]["max_haram_revenue_ratio"],
    max_debt_to_market_cap=raw["financial_ratios"]["max_debt_to_market_cap"],
    max_cash_interest_to_market_cap=raw["financial_ratios"]["max_cash_interest_to_market_cap"],
    max_receivables_to_market_cap=raw["financial_ratios"]["max_receivables_to_market_cap"],
    purification_threshold=raw["purification"]["purification_threshold"],
)
```

## Considerații de securitate și confidențialitate a datelor

- Toolkit-ul nu persistă date implicit — fiecare apel este stateless.
- Pentru integrare cu date financiare reale, se recomandă rularea API-ului
  în interiorul perimetrului de rețea al instituției (nu expus public fără
  autentificare/autorizare suplimentară — vezi `docs/roadmap.md`, item
  "Autentificare API").
- Lexiconul NLP conține doar termeni financiari/juridici generici — nu
  procesează sau stochează date personale.
