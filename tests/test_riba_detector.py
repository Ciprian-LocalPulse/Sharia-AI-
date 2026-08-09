import unittest

from sharia_ai.nlp.riba_detector import ConcernCategory, LexicalRibaDetector


class TestLexicalRibaDetector(unittest.TestCase):
    def setUp(self):
        self.detector = LexicalRibaDetector()

    def test_detects_riba_keyword(self):
        text = "يلتزم المقترض بسداد القرض بفائدة سنوية قدرها خمسة بالمئة."
        report = self.detector.analyze(text)
        self.assertTrue(report.has_concerns)
        self.assertIn(ConcernCategory.RIBA, report.categories_found)

    def test_detects_maysir_keyword(self):
        text = "يخضع هذا العقد لشروط قمار بين الطرفين."
        report = self.detector.analyze(text)
        self.assertIn(ConcernCategory.MAYSIR, report.categories_found)

    def test_clean_text_has_no_flags(self):
        text = "يلتزم الطرف الأول بتسليم البضاعة في الموعد المحدد مقابل ثمن معلوم."
        report = self.detector.analyze(text)
        self.assertFalse(report.has_concerns)

    def test_no_false_positive_on_profits_word(self):
        # 'الأرباح' (profituri) NU trebuie confundat cu 'ربا' (riba) ca substring
        text = "يتفق الطرفان على تقاسم الأرباح والخسائر بنسب محددة سلفًا."
        report = self.detector.analyze(text)
        self.assertFalse(report.has_concerns)

    def test_detects_riba_with_attached_preposition(self):
        # 'بفائدة' = 'ب' (cu) + 'فائدة' (dobândă), fără spațiu — clitic arab uzual
        text = "يُسدد القرض بفائدة سنوية."
        report = self.detector.analyze(text)
        self.assertIn(ConcernCategory.RIBA, report.categories_found)

    def test_empty_text_returns_empty_report(self):
        report = self.detector.analyze("")
        self.assertFalse(report.has_concerns)
        self.assertEqual(len(report.flags), 0)


if __name__ == "__main__":
    unittest.main()
