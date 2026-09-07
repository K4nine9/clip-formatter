"""tests/test_latex.py: LaTeX 表組み変換および数式双方向変換の単体テスト"""

import unittest

from app.transformers.latex import LatexFormulaTransformer, LatexTableTransformer


class TestLatexTableTransformer(unittest.TestCase):
    """LatexTableTransformer の単体テスト"""

    def test_tsv_booktabs(self):
        """TSVからBooktabs形式のLaTeX表組への変換を検証する。

        Returns
        -------
        None
        """
        tsv_text = (
            "Model\tAccuracy\tLoss\n"
            "Baseline\t0.852\t0.128\n"
            "Ours\t0.941\t0.034"
        )
        transformer = LatexTableTransformer(
            delimiter="\t",
            style=LatexTableTransformer.STYLE_BOOKTABS,
            has_header=True,
        )
        res = transformer.transform(tsv_text)
        self.assertTrue(res.success)
        expected = (
            "\\begin{tabular}{lrr}\n"
            "\\toprule\n"
            "Model & Accuracy & Loss \\\\\n"
            "\\midrule\n"
            "Baseline & 0.852 & 0.128 \\\\\n"
            "Ours & 0.941 & 0.034 \\\\\n"
            "\\bottomrule\n"
            "\\end{tabular}"
        )
        self.assertEqual(res.text, expected)

    def test_csv_body_only_with_rounding(self):
        """CSVからテーブル本体のみ（行データのみ）かつ小数丸め付きの変換を検証する。

        Returns
        -------
        None
        """
        csv_text = "Item, 3.14159, 2.71828\nVal, 1.41421, 1.73205"
        transformer = LatexTableTransformer(
            delimiter=",",
            style=LatexTableTransformer.STYLE_BODY_ONLY,
            has_header=False,
            round_digits=2,
        )
        res = transformer.transform(csv_text)
        self.assertTrue(res.success)
        expected = (
            "Item & 3.14 & 2.72 \\\\\n"
            "Val & 1.41 & 1.73 \\\\"
        )
        self.assertEqual(res.text, expected)

    def test_markdown_table_conversion(self):
        """TSVからMarkdownテーブル形式への変換を検証する。

        Returns
        -------
        None
        """
        tsv_text = (
            "Model\tAccuracy\tLoss\n"
            "Baseline\t0.852\t0.128\n"
            "Ours\t0.941\t0.034"
        )
        transformer = LatexTableTransformer(
            delimiter="\t",
            style=LatexTableTransformer.STYLE_MARKDOWN,
            has_header=True,
        )
        res = transformer.transform(tsv_text)
        self.assertTrue(res.success)
        expected = (
            "| Model | Accuracy | Loss |\n"
            "| :--- | ---: | ---: |\n"
            "| Baseline | 0.852 | 0.128 |\n"
            "| Ours | 0.941 | 0.034 |"
        )
        self.assertEqual(res.text, expected)

    def test_latex_table_highlight_max(self):
        """LaTeX表において各列の最良値（最大値）が太字強調されることを検証する。

        Returns
        -------
        None
        """
        tsv_text = (
            "Model\tScoreA\tScoreB\n"
            "Baseline\t0.85\t0.90\n"
            "Ours\t0.94\t0.88"
        )
        transformer = LatexTableTransformer(
            delimiter="\t",
            style=LatexTableTransformer.STYLE_BOOKTABS,
            has_header=True,
            highlight_best=LatexTableTransformer.HIGHLIGHT_MAX,
        )
        res = transformer.transform(tsv_text)
        self.assertTrue(res.success)
        self.assertIn(r"Baseline & 0.85 & \textbf{0.90} \\", res.text)
        self.assertIn(r"Ours & \textbf{0.94} & 0.88 \\", res.text)

    def test_markdown_table_highlight_max(self):
        """Markdownテーブルにおいて各列の最良値（最大値）が太字強調されることを検証する。

        Returns
        -------
        None
        """
        tsv_text = (
            "Model\tScoreA\tScoreB\n"
            "Baseline\t0.85\t0.90\n"
            "Ours\t0.94\t0.88"
        )
        transformer = LatexTableTransformer(
            delimiter="\t",
            style=LatexTableTransformer.STYLE_MARKDOWN,
            has_header=True,
            highlight_best=LatexTableTransformer.HIGHLIGHT_MAX,
        )
        res = transformer.transform(tsv_text)
        self.assertTrue(res.success)
        self.assertIn("| Baseline | 0.85 | **0.90** |", res.text)
        self.assertIn("| Ours | **0.94** | 0.88 |", res.text)

    def test_highlight_best_with_commas(self):
        """カンマ付き数値を含む列の最良値判定と太字強調を検証する。

        Returns
        -------
        None
        """
        tsv_text = (
            "Model\tParameters\tCost\n"
            "ModelA\t1,200.5\t$500\n"
            "ModelB\t850.0\t$750"
        )
        transformer = LatexTableTransformer(
            delimiter="\t",
            style=LatexTableTransformer.STYLE_MARKDOWN,
            has_header=True,
            highlight_best=LatexTableTransformer.HIGHLIGHT_MAX,
        )
        res = transformer.transform(tsv_text)
        self.assertTrue(res.success)
        self.assertIn("**1,200.5**", res.text)


