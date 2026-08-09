import unittest

from sharia_ai.nlp.arabic_preprocessing import (
    clitic_variants,
    normalize_arabic,
    normalize_letters,
    sentence_split,
    strip_diacritics,
    tokenize,
)


class TestStripDiacritics(unittest.TestCase):
    def test_removes_tashkeel(self):
        # الفَائِدَة with full diacritics -> الفائدة
        self.assertEqual(strip_diacritics("الفَائِدَة"), "الفائدة")

    def test_no_diacritics_unchanged(self):
        self.assertEqual(strip_diacritics("الربا"), "الربا")

    def test_empty_string(self):
        self.assertEqual(strip_diacritics(""), "")


class TestNormalizeLetters(unittest.TestCase):
    def test_alef_variants_normalized(self):
        self.assertEqual(normalize_letters("آمن"), "امن")
        self.assertEqual(normalize_letters("أمن"), "امن")
        self.assertEqual(normalize_letters("إمن"), "امن")

    def test_alef_maqsura_to_ya(self):
        self.assertEqual(normalize_letters("على"), "علي")

    def test_ta_marbuta_to_ha(self):
        # فائدة contains hamza-on-ya (ئ), which also normalizes to ي,
        # and ta marbuta (ة) normalizes to ه.
        self.assertEqual(normalize_letters("فائدة"), "فايده")

    def test_hamza_variants(self):
        self.assertEqual(normalize_letters("سئل"), "سيل")
        self.assertEqual(normalize_letters("مؤمن"), "مومن")

    def test_leaves_non_arabic_untouched(self):
        self.assertEqual(normalize_letters("abc123"), "abc123")


class TestNormalizeArabic(unittest.TestCase):
    def test_full_pipeline_combines_diacritics_letters_whitespace(self):
        text = "  أَلرِّبَا   حَرَام  "
        result = normalize_arabic(text)
        # لا تشكيل، لا مسافات مكررة/طرفية، ألف موحّدة
        self.assertNotIn("\u064B", result)
        self.assertFalse(result.startswith(" "))
        self.assertFalse(result.endswith(" "))
        self.assertNotIn("  ", result)
        self.assertNotIn("أ", result)

    def test_collapses_multiple_whitespace(self):
        result = normalize_arabic("كلمة   أخرى")
        self.assertNotIn("   ", result)
        self.assertNotIn("  ", result)

    def test_idempotent(self):
        text = "القرض بفائدة مركبة"
        once = normalize_arabic(text)
        twice = normalize_arabic(once)
        self.assertEqual(once, twice)


class TestTokenize(unittest.TestCase):
    def test_basic_tokenization(self):
        tokens = tokenize("القرض بفائدة مركبة")
        self.assertEqual(tokens, ["القرض", "بفايده", "مركبه"])

    def test_strips_punctuation(self):
        tokens = tokenize("الربا، والقمار؛ ممنوعان!")
        self.assertNotIn("،", tokens)
        self.assertNotIn("؛", tokens)
        self.assertNotIn("!", tokens)

    def test_empty_text_returns_empty_list(self):
        self.assertEqual(tokenize(""), [])

    def test_ascii_punctuation_only_returns_empty_list(self):
        # ASCII punctuation is outside \w and outside the Arabic block,
        # so it is treated purely as a separator.
        self.assertEqual(tokenize("... !"), [])

    def test_arabic_punctuation_marks_survive_as_tokens(self):
        # Arabic comma/semicolon fall within the \u0600-\u06FF block used
        # by the tokenizer's "keep" set, so they are not stripped like
        # ASCII punctuation is.
        tokens = tokenize("، ؛")
        self.assertEqual(tokens, ["،", "؛"])


class TestCliticVariants(unittest.TestCase):
    def test_returns_original_token(self):
        variants = clitic_variants("فائدة")
        self.assertIn("فائدة", variants)

    def test_strips_single_letter_prefix(self):
        variants = clitic_variants("بفائدة")
        self.assertIn("فائدة", variants)
        self.assertIn("بفائدة", variants)

    def test_strips_definite_article(self):
        variants = clitic_variants("الربا")
        self.assertIn("ربا", variants)
        self.assertIn("الربا", variants)

    def test_strips_prefix_then_definite_article(self):
        variants = clitic_variants("والقمار")
        self.assertIn("والقمار", variants)
        self.assertIn("القمار", variants)
        self.assertIn("قمار", variants)

    def test_respects_min_len_short_token_untouched(self):
        # too short after stripping prefix -> should not add spurious short variants
        variants = clitic_variants("بر", min_len=2)
        self.assertEqual(variants, {"بر"})

    def test_no_prefix_no_article_only_original(self):
        variants = clitic_variants("قمار")
        self.assertEqual(variants, {"قمار"})


class TestSentenceSplit(unittest.TestCase):
    def test_splits_on_periods(self):
        parts = sentence_split("الجملة الأولى. الجملة الثانية.")
        self.assertEqual(parts, ["الجملة الأولى", "الجملة الثانية"])

    def test_splits_on_arabic_punctuation(self):
        parts = sentence_split("بند أول؛ بند ثاني؟ بند ثالث")
        self.assertEqual(len(parts), 3)

    def test_splits_on_newlines(self):
        parts = sentence_split("سطر أول\nسطر ثاني")
        self.assertEqual(parts, ["سطر أول", "سطر ثاني"])

    def test_strips_empty_fragments(self):
        parts = sentence_split("جملة واحدة...")
        self.assertEqual(parts, ["جملة واحدة"])

    def test_empty_text_returns_empty_list(self):
        self.assertEqual(sentence_split(""), [])


if __name__ == "__main__":
    unittest.main()
