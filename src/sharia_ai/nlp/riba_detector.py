"""
riba_detector.py — Detecție de clauze contractuale problematice din perspectiva
Sharia: riba (dobândă), gharar (incertitudine excesivă) și maysir (jocuri de
noroc/speculație pură), în text arab.

Arhitectură pe două niveluri:
    1. `LexicalRibaDetector`  — motor bazat pe reguli/lexicon (rulează offline,
       fără dependențe externe, determinist și auditabil — potrivit ca prim
       filtru într-un pipeline de conformitate reglementat).
    2. `RibaClassifierProtocol` — interfață pe care o poate implementa orice
       model ML/transformer (ex: AraBERT fine-tuned) pentru scoring semantic,
       fără să schimbe restul pipeline-ului. Vezi docs/architecture.md.

Acest fișier NU emite fatwa. El semnalează clauze pentru revizuire umană
de către un jurist/comitet Sharia — este un instrument de triaj, nu de
decizie finală.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from .arabic_preprocessing import clitic_variants, sentence_split, tokenize


class ConcernCategory(str, Enum):
    RIBA = "riba"          # dobândă / interes
    GHARAR = "gharar"      # incertitudine excesivă / ambiguitate contractuală
    MAYSIR = "maysir"      # speculație pură / joc de noroc
    UNKNOWN_CLAUSE = "unknown_clause"


# Lexicon inițial (extensibil). Cheile sunt forme normalizate (fără diacritice).
# Fiecare intrare: termen -> (categorie, greutate de încredere 0-1)
_LEXICON: dict[str, tuple[ConcernCategory, float]] = {
    # --- Riba (dobândă) ---
    "فايده": (ConcernCategory.RIBA, 0.9),       # فائدة (dobândă) - normalizat
    "ربا": (ConcernCategory.RIBA, 0.95),
    "سعر الفايده": (ConcernCategory.RIBA, 0.95),
    "معدل الفايده": (ConcernCategory.RIBA, 0.95),
    "فايده مركبه": (ConcernCategory.RIBA, 0.97),  # dobândă compusă
    "قرض بفايده": (ConcernCategory.RIBA, 0.97),   # împrumut cu dobândă
    "غرامه تاخير": (ConcernCategory.RIBA, 0.6),   # penalizare de întârziere (poate fi riba dacă e procentuală/timp)
    # --- Gharar (incertitudine excesivă) ---
    "غرر": (ConcernCategory.GHARAR, 0.85),
    "غموض": (ConcernCategory.GHARAR, 0.5),
    "غير محدد": (ConcernCategory.GHARAR, 0.5),      # nedeterminat
    "مجهول": (ConcernCategory.GHARAR, 0.55),        # necunoscut/nespecificat
    "بيع ما لا يملك": (ConcernCategory.GHARAR, 0.9),  # vânzarea a ceva ce nu deții
    # --- Maysir (speculație/joc de noroc) ---
    "ميسر": (ConcernCategory.MAYSIR, 0.9),
    "قمار": (ConcernCategory.MAYSIR, 0.95),
    "رهان": (ConcernCategory.MAYSIR, 0.85),          # pariu
    "مضاربه بحته": (ConcernCategory.MAYSIR, 0.7),   # speculație pură
}


@dataclass
class Flag:
    """O semnalare a unei posibile clauze problematice."""

    sentence: str
    category: ConcernCategory
    matched_term: str
    confidence: float


@dataclass
class DetectionReport:
    text_length_chars: int
    flags: list[Flag]

    @property
    def has_concerns(self) -> bool:
        return len(self.flags) > 0

    @property
    def categories_found(self) -> set[ConcernCategory]:
        return {f.category for f in self.flags}

    def summary(self) -> str:
        if not self.flags:
            return "Nicio clauză suspectă detectată (screening lexical)."
        lines = [f"{len(self.flags)} semnalări găsite:"]
        for f in self.flags:
            lines.append(
                f"  [{f.category.value.upper()} | încredere {f.confidence:.0%}] "
                f"'{f.matched_term}' în: \"{f.sentence[:80]}...\""
                if len(f.sentence) > 80
                else f"  [{f.category.value.upper()} | încredere {f.confidence:.0%}] "
                f"'{f.matched_term}' în: \"{f.sentence}\""
            )
        return "\n".join(lines)


class RibaClassifierProtocol(Protocol):
    """Interfață pentru un clasificator ML extern (ex: AraBERT fine-tuned).

    Orice implementare trebuie doar să respecte această semnătură pentru a fi
    conectată la `HybridContractScreener` fără modificări în restul codului.
    """

    def predict(self, sentence: str) -> list[tuple[ConcernCategory, float]]:
        """Returnează o listă de (categorie, scor de încredere 0-1) pentru propoziția dată."""
        ...


class LexicalRibaDetector:
    """Detector determinist bazat pe lexicon — rulează 100% offline."""

    def __init__(self, lexicon: dict[str, tuple[ConcernCategory, float]] | None = None):
        self.lexicon = lexicon or _LEXICON

    def analyze(self, contract_text: str) -> DetectionReport:
        """Potrivire pe granițe de cuvânt (nu substring brut), pentru a evita
        falși pozitivi frecvenți în arabă — ex: termenul 'ربا' (riba) NU
        trebuie să se potrivească în interiorul cuvântului 'الأرباح' (profituri),
        deși acesta din urmă îl conține ca șir de caractere."""
        flags: list[Flag] = []
        for sentence in sentence_split(contract_text):
            sentence_tokens = tokenize(sentence)
            for term, (category, confidence) in self.lexicon.items():
                term_tokens = tokenize(term)
                if not term_tokens:
                    continue
                if self._contains_sequence(sentence_tokens, term_tokens):
                    flags.append(
                        Flag(
                            sentence=sentence,
                            category=category,
                            matched_term=term,
                            confidence=confidence,
                        )
                    )
        return DetectionReport(text_length_chars=len(contract_text), flags=flags)

    @staticmethod
    def _contains_sequence(haystack: list[str], needle: list[str]) -> bool:
        """Verifică dacă `needle` apare ca subsecvență CONTIGUĂ de tokenuri
        întregi în `haystack` (matching pe cuvânt complet, nu pe substring).

        Fiecare token din `haystack` este comparat prin variantele sale fără
        clitic-e (ex: 'بفائدة' -> și 'فائدة'), pentru a recunoaște termeni de
        lexicon chiar și atunci când apar cu prepoziții/conjuncții atașate —
        foarte frecvent în arabă ('بفائدة', 'والقمار', 'كالربا' etc.).
        """
        n, m = len(haystack), len(needle)
        if m == 0 or m > n:
            return False
        haystack_variants = [clitic_variants(tok) for tok in haystack]
        for i in range(n - m + 1):
            if all(needle[j] in haystack_variants[i + j] for j in range(m)):
                return True
        return False


class HybridContractScreener:
    """Combină detectorul lexical cu un clasificator ML opțional.

    Dacă `ml_classifier` este furnizat (orice obiect ce respectă
    `RibaClassifierProtocol`), scorurile sale sunt fuzionate cu cele
    lexicale (max pe categorie) pentru un rezultat mai robust semantic.
    """

    def __init__(
        self,
        lexical_detector: LexicalRibaDetector | None = None,
        ml_classifier: "RibaClassifierProtocol | None" = None,
    ):
        self.lexical_detector = lexical_detector or LexicalRibaDetector()
        self.ml_classifier = ml_classifier

    def analyze(self, contract_text: str) -> DetectionReport:
        report = self.lexical_detector.analyze(contract_text)

        if self.ml_classifier is None:
            return report

        extra_flags: list[Flag] = []
        for sentence in sentence_split(contract_text):
            for category, score in self.ml_classifier.predict(sentence):
                extra_flags.append(
                    Flag(
                        sentence=sentence,
                        category=category,
                        matched_term="[model ML]",
                        confidence=score,
                    )
                )
        return DetectionReport(
            text_length_chars=report.text_length_chars,
            flags=report.flags + extra_flags,
        )
