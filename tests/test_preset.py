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
        """パーセント表記の数値が指定桁数で四捨五入されることを検証する。

        Returns
        -------
        None
        """
        transformer = RoundTransformer(digits=2)
        result = transformer.transform("精度は 95.2251% でした。")
        self.assertTrue(result.success)
        self.assertEqual(result.text, "精度は 95.23% でした。")
        self.assertEqual(result.message, "小数2桁丸め")

    def test_round_negative_and_multiple_numbers(self):
        """負数や符号付き複数数値の丸め処理を検証する。

        Returns
        -------
        None
        """
        transformer = RoundTransformer(digits=1)
        result = transformer.transform("loss: -0.456, val_loss: +1.289")
        self.assertTrue(result.success)
        self.assertEqual(result.text, "loss: -0.5, val_loss: +1.3")

    def test_round_zero_digits(self):
        """小数0桁（整数四捨五入）の丸め処理を検証する。

        Returns
        -------
        None
        """
        transformer = RoundTransformer(digits=0)
        result = transformer.transform("スコア: 88.75点")
        self.assertTrue(result.success)
        self.assertEqual(result.text, "スコア: 89点")

    def test_no_match_unchanged(self):
        """丸め対象の小数を含まないテキストで変更が行われないことを検証する。

        Returns
        -------
        None
        """
        transformer = RoundTransformer(digits=2)
        result = transformer.transform("数値なしテキスト 100")
        self.assertFalse(result.success)
        self.assertEqual(result.text, "数値なしテキスト 100")


class TestColumnExtractTransformer(unittest.TestCase):
    """列抽出変換器のテスト"""

    def test_single_line_first_and_last(self):
        """単一行のカンマ区切りデータから先頭列と末尾列を抽出できることを検証する。

        Returns
        -------
        None
        """
        # 1-based: 1 (先頭), -1 (末尾)
        transformer = ColumnExtractTransformer(indices=[1, -1], delimiter=",")
        result = transformer.transform("apple, banana, cherry, date")
        self.assertTrue(result.success)
        self.assertEqual(result.text, "apple, date")

    def test_multiline_extraction(self):
        """複数行データから指定列が正しく抽出されることを検証する。

        Returns
        -------
        None
        """
        input_text = "id, name, age, dept\n1, Alice, 25, HR\n2, Bob, 30, Dev"
        transformer = ColumnExtractTransformer(indices=[1, 2, -1], delimiter=",")
        result = transformer.transform(input_text)
        self.assertTrue(result.success)
        expected = "id, name, dept\n1, Alice, HR\n2, Bob, Dev"
        self.assertEqual(result.text, expected)

    def test_tab_delimiter(self):
        """タブ区切りデータからの列抽出を検証する。

        Returns
        -------
        None
        """
        input_text = "col1\tcol2\tcol3\nval1\tval2\tval3"
        transformer = ColumnExtractTransformer(
            indices=[2], delimiter="\t", output_delimiter=" | "
        )
        result = transformer.transform(input_text)
        self.assertTrue(result.success)
        self.assertEqual(result.text, "col2\nval2")

    def test_parse_indices_string(self):
        """インデックス文字列のパースおよび不正文字列時の例外発生を検証する。

        Returns
        -------
        None
        """
        indices = ColumnExtractTransformer.parse_indices_string("1, -1, 3")
        self.assertEqual(indices, [1, -1, 3])

        with self.assertRaises(ValueError):
            ColumnExtractTransformer.parse_indices_string("0, 1")

    def test_insufficient_columns_fallback(self):
        """列数が不足している行がある場合にフォールバックして保持されることを検証する。

        Returns
        -------
        None
        """
        # 1行目は3列あるが、2行目は1列のみの場合、有効行は抽出され、不足行はそのまま保持される
        input_text = "a, b, c\nx"
        transformer = ColumnExtractTransformer(indices=[1, 3], delimiter=",")
        result = transformer.transform(input_text)
        self.assertTrue(result.success)
        self.assertEqual(result.text, "a, c\nx")


class TestZeroPadTransformer(unittest.TestCase):
    """数値ゼロ埋め（パディング）変換器のテスト"""

    def test_pad_integer_only(self):
        """整数部のみのゼロ埋めが正しく行われることを検証する。

        Returns
        -------
        None
        """
        transformer = ZeroPadTransformer(int_digits=3, dec_digits=0)
        result = transformer.transform("5, 42.1, -7, 1234")
        self.assertTrue(result.success)
        self.assertEqual(result.text, "005, 042.1, -007, 1234")

    def test_pad_decimal_only(self):
        """小数部のみのゼロ埋め（固定長化）を検証する。

        Returns
        -------
        None
        """
        transformer = ZeroPadTransformer(int_digits=0, dec_digits=2)
        result = transformer.transform("5, 42.1, 3.1415")
        self.assertTrue(result.success)
        self.assertEqual(result.text, "5.00, 42.10, 3.14")

    def test_pad_both_integer_and_decimal(self):
        """整数部・小数部両方のゼロ埋めを検証する。

        Returns
        -------
        None
        """
        transformer = ZeroPadTransformer(int_digits=3, dec_digits=2)
        result = transformer.transform("5, 42.1, -7.5, 98.2%")
        self.assertTrue(result.success)
        self.assertEqual(result.text, "005.00, 042.10, -007.50, 098.20%")

    def test_rounding_carry_over(self):
        """小数部丸めによる繰り上がり時の整数部ゼロ埋めを検証する。

        Returns
        -------
        None
        """
        # 0.999 を小数2桁に丸めると 1.00 になり、整数部が 0 -> 1 になるケース
        transformer = ZeroPadTransformer(int_digits=3, dec_digits=2)
        result = transformer.transform("0.999")
        self.assertTrue(result.success)
        self.assertEqual(result.text, "001.00")

    def test_invalid_digits_raises(self):
        """両方の桁数が0の場合に ValueError が送出されることを検証する。

        Returns
        -------
        None
        """
        with self.assertRaises(ValueError):
            ZeroPadTransformer(int_digits=0, dec_digits=0)


