"""定型ルール（数値フォーマット、列抽出など）の変換器モジュール。"""

import re
from typing import List, Optional, Sequence, Union

from app.transformers.base import BaseTransformer, TransformResult


class NumberFormatTransformer(BaseTransformer):
    r"""整数部（小数点以上）と小数部（小数点以下）を個別に設定してフォーマットする数値変換器。

    Parameters
    ----------
    int_mode : str, optional
        整数部の処理モード。'none'（変更しない）または 'pad'（ゼロ埋め）。デフォルトは 'none'。
    int_digits : int, optional
        整数部ゼロ埋め時の最小桁数。デフォルトは 3。
    dec_mode : str, optional
        小数部の処理モード。'none'（変更しない）、'round'（小数丸め・可変長）、'pad'（ゼロ埋め・固定長）。デフォルトは 'none'。
    dec_digits : int, optional
        小数部の桁数。デフォルトは 2。
    dec_overflow : str, optional
        小数部が指定桁数を超過した際の処理。'round'（四捨五入）または 'truncate'（切り捨て）。デフォルトは 'round'。

    Notes
    -----
    - パーセント記号（`%`）付き数値や負符号（`-`）付き数値にも対応しています。
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
        """NumberFormatTransformer を初期化する。

        Parameters
        ----------
        int_mode : str, optional
            整数部モード ('none' または 'pad')。デフォルトは 'none'。
        int_digits : int, optional
            整数部桁数。デフォルトは 3。
        dec_mode : str, optional
            小数部モード ('none', 'round', 'pad')。デフォルトは 'none'。
        dec_digits : int, optional
            小数部桁数。デフォルトは 2。
        dec_overflow : str, optional
            超過時処理 ('round' または 'truncate')。デフォルトは 'round'。
        """
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
        """何らかのフォーマット変換が有効になっているかどうかを判定する。

        Returns
        -------
        bool
            整数部または小数部が有効な変換設定になっている場合は True。
        """
        int_active = (self.int_mode == self.MODE_PAD and self.int_digits > 0)
        dec_active = (self.dec_mode != self.MODE_NONE)
        return int_active or dec_active

    def transform(self, text: str) -> TransformResult:
        """テキスト内の数値を検知し、整数部・小数部の設定に従って変換する。

        Parameters
        ----------
        text : str
            変換対象のテキスト。

        Returns
        -------
        TransformResult
            数値がフォーマットされた結果オブジェクト。
        """
        if not text:
            return TransformResult.unchanged(text, "入力テキストが空です")

        if not self.is_active():
            return TransformResult.skipped("有効な数値フォーマットルールが指定されていません", original_text=text)

        applied = False

        def _repl(match: re.Match) -> str:
            """正規表現に一致した各数値に対して、整数部・小数部の設定に応じたフォーマットを適用する。

            Parameters
            ----------
            match : re.Match
                数値・符号・パーセント記号を含む正規表現マッチオブジェクト。

            Returns
            -------
            str
                フォーマット適用後の数値文字列。
            """
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
                            if self.dec_overflow == self.OVERFLOW_TRUNCATE:
                                truncated = raw_dec[:self.dec_digits]
                                final_dec = f".{truncated}" if self.dec_digits > 0 else ""
                            else:
                                # 四捨五入
                                full_float_str = f"{raw_int}.{raw_dec}"
                                rounded = round(float(full_float_str), self.dec_digits)
                                if self.dec_digits == 0:
                                    base_int = str(int(rounded))
                                    final_dec = ""
                                else:
                                    r_parts = f"{rounded:.{self.dec_digits}f}".split(".")
                                    base_int = r_parts[0]
                                    final_dec = f".{r_parts[1]}"

                elif self.dec_mode == self.MODE_PAD:
                    # 固定長（元が整数でも小数点とゼロを付与し、不足桁は0で補完）
                    if raw_dec is None:
                        final_dec = f".{'0' * self.dec_digits}" if self.dec_digits > 0 else ""
                    else:
                        if len(raw_dec) < self.dec_digits:
                            final_dec = f".{raw_dec.ljust(self.dec_digits, '0')}"
                        elif len(raw_dec) == self.dec_digits:
                            final_dec = f".{raw_dec}"
                        else:
                            if self.dec_overflow == self.OVERFLOW_TRUNCATE:
                                final_dec = f".{raw_dec[:self.dec_digits]}" if self.dec_digits > 0 else ""
                            else:
                                # 四捨五入
                                full_float_str = f"{raw_int}.{raw_dec}"
                                rounded = round(float(full_float_str), self.dec_digits)
                                if self.dec_digits == 0:
                                    base_int = str(int(rounded))
                                    final_dec = ""
                                else:
                                    r_parts = f"{rounded:.{self.dec_digits}f}".split(".")
                                    base_int = r_parts[0]
                                    final_dec = f".{r_parts[1]}"

                # --- 2. 整数部の処理 ---
                if self.int_mode == self.MODE_PAD and self.int_digits > 0:
                    final_int = base_int.zfill(self.int_digits)
                else:
                    final_int = base_int

                formatted = f"{sign}{final_int}{final_dec}{pct}"
                if formatted != match.group(0):
                    applied = True
                return formatted
            except Exception:
                return match.group(0)

        new_text = self.PATTERN.sub(_repl, text)

        descs = []
        if self.int_mode == self.MODE_PAD and self.int_digits > 0:
            descs.append(f"整数{self.int_digits}桁ゼロ埋め")
        if self.dec_mode == self.MODE_ROUND:
            over_text = "切り捨て" if self.dec_overflow == self.OVERFLOW_TRUNCATE else "四捨五入"
            descs.append(f"小数{self.dec_digits}桁丸め({over_text})")
        elif self.dec_mode == self.MODE_PAD:
            over_text = "切り捨て" if self.dec_overflow == self.OVERFLOW_TRUNCATE else "四捨五入"
            descs.append(f"小数{self.dec_digits}桁ゼロ埋め({over_text})")

        desc_str = ", ".join(descs) if descs else "数値フォーマット"
        if applied and new_text != text:
            return TransformResult.successful(new_text, desc_str)
        return TransformResult.unchanged(text, "数値フォーマットによる変更はありませんでした")


class RoundTransformer(BaseTransformer):
    """(後方互換用) 数値・パーセントの小数点丸め変換器。

    Parameters
    ----------
    digits : int, optional
        丸め対象の小数桁数。デフォルトは 2。
    """

    def __init__(self, digits: int = 2):
        """RoundTransformer を初期化する。

        Parameters
        ----------
        digits : int, optional
            小数桁数。デフォルトは 2。
        """
        self._inner = NumberFormatTransformer(
            int_mode="none",
            dec_mode="round",
            dec_digits=digits,
        )
        self.digits = digits

    def transform(self, text: str) -> TransformResult:
        """テキスト内の数値を指定桁数で丸める。

        Parameters
        ----------
        text : str
            入力テキスト。

        Returns
        -------
        TransformResult
            変換結果オブジェクト。
        """
        res = self._inner.transform(text)
        if res.success:
            return TransformResult.successful(res.text, f"小数{self.digits}桁丸め")
        return res


class ZeroPadTransformer(BaseTransformer):
    """(後方互換用) 数値ゼロ埋め変換器。

    Parameters
    ----------
    int_digits : int, optional
        整数部のゼロ埋め桁数。デフォルトは 0。
    dec_digits : int, optional
        小数部のゼロ埋め桁数。デフォルトは 0。
    """

    def __init__(self, int_digits: int = 0, dec_digits: int = 0):
        """ZeroPadTransformer を初期化する。

        Parameters
        ----------
        int_digits : int, optional
            整数部桁数。デフォルトは 0。
        dec_digits : int, optional
            小数部桁数。デフォルトは 0。
        """
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
        """テキスト内の数値をゼロ埋めする。

        Parameters
        ----------
        text : str
            入力テキスト。

        Returns
        -------
        TransformResult
            変換結果オブジェクト。
        """
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
    """区切り文字で区切られたデータから特定列を抽出する変換器。

    Parameters
    ----------
    indices : Sequence[int]
        抽出対象の列インデックス（1-based、負数は末尾から）。
    delimiter : str, optional
        入力データの列区切り文字。デフォルトは ','。
    output_delimiter : str, optional
        出力時の列区切り文字。デフォルトは ', '。
    """

    def __init__(
        self,
        indices: Sequence[int],
        delimiter: str = ",",
        output_delimiter: str = ", ",
    ):
        """ColumnExtractTransformer を初期化する。

        Parameters
        ----------
        indices : Sequence[int]
            1-basedの列インデックス列。
        delimiter : str, optional
            入力区切り文字。デフォルトは ','。
        output_delimiter : str, optional
            出力区切り文字。デフォルトは ', '。
        """
        if not indices:
            raise ValueError("抽出インデックスが指定されていません。")
        self.indices = list(indices)
        self.delimiter = delimiter
        self.output_delimiter = output_delimiter

    @staticmethod
    def parse_indices_string(indices_str: str) -> List[int]:
        """カンマ区切りのインデックス文字列をパースして整数のリストを返す。

        Parameters
        ----------
        indices_str : str
            1-based表記のカンマ区切り文字列（例: '1, -1'）。

        Returns
        -------
        list[int]
            整数のリスト。

        Raises
        ------
        ValueError
            0 が含まれる場合やパースできない場合。
        """
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
        """1-based のインデックスを 0-based のインデックスに変換する。

        Parameters
        ----------
        index : int
            1-based インデックス。

        Returns
        -------
        int
            0-based インデックス。
        """
        return index - 1 if index > 0 else index

    def transform(self, text: str) -> TransformResult:
        """入力テキストを行ごとに分割し、指定列を抽出して結合する。

        Parameters
        ----------
        text : str
            入力テキスト。

        Returns
        -------
        TransformResult
            列抽出結果オブジェクト。
        """
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
    """定型ルール（数値フォーマット、列抽出、改行除去）を複合適用するトランスフォーマー。

    Parameters
    ----------
    int_mode : str, optional
        整数部モード ('none' または 'pad')。デフォルトは 'none'。
    int_digits : int, optional
        整数部桁数。デフォルトは 3。
    dec_mode : str, optional
        小数部モード ('none', 'round', 'pad')。デフォルトは 'none'。
    dec_digits : int, optional
        小数部桁数。デフォルトは 2。
    dec_overflow : str, optional
        小数超過時処理 ('round' または 'truncate')。デフォルトは 'round'。
    col_enabled : bool, optional
        列抽出を有効にするかどうか。デフォルトは False。
    col_delimiter : str, optional
        列区切り文字。デフォルトは ','。
    col_indices : Optional[Union[List[int], str]], optional
        抽出列インデックス。デフォルトは None (1, -1)。
    col_output_delimiter : str, optional
        抽出後の列区切り文字。デフォルトは ', '。
    unwrap_enabled : bool, optional
        PDF改行・ハイフン除去を有効にするかどうか。デフォルトは False。
    round_enabled : Optional[bool], optional
        後方互換用フラグ。
    round_digits : Optional[int], optional
        後方互換用桁数。
    pad_enabled : Optional[bool], optional
        後方互換用フラグ。
    pad_int_digits : Optional[int], optional
        後方互換用整数桁数。
    pad_dec_digits : Optional[int], optional
        後方互換用小数桁数。
    """

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
        """PresetTransformer を初期化する。"""
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
        """有効化されている定型ルール（改行除去・列抽出・数値整形）を順次適用する。

        Parameters
        ----------
        text : str
            入力テキスト。

        Returns
        -------
        TransformResult
            複合適用後の結果オブジェクト。
        """
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
