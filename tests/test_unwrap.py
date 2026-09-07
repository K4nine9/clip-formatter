"""tests/test_unwrap.py: 改行・ハイフン除去 (Unwrap) の単体テスト"""

import unittest

from app.transformers.preset import PresetTransformer
from app.transformers.unwrap import TextUnwrapTransformer


class TestTextUnwrapTransformer(unittest.TestCase):
    """TextUnwrapTransformer の単体テスト"""

    def setUp(self):
        self.transformer = TextUnwrapTransformer()

    def test_english_newline_removal(self):
        # 英文の単一改行が半角スペースで結合される
        text = "Recent advances in deep learning\nhave enabled significant improvements\nin natural language processing."
        res = self.transformer.transform(text)
        self.assertTrue(res.success)
        self.assertEqual(
            res.text,
            "Recent advances in deep learning have enabled significant improvements in natural language processing.",
        )

    def test_hyphen_dehyphenation(self):
        # 行末のハイフン分断が結合される
        text = "Deep neural networks are cap-\nable of learning complex repre-\nsentations from data."
        res = self.transformer.transform(text)
        self.assertTrue(res.success)
        self.assertEqual(
            res.text,
            "Deep neural networks are capable of learning complex representations from data.",
        )

    def test_paragraphs_preserved(self):
        # 空行区切りの段落構造は保持される
        text = (
            "Paragraph one line one\n"
            "paragraph one line two.\n\n"
            "Paragraph two line one\n"
            "paragraph two line two."
        )
        res = self.transformer.transform(text)
        self.assertTrue(res.success)
        expected = (
            "Paragraph one line one paragraph one line two.\n\n"
            "Paragraph two line one paragraph two line two."
        )
        self.assertEqual(res.text, expected)

    def test_japanese_smart_joining(self):
        # 和文同士の行末改行は半角スペースなしで直接結合される
        text = "近年、深層学習技術の\n急速な発展により、自然言語処理の\n精度が大幅に向上しました。"
        res = self.transformer.transform(text)
        self.assertTrue(res.success)
        self.assertEqual(
            res.text,
            "近年、深層学習技術の急速な発展により、自然言語処理の精度が大幅に向上しました。",
        )

    def test_preset_transformer_with_unwrap(self):
        # PresetTransformer への統合動作
        pt = PresetTransformer(
            unwrap_enabled=True,
            int_mode="pad",
            int_digits=3,
        )
        text = "Value is 5 and\nscore is 42."
        res = pt.transform(text)
        self.assertTrue(res.success)
        self.assertEqual(res.text, "Value is 005 and score is 042.")


if __name__ == "__main__":
    unittest.main()
