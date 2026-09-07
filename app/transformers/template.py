"""プログラマブル変数テンプレート変換器モジュール。"""

import string
from typing import List, Sequence, Union

from app.transformers.base import BaseTransformer, TransformResult


class TemplateTransformer(BaseTransformer):
    """入力文字列を指定区切り文字でパースし、定義された変数にバインドしてテンプレートへ展開する変換器。

    Parameters
    ----------
    var_names : Union[Sequence[str], str]
        変数名のシーケンス、またはカンマ区切りの変数名文字列。
    template : str
        '{変数名}' を含む出力フォーマット文字列。
    delimiter : str, optional
        入力データの列区切り文字。デフォルトは ','。
    """

    def __init__(
        self,
        var_names: Union[Sequence[str], str],
        template: str,
        delimiter: str = ",",
    ):
        """TemplateTransformer を初期化する。

        Parameters
        ----------
        var_names : Union[Sequence[str], str]
            変数名のリストまたはカンマ/区切り文字で区切られた文字列。
        template : str
            展開対象のテンプレート文字列。
        delimiter : str, optional
            区切り文字。デフォルトは ','。
        """
        if isinstance(var_names, str):
            self.var_names = self.parse_var_names(var_names, delimiter)
        else:
            self.var_names = [v.strip() for v in var_names if v.strip()]

        self.template = template
        self.delimiter = delimiter

        # テンプレート内の参照変数を事前に抽出・検証
        self._referenced_vars = self._extract_template_variables(self.template)

    @staticmethod
    def parse_var_names(raw_str: str, delimiter: str = ",") -> List[str]:
        """区切り文字で区切られた文字列から変数名リストを抽出する。

        Parameters
        ----------
        raw_str : str
            変数名が並んだ未加工の文字列（例: 'a, b, c' または 'col1\tcol2'）。
        delimiter : str, optional
            区切り文字。デフォルトは ','。

        Returns
        -------
        list[str]
            空白がトリムされた変数名のリスト。
        """
        if delimiter != "," and delimiter in raw_str:
            parts = [p.strip() for p in raw_str.split(delimiter) if p.strip()]
        elif "," in raw_str:
            parts = [p.strip() for p in raw_str.split(",") if p.strip()]
        else:
            parts = [p.strip() for p in raw_str.split(delimiter) if p.strip()]
        return parts

    @staticmethod
    def _extract_template_variables(template_str: str) -> List[str]:
        """string.Formatter を使用してテンプレート内で参照されているフィールド名を抽出する。

        Parameters
        ----------
        template_str : str
            解析対象のフォーマット文字列。

        Returns
        -------
        list[str]
            テンプレート内で参照されている基底変数名のリスト。
        """
        formatter = string.Formatter()
        referenced = []
        try:
            for _, field_name, _, _ in formatter.parse(template_str):
                if field_name is not None and field_name:
                    # 'var.attr' や 'var[0]' などの場合は基底の変数名を取得
                    var_root = field_name.split(".")[0].split("[")[0]
                    referenced.append(var_root)
        except ValueError:
            pass
        return referenced

    def transform(self, text: str) -> TransformResult:
        """入力テキストを行ごとに分割し、各行を変数にマッピングしてテンプレートへ展開する。

        Parameters
        ----------
        text : str
            区切り文字で記述された複数行テキスト。

        Returns
        -------
        TransformResult
            テンプレート展開後の結果オブジェクト。要素数不一致や未定義変数の場合はスキップ。

        Notes
        -----
        - 空行はそのまま保持されます。
        - 1行でも要素数が定義変数数と一致しない場合、誤変換を防ぐため全体がスキップされます。
        """
        if not text or not text.strip():
            return TransformResult.unchanged(text, "入力テキストが空です")

        if not self.var_names:
            return TransformResult.skipped("入力変数が定義されていません", original_text=text)

        if not self.template:
            return TransformResult.skipped("出力テンプレートが指定されていません", original_text=text)

        # テンプレート内の変数が定義変数に含まれているか検証
        var_set = set(self.var_names)
        undefined_vars = [v for v in self._referenced_vars if v not in var_set]
        if undefined_vars:
            return TransformResult.skipped(
                f"未定義の変数がテンプレートに含まれています: {', '.join(undefined_vars)}",
                original_text=text,
            )

        lines = text.splitlines(keepends=False)
        result_lines: List[str] = []
        expected_len = len(self.var_names)

        for line_num, line in enumerate(lines, start=1):
            stripped_line = line.strip()
            # 空行はそのまま保持
            if not stripped_line:
                result_lines.append("")
                continue

            parts = [p.strip() for p in line.split(self.delimiter)]
            actual_len = len(parts)

            if actual_len != expected_len:
                return TransformResult.skipped(
                    f"{line_num}行目の要素数が一致しません (期待: {expected_len}, 実際: {actual_len})",
                    original_text=text,
                )

            var_map = dict(zip(self.var_names, parts))
            try:
                formatted_line = self.template.format_map(var_map)
                result_lines.append(formatted_line)
            except KeyError as e:
                return TransformResult.skipped(
                    f"未定義の変数があります: {e}", original_text=text
                )

        transformed_text = "\n".join(result_lines)
        return TransformResult.successful(
            transformed_text, "変数テンプレート適用完了"
        )
