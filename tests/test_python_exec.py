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
        code = "result = f'{int(a) + int(b)}'"
        scope = {"a": "10", "b": "25"}
        ok, res, err = execute_user_script(code, scope)
        self.assertTrue(ok)
        self.assertEqual(res, "35")
        self.assertIsNone(err)

    def test_math_module(self):
        code = "result = f'{math.sqrt(float(x)):.2f}'"
        scope = {"x": "16"}
        ok, res, err = execute_user_script(code, scope)
        self.assertTrue(ok)
        self.assertEqual(res, "4.00")

    def test_missing_result_variable(self):
        code = "x = 1 + 2"
        ok, res, err = execute_user_script(code, {})
        self.assertFalse(ok)
        self.assertIsNone(res)
        self.assertIn("result", err)

    def test_syntax_error(self):
        code = "result = 1 +"
        ok, res, err = execute_user_script(code, {})
        self.assertFalse(ok)
        self.assertIn("構文エラー", err)

    def test_zero_division_error(self):
        code = "result = 10 / 0"
        ok, res, err = execute_user_script(code, {})
        self.assertFalse(ok)
        self.assertIn("ZeroDivisionError", err)

    def test_undefined_variable_error(self):
        code = "result = undefined_foo + 1"
        ok, res, err = execute_user_script(code, {})
        self.assertFalse(ok)
        self.assertIn("NameError", err)


class TestPythonScriptTransformer(unittest.TestCase):
    """PythonScriptTransformer の各入力モードに対するテスト。"""

    def test_pattern_mode_simple(self):
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
        transformer = PythonScriptTransformer(
            input_mode="pattern",
            pattern_input="リンゴが{a}個",
            script_code="result = f'{a}個'",
        )
        res = transformer.transform("ミカンが5個")
        self.assertFalse(res.success)
        self.assertIn("見つかりませんでした", res.message)

    def test_delimiter_mode_multiline(self):
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
        transformer = PythonScriptTransformer(
            input_mode="full_text",
            script_code="result = 'abc'",
        )
        res = transformer.transform("")
        self.assertFalse(res.success)
        self.assertEqual(res.message, "入力テキストが空です")

    def test_script_runtime_error_handled(self):
        transformer = PythonScriptTransformer(
            input_mode="full_text",
            script_code="result = 1 / 0",
        )
        res = transformer.transform("some text")
        self.assertFalse(res.success)
        self.assertIn("ZeroDivisionError", res.message)


if __name__ == "__main__":
    unittest.main()
