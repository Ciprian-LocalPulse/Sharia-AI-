"""
riba_detector.py — كشف البنود التعاقدية الإشكالية من منظور شرعي: الربا
(الفائدة)، الغرر (عدم اليقين المفرط)، والميسر (القمار/المضاربة البحتة)،
في النص العربي.

بنية على مستويين:
    1. `LexicalRibaDetector` — محرك قائم على القواعد/المعجم (يعمل دون
       اتصال بالإنترنت، بلا اعتماديات خارجية، حتمي وقابل للتدقيق —
       مناسب كمرشّح أول ضمن خط معالجة امتثال منظَّم).
    2. `RibaClassifierProtocol` — واجهة يمكن لأي نموذج تعلّم آلة/تحويلي
       (مثل AraBERT مُدرَّب) تنفيذها لتقييم دلالي، دون تغيير بقية خط
       المعالجة. راجع docs/architecture.md.

هذا الملف **لا** يصدر فتوى. إنه يشير إلى بنود لمراجعة بشرية من قبل
فقيه/هيئة رقابة شرعية — إنه أداة فرز أولي، وليس أداة قرار نهائي.

المؤلف: Ciprian Ștefan Pleșca
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from .arabic_preprocessing import clitic_variants, sentence_split, tokenize


class ConcernCategory(str, Enum):
    RIBA = "riba"          # فائدة / ربا
    GHARAR = "gharar"      # عدم يقين مفرط / غموض تعاقدي
    MAYSIR = "maysir"      # مضاربة بحتة / قمار
    UNKNOWN_CLAUSE = "unknown_clause"


# معجم أوّلي (قابل للتوسيع). المفاتيح صيغ مُطبَّعة (بلا تشكيل).
# كل مدخل: مصطلح -> (الفئة، وزن الثقة 0-1)
_LEXICON: dict[str, tuple[ConcernCategory, float]] = {
    # --- الربا (الفائدة) ---
    "فايده": (ConcernCategory.RIBA, 0.9),       # فائدة - مُطبَّعة
    "ربا": (ConcernCategory.RIBA, 0.95),
    "سعر الفايده": (ConcernCategory.RIBA, 0.95),
    "معدل الفايده": (ConcernCategory.RIBA, 0.95),
    "فايده مركبه": (ConcernCategory.RIBA, 0.97),  # فائدة مركّبة
    "قرض بفايده": (ConcernCategory.RIBA, 0.97),   # قرض بفائدة
    "غرامه تاخير": (ConcernCategory.RIBA, 0.6),   # غرامة تأخير (قد تكون ربا إذا كانت نسبية/زمنية)
    # --- الغرر (عدم اليقين المفرط) ---
    "غرر": (ConcernCategory.GHARAR, 0.85),
    "غموض": (ConcernCategory.GHARAR, 0.5),
    "غير محدد": (ConcernCategory.GHARAR, 0.5),      # غير محدد
    "مجهول": (ConcernCategory.GHARAR, 0.55),        # مجهول/غير مُحدَّد
    "بيع ما لا يملك": (ConcernCategory.GHARAR, 0.9),  # بيع ما لا تملكه
    # --- الميسر (المضاربة/القمار) ---
    "ميسر": (ConcernCategory.MAYSIR, 0.9),
    "قمار": (ConcernCategory.MAYSIR, 0.95),
    "رهان": (ConcernCategory.MAYSIR, 0.85),          # رهان
    "مضاربه بحته": (ConcernCategory.MAYSIR, 0.7),   # مضاربة بحتة
}


@dataclass
class Flag:
    """إشارة إلى بند محتمل الإشكالية."""

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
            return "لم يتم اكتشاف أي بند مشبوه (فرز معجمي)."
        lines = [f"تم العثور على {len(self.flags)} إشارة/إشارات:"]
        for f in self.flags:
            lines.append(
                f"  [{f.category.value.upper()} | الثقة {f.confidence:.0%}] "
                f"'{f.matched_term}' في: \"{f.sentence[:80]}...\""
                if len(f.sentence) > 80
                else f"  [{f.category.value.upper()} | الثقة {f.confidence:.0%}] "
                f"'{f.matched_term}' في: \"{f.sentence}\""
            )
        return "\n".join(lines)


class RibaClassifierProtocol(Protocol):
    """واجهة لمصنّف تعلّم آلة خارجي (مثل AraBERT مُدرَّب).

    يجب على أي تنفيذ فقط احترام هذا التوقيع ليتم توصيله بـ
    `HybridContractScreener` دون تعديلات في بقية الكود.
    """

    def predict(self, sentence: str) -> list[tuple[ConcernCategory, float]]:
        """يُعيد قائمة من (الفئة، درجة الثقة 0-1) للجملة المُعطاة."""
        ...


class LexicalRibaDetector:
    """كاشف حتمي قائم على المعجم — يعمل 100% دون اتصال بالإنترنت."""

    def __init__(self, lexicon: dict[str, tuple[ConcernCategory, float]] | None = None):
        self.lexicon = lexicon or _LEXICON

    def analyze(self, contract_text: str) -> DetectionReport:
        """مطابقة على حدود الكلمة (وليس سلسلة فرعية خام)، لتجنّب
        الإيجابيات الكاذبة الشائعة في العربية — مثال: مصطلح 'ربا' يجب
        **ألا** يتطابق داخل كلمة 'الأرباح'، رغم أن هذه الأخيرة تحتويه
        كسلسلة أحرف."""
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
        """يتحقق من ظهور `needle` كتسلسل فرعي **متجاور** من رموز كاملة
        ضمن `haystack` (مطابقة على مستوى الكلمة الكاملة، لا السلسلة
        الفرعية).

        تتم مقارنة كل رمز من `haystack` عبر صيغه الخالية من اللواصق
        النحوية (مثال: 'بفائدة' -> أيضًا 'فائدة')، للتعرّف على مصطلحات
        المعجم حتى عندما تظهر مع حروف جر/عطف ملتصقة — أمر شائع جدًا في
        العربية ('بفائدة'، 'والقمار'، 'كالربا' إلخ).
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
    """يجمع بين الكاشف المعجمي ومصنّف تعلّم آلة اختياري.

    إذا تم توفير `ml_classifier` (أي كائن يحترم `RibaClassifierProtocol`)،
    تُدمَج درجاته مع الدرجات المعجمية (الحد الأقصى لكل فئة) للحصول على
    نتيجة أكثر متانة دلاليًا.
    """

    def __init__(
        self,
        lexical_detector: LexicalRibaDetector | None = None,
        ml_classifier: RibaClassifierProtocol | None = None,
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
                        matched_term="[نموذج تعلّم آلة]",
                        confidence=score,
                    )
                )
        return DetectionReport(
            text_length_chars=report.text_length_chars,
            flags=report.flags + extra_flags,
        )
