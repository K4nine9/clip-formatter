"""tests/test_latex.py: LaTeX 表組み変換および数式双方向変換の単体テスト"""

import unittest

from app.transformers.latex import LatexFormulaTransformer, LatexTableTransformer


class TestLatexTableTransformer(unittest.TestCase):
    """LatexTableTransformer の単体テスト"""

    def test_tsv_booktabs(self):
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


class TestLatexFormulaTransformer(unittest.TestCase):
    """LatexFormulaTransformer の単体テスト"""

    def test_plain_to_latex_fraction_and_variables(self):
        # 1 / (2x) -> \frac{1}{2x}
        trans = LatexFormulaTransformer(
            direction=LatexFormulaTransformer.DIR_PLAIN_TO_LATEX,
            env=LatexFormulaTransformer.ENV_INLINE,
        )
        res = trans.transform("1 / (2x)")
        self.assertTrue(res.success)
        self.assertEqual(res.text, r"$\frac{1}{2x}$")

    def test_plain_to_latex_complex(self):
        # (a + b) / (c + d) * sqrt(x)
        trans = LatexFormulaTransformer(
            direction=LatexFormulaTransformer.DIR_PLAIN_TO_LATEX,
            env=LatexFormulaTransformer.ENV_NONE,
        )
        res = trans.transform("(a + b) / (c + d) * sqrt(x)")
        self.assertTrue(res.success)
        self.assertEqual(res.text, r"\frac{a + b}{c + d} \cdot \sqrt{x}")

    def test_plain_to_latex_greek_and_power(self):
        trans = LatexFormulaTransformer(
            direction=LatexFormulaTransformer.DIR_PLAIN_TO_LATEX,
            env=LatexFormulaTransformer.ENV_INLINE,
        )
        res = trans.transform("alpha^2 + beta^(n+1) +- 1")
        self.assertTrue(res.success)
        self.assertEqual(res.text, r"$\alpha^{2} + \beta^{n+1} \pm 1$")

    def test_latex_to_plain_reverse(self):
        trans = LatexFormulaTransformer(
            direction=LatexFormulaTransformer.DIR_LATEX_TO_PLAIN,
            env=LatexFormulaTransformer.ENV_NONE,
        )
        res = trans.transform(r"$\frac{1}{2x} + \sqrt{y} \cdot \alpha$")
        self.assertTrue(res.success)
        self.assertEqual(res.text, "(1) / (2x) + sqrt(y) * alpha")


if __name__ == "__main__":
    unittest.main()
