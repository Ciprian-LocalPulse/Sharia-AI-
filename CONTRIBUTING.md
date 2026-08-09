# Contribuție

Ghidul complet de contribuție a fost mutat în
[`docs/contributing.md`](./docs/contributing.md) pentru a păstra rădăcina
proiectului curată și aliniată cu structura standard de documentație.

Pe scurt:

1. Fork + branch dedicat pentru fiecare schimbare.
2. `pip install -e ".[dev]"` pentru mediul de dezvoltare.
3. `ruff check src tests && mypy src && pytest --cov=sharia_ai` înainte de commit.
4. Orice modificare a pragurilor de screening sau a lexiconului NLP
   trebuie însoțită de o sursă metodologică și de un test de regresie
   (inclusiv un caz negativ, pentru a preveni falsuri pozitive).
5. Deschide un Pull Request descriind clar problema rezolvată.

Vezi [`docs/contributing.md`](./docs/contributing.md) pentru detalii complete
și [`CODE_OF_CONDUCT.md`](./CODE_OF_CONDUCT.md) pentru regulile comunității.
