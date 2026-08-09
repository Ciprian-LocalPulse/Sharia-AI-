# Ghid de Contribuție

Mulțumim pentru interesul de a contribui la Sharia-AI! Acest proiect
combină cod cu subiecte sensibile din jurisprudența islamică — de aceea
avem câteva reguli suplimentare față de un proiect open-source tipic.

## Tipuri de contribuții binevenite

- **Extinderea lexiconului NLP** (`nlp/riba_detector.py`) — termeni
  suplimentari pentru riba/gharar/maysir, în special dialecte regionale
  sau formulări contractuale specifice unei jurisdicții.
- **Noi module de screening** — ex: conformitate pentru Sukuk (obligațiuni
  islamice), Takaful (asigurări islamice).
- **Îmbunătățiri de acuratețe NLP** — tokenizare, stemming, gestionarea
  ambiguităților morfologice arabe.
- **Documentație și traduceri** (engleză, franceză, alte limbi vorbite în
  regiunea MENA).
- **Teste suplimentare**, în special cazuri de regresie pentru falsuri
  pozitive/negative descoperite în producție.

## Reguli specifice pentru conținut Sharia

1. **Orice modificare a pragurilor din `screening/rules.py` sau a
   lexiconului din `nlp/riba_detector.py` trebuie însoțită de o sursă
   metodologică** (standard AAOIFI, metodologie de index, sau referință
   la un text juridic recunoscut) în descrierea Pull Request-ului.
2. **Nu adăugați afirmații care emit fatwa** (ex: "X este definitiv haram
   în toate școlile juridice"). Formulați neutru, cu referință la
   interpretarea majoritară și menționați existența unor opinii diferite
   acolo unde acestea sunt cunoscute.
3. **Contribuțiile la lexiconul NLP trebuie testate pentru falși pozitivi**
   — un termen adăugat fără caz de test care verifică și non-declanșarea
   pe cuvinte similare (omonime, derivate) va fi respins.

## Workflow tehnic

```bash
git clone https://github.com/Ciprian-LocalPulse/sharia-fintech-ai.git
cd sharia-fintech-ai
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# înainte de commit:
ruff check src tests
mypy src
pytest --cov=sharia_ai --cov-report=term-missing
```

Toate PR-urile rulează automat prin CI (`.github/workflows/ci.yml`) pe
Python 3.10, 3.11 și 3.12.

## Stil de commit

Folosim mesaje de commit descriptive, la timpul prezent imperativ:
`Add gharar detection for undefined-price clauses`, nu
`Added gharar stuff`.

## Cod de conduită

Acest proiect adoptă un [Cod de Conduită](../CODE_OF_CONDUCT.md) bazat pe
Contributor Covenant. Prin participare, sunteți de acord să îl respectați.
