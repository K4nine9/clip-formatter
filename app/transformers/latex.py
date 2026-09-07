"""LaTeX向けの表組み変換および数式双方向変換モジュール。"""

import re
from typing import List, Optional

from app.transformers.base import BaseTransformer, TransformResult
from app.transformers.preset import NumberFormatTransformer


class LatexTableTransformer(BaseTransformer):
    """TSV、CSV、スペース区切り等の表データを LaTeX の tabular 形式へ変換する。"""

    STYLE_BOOKTABS = "booktabs"
    STYLE_STANDARD = "standard"
    STYLE_BODY_ONLY = "body_only"

    def __init__(
        self,
        delimiter: str = "\t",
        style: str = STYLE_BOOKTABS,
        alignment: str = "auto",
        has_header: bool = True,
        round_digits: Optional[int] = None,
    ):
        self.delimiter = delimiter
        self.style = style
        self.alignment = alignment
        self.has_header = has_header
        self.round_digits = round_digits
        if self.round_digits is not None:
            self._number_transformer = NumberFormatTransformer(
                dec_mode="round", dec_digits=self.round_digits
            )
        else:
            self._number_transformer = None

    def _infer_alignment(self, rows: List[List[str]]) -> str:
        """各列の型を推測してアライメント文字列 (例: 'lrr') を生成する。"""
        if not rows:
            return "c"
        num_cols = max(len(r) for r in rows)
        aligns = []

        for col_idx in range(num_cols):
            numeric_count = 0
            total_cells = 0
            # ヘッダーを除いたデータ行で判定（ヘッダーのみの場合は全体）
            start_row = 1 if (self.has_header and len(rows) > 1) else 0
            for row in rows[start_row:]:
                if col_idx < len(row):
                    val = row[col_idx].strip()
                    if val:
                        total_cells += 1
                        # 数値判定 (例: 123, -4.56, 95%)
                        cleaned = val.rstrip("%").strip()
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

    def transform(self, text: str) -> TransformResult:
        if not text or not text.strip():
            return TransformResult.unchanged(text, "入力テキストが空です")

        lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
        if not lines:
            return TransformResult.unchanged(text, "処理対象の行がありません")

        # 行・列に分割
        rows: List[List[str]] = []
        for line in lines:
            # 数値丸めの適用（有効な場合）
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

        # テーブル本体の行生成
        body_lines: List[str] = []
        for idx, row in enumerate(rows):
            row_str = " & ".join(row) + r" \\"
            body_lines.append(row_str)
            if self.has_header and idx == 0 and len(rows) > 1:
                if self.style == self.STYLE_BOOKTABS:
                    body_lines.append(r"\midrule")
                elif self.style == self.STYLE_STANDARD:
                    body_lines.append(r"\hline")

        # スタイル別出力構築
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
    """手打ち数式 ⇄ LaTeX数式の双方向変換器。"""

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
        self.direction = direction
        self.env = env

    def _plain_to_latex(self, s: str) -> str:
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
        # カッコまたは単一の識別子/数値を捉えて \frac{...}{...} に変換
        # 例: (A)/(B) -> \frac{A}{B}, 1/(2x) -> \frac{1}{2x}
        frac_pattern = re.compile(
            r"(\((?:[^()]|\([^()]*\))*\)|[A-Za-z0-9_.]+)\s*/\s*(\((?:[^()]|\([^()]*\))*\)|[A-Za-z0-9_.]+)"
        )
        # ネストした分数のために複数回適用
        for _ in range(3):
            def _replace_frac(m: re.Match) -> str:
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
        if not text or not text.strip():
            return TransformResult.unchanged(text, "入力テキストが空です")

        if self.direction == self.DIR_PLAIN_TO_LATEX:
            converted = self._plain_to_latex(text)
            return TransformResult.successful(converted, "手打ち数式 → LaTeX数式変換")
        else:
            converted = self._latex_to_plain(text)
            return TransformResult.successful(converted, "LaTeX数式 → 手打ち数式変換")
