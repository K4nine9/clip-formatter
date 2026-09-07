"""Pythonスクリプト実行変換器の単体テスト。"""

import unittest

from app.transformers.python_exec import (
    PythonScriptTransformer,
    execute_user_script,
    sanitize_result,
)


class TestSanitizeResult(unittest.TestCase):
    """sanitize_result 関数のテスト。"""

    def test_sanitize_types(self):
        """様々なPythonオブジェクト型が適切な文字列に正規化されることを検証する。

        Returns
        -------
        None
        """
        self.assertEqual(sanitize_result(None), "")
        self.assertEqual(sanitize_result("hello"), "hello")
        self.assertEqual(sanitize_result(123), "123")
        self.assertEqual(sanitize_result(3.14), "3.14")
        self.assertEqual(sanitize_result(True), "True")
        self.assertEqual(sanitize_result([1, 2, "three"]), "1\n2\nthree")
        self.assertIn("key", sanitize_result({"key": "val"}))


class TestExecuteUserScript(unittest.TestCase):
    """execute_user_script 関数のテスト。"""

    def test_successful_script(self):
        """正常なユーザースクリプト実行で result 変数の値が返されることを検証する。

        Returns
        -------
        None
        """
        code = "result = f'{int(a) + int(b)}'"
        scope = {"a": "10", "b": "25"}
        ok, res, err = execute_user_script(code, scope)
        self.assertTrue(ok)
        self.assertEqual(res, "35")
        self.assertIsNone(err)

    def test_math_module(self):
        """math モジュールを利用したスクリプトが正しく実行されることを検証する。

        Returns
        -------
        None
        """
        code = "result = f'{math.sqrt(float(x)):.2f}'"
        scope = {"x": "16"}
        ok, res, err = execute_user_script(code, scope)
        self.assertTrue(ok)
        self.assertEqual(res, "4.00")

    def test_missing_result_variable(self):
        """result 変数が未代入の場合にエラーが返されることを検証する。

        Returns
        -------
        None
        """
        code = "x = 1 + 2"
        ok, res, err = execute_user_script(code, {})
        self.assertFalse(ok)
        self.assertIsNone(res)
        self.assertIn("result", err)

    def test_syntax_error(self):
        """構文エラーのあるスクリプトを実行した際に構文エラーメッセージが返されることを検証する。

        Returns
        -------
        None
        """
        code = "result = 1 +"
        ok, res, err = execute_user_script(code, {})
        self.assertFalse(ok)
        self.assertIn("構文エラー", err)

    def test_zero_division_error(self):
        """ゼロ除算などの実行時例外が捕捉されエラーメッセージが返されることを検証する。

        Returns
        -------
        None
        """
        code = "result = 10 / 0"
        ok, res, err = execute_user_script(code, {})
        self.assertFalse(ok)
        self.assertIn("ZeroDivisionError", err)

    def test_undefined_variable_error(self):
        """未定義の変数を参照した際に NameError が捕捉されることを検証する。

        Returns
        -------
        None
        """
        code = "result = undefined_foo + 1"
        ok, res, err = execute_user_script(code, {})
        self.assertFalse(ok)
        self.assertIn("NameError", err)


class TestPythonScriptTransformer(unittest.TestCase):
    """PythonScriptTransformer の各入力モードに対するテスト。"""

    def test_pattern_mode_simple(self):
        """パターン入力モードでのスクリプト置換を検証する。

        Returns
        -------
        None
        """
        transformer = PythonScriptTransformer(
            input_mode="pattern",
            pattern_input="私は{a}時間で{b}個食べました",
            script_code="result = f'私は{int(a)*2}時間で{int(b)*3}個食べました'",
        )
        text = "私は2時間で3個食べました"
        res = transformer.transform(text)
        self.assertTrue(res.success)
        self.assertEqual(res.text, "私は4時間で9個食べました")

    def test_pattern_mode_no_match(self):
        """パターン入力モードでマッチしない場合にスキップされることを検証する。

        Returns
        -------
        None
        """
        transformer = PythonScriptTransformer(
            input_mode="pattern",
            pattern_input="リンゴが{a}個",
            script_code="result = f'{a}個'",
        )
        res = transformer.transform("ミカンが5個")
        self.assertFalse(res.success)
        self.assertIn("見つかりませんでした", res.message)

    def test_delimiter_mode_multiline(self):
        """区切り文字モードでの複数行スクリプト変換を検証する。

        Returns
        -------
        None
        """
        transformer = PythonScriptTransformer(
            input_mode="delimiter",
            delimiter=",",
            var_names="item, price, qty",
            script_code="subtotal = int(price) * int(qty)\nresult = f'{item}: {subtotal}円'",
        )
        text = "Apple, 100, 2\nBanana, 80, 5"
        res = transformer.transform(text)
        self.assertTrue(res.success)
        self.assertEqual(res.text, "Apple: 200円\nBanana: 400円")

    def test_delimiter_mode_mismatch_element_count(self):
        """区切り文字モードで要素数が不一致の行がある場合にスキップされることを検証する。

        Returns
        -------
        None
        """
        transformer = PythonScriptTransformer(
            input_mode="delimiter",
            delimiter=",",
            var_names="a, b",
            script_code="result = f'{a}-{b}'",
        )
        text = "one, two, three"
        res = transformer.transform(text)
        self.assertFalse(res.success)
        self.assertIn("要素数が一致しません", res.message)

    def test_full_text_mode(self):
        """全文入力モードでのスクリプト変換を検証する。

        Returns
        -------
        None
        """
        transformer = PythonScriptTransformer(
            input_mode="full_text",
            script_code=(
                "total = sum(float(line.strip()) for line in lines if line.strip())\n"
                "result = f'合計: {total:.1f}'"
            ),
        )
        text = "10.5\n20.0\n30.5"
        res = transformer.transform(text)
        self.assertTrue(res.success)
        self.assertEqual(res.text, "合計: 61.0")

    def test_empty_text(self):
        """入力テキストが空の場合にスキップされることを検証する。

        Returns
        -------
        None
        """
        transformer = PythonScriptTransformer(
            input_mode="full_text",
            script_code="result = 'abc'",
        )
        res = transformer.transform("")
        self.assertFalse(res.success)
        self.assertEqual(res.message, "入力テキストが空です")

    def test_script_runtime_error_handled(self):
        """スクリプト実行時エラーが安全にハンドリングされメッセージに含まれることを検証する。

        Returns
        -------
        None
        """
        transformer = PythonScriptTransformer(
            input_mode="full_text",
            script_code="result = 1 / 0",
        )
        res = transformer.transform("some text")
        self.assertFalse(res.success)
        self.assertIn("ZeroDivisionError", res.message)

    def test_non_identifier_variable_names(self):
        """不正な識別子名の変数が定義されている場合でも vars 辞書から参照できることを検証する。

        Returns
        -------
        None
        """
        # 変数名にハイフンが含まれていても辞書 vars から安全に参照可能
        transformer = PythonScriptTransformer(
            input_mode="pattern",
            pattern_input="項目{item-1}の値",
            script_code="result = f'取得: {vars[\"item-1\"]}'",
        )
        res = transformer.transform("項目A-100の値")
        self.assertTrue(res.success)
        self.assertEqual(res.text, "取得: A-100")


if __name__ == "__main__":
    unittest.main()
