"""PDFコピペ等の不要な改行・行末ハイフンを結合するトランスフォーマーモジュール。"""

import re
import unicodedata
from typing import List

from app.transformers.base import BaseTransformer, TransformResult


def _is_cjk(char: str) -> bool:
    """指定された1文字が和文（漢字、ひらがな、カタカナ、全角記号等）かどうかを判定する。

    Parameters
    ----------
    char : str
        判定対象の1文字。

    Returns
    -------
    bool
        和文または全角記号である場合は True、英数字や半角記号の場合は False。
    """
    if not char:
        return False
    name = unicodedata.name(char, "")
    if any(k in name for k in ("CJK", "HIRAGANA", "KATAKANA", "IDEOGRAPHIC")):
        return True
    code = ord(char)
    return (
        0x3000 <= code <= 0x303F
        or 0x3040 <= code <= 0x309F
        or 0x30A0 <= code <= 0x30FF
        or 0x4E00 <= code <= 0x9FFF
        or 0xFF00 <= code <= 0xFFEF
    )


class TextUnwrapTransformer(BaseTransformer):
    """PDFなどからコピーしたテキストの行末改行・ハイフネーションを自然な1段落に整形する変換器。"""

    # 行末ハイフネーションの検出パターン (例: "differ-\n ent" -> "different")
    HYPHEN_BREAK_PATTERN = re.compile(r"([A-Za-z0-9]+)-\s*\r?\n\s*([A-Za-z0-9]+)")

    def transform(self, text: str) -> TransformResult:
        """入力テキストの改行およびハイフネーションを解除・結合する。

        Parameters
        ----------
        text : str
            変換対象のテキスト（PDF等からコピーされた複数行テキスト）。

        Returns
        -------
        TransformResult
            改行やハイフンが結合された結果オブジェクト。

        Notes
        -----
        - 連続する空行による段落の区切りは保持されます。
        - 英文同士の改行は半角スペースで結合されますが、和文同士の改行は余分なスペースを入れずに直接結合されます。
        """
        if not text or not text.strip():
            return TransformResult.unchanged(text, "入力テキストが空です")

        # 1. 行末のハイフン分断を結合 (例: "differ-\n ent" -> "different")
        unhyphenated = self.HYPHEN_BREAK_PATTERN.sub(r"\1\2", text)

        # 2. 段落（連続する空行）ごとに分割して処理
        normalized = unhyphenated.replace("\r\n", "\n")
        paragraphs = re.split(r"\n\s*\n", normalized)

        unwrapped_paras: List[str] = []
        for p in paragraphs:
            lines = [line.strip() for line in p.split("\n") if line.strip()]
            if not lines:
                continue

            joined = lines[0]
            for next_line in lines[1:]:
                last_char = joined[-1] if joined else ""
                first_char = next_line[0] if next_line else ""

                # 和文同士の結合ならスペース不要、それ以外は半角スペースを挿入
                if _is_cjk(last_char) and _is_cjk(first_char):
                    joined += next_line
                else:
                    joined += " " + next_line

            # 連続する複数の空白を1つの半角スペースに正規化
            joined = re.sub(r"[ \t]+", " ", joined)
            unwrapped_paras.append(joined.strip())

        result_text = "\n\n".join(unwrapped_paras)

        if result_text != text:
            return TransformResult.successful(result_text, "改行・ハイフン除去 (Unwrap)")
        return TransformResult.unchanged(text, "変更の必要な改行・ハイフンはありませんでした")
