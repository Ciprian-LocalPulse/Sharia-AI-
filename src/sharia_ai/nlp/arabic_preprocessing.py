"""
arabic_preprocessing.py — تطبيع أساسي للنص العربي من أجل خطوط معالجة
فرز العقود.

لا يعتمد على مكتبات خارجية (يعمل دون اتصال بالإنترنت، مكتبة قياسية
فقط)، بحيث يمكن تشغيله في بيئات معزولة، شائعة في المؤسسات المالية ذات
متطلبات صارمة لامتثال البيانات.

للإنتاج، يُوصى باستبدال/توسيع هذا بمُرمِّز صرفي مخصّص (مثل CAMeL Tools،
Farasa) — راجع docs/architecture.md قسم "قابلية التوسع لمعالجة اللغة
الطبيعية".

المؤلف: Ciprian Ștefan Pleșca
"""

from __future__ import annotations

import re
import unicodedata

# التشكيل العربي — يونيكود 0617–061A، 064B–0652، 0670، 06D6–06ED
_ARABIC_DIACRITICS = re.compile(
    r"[\u0617-\u061A\u064B-\u0652\u0670\u06D6-\u06ED]"
)

# تطبيع شائع للحروف (صيغ الألف، الياء، التاء المربوطة)
_NORMALIZATION_MAP = {
    "\u0622": "\u0627",  # آ -> ا
    "\u0623": "\u0627",  # أ -> ا
    "\u0625": "\u0627",  # إ -> ا
    "\u0649": "\u064A",  # ى -> ي
    "\u0629": "\u0647",  # ة -> ه (اختياري، مفيد لمطابقة مرنة)
    "\u0626": "\u064A",  # ئ (ياء بهمزة) -> ي
    "\u0624": "\u0648",  # ؤ (واو بهمزة) -> و
}

_WHITESPACE = re.compile(r"\s+")
_TOKEN_SPLIT = re.compile(r"[^\w\u0600-\u06FF]+")


def strip_diacritics(text: str) -> str:
    """يزيل التشكيل من النص."""
    return _ARABIC_DIACRITICS.sub("", text)


def normalize_letters(text: str) -> str:
    """يوحّد صيغ الألف/الياء/التاء المربوطة لمطابقة متينة."""
    for src, dst in _NORMALIZATION_MAP.items():
        text = text.replace(src, dst)
    return text


def normalize_arabic(text: str) -> str:
    """خط تطبيع كامل: يونيكود NFC -> التشكيل -> الحروف -> المسافات."""
    text = unicodedata.normalize("NFC", text)
    text = strip_diacritics(text)
    text = normalize_letters(text)
    text = _WHITESPACE.sub(" ", text).strip()
    return text


def tokenize(text: str) -> list[str]:
    """ترميز بسيط على الكلمات، مع الاحتفاظ فقط بالأحرف العربية/الأبجدية الرقمية."""
    normalized = normalize_arabic(text)
    tokens = [t for t in _TOKEN_SPLIT.split(normalized) if t]
    return tokens


_CLITIC_PREFIXES_1 = ("و", "ف", "ب", "ك", "ل")  # أدوات عطف/جر ملتصقة مباشرة (دون فراغ)
_DEFINITE_ARTICLE = "ال"


def clitic_variants(token: str, min_len: int = 2) -> set[str]:
    """يولّد صيغًا لرمز عبر إزالة اللواصق النحوية العربية الشائعة (جزيئات
    ملتصقة دون فراغ: و ف ب ك ل وأداة التعريف ال)، دون تعديل المعجم
    المرجعي — مفيد لزيادة استدعاء المطابقة المعجمية (مثال: 'بفائدة' ->
    الصيغة 'فائدة') دون المخاطرة بإفساد المصطلحات المرجعية في المعجم.

    لا تُطبَّق هذه الصيغ بشكل أعمى على المصطلحات المرجعية — فقط على
    رموز النص المُحلَّل، ثم تُقارَن بالصيغ المرجعية.
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
    """تقسيم بسيط إلى جمل/بنود تعاقدية، وفق علامات ترقيم شائعة في
    المستندات العربية (.، !، ؟، ،، ؛، وسطر جديد)."""
    parts = re.split(r"[\.\!\?؟؛\n]+", text)
    return [p.strip() for p in parts if p.strip()]
