"""tests/test_pattern.py: パターンマッチ変換器の単体テスト"""

import unittest
from app.transformers.pattern import PatternTransformer, tokenize_pattern


class TestTokenizePattern(unittest.TestCase):
    """パターン文字列のトークナイズ処理のテスト"""

    def test_basic_tokens(self):
        """基本的なリテラルと変数のトークン分割を検証する。

        Returns
        -------
        None
        """
        tokens = tokenize_pattern("私は{a}時間で{b}つのりんご")
        self.assertEqual(len(tokens), 5)
        self.assertFalse(tokens[0].is_var)
        self.assertEqual(tokens[0].content, "私は")
        self.assertTrue(tokens[1].is_var)
        self.assertEqual(tokens[1].content, "a")
        self.assertFalse(tokens[2].is_var)
        self.assertEqual(tokens[2].content, "時間で")
        self.assertTrue(tokens[3].is_var)
        self.assertEqual(tokens[3].content, "b")
        self.assertFalse(tokens[4].is_var)
        self.assertEqual(tokens[4].content, "つのりんご")

    def test_backslash_escapes(self):
        """バックスラッシュによる波括弧エスケープが正しくリテラル化されることを検証する。

        Returns
        -------
        None
        """
        tokens = tokenize_pattern(r"val = \{ {var} \}")
        self.assertEqual(len(tokens), 3)
        self.assertEqual(tokens[0].content, "val = { ")
        self.assertTrue(tokens[1].is_var)
        self.assertEqual(tokens[1].content, "var")
        self.assertEqual(tokens[2].content, " }")

    def test_double_brace_escapes(self):
        """二重波括弧によるエスケープが正しくリテラル化されることを検証する。

        Returns
        -------
        None
        """
        tokens = tokenize_pattern("val = {{ {var} }}")
        self.assertEqual(tokens[0].content, "val = { ")
        self.assertTrue(tokens[1].is_var)
        self.assertEqual(tokens[1].content, "var")
        self.assertEqual(tokens[2].content, " }")