class TestLatexFormulaTransformer(unittest.TestCase):
    """LatexFormulaTransformer の単体テスト"""

    def test_plain_to_latex_fraction_and_variables(self):
        """プレーンテキスト数式の分数表記がLaTeX形式に変換されることを検証する。

        Returns
        -------
        None
        """
        # 1 / (2x) -> \frac{1}{2x}
        trans = LatexFormulaTransformer(
            direction=LatexFormulaTransformer.DIR_PLAIN_TO_LATEX,
            env=LatexFormulaTransformer.ENV_INLINE,
        )
        res = trans.transform("1 / (2x)")
        self.assertTrue(res.success)
        self.assertEqual(res.text, r"$\frac{1}{2x}$")

    def test_plain_to_latex_complex(self):
        """複雑な算術演算・平方根・括弧のLaTeX変換を検証する。

        Returns
        -------
        None
        """
        # (a + b) / (c + d) * sqrt(x)
        trans = LatexFormulaTransformer(
            direction=LatexFormulaTransformer.DIR_PLAIN_TO_LATEX,
            env=LatexFormulaTransformer.ENV_NONE,
        )
        res = trans.transform("(a + b) / (c + d) * sqrt(x)")
        self.assertTrue(res.success)
        self.assertEqual(res.text, r"\frac{a + b}{c + d} \cdot \sqrt{x}")

    def test_plain_to_latex_greek_and_power(self):
        """ギリシャ文字および累乗記号のLaTeX変換を検証する。

        Returns
        -------
        None
        """
        trans = LatexFormulaTransformer(
            direction=LatexFormulaTransformer.DIR_PLAIN_TO_LATEX,
            env=LatexFormulaTransformer.ENV_INLINE,
        )
        res = trans.transform("alpha^2 + beta^(n+1) +- 1")
        self.assertTrue(res.success)
        self.assertEqual(res.text, r"$\alpha^{2} + \beta^{n+1} \pm 1$")

    def test_latex_to_plain_reverse(self):
        """LaTeX数式からプレーンテキスト数式への逆変換を検証する。

        Returns
        -------
        None
        """
        trans = LatexFormulaTransformer(
            direction=LatexFormulaTransformer.DIR_LATEX_TO_PLAIN,
            env=LatexFormulaTransformer.ENV_NONE,
        )
        res = trans.transform(r"$\frac{1}{2x} + \sqrt{y} \cdot \alpha$")
        self.assertTrue(res.success)
        self.assertEqual(res.text, "(1) / (2x) + sqrt(y) * alpha")


if __name__ == "__main__":
    unittest.main()
