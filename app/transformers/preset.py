"""定型ルール（数値フォーマット、列抽出など）の変換器モジュール。"""

import re
from typing import List, Optional, Sequence, Union

from app.transformers.base import BaseTransformer, TransformResult


class NumberFormatTransformer(BaseTransformer):
    r"""整数部（小数点以上）と小数部（小数点以下）を個別に設定してフォーマットする数値変換器。

    SPEC:
        - 整数部モード (int_mode):
            - 'none': 整数部を変更しない。
            - 'pad': 指定桁数 (int_digits) まで左側を '0' でパディング。
        - 小数部モード (dec_mode):
            - 'none': 小数部を変更しない。
            - 'round': 小数丸め（可変長。元が整数なら小数点は付けず、指定桁数未満なら '0' を補完しない）。
            - 'pad': ゼロ埋め（固定長。元が整数でも小数点とゼロを付与し、不足桁は '0' で補完）。
        - 小数超過時処理 (dec_overflow):
            - 'round': 四捨五入
            - 'truncate': 切り捨て
    """

    PATTERN = re.compile(r"([-+]?)(\d+)(?:\.(\d+))?(%)?")

    MODE_NONE = "none"
    MODE_ROUND = "round"
    MODE_TRUNCATE = "truncate"  # 後方互換用
    MODE_PAD = "pad"

    OVERFLOW_ROUND = "round"
    OVERFLOW_TRUNCATE = "truncate"

    def __init__(
        self,
        int_mode: str = "none",
        int_digits: int = 3,
        dec_mode: str = "none",
        dec_digits: int = 2,
        dec_overflow: str = "round",
    ):
        self.int_mode = int_mode
        self.int_digits = max(0, int_digits)

        # 後方互換性: dec_mode="truncate" の場合
        if dec_mode == "truncate":
            self.dec_mode = self.MODE_ROUND
            self.dec_overflow = self.OVERFLOW_TRUNCATE
        else:
            self.dec_mode = dec_mode
            self.dec_overflow = (
                self.OVERFLOW_TRUNCATE
                if dec_overflow == self.OVERFLOW_TRUNCATE
                else self.OVERFLOW_ROUND
            )

        self.dec_digits = max(0, dec_digits)

        if self.int_mode not in (self.MODE_NONE, self.MODE_PAD):
            raise ValueError(f"無効な int_mode です: {int_mode}")
        if self.dec_mode not in (self.MODE_NONE, self.MODE_ROUND, self.MODE_PAD):
            raise ValueError(f"無効な dec_mode です: {dec_mode}")

    def is_active(self) -> bool:
        """何らかの変換が有効になっているかどうかを判定する。"""
        int_active = (self.int_mode == self.MODE_PAD and self.int_digits > 0)
        dec_active = (self.dec_mode != self.MODE_NONE)
        return int_active or dec_active

    def transform(self, text: str) -> TransformResult:
        if not text:
            return TransformResult.unchanged(text, "入力テキストが空です")

        if not self.is_active():
            return TransformResult.skipped("有効な数値フォーマットルールが指定されていません", original_text=text)

        applied = False

        def _repl(match: re.Match) -> str:
            nonlocal applied
            sign = match.group(1) or ""
            raw_int = match.group(2)
            raw_dec = match.group(3)
            pct = match.group(4) or ""

            try:
                base_int = raw_int
                final_dec = ""

                # --- 1. 小数部の処理 ---
                if self.dec_mode == self.MODE_NONE:
                    final_dec = f".{raw_dec}" if raw_dec is not None else ""

                elif self.dec_mode == self.MODE_ROUND:
                    # 可変長（元が整数なら小数点は付与しない。不足桁の0補完もしない）
                    if raw_dec is None:
                        final_dec = ""
                    else:
                        if len(raw_dec) <= self.dec_digits:
                            final_dec = f".{raw_dec}"
                        else:
                            # 超過処理
                            if self.dec_overflow == self.OVERFLOW_TRUNCATE:
                                if self.dec_digits == 0:
                                    final_dec = ""
                                else:
                                    final_dec = f".{raw_dec[:self.dec_digits]}"
                            else:  # 四捨五入
                                num = float(f"{raw_int}.{raw_dec}")
                                if self.dec_digits == 0:
                                    base_int = f"{round(num):.0f}"
                                    final_dec = ""
                                else:
                                    formatted = f"{num:.{self.dec_digits}f}"
                                    base_int, dec_part = formatted.split(".")
                                    final_dec = f".{dec_part}"

                elif self.dec_mode == self.MODE_PAD:
                    # 固定長（常に指定桁数に固定。元が整数でも .00 を付与。不足は 0 補完）
                    if self.dec_digits == 0:
                        if raw_dec is not None and self.dec_overflow == self.OVERFLOW_ROUND:
                            num = float(f"{raw_int}.{raw_dec}")
                            base_int = f"{round(num):.0f}"
                        final_dec = ""
                    else:
                        if raw_dec is None:
                            final_dec = f".{'0' * self.dec_digits}"
                        elif len(raw_dec) < self.dec_digits:
                            # 不足分を0埋め
                            final_dec = f".{raw_dec.ljust(self.dec_digits, '0')}"
                        elif len(raw_dec) == self.dec_digits:
                            final_dec = f".{raw_dec}"
                        else:
                            # 超過処理
                            if self.dec_overflow == self.OVERFLOW_TRUNCATE:
                                final_dec = f".{raw_dec[:self.dec_digits]}"
                            else:  # 四捨五入
                                num = float(f"{raw_int}.{raw_dec}")
                                formatted = f"{num:.{self.dec_digits}f}"
                                base_int, dec_part = formatted.split(".")
                                final_dec = f".{dec_part}"

                # --- 2. 整数部の処理 ---
                if self.int_mode == self.MODE_PAD and self.int_digits > 0:
                    final_int = base_int.zfill(self.int_digits)
                else:
                    final_int = base_int

                res = f"{sign}{final_int}{final_dec}{pct}"
                if res != match.group(0):
                    applied = True
                return res
            except Exception:
                return match.group(0)

        new_text = self.PATTERN.sub(_repl, text)

        # 適用ルールの概要文
        descs = []
        if self.int_mode == self.MODE_PAD and self.int_digits > 0:
            descs.append(f"整数{self.int_digits}桁パディング")

        overflow_text = "四捨五入" if self.dec_overflow == self.OVERFLOW_ROUND else "切り捨て"
        if self.dec_mode == self.MODE_ROUND:
            descs.append(f"小数{self.dec_digits}桁丸め({overflow_text})")
        elif self.dec_mode == self.MODE_PAD:
            descs.append(f"小数{self.dec_digits}桁ゼロ埋め({overflow_text})")

        desc_str = ", ".join(descs) if descs else "数値フォーマット"
        if applied and new_text != text:
            return TransformResult.successful(new_text, desc_str)
        return TransformResult.unchanged(text, "数値フォーマットによる変更はありませんでした")


