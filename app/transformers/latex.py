"""LaTeX向けの表組み変換および数式双方向変換モジュール。"""

import re
from typing import List, Optional

from app.transformers.base import BaseTransformer, TransformResult
from app.transformers.preset import NumberFormatTransformer


class LatexTableTransformer(BaseTransformer):
    """TSV、CSV、スペース区切り等の表データを LaTeX / Markdown の表形式へ変換する変換器。

    Parameters
    ----------
    delimiter : str, optional
        入力データの列区切り文字。デフォルトは '\\t'。
    style : str, optional
        表のスタイル ('booktabs', 'standard', 'body_only', 'markdown')。デフォルトは 'booktabs'。
    alignment : str, optional
        列揃え ('auto', 'l', 'c', 'r' または各列指定文字列)。デフォルトは 'auto'。
    has_header : bool, optional
        先頭行をヘッダーとして扱うかどうか。デフォルトは True。
    round_digits : Optional[int], optional
        表内の数値を自動丸めする小数桁数。None の場合は丸めを行わない。デフォルトは None。
    highlight_best : str, optional
        最良値の自動太字化 ('none', 'max', 'min')。デフォルトは 'none'。
    """

    STYLE_BOOKTABS = "booktabs"
    STYLE_STANDARD = "standard"
    STYLE_BODY_ONLY = "body_only"
    STYLE_MARKDOWN = "markdown"

    HIGHLIGHT_NONE = "none"
    HIGHLIGHT_MAX = "max"
    HIGHLIGHT_MIN = "min"

    def __init__(
        self,
        delimiter: str = "\t",
        style: str = STYLE_BOOKTABS,
        alignment: str = "auto",
        has_header: bool = True,
        round_digits: Optional[int] = None,
        highlight_best: str = HIGHLIGHT_NONE,
    ):
        """LatexTableTransformer を初期化する。"""
        self.delimiter = delimiter
        self.style = style
        self.alignment = alignment
        self.has_header = has_header
        self.round_digits = round_digits
        self.highlight_best = highlight_best
        if self.round_digits is not None:
            self._number_transformer = NumberFormatTransformer(
                dec_mode="round", dec_digits=self.round_digits
            )
        else:
            self._number_transformer = None

    def _infer_alignment(self, rows: List[List[str]]) -> str:
        """各列のデータ型を推測してアライメント文字列 (例: 'lrr') を自動生成する。

        Parameters
        ----------
        rows : list[list[str]]
            セル文字列の2次元リスト。

        Returns
        -------
        str
            列数分のアライメント指定文字列（'l' または 'r' の組み合わせ）。
        """
        if not rows:
            return "c"
        num_cols = max(len(r) for r in rows)
        aligns = []

        for col_idx in range(num_cols):
            numeric_count = 0
            total_cells = 0
            start_row = 1 if (self.has_header and len(rows) > 1) else 0
            for row in rows[start_row:]:
                if col_idx < len(row):
                    val = row[col_idx].strip()
                    if val:
                        total_cells += 1
                        # カンマやパーセントを除去して数値判定
                        cleaned = val.rstrip("%").replace(",", "").strip()
                        try:
                            float(cleaned)
                            numeric_count += 1
                        except ValueError:
                            pass

            if total_cells > 0 and (numeric_count / total_cells) >= 0.5:
                aligns.append("r")
            else:
                aligns.append("l")

        return "".join(aligns)

    def _apply_highlight_best(self, rows: List[List[str]]) -> None:
        """各列の最良値（最大値または最小値）を判定し、太字タグで装飾する。

        Parameters
        ----------
        rows : list[list[str]]
            装飾対象の2次元セルリスト（インプレースで変更されます）。

        Returns
        -------
        None
        """
        if self.highlight_best not in (self.HIGHLIGHT_MAX, self.HIGHLIGHT_MIN):
            return

        start_row = 1 if (self.has_header and len(rows) > 1) else 0
        num_cols = max(len(r) for r in rows)
        is_markdown = (self.style == self.STYLE_MARKDOWN)

        for col_idx in range(num_cols):
            col_vals = []
            for row_idx in range(start_row, len(rows)):
                if col_idx < len(rows[row_idx]):
                    raw = rows[row_idx][col_idx].strip()
                    # カンマやパーセント記号付き数値にも対応
                    cleaned = raw.rstrip("%").replace(",", "").strip()
                    try:
                        val = float(cleaned)
                        col_vals.append((val, row_idx))
                    except ValueError:
                        pass

            if not col_vals:
                continue

            # 最良値の決定
            if self.highlight_best == self.HIGHLIGHT_MAX:
                target_val = max(v for v, _ in col_vals)
            else:
                target_val = min(v for v, _ in col_vals)

            # 最良値に一致するセルを太字化
            for val, row_idx in col_vals:
                if val == target_val:
                    cell_text = rows[row_idx][col_idx]
                    if is_markdown:
                        rows[row_idx][col_idx] = f"**{cell_text}**"
                    else:
                        rows[row_idx][col_idx] = f"\\textbf{{{cell_text}}}"

    def transform(self, text: str) -> TransformResult:
        """表形式テキストを LaTeX または Markdown の表に変換する。

        Parameters
        ----------
        text : str
            TSV、CSVなどの複数行テキスト。

        Returns
        -------
        TransformResult
            変換後の表テキストを含む結果オブジェクト。
        """
        if not text or not text.strip():
            return TransformResult.unchanged(text, "入力テキストが空です")

        lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
        if not lines:
            return TransformResult.unchanged(text, "処理対象の行がありません")

        # 行・列に分割
        rows: List[List[str]] = []
        for line in lines:
            processed_line = line
            if self._number_transformer:
                num_res = self._number_transformer.transform(line)
                if num_res.success and num_res.text:
                    processed_line = num_res.text

            cells = [c.strip() for c in processed_line.split(self.delimiter)]
            rows.append(cells)

        num_cols = max(len(r) for r in rows)
        # 列数の不足セルを空文字でパディング
        for r in rows:
            if len(r) < num_cols:
                r.extend([""] * (num_cols - len(r)))

        # アライメント決定
        if self.alignment == "auto":
            col_align = self._infer_alignment(rows)
        elif self.alignment in ("l", "c", "r"):
            col_align = self.alignment * num_cols
        else:
            col_align = self.alignment

        # 最良値の太字化
        self._apply_highlight_best(rows)

        # 1. Markdown 表スタイル
        if self.style == self.STYLE_MARKDOWN:
            md_lines: List[str] = []
            # セパレータ生成
            sep_parts = []
            for a in col_align:
                if a == "r":
                    sep_parts.append("---:")
                elif a == "c":
                    sep_parts.append(":---:")
                else:
                    sep_parts.append(":---")

            if self.has_header and len(rows) > 1:
                header_row = "| " + " | ".join(rows[0]) + " |"
                md_lines.append(header_row)
                md_lines.append("| " + " | ".join(sep_parts) + " |")
                for row in rows[1:]:
                    md_lines.append("| " + " | ".join(row) + " |")
            else:
                # ヘッダーなしの場合は先頭に Col 1, Col 2 などを付与
                dummy_headers = [f"Col {i+1}" for i in range(num_cols)]
                md_lines.append("| " + " | ".join(dummy_headers) + " |")
                md_lines.append("| " + " | ".join(sep_parts) + " |")
                for row in rows:
                    md_lines.append("| " + " | ".join(row) + " |")

            return TransformResult.successful("\n".join(md_lines), "Markdown 表への変換")

        # 2. LaTeX テーブル本体の行生成
        body_lines: List[str] = []
        for idx, row in enumerate(rows):
            row_str = " & ".join(row) + r" \\"
            body_lines.append(row_str)
            if self.has_header and idx == 0 and len(rows) > 1:
                if self.style == self.STYLE_BOOKTABS:
                    body_lines.append(r"\midrule")
                elif self.style == self.STYLE_STANDARD:
                    body_lines.append(r"\hline")

        # 3. スタイル別出力構築
        if self.style == self.STYLE_BODY_ONLY:
            result_text = "\n".join(body_lines)
            return TransformResult.successful(result_text, "LaTeX 表本体への変換")

        out: List[str] = []
        out.append(f"\\begin{{tabular}}{{{col_align}}}")
        if self.style == self.STYLE_BOOKTABS:
            out.append(r"\toprule")
            out.extend(body_lines)
            out.append(r"\bottomrule")
        else:  # standard
            out.append(r"\hline")
            out.extend(body_lines)
            out.append(r"\hline")
        out.append(r"\end{tabular}")

        result_text = "\n".join(out)
        return TransformResult.successful(result_text, "LaTeX 表組への変換")


