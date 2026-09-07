"""tests/test_preset.py: 定型ルール変換器の単体テスト"""

import unittest
from app.transformers.preset import (
    ColumnExtractTransformer,
    PresetTransformer,
    RoundTransformer,
)


class TestRoundTransformer(unittest.TestCase):
    """数値・パーセント丸め変換器のテスト"""

    def test_round_percentage(self):
        transformer = RoundTransformer(digits=2)
        result = transformer.transform("精度は 95.2251% でした。")
        self.assertTrue(result.success)
        self.assertEqual(result.text, "精度は 95.23% でした。")
        self.assertEqual(result.message, "小数2桁丸め")

    def test_round_negative_and_multiple_numbers(self):
        transformer = RoundTransformer(digits=1)
        result = transformer.transform("loss: -0.456, val_loss: +1.289")
        self.assertTrue(result.success)
        self.assertEqual(result.text, "loss: -0.5, val_loss: +1.3")

    def test_round_zero_digits(self):
        transformer = RoundTransformer(digits=0)
        result = transformer.transform("スコア: 88.75点")
        self.assertTrue(result.success)
        self.assertEqual(result.text, "スコア: 89点")

    def test_no_match_unchanged(self):
        transformer = RoundTransformer(digits=2)
        result = transformer.transform("数値なしテキスト 100")
        self.assertFalse(result.success)
        self.assertEqual(result.text, "数値なしテキスト 100")


class TestColumnExtractTransformer(unittest.TestCase):
    """列抽出変換器のテスト"""

    def test_single_line_first_and_last(self):
        # 1-based: 1 (先頭), -1 (末尾)
        transformer = ColumnExtractTransformer(indices=[1, -1], delimiter=",")
        result = transformer.transform("apple, banana, cherry, date")
        self.assertTrue(result.success)
        self.assertEqual(result.text, "apple, date")

    def test_multiline_extraction(self):
        input_text = "id, name, age, dept\n1, Alice, 25, HR\n2, Bob, 30, Dev"
        transformer = ColumnExtractTransformer(indices=[1, 2, -1], delimiter=",")
        result = transformer.transform(input_text)
        self.assertTrue(result.success)
        expected = "id, name, dept\n1, Alice, HR\n2, Bob, Dev"
        self.assertEqual(result.text, expected)

    def test_tab_delimiter(self):
        input_text = "col1\tcol2\tcol3\nval1\tval2\tval3"
        transformer = ColumnExtractTransformer(
            indices=[2], delimiter="\t", output_delimiter=" | "
        )
        result = transformer.transform(input_text)
        self.assertTrue(result.success)
        self.assertEqual(result.text, "col2\nval2")

    def test_parse_indices_string(self):
        indices = ColumnExtractTransformer.parse_indices_string("1, -1, 3")
        self.assertEqual(indices, [1, -1, 3])

        with self.assertRaises(ValueError):
            ColumnExtractTransformer.parse_indices_string("0, 1")

    def test_insufficient_columns_fallback(self):
        # 1行目は3列あるが、2行目は1列のみの場合、有効行は抽出され、不足行はそのまま保持される
        input_text = "a, b, c\nx"
        transformer = ColumnExtractTransformer(indices=[1, 3], delimiter=",")
        result = transformer.transform(input_text)
        self.assertTrue(result.success)
        self.assertEqual(result.text, "a, c\nx")


class TestPresetTransformer(unittest.TestCase):
    """複合定型ルール変換器のテスト"""

    def test_combined_round_and_column_extract(self):
        transformer = PresetTransformer(
            round_enabled=True,
            round_digits=2,
            col_enabled=True,
            col_delimiter=",",
            col_indices=[1, 3],
        )
        # 1列目: 名前, 2列目: 未使用, 3列目: パーセント
        input_text = "Alice, dummy, 95.1234%\nBob, dummy, 80.5678%"
        result = transformer.transform(input_text)
        self.assertTrue(result.success)
        expected = "Alice, 95.12%\nBob, 80.57%"
        self.assertEqual(result.text, expected)
        self.assertIn("小数2桁丸め", result.message)
        self.assertIn("列抽出", result.message)

    def test_no_rule_enabled(self):
        transformer = PresetTransformer(round_enabled=False, col_enabled=False)
        result = transformer.transform("12.345%")
        self.assertFalse(result.success)
        self.assertEqual(result.status, "skip")


if __name__ == "__main__":
    unittest.main()