class RoundTransformer(BaseTransformer):
    """(後方互換用) 数値・パーセントの小数点丸め変換器。"""

    def __init__(self, digits: int = 2):
        self._inner = NumberFormatTransformer(
            int_mode="none",
            dec_mode="round",
            dec_digits=digits,
        )
        self.digits = digits

    def transform(self, text: str) -> TransformResult:
        res = self._inner.transform(text)
        if res.success:
            return TransformResult.successful(res.text, f"小数{self.digits}桁丸め")
        return res


class ZeroPadTransformer(BaseTransformer):
    """(後方互換用) 数値ゼロ埋め変換器。"""

    def __init__(self, int_digits: int = 0, dec_digits: int = 0):
        if int_digits == 0 and dec_digits == 0:
            raise ValueError("整数部または小数部の少なくとも一方に 1 以上の桁数を指定してください。")
        self.int_digits = int_digits
        self.dec_digits = dec_digits
        self._inner = NumberFormatTransformer(
            int_mode="pad" if int_digits > 0 else "none",
            int_digits=int_digits,
            dec_mode="pad" if dec_digits > 0 else "none",
            dec_digits=dec_digits,
        )

    def transform(self, text: str) -> TransformResult:
        res = self._inner.transform(text)
        if res.success:
            parts = []
            if self.int_digits > 0:
                parts.append(f"整数{self.int_digits}桁")
            if self.dec_digits > 0:
                parts.append(f"小数{self.dec_digits}桁")
            return TransformResult.successful(res.text, f"ゼロ埋め({'/'.join(parts)})")
        return res


