"""定型ルール（数値丸め、ゼロ埋め、列抽出など）の変換器モジュール。"""

import re
from typing import List, Optional, Sequence, Union

from app.transformers.base import BaseTransformer, TransformResult


class RoundTransformer(BaseTransformer):
    r"""数値およびパーセンテージの小数点以下桁数を丸める変換器。

    SPEC:
        - 正規表現パターン: r"([-+]?)(\d*\.\d+)(%)?"
        - 指定した小数点以下桁数（デフォルト: 2）に丸める（例: 95.2251% -> 95.23%）。
    """

    DEFAULT_PATTERN = re.compile(r"([-+]?)(\d*\.\d+)(%)?")

    def __init__(self, digits: int = 2):
        """
        Args:
            digits: 丸める小数点以下の桁数 (>= 0)。
        """
        if digits < 0:
            raise ValueError("digits は 0 以上である必要があります。")
        self.digits = digits

    def transform(self, text: str) -> TransformResult:
        if not text:
            return TransformResult.unchanged(text, "入力テキストが空です")

        applied = False

        def _repl(match: re.Match) -> str:
            nonlocal applied
            sign = match.group(1)
            raw_val = match.group(2)
            pct = match.group(3) or ""
            try:
                num = float(sign + raw_val)
                applied = True
                formatted_num = f"{abs(num):.{self.digits}f}"
                if num < 0:
                    prefix = "-"
                elif sign == "+":
                    prefix = "+"
                else:
                    prefix = ""
                return f"{prefix}{formatted_num}{pct}"
            except ValueError:
                return match.group(0)

        new_text = self.DEFAULT_PATTERN.sub(_repl, text)

        if applied and new_text != text:
            return TransformResult.successful(
                new_text, f"小数{self.digits}桁丸め"
            )
        return TransformResult.unchanged(text, "丸め対象の数値が見つかりませんでした")


class ZeroPadTransformer(BaseTransformer):
    r"""数値の整数部（小数点以上）および小数部（小数点以下）をゼロ埋め（パディング）する変換器。

    SPEC:
        - 整数部桁数 (int_digits): 指定桁数に達するまで左側を '0' で埋める（例: 3桁なら 5 -> 005, -7 -> -007）。
        - 小数部桁数 (dec_digits): 指定桁数に達するまで右側を '0' で埋める（例: 2桁なら 3.1 -> 3.10, 5 -> 5.00）。
          指定桁数を超える小数は四捨五入により丸める。
    """

    PATTERN = re.compile(r"([-+]?)(\d+)(?:\.(\d+))?(%)?")

    def __init__(self, int_digits: int = 0, dec_digits: int = 0):
        """
        Args:
            int_digits: 整数部の固定桁数 (0 の場合はパディングなし)。
            dec_digits: 小数部の固定桁数 (0 の場合はパディングなし)。
        """
        if int_digits < 0 or dec_digits < 0:
            raise ValueError("桁数は 0 以上である必要があります。")
        if int_digits == 0 and dec_digits == 0:
            raise ValueError("整数部または小数部の少なくとも一方に 1 以上の桁数を指定してください。")

        self.int_digits = int_digits
        self.dec_digits = dec_digits

    def transform(self, text: str) -> TransformResult:
        if not text:
            return TransformResult.unchanged(text, "入力テキストが空です")

        applied = False

        def _repl(match: re.Match) -> str:
            nonlocal applied
            sign = match.group(1) or ""
            raw_int = match.group(2)
            raw_dec = match.group(3)
            pct = match.group(4) or ""

            try:
                # 1. 小数部の処理
                if self.dec_digits > 0:
                    if raw_dec is not None:
                        # 既存の小数部がある場合は四捨五入して整形
                        num = float(f"{sign}{raw_int}.{raw_dec}")
                        formatted = f"{abs(num):.{self.dec_digits}f}"
                        part_int, part_dec = formatted.split(".")
                        final_dec = f".{part_dec}"
                    else:
                        # 整数のみの場合はゼロを付与
                        part_int = raw_int
                        final_dec = f".{'0' * self.dec_digits}"
                else:
                    part_int = raw_int
                    final_dec = f".{raw_dec}" if raw_dec is not None else ""

                # 2. 整数部の処理 (zfill)
                if self.int_digits > 0:
                    part_int = part_int.zfill(self.int_digits)

                applied = True
                return f"{sign}{part_int}{final_dec}{pct}"
            except ValueError:
                return match.group(0)

        new_text = self.PATTERN.sub(_repl, text)

        parts = []
        if self.int_digits > 0:
            parts.append(f"整数{self.int_digits}桁")
        if self.dec_digits > 0:
            parts.append(f"小数{self.dec_digits}桁")
        pad_desc = "/".join(parts)

        if applied and new_text != text:
            return TransformResult.successful(
                new_text, f"ゼロ埋め({pad_desc})"
            )
        return TransformResult.unchanged(text, "ゼロ埋め対象の数値が見つかりませんでした")