class TestPatternTransformer(unittest.TestCase):
    """PatternTransformer の変換ロジックテスト"""

    def test_reorder_numbers_example(self):
        """変数を用いた順序入れ替えパターン置換を検証する。

        Returns
        -------
        None
        """
        # ユーザー例1: "私は1時間で2つのりんごを食べました" → "私は2時間で1つのりんごを食べました"
        transformer = PatternTransformer(
            input_pattern="私は{a}時間で{b}つのりんごを食べました",
            output_template="私は{b}時間で{a}つのりんごを食べました",
        )
        input_text = "私は1時間で2つのりんごを食べました"
        result = transformer.transform(input_text)
        self.assertTrue(result.success)
        self.assertEqual(result.text, "私は2時間で1つのりんごを食べました")
        self.assertIn("パターンマッチ変換完了", result.message)

    def test_replace_part_fixed_example(self):
        """一部分のみを固定値へ置換するパターン変換を検証する。

        Returns
        -------
        None
        """
        # ユーザー例2: "高橋くんと佐藤くんと遊びました" → "高橋くんと伊藤くんと遊びました"
        transformer = PatternTransformer(
            input_pattern="高橋くんと{a}くんと遊びました",
            output_template="高橋くんと伊藤くんと遊びました",
        )
        input_text = "高橋くんと佐藤くんと遊びました"
        result = transformer.transform(input_text)
        self.assertTrue(result.success)
        self.assertEqual(result.text, "高橋くんと伊藤くんと遊びました")

    def test_partial_match_inside_sentence(self):
        """長い文章内に含まれる部分一致箇所の置換を検証する。

        Returns
        -------
        None
        """
        # 長い文章の中の一部だけを置換
        transformer = PatternTransformer(
            input_pattern="私は{a}時間で{b}つのりんごを食べました",
            output_template="私は{b}時間で{a}つのりんごを食べました",
        )
        input_text = "今日はいい天気でした。私は1時間で2つのりんごを食べました。お腹いっぱいです。"
        result = transformer.transform(input_text)
        self.assertTrue(result.success)
        self.assertEqual(
            result.text,
            "今日はいい天気でした。私は2時間で1つのりんごを食べました。お腹いっぱいです。",
        )

    def test_multiline_match(self):
        """複数行にまたがる複数箇所の一致および置換を検証する。

        Returns
        -------
        None
        """
        # 複数行の該当箇所をすべて置換
        transformer = PatternTransformer(
            input_pattern="私は{a}時間で{b}つのりんごを食べました",
            output_template="私は{b}時間で{a}つのりんごを食べました",
        )
        input_text = "私は1時間で2つのりんごを食べました\n私は3時間で5つのりんごを食べました"
        result = transformer.transform(input_text)
        self.assertTrue(result.success)
        expected = "私は2時間で1つのりんごを食べました\n私は5時間で3つのりんごを食べました"
        self.assertEqual(result.text, expected)
        self.assertIn("2箇所", result.message)

    def test_brace_escapes_in_input_and_output(self):
        """バックスラッシュエスケープを用いた波括弧含有パターンの置換を検証する。

        Returns
        -------
        None
        """
        # 入出力に波括弧が含まれる場合のエスケープ
        # 入力: fn({x}) = {100}
        # 出力: fn({x}) => {100}
        transformer = PatternTransformer(
            input_pattern=r"fn(\{{param}\}) = \{{val}\}",
            output_template=r"fn(\{{param}\}) => \{{val}\}",
        )
        input_text = "コード: fn({x}) = {100}"
        result = transformer.transform(input_text)
        self.assertTrue(result.success)
        self.assertEqual(result.text, "コード: fn({x}) => {100}")

    def test_double_brace_escapes_in_input_and_output(self):
        """二重波括弧エスケープを用いたパターンの置換を検証する。

        Returns
        -------
        None
        """
        # 二重波括弧でのエスケープ
        transformer = PatternTransformer(
            input_pattern="func({{{param}}}) = {{{val}}}",
            output_template="func({{{param}}}) => {{{val}}}",
        )
        input_text = "func({arg}) = {999}"
        result = transformer.transform(input_text)
        self.assertTrue(result.success)
        self.assertEqual(result.text, "func({arg}) => {999}")

    def test_undefined_variable_skips(self):
        """出力テンプレートに未定義の変数が含まれる場合にスキップされることを検証する。

        Returns
        -------
        None
        """
        # テンプレートに未定義変数 {c} がある場合はスキップ
        transformer = PatternTransformer(
            input_pattern="{a}と{b}",
            output_template="{a}と{c}",
        )
        result = transformer.transform("犬と猫")
        self.assertFalse(result.success)
        self.assertEqual(result.status, "skip")
        self.assertIn("未定義の変数がテンプレートに含まれています", result.message)
        self.assertIn("c", result.message)

    def test_pattern_mismatch_skips(self):
        """パターンに一致しないテキストが入力された場合にスキップされることを検証する。

        Returns
        -------
        None
        """
        transformer = PatternTransformer(
            input_pattern="私は{a}時間で{b}つのりんごを食べました",
            output_template="私は{b}時間で{a}つのりんごを食べました",
        )
        result = transformer.transform("全く関係のないテキストです")
        self.assertFalse(result.success)
        self.assertEqual(result.status, "skip")
        self.assertIn("パターンに一致する箇所が見つかりませんでした", result.message)

    def test_japanese_variable_names(self):
        """日本語を含む変数名が正しく認識・置換されることを検証する。

        Returns
        -------
        None
        """
        # 日本語変数名
        transformer = PatternTransformer(
            input_pattern="今日は{天気}で気温は{度}度です",
            output_template="気温{度}度（天気: {天気}）",
        )
        result = transformer.transform("今日は晴れで気温は25度です")
        self.assertTrue(result.success)
        self.assertEqual(result.text, "気温25度（天気: 晴れ）")


if __name__ == "__main__":
    unittest.main()