class LatexFormulaTransformer(BaseTransformer):
    """手打ち数式 ⇄ LaTeX数式の双方向変換器。

    Parameters
    ----------
    direction : str, optional
        変換方向 ('plain_to_latex' または 'latex_to_plain')。デフォルトは 'plain_to_latex'。
    env : str, optional
        LaTeX数式環境 ('inline': '$ ... $', 'display': '\\[ ... \\]', 'none': 囲みなし)。デフォルトは 'inline'。
    """

    DIR_PLAIN_TO_LATEX = "plain_to_latex"
    DIR_LATEX_TO_PLAIN = "latex_to_plain"

    ENV_INLINE = "inline"  # $ ... $
    ENV_DISPLAY = "display"  # \[ ... \]
    ENV_NONE = "none"

    GREEK_LETTERS = [
        "alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta",
        "iota", "kappa", "lambda", "mu", "nu", "xi", "pi", "rho",
        "sigma", "tau", "upsilon", "phi", "chi", "psi", "omega",
        "Gamma", "Delta", "Theta", "Lambda", "Xi", "Pi", "Sigma",
        "Upsilon", "Phi", "Psi", "Omega",
    ]

    def __init__(
        self,
        direction: str = DIR_PLAIN_TO_LATEX,
        env: str = ENV_INLINE,
    ):
        """LatexFormulaTransformer を初期化する。"""
        self.direction = direction
        self.env = env

    def _plain_to_latex(self, s: str) -> str:
        """手打ち数式文字列を LaTeX 数式記法に変換する。

        Parameters
        ----------
        s : str
            手打ち数式文字列（例: '1 / (2x)'）。

        Returns
        -------
        str
            LaTeX 数式文字列（例: '$\\frac{1}{2x}$'）。
        """
        res = s.strip()
        # 外側の既存の $ や \[ \] をトリム
        if res.startswith("$") and res.endswith("$") and len(res) >= 2:
            res = res[1:-1].strip()
        elif res.startswith(r"\[") and res.endswith(r"\]"):
            res = res[2:-2].strip()

        # 1. プラスマイナス: +- または +/-
        res = re.sub(r"\+\s*/\s*-|\+-\s*", r"\\pm ", res)

        # 2. 乗算記号: *
        res = re.sub(r"\s*\*\s*", r" \\cdot ", res)

        # 3. 平方根: sqrt(x) または sqrt[3](x)
        res = re.sub(r"\bsqrt\[(.*?)\]\((.*?)\)", r"\\sqrt[\1]{\2}", res)
        res = re.sub(r"\bsqrt\((.*?)\)", r"\\sqrt{\1}", res)

        # 4. べき乗: x^2 -> x^{2}, (a+b)^(2n) -> (a+b)^{2n}
        res = re.sub(r"\^\((.*?)\)", r"^{\1}", res)
        res = re.sub(r"\^([A-Za-z0-9]+)", r"^{\1}", res)

        # 5. 分数: a / b, 1 / (2x), (a + b) / (c + d)
        frac_pattern = re.compile(
            r"(\((?:[^()]|\([^()]*\))*\)|[A-Za-z0-9_.]+)\s*/\s*(\((?:[^()]|\([^()]*\))*\)|[A-Za-z0-9_.]+)"
        )
        # ネストした分数のために複数回適用
        for _ in range(3):
            def _replace_frac(m: re.Match) -> str:
                """正規表現マッチ結果から分子と分母を抽出し、LaTeXの \\frac{num}{den} 形式に変換する。

                Parameters
                ----------
                m : re.Match
                    スラッシュ区切りの分数マッチオブジェクト。

                Returns
                -------
                str
                    LaTeX 分数表現文字列。
                """
                num = m.group(1).strip()
                den = m.group(2).strip()
                if num.startswith("(") and num.endswith(")"):
                    num = num[1:-1].strip()
                if den.startswith("(") and den.endswith(")"):
                    den = den[1:-1].strip()
                return f"\\frac{{{num}}}{{{den}}}"

            new_res, count = frac_pattern.subn(_replace_frac, res)
            res = new_res
            if count == 0:
                break

        # 6. ギリシャ文字
        for letter in self.GREEK_LETTERS:
            res = re.sub(rf"\b{letter}\b", rf"\\{letter}", res)

        # 7. 余分な連続空白を正規化
        res = re.sub(r"\s+", " ", res).strip()

        # 8. 数式環境でラップ
        if self.env == self.ENV_INLINE:
            return f"${res}$"
        elif self.env == self.ENV_DISPLAY:
            return f"\\[\n{res}\n\\]"
        return res

    def _latex_to_plain(self, s: str) -> str:
        """LaTeX 数式文字列を手打ち数式記法に逆変換する。

        Parameters
        ----------
        s : str
            LaTeX 数式文字列（例: '\\frac{1}{2x}'）。

        Returns
        -------
        str
            手打ち数式文字列（例: '(1) / (2x)'）。
        """
        res = s.strip()
        # 外側の $, $$, \[, \] 除去
        if res.startswith("$$") and res.endswith("$$") and len(res) >= 4:
            res = res[2:-2].strip()
        elif res.startswith("$") and res.endswith("$") and len(res) >= 2:
            res = res[1:-1].strip()
        elif res.startswith(r"\[") and res.endswith(r"\]"):
            res = res[2:-2].strip()

        # 1. \frac{num}{den} -> (num) / (den)
        frac_pattern = re.compile(r"\\frac\{([^{}]+)\}\{([^{}]+)\}")
        for _ in range(3):
            new_res, count = frac_pattern.subn(r"(\1) / (\2)", res)
            res = new_res
            if count == 0:
                break

        # 2. \sqrt[n]{x} -> sqrt[n](x), \sqrt{x} -> sqrt(x)
        res = re.sub(r"\\sqrt\[(.*?)\]\{(.*?)\}", r"sqrt[\1](\2)", res)
        res = re.sub(r"\\sqrt\{(.*?)\}", r"sqrt(\1)", res)

        # 3. べき乗 ^{x} -> ^(x)
        res = re.sub(r"\^\{([^{}]+)\}", r"^(\1)", res)

        # 4. 記号
        res = re.sub(r"\\pm\b\s*", r"+/- ", res)
        res = re.sub(r"\\(?:cdot|times)\b\s*", r"* ", res)

        # 5. ギリシャ文字のバックスラッシュ除去
        for letter in self.GREEK_LETTERS:
            res = re.sub(rf"\\{letter}\b", letter, res)

        # 6. 余分な連続空白を正規化
        res = re.sub(r"\s+", " ", res).strip()
        return res

    def transform(self, text: str) -> TransformResult:
        """数式テキストの双方向変換を実行する。

        Parameters
        ----------
        text : str
            変換対象の数式テキスト。

        Returns
        -------
        TransformResult
            数式変換結果オブジェクト。
        """
        if not text or not text.strip():
            return TransformResult.unchanged(text, "入力テキストが空です")

        if self.direction == self.DIR_PLAIN_TO_LATEX:
            converted = self._plain_to_latex(text)
            return TransformResult.successful(converted, "手打ち数式 → LaTeX数式変換")
        else:
            converted = self._latex_to_plain(text)
            return TransformResult.successful(converted, "LaTeX数式 → 手打ち数式変換")
