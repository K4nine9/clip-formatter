"""tests/test_preset.py: 定型ルール変換器の単体テスト"""

import unittest
from app.transformers.preset import (
    ColumnExtractTransformer,
    NumberFormatTransformer,
    PresetTransformer,
    RoundTransformer,
    ZeroPadTransformer,
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


class TestZeroPadTransformer(unittest.TestCase):
    """数値ゼロ埋め（パディング）変換器のテスト"""

    def test_pad_integer_only(self):
        transformer = ZeroPadTransformer(int_digits=3, dec_digits=0)
        result = transformer.transform("5, 42.1, -7, 1234")
        self.assertTrue(result.success)
        self.assertEqual(result.text, "005, 042.1, -007, 1234")

    def test_pad_decimal_only(self):
        transformer = ZeroPadTransformer(int_digits=0, dec_digits=2)
        result = transformer.transform("5, 42.1, 3.1415")
        self.assertTrue(result.success)
        self.assertEqual(result.text, "5.00, 42.10, 3.14")

    def test_pad_both_integer_and_decimal(self):
        transformer = ZeroPadTransformer(int_digits=3, dec_digits=2)
        result = transformer.transform("5, 42.1, -7.5, 98.2%")
        self.assertTrue(result.success)
        self.assertEqual(result.text, "005.00, 042.10, -007.50, 098.20%")

    def test_rounding_carry_over(self):
        # 0.999 を小数2桁に丸めると 1.00 になり、整数部が 0 -> 1 になるケース
        transformer = ZeroPadTransformer(int_digits=3, dec_digits=2)
        result = transformer.transform("0.999")
        self.assertTrue(result.success)
        self.assertEqual(result.text, "001.00")

    def test_invalid_digits_raises(self):
        with self.assertRaises(ValueError):
            ZeroPadTransformer(int_digits=0, dec_digits=0)


class TestNumberFormatTransformer(unittest.TestCase):
    """整数部・小数部を個別に設定する数値フォーマット変換器のテスト"""

    def test_pad_int_and_round_dec(self):
        # 整数3桁ゼロ埋め ＋ 小数2桁四捨五入（可変長）
        transformer = NumberFormatTransformer(
            int_mode="pad", int_digits=3, dec_mode="round", dec_digits=2, dec_overflow="round"
        )
        # 5 -> 005 (小数なし), 42.1 -> 042.1 (小数1桁はそのまま), 7.896 -> 007.90 (四捨五入)
        result = transformer.transform("5, 42.1, 7.896, -3.5")
        self.assertTrue(result.success)
        self.assertEqual(result.text, "005, 042.1, 007.90, -003.5")

    def test_pad_int_and_truncate_dec_backward_compat(self):
        # 後方互換: dec_mode="truncate" の指定
        transformer = NumberFormatTransformer(
            int_mode="pad", int_digits=3, dec_mode="truncate", dec_digits=2
        )
        result = transformer.transform("7.896, 5, 42.1")
        self.assertTrue(result.success)
        self.assertEqual(result.text, "007.89, 005, 042.1")

    def test_pad_dec_with_truncate(self):
        # 小数部ゼロ埋め（固定長）＋ 超過時切り捨て
        transformer = NumberFormatTransformer(
            int_mode="none", dec_mode="pad", dec_digits=2, dec_overflow="truncate"
        )
        # 3.149 -> 3.14 (切り捨て), 3.1 -> 3.10 (0埋め), 5 -> 5.00 (0埋め)
        result = transformer.transform("3.149, 3.1, 5")
        self.assertTrue(result.success)
        self.assertEqual(result.text, "3.14, 3.10, 5.00")

    def test_round_dec_with_truncate(self):
        # 小数部丸め（可変長）＋ 超過時切り捨て
        transformer = NumberFormatTransformer(
            int_mode="none", dec_mode="round", dec_digits=2, dec_overflow="truncate"
        )
        # 3.149 -> 3.14 (切り捨て), 3.1 -> 3.1 (可変長のためそのまま), 5 -> 5 (そのまま)
        result = transformer.transform("3.149, 3.1, 5")
        self.assertTrue(result.success)
        self.assertEqual(result.text, "3.14, 3.1, 5")

    def test_pad_int_and_pad_dec_with_truncate(self):
        # 整数3桁ゼロ埋め ＋ 小数2桁ゼロ埋め（固定長・超過時切り捨て）
        transformer = NumberFormatTransformer(
            int_mode="pad", int_digits=3, dec_mode="pad", dec_digits=2, dec_overflow="truncate"
        )
        result = transformer.transform("5, 42.1, 7.896")
        self.assertTrue(result.success)
        self.assertEqual(result.text, "005.00, 042.10, 007.89")

    def test_dec_digits_zero_truncate(self):
        # 小数0桁指定（整数化・切り捨て）
        transformer = NumberFormatTransformer(
            int_mode="none", dec_mode="round", dec_digits=0, dec_overflow="truncate"
        )
        result = transformer.transform("12.34, 12.89")
        self.assertTrue(result.success)
        self.assertEqual(result.text, "12, 12")

    def test_pad_int_and_pad_dec(self):
        # 整数3桁ゼロ埋め ＋ 小数2桁ゼロ埋め（固定長・デフォルト四捨五入）
        transformer = NumberFormatTransformer(
            int_mode="pad", int_digits=3, dec_mode="pad", dec_digits=2, dec_overflow="round"
        )
        result = transformer.transform("5, 42.1, 7.896")
        self.assertTrue(result.success)
        self.assertEqual(result.text, "005.00, 042.10, 007.90")


class TestPresetTransformer(unittest.TestCase):
    """複合定型ルール変換器のテスト"""

    def test_combined_separated_number_and_col_extract(self):
        # 新しい分離設定（整数部パディング3桁、小数部四捨五入2桁、列抽出）
        transformer = PresetTransformer(
            int_mode="pad",
            int_digits=3,
            dec_mode="round",
            dec_digits=2,
            dec_overflow="round",
            col_enabled=True,
            col_delimiter=",",
            col_indices=[1, 2],
        )
        input_text = "ItemA, 5\nItemB, 42.158"
        result = transformer.transform(input_text)
        self.assertTrue(result.success)
        self.assertEqual(result.text, "ItemA, 005\nItemB, 042.16")

    def test_combined_separated_number_pad_truncate(self):
        # 整数3桁ゼロ埋め ＋ 小数2桁ゼロ埋め（超過時切り捨て）＋ 列抽出
        transformer = PresetTransformer(
            int_mode="pad",
            int_digits=3,
            dec_mode="pad",
            dec_digits=2,
            dec_overflow="truncate",
            col_enabled=True,
            col_delimiter=",",
            col_indices=[1, 2],
        )
        input_text = "ItemA, 5\nItemB, 42.158"
        result = transformer.transform(input_text)
        self.assertTrue(result.success)
        # 5 -> 005.00, 42.158 -> 042.15 (切り捨て)
        self.assertEqual(result.text, "ItemA, 005.00\nItemB, 042.15")

    def test_backward_compat_round(self):
        transformer = PresetTransformer(
            round_enabled=True,
            round_digits=2,
            col_enabled=False,
        )
        result = transformer.transform("95.2251%")
        self.assertTrue(result.success)
        self.assertEqual(result.text, "95.23%")

    def test_backward_compat_pad(self):
        transformer = PresetTransformer(
            pad_enabled=True,
            pad_int_digits=3,
            pad_dec_digits=2,
            col_enabled=False,
        )
        result = transformer.transform("5")
        self.assertTrue(result.success)
        self.assertEqual(result.text, "005.00")

    def test_no_rule_enabled(self):
        transformer = PresetTransformer(int_mode="none", dec_mode="none", col_enabled=False)
        result = transformer.transform("12.345%")
        self.assertFalse(result.success)
        self.assertEqual(result.status, "skip")


if __name__ == "__main__":
    unittest.main()