class TestNumberFormatTransformer(unittest.TestCase):
    """整数部・小数部を個別に設定する数値フォーマット変換器のテスト"""

    def test_pad_int_and_round_dec(self):
        """整数部のゼロ埋めと小数部の四捨五入丸めが同時に適用されることを検証する。

        Returns
        -------
        None
        """
        # 整数3桁ゼロ埋め ＋ 小数2桁四捨五入（可変長）
        transformer = NumberFormatTransformer(
            int_mode="pad", int_digits=3, dec_mode="round", dec_digits=2, dec_overflow="round"
        )
        # 5 -> 005 (小数なし), 42.1 -> 042.1 (小数1桁はそのまま), 7.896 -> 007.90 (四捨五入)
        result = transformer.transform("5, 42.1, 7.896, -3.5")
        self.assertTrue(result.success)
        self.assertEqual(result.text, "005, 042.1, 007.90, -003.5")

    def test_pad_int_and_truncate_dec_backward_compat(self):
        """dec_mode='truncate' の後方互換指定時の動作を検証する。

        Returns
        -------
        None
        """
        # 後方互換: dec_mode="truncate" の指定
        transformer = NumberFormatTransformer(
            int_mode="pad", int_digits=3, dec_mode="truncate", dec_digits=2
        )
        result = transformer.transform("7.896, 5, 42.1")
        self.assertTrue(result.success)
        self.assertEqual(result.text, "007.89, 005, 042.1")

    def test_pad_dec_with_truncate(self):
        """小数部のゼロ埋め（固定長）と超過時切り捨てが正しく動作することを検証する。

        Returns
        -------
        None
        """
        # 小数部ゼロ埋め（固定長）＋ 超過時切り捨て
        transformer = NumberFormatTransformer(
            int_mode="none", dec_mode="pad", dec_digits=2, dec_overflow="truncate"
        )
        # 3.149 -> 3.14 (切り捨て), 3.1 -> 3.10 (0埋め), 5 -> 5.00 (0埋め)
        result = transformer.transform("3.149, 3.1, 5")
        self.assertTrue(result.success)
        self.assertEqual(result.text, "3.14, 3.10, 5.00")

    def test_round_dec_with_truncate(self):
        """小数部の丸め（可変長）と超過時切り捨てが正しく動作することを検証する。

        Returns
        -------
        None
        """
        # 小数部丸め（可変長）＋ 超過時切り捨て
        transformer = NumberFormatTransformer(
            int_mode="none", dec_mode="round", dec_digits=2, dec_overflow="truncate"
        )
        # 3.149 -> 3.14 (切り捨て), 3.1 -> 3.1 (可変長のためそのまま), 5 -> 5 (そのまま)
        result = transformer.transform("3.149, 3.1, 5")
        self.assertTrue(result.success)
        self.assertEqual(result.text, "3.14, 3.1, 5")

    def test_pad_int_and_pad_dec_with_truncate(self):
        """整数部ゼロ埋めと小数部固定長ゼロ埋め（超過時切り捨て）の組み合わせを検証する。

        Returns
        -------
        None
        """
        # 整数3桁ゼロ埋め ＋ 小数2桁ゼロ埋め（固定長・超過時切り捨て）
        transformer = NumberFormatTransformer(
            int_mode="pad", int_digits=3, dec_mode="pad", dec_digits=2, dec_overflow="truncate"
        )
        result = transformer.transform("5, 42.1, 7.896")
        self.assertTrue(result.success)
        self.assertEqual(result.text, "005.00, 042.10, 007.89")

    def test_dec_digits_zero_truncate(self):
        """小数部0桁指定による切り捨て（整数化）を検証する。

        Returns
        -------
        None
        """
        # 小数0桁指定（整数化・切り捨て）
        transformer = NumberFormatTransformer(
            int_mode="none", dec_mode="round", dec_digits=0, dec_overflow="truncate"
        )
        result = transformer.transform("12.34, 12.89")
        self.assertTrue(result.success)
        self.assertEqual(result.text, "12, 12")

    def test_pad_int_and_pad_dec(self):
        """整数部・小数部の固定長ゼロ埋めと四捨五入の組み合わせを検証する。

        Returns
        -------
        None
        """
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
        """数値フォーマットと列抽出の複合適用を検証する。

        Returns
        -------
        None
        """
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
        """数値固定長ゼロ埋め（切り捨て）と列抽出の複合適用を検証する。

        Returns
        -------
        None
        """
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
        """PresetTransformer の丸め後方互換フラグを検証する。

        Returns
        -------
        None
        """
        transformer = PresetTransformer(
            round_enabled=True,
            round_digits=2,
            col_enabled=False,
        )
        result = transformer.transform("95.2251%")
        self.assertTrue(result.success)
        self.assertEqual(result.text, "95.23%")

    def test_backward_compat_pad(self):
        """PresetTransformer のゼロ埋め後方互換フラグを検証する。

        Returns
        -------
        None
        """
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
        """いずれのルールも有効でない場合にスキップされることを検証する。

        Returns
        -------
        None
        """
        transformer = PresetTransformer(int_mode="none", dec_mode="none", col_enabled=False)
        result = transformer.transform("12.345%")
        self.assertFalse(result.success)
        self.assertEqual(result.status, "skip")


if __name__ == "__main__":
    unittest.main()
