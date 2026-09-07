"""tests/test_template.py: プログラマブル変数テンプレート変換器の単体テスト"""

import unittest
from app.transformers.template import TemplateTransformer


class TestTemplateTransformer(unittest.TestCase):
    """変数テンプレート変換器のテスト"""

    def test_basic_transformation(self):
        transformer = TemplateTransformer(
            var_names=["a", "b", "c", "d", "e"],
            template="{e}, {b}, {c}, {d}, {a}",
            delimiter=",",
        )
        input_text = "1, 2, 3, 4, 5"
        result = transformer.transform(input_text)
        self.assertTrue(result.success)
        self.assertEqual(result.text, "5, 2, 3, 4, 1")
        self.assertEqual(result.message, "変数テンプレート適用完了")

    def test_multiline_transformation(self):
        transformer = TemplateTransformer(
            var_names="first, last, role",
            template="Name: {last}, {first} ({role})",
            delimiter=",",
        )
        input_text = "John, Doe, Engineer\nJane, Smith, Designer"
        result = transformer.transform(input_text)
        self.assertTrue(result.success)
        expected = "Name: Doe, John (Engineer)\nName: Smith, Jane (Designer)"
        self.assertEqual(result.text, expected)

    def test_element_count_mismatch_skips(self):
        # 3つの変数を期待するが、2行目に2つしかない場合
        transformer = TemplateTransformer(
            var_names="x, y, z",
            template="({x}, {y}, {z})",
            delimiter=",",
        )
        input_text = "1, 2, 3\n4, 5"
        result = transformer.transform(input_text)
        self.assertFalse(result.success)
        self.assertEqual(result.status, "skip")
        self.assertIn("2行目の要素数が一致しません", result.message)
        self.assertIn("期待: 3", result.message)
        self.assertIn("実際: 2", result.message)
        # 元のテキストが保持されていること
        self.assertEqual(result.text, input_text)

    def test_undefined_variable_in_template_skips(self):
        # 定義は a, b だが テンプレートに {c} が含まれる場合
        transformer = TemplateTransformer(
            var_names="a, b",
            template="{a} - {b} - {c}",
            delimiter=",",
        )
        result = transformer.transform("val1, val2")
        self.assertFalse(result.success)
        self.assertEqual(result.status, "skip")
        self.assertIn("未定義の変数がテンプレートに含まれています", result.message)
        self.assertIn("c", result.message)

    def test_tab_delimited_input(self):
        transformer = TemplateTransformer(
            var_names="colA, colB",
            template="{colB} <=> {colA}",
            delimiter="\t",
        )
        result = transformer.transform("hello\tworld")
        self.assertTrue(result.success)
        self.assertEqual(result.text, "world <=> hello")


if __name__ == "__main__":
    unittest.main()
