"""PDFコピペ等の不要な改行・行末ハイフンを結合するトランスフォーマーモジュール。"""

import re
import unicodedata
from typing import List

from app.transformers.base import BaseTransformer, TransformResult


def _is_cjk(char: str) -> bool:
    """文字が和文（漢字、ひらがな、カタカナ、全角記号等）かどうかを判定する。"""
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
    """PDFなどからコピーしたテキストの行末改行・ハイフネーションを自然な1段落に整形する。"""

    HYPHEN_BREAK_PATTERN = re.compile(r"([A-Za-z0-9]+)-\s*\r?\n\s*([A-Za-z0-9]+)")

    def transform(self, text: str) -> TransformResult:
        if not text or not text.strip():
            return TransformResult.unchanged(text, "入力テキストが空です")

        # 1. 行末のハイフン分断を結合 (例: "differ-\n ent" -> "different")
        unhyphenated = self.HYPHEN_BREAK_PATTERN.sub(r"\1\2", text)

        # 2. 段落（連続する空行）ごとに分割して処理
        normalized = unhyphenated.replace("\r\n", "\n")
        paragraphs = re.split(r"\n\s*\n", normalized)

        unwrapped_paras: List[str] = []
        for p in paragraphs:
            lines = [l.strip() for l in p.split("\n") if l.strip()]
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