class ColumnExtractTransformer(BaseTransformer):
    """区切り文字で区切られたデータから特定列を抽出する変換器。

    SPEC:
        - 区切り文字: カンマ、タブ、スペース等を指定。
        - 抽出インデックス: 1-based表記（負数で末尾からの指定に対応。例: 1, -1 で先頭列と末尾列）。
        - 複数行入力に対応し、行ごとに分割して抽出。
    """

    def __init__(
        self,
        indices: Sequence[int],
        delimiter: str = ",",
        output_delimiter: str = ", ",
    ):
        """
        Args:
            indices: 1-based の抽出列インデックス配列（例: [1, -1]）。
            delimiter: 入力の列区切り文字。
            output_delimiter: 抽出後に出力する際の列結合文字。
        """
        if not indices:
            raise ValueError("抽出インデックスが指定されていません。")
        self.indices = list(indices)
        self.delimiter = delimiter
        self.output_delimiter = output_delimiter

    @staticmethod
    def parse_indices_string(indices_str: str) -> List[int]:
        """カンマ区切りの文字列（例: '1, -1, 3'）を 1-based インデックスのリストへ変換する。"""
        results: List[int] = []
        for part in indices_str.split(","):
            part = part.strip()
            if not part:
                continue
            idx = int(part)
            if idx == 0:
                raise ValueError("インデックスは 1-based です。0 は指定できません。")
            results.append(idx)
        if not results:
            raise ValueError("有効なインデックスが指定されていません。")
        return results

    def _to_zero_based(self, index: int) -> int:
        """1-based インデックス（正または負）を 0-based インデックスに変換する。"""
        return index - 1 if index > 0 else index

    def transform(self, text: str) -> TransformResult:
        if not text:
            return TransformResult.unchanged(text, "入力テキストが空です")

        lines = text.splitlines(keepends=False)
        if not lines:
            return TransformResult.unchanged(text, "処理対象の行がありません")

        extracted_lines: List[str] = []
        extracted_count = 0
        zero_based_indices = [self._to_zero_based(i) for i in self.indices]

        for line in lines:
            # 空行はそのまま保持
            if not line.strip():
                extracted_lines.append(line)
                continue

            parts = [p.strip() for p in line.split(self.delimiter)]
            try:
                extracted_parts = [parts[i] for i in zero_based_indices]
                extracted_lines.append(self.output_delimiter.join(extracted_parts))
                extracted_count += 1
            except IndexError:
                # 列数が不足している行は元のまま保持
                extracted_lines.append(line)

        if extracted_count > 0:
            result_text = "\n".join(extracted_lines)
            return TransformResult.successful(result_text, "列抽出")
        return TransformResult.skipped(
            "抽出可能な列が存在しませんでした", original_text=text
        )


class PresetTransformer(BaseTransformer):
    """定型ルール（数値丸め、ゼロ埋め、列抽出）を複合適用するトランスフォーマー。"""

    def __init__(
        self,
        round_enabled: bool = True,
        round_digits: int = 2,
        pad_enabled: bool = False,
        pad_int_digits: int = 0,
        pad_dec_digits: int = 0,
        col_enabled: bool = False,
        col_delimiter: str = ",",
        col_indices: Optional[Union[List[int], str]] = None,
        col_output_delimiter: str = ", ",
    ):
        self.round_enabled = round_enabled
        self.round_digits = round_digits
        self.pad_enabled = pad_enabled
        self.pad_int_digits = pad_int_digits
        self.pad_dec_digits = pad_dec_digits
        self.col_enabled = col_enabled
        self.col_delimiter = col_delimiter
        self.col_output_delimiter = col_output_delimiter

        if isinstance(col_indices, str):
            self.col_indices = ColumnExtractTransformer.parse_indices_string(col_indices)
        elif col_indices is not None:
            self.col_indices = list(col_indices)
        else:
            self.col_indices = [1, -1]

    def transform(self, text: str) -> TransformResult:
        if not self.round_enabled and not self.pad_enabled and not self.col_enabled:
            return TransformResult.skipped("適用可能な定型ルールが選択されていません", original_text=text)

        current_text = text
        applied_messages: List[str] = []

        # 1. 列抽出
        if self.col_enabled:
            try:
                col_transformer = ColumnExtractTransformer(
                    indices=self.col_indices,
                    delimiter=self.col_delimiter,
                    output_delimiter=self.col_output_delimiter,
                )
                res = col_transformer.transform(current_text)
                if res.success and res.text is not None:
                    current_text = res.text
                    applied_messages.append(res.message)
            except Exception as e:
                return TransformResult.error(f"列抽出エラー: {e}", original_text=text)

        # 2. 数値丸め (ゼロ埋め小数部と重複しない場合、または先行適用)
        if self.round_enabled:
            round_transformer = RoundTransformer(digits=self.round_digits)
            res = round_transformer.transform(current_text)
            if res.success and res.text is not None:
                current_text = res.text
                applied_messages.append(res.message)

        # 3. ゼロ埋め
        if self.pad_enabled and (self.pad_int_digits > 0 or self.pad_dec_digits > 0):
            try:
                pad_transformer = ZeroPadTransformer(
                    int_digits=self.pad_int_digits, dec_digits=self.pad_dec_digits
                )
                res = pad_transformer.transform(current_text)
                if res.success and res.text is not None:
                    current_text = res.text
                    applied_messages.append(res.message)
            except Exception as e:
                return TransformResult.error(f"ゼロ埋めエラー: {e}", original_text=text)

        if applied_messages and current_text != text:
            return TransformResult.successful(
                current_text, ", ".join(applied_messages)
            )

        return TransformResult.unchanged(text, "適用可能な定型ルールによる変更はありませんでした")