class ColumnExtractTransformer(BaseTransformer):
    """区切り文字で区切られたデータから特定列を抽出する変換器。"""

    def __init__(
        self,
        indices: Sequence[int],
        delimiter: str = ",",
        output_delimiter: str = ", ",
    ):
        if not indices:
            raise ValueError("抽出インデックスが指定されていません。")
        self.indices = list(indices)
        self.delimiter = delimiter
        self.output_delimiter = output_delimiter

    @staticmethod
    def parse_indices_string(indices_str: str) -> List[int]:
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
            if not line.strip():
                extracted_lines.append(line)
                continue

            parts = [p.strip() for p in line.split(self.delimiter)]
            try:
                extracted_parts = [parts[i] for i in zero_based_indices]
                extracted_lines.append(self.output_delimiter.join(extracted_parts))
                extracted_count += 1
            except IndexError:
                extracted_lines.append(line)

        if extracted_count > 0:
            result_text = "\n".join(extracted_lines)
            return TransformResult.successful(result_text, "列抽出")
        return TransformResult.skipped(
            "抽出可能な列が存在しませんでした", original_text=text
        )


class PresetTransformer(BaseTransformer):
    """定型ルール（数値フォーマット、列抽出）を複合適用するトランスフォーマー。"""

    def __init__(
        self,
        # 整数部・小数部 分離設定
        int_mode: str = "none",
        int_digits: int = 3,
        dec_mode: str = "none",
        dec_digits: int = 2,
        dec_overflow: str = "round",
        # 列抽出設定
        col_enabled: bool = False,
        col_delimiter: str = ",",
        col_indices: Optional[Union[List[int], str]] = None,
        col_output_delimiter: str = ", ",
        # 改行・ハイフン除去
        unwrap_enabled: bool = False,
        # 後方互換用引数
        round_enabled: Optional[bool] = None,
        round_digits: Optional[int] = None,
        pad_enabled: Optional[bool] = None,
        pad_int_digits: Optional[int] = None,
        pad_dec_digits: Optional[int] = None,
    ):
        # 後方互換マッピング
        if pad_enabled is not None and pad_enabled:
            int_mode = "pad" if (pad_int_digits or 0) > 0 else "none"
            int_digits = pad_int_digits or 3
            dec_mode = "pad" if (pad_dec_digits or 0) > 0 else "none"
            dec_digits = pad_dec_digits or 2
        elif round_enabled is not None:
            if round_enabled:
                dec_mode = "round"
                dec_digits = round_digits if round_digits is not None else 2
            elif pad_enabled is False and round_enabled is False:
                int_mode = "none"
                dec_mode = "none"

        self.number_transformer = NumberFormatTransformer(
            int_mode=int_mode,
            int_digits=int_digits,
            dec_mode=dec_mode,
            dec_digits=dec_digits,
            dec_overflow=dec_overflow,
        )

        self.col_enabled = col_enabled
        self.col_delimiter = col_delimiter
        self.col_output_delimiter = col_output_delimiter
        self.unwrap_enabled = unwrap_enabled

        if isinstance(col_indices, str):
            self.col_indices = ColumnExtractTransformer.parse_indices_string(col_indices)
        elif col_indices is not None:
            self.col_indices = list(col_indices)
        else:
            self.col_indices = [1, -1]

    def transform(self, text: str) -> TransformResult:
        if (
            not self.number_transformer.is_active()
            and not self.col_enabled
            and not self.unwrap_enabled
        ):
            return TransformResult.skipped("適用可能な定型ルールが選択されていません", original_text=text)

        current_text = text
        applied_messages: List[str] = []

        # 1. 改行・ハイフン除去 (Unwrap)
        if self.unwrap_enabled:
            from app.transformers.unwrap import TextUnwrapTransformer
            unwrap_trans = TextUnwrapTransformer()
            res = unwrap_trans.transform(current_text)
            if res.success and res.text is not None:
                current_text = res.text
                applied_messages.append(res.message)

        # 2. 列抽出
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

        # 3. 数値フォーマット (整数部・小数部)
        if self.number_transformer.is_active():
            res = self.number_transformer.transform(current_text)
            if res.success and res.text is not None:
                current_text = res.text
                applied_messages.append(res.message)

        if applied_messages and current_text != text:
            return TransformResult.successful(
                current_text, ", ".join(applied_messages)
            )

        return TransformResult.unchanged(text, "適用可能な定型ルールによる変更はありませんでした")
