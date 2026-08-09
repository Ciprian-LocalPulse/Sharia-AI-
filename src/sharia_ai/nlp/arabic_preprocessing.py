"""
arabic_preprocessing.py — Normalizare de bază a textului arab pentru
pipeline-urile de screening de contracte.

Nu depinde de biblioteci externe (funcționează offline, doar stdlib),
astfel încât să poată rula în medii izolate / air-gapped, frecvente în
instituțiile financiare cu cerințe stricte de conformitate a datelor.

Pentru producție, se recomandă înlocuirea/extinderea cu un tokenizer
morfologic dedicat (ex: CAMeL Tools, Farasa) — vezi docs/architecture.md
secțiunea "Extensibilitate NLP".
"""

from __future__ import annotations

import re
import unicodedata

# Diacritice arabe (tashkeel) — Unicode 0617–061A, 064B–0652, 0670, 06D6–06ED
_ARABIC_DIACRITICS = re.compile(
    r"[\u0617-\u061A\u064B-\u0652\u0670\u06D6-\u06ED]"
)

# Normalizări comune de caractere (variante de alif, ya, ta marbuta)
_NORMALIZATION_MAP = {
    "\u0622": "\u0627",  # آ -> ا
    "\u0623": "\u0627",  # أ -> ا
    "\u0625": "\u0627",  # إ -> ا
    "\u0649": "\u064A",  # ى -> ي
    "\u0629": "\u0647",  # ة -> ه (opțional, util pentru matching lejer)
    "\u0626": "\u064A",  # ئ (ya cu hamza) -> ي
    "\u0624": "\u0648",  # ؤ (waw cu hamza) -> و
}

_WHITESPACE = re.compile(r"\s+")
_TOKEN_SPLIT = re.compile(r"[^\w\u0600-\u06FF]+")


def strip_diacritics(text: str) -> str:
    """Elimină tashkeel (diacriticele) din text."""
    return _ARABIC_DIACRITICS.sub("", text)


def normalize_letters(text: str) -> str:
    """Unifică variantele de alif/ya/ta marbuta pentru matching robust."""
    for src, dst in _NORMALIZATION_MAP.items():
        text = text.replace(src, dst)
    return text


def normalize_arabic(text: str) -> str:
    """Pipeline complet de normalizare: unicode NFC -> diacritice -> litere -> spații."""
    text = unicodedata.normalize("NFC", text)
    text = strip_diacritics(text)
    text = normalize_letters(text)
    text = _WHITESPACE.sub(" ", text).strip()
    return text


def tokenize(text: str) -> list[str]:
    """Tokenizare simplă pe cuvinte, păstrând doar caractere arabe/alfanumerice."""
    normalized = normalize_arabic(text)
    tokens = [t for t in _TOKEN_SPLIT.split(normalized) if t]
    return tokens


_CLITIC_PREFIXES_1 = ("و", "ف", "ب", "ك", "ل")  # conjuncții/prepoziții atașate direct (fără spațiu)
_DEFINITE_ARTICLE = "ال"


def clitic_variants(token: str, min_len: int = 2) -> set[str]:
    """Generează variante ale unui token prin eliminarea clitic-elor arabe
    uzuale (particule atașate fără spațiu: و ف ب ك ل și articolul hotărât ال),
    fără a modifica lexiconul de referință — util pentru a crește recall-ul
    matching-ului lexical (ex: 'بفائدة' -> variantă 'فائدة') fără a risca
    coruperea termenilor canonici din lexicon.

    NU aplica aceste variante orbește pe termenii de referință — doar pe
    tokenurile din textul analizat, apoi compară cu formele canonice.
    """
    variants = {token}

    stripped_prefix1 = None
    if len(token) > min_len + 1 and token[0] in _CLITIC_PREFIXES_1:
        stripped_prefix1 = token[1:]
        variants.add(stripped_prefix1)

    if token.startswith(_DEFINITE_ARTICLE) and len(token) > min_len + 2:
        variants.add(token[2:])

    if stripped_prefix1 and stripped_prefix1.startswith(_DEFINITE_ARTICLE) and len(stripped_prefix1) > min_len + 2:
        variants.add(stripped_prefix1[2:])

    return variants


def sentence_split(text: str) -> list[str]:
    """Segmentare simplă în propoziții/clauze contractuale, pe semne de punctuație
    comune în documente arabe (., !, ?, ؟, ،, ;, و newline)."""
    parts = re.split(r"[\.\!\?؟؛\n]+", text)
    return [p.strip() for p in parts if p.strip()]
