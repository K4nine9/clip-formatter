"""文脈抽出・パターンマッチングによるテキスト置換・並び替え変換器モジュール。"""

from dataclasses import dataclass
import re
from typing import Dict, List, Optional

from app.transformers.base import BaseTransformer, TransformResult


@dataclass(frozen=True)
class PatternToken:
    """パターンの構文要素（リテラル文字列または変数）。

    Parameters
    ----------
    is_var : bool
        変数トークンであるかどうか（True の場合は変数名、False の場合はリテラル文字列）。
    content : str
        トークンの内容（変数名またはリテラル文字列）。
    """

    is_var: bool
    content: str


def tokenize_pattern(pattern_str: str) -> List[PatternToken]:
    """パターン文字列を解析し、リテラルと変数のトークン列に分解する。

    Parameters
    ----------
    pattern_str : str
        解析対象のパターン文字列（例: '私は{a}時間で{b}つのりんご'）。

    Returns
    -------
    list[PatternToken]
        解析されたトークン列のリスト。

    Notes
    -----
    以下のエスケープシーケンスをサポートしています:
    - `\\{` -> リテラル `{`
    - `\\}` -> リテラル `}`
    - `\\\\` -> リテラル `\\`
    - `{{` -> リテラル `{`
    - `}}` -> リテラル `}`
    - `{変数名}` -> 変数トークン
    """
    tokens: List[PatternToken] = []
    i = 0
    n = len(pattern_str)
    literal_buf: List[str] = []

    def flush_literal():
        """バッファに蓄積されたリテラル文字列をトークンとして確定し、バッファをクリアする。

        Returns
        -------
        None
        """
        if literal_buf:
            tokens.append(PatternToken(is_var=False, content="".join(literal_buf)))
            literal_buf.clear()

    while i < n:
        ch = pattern_str[i]

        # 1. バックスラッシュエスケープ (\ {, \ }, \ \)
        if ch == "\\" and i + 1 < n:
            next_ch = pattern_str[i + 1]
            if next_ch in ("{", "}", "\\"):
                literal_buf.append(next_ch)
                i += 2
                continue
            else:
                literal_buf.append("\\")
                i += 1
                continue

        # 2. 二重波括弧エスケープ ({{, }})
        if ch == "{" and i + 1 < n and pattern_str[i + 1] == "{":
            literal_buf.append("{")
            i += 2
            continue

        if ch == "}" and i + 1 < n and pattern_str[i + 1] == "}":
            literal_buf.append("}")
            i += 2
            continue

        # 3. 変数宣言 ({変数名})
        if ch == "{":
            close_idx = pattern_str.find("}", i + 1)
            if close_idx != -1:
                var_name = pattern_str[i + 1 : close_idx].strip()
                if var_name:
                    flush_literal()
                    tokens.append(PatternToken(is_var=True, content=var_name))
                    i = close_idx + 1
                    continue

        # 4. 通常文字
        literal_buf.append(ch)
        i += 1

    flush_literal()
    return tokens


class PatternTransformer(BaseTransformer):
    """入力パターンにマッチする箇所を変数キャプチャし、出力テンプレートに従って並び替え・置換する変換器。

    Parameters
    ----------
    input_pattern : str
        入力マッチングパターン（変数 `{var}` およびエスケープ対応）。
    output_template : str
        出力テンプレート（変数 `{var}` およびエスケープ対応）。
    """

    def __init__(self, input_pattern: str, output_template: str):
        """PatternTransformer を初期化する。

        Parameters
        ----------
        input_pattern : str
            入力マッチングパターン。
        output_template : str
            出力テンプレート。
        """
        self.raw_input_pattern = input_pattern
        self.raw_output_template = output_template

        self.input_tokens = tokenize_pattern(input_pattern)
        self.output_tokens = tokenize_pattern(output_template)

        # 入力パターンで定義された変数一覧とそのマッピング
        self.var_id_mapping: Dict[int, str] = {}
        self.defined_vars = set()

        # 入力パターンから正規表現を構築
        regex_parts: List[str] = []
        for idx, tok in enumerate(self.input_tokens):
            if not tok.is_var:
                regex_parts.append(re.escape(tok.content))
            else:
                self.var_id_mapping[idx] = tok.content
                self.defined_vars.add(tok.content)
                group_name = f"g_{idx}"
                # 末尾の変数の場合は末尾までマッチ、それ以外は非貪欲マッチ
                is_last = idx == (len(self.input_tokens) - 1)
                capture_regex = "(.+)" if is_last else "(.+?)"
                regex_parts.append(f"(?P<{group_name}>{capture_regex})")

        self.pattern_regex: Optional[re.Pattern] = None
        if regex_parts:
            # DOTALL を指定して複数行にまたがる一致も許容
            regex_str = "".join(regex_parts)
            self.pattern_regex = re.compile(regex_str, re.DOTALL)

        # 出力テンプレート内の未定義変数を検証
        self.output_vars = {tok.content for tok in self.output_tokens if tok.is_var}
        self.undefined_vars = self.output_vars - self.defined_vars

    def transform(self, text: str) -> TransformResult:
        """入力テキストに対してパターンマッチ置換を実行する。

        Parameters
        ----------
        text : str
            置換対象のテキスト。

        Returns
        -------
        TransformResult
            置換結果オブジェクト。マッチしない場合や未定義変数がある場合はスキップ。
        """
        if not text:
            return TransformResult.unchanged(text, "入力テキストが空です")

        if not self.raw_input_pattern:
            return TransformResult.skipped("入力パターンが指定されていません", original_text=text)

        if self.pattern_regex is None:
            return TransformResult.skipped("正規表現の生成に失敗しました", original_text=text)

        if self.undefined_vars:
            undefined_str = ", ".join(sorted(self.undefined_vars))
            return TransformResult.skipped(
                f"未定義の変数がテンプレートに含まれています: '{undefined_str}'",
                original_text=text,
            )

        matches = list(self.pattern_regex.finditer(text))
        if not matches:
            return TransformResult.skipped(
                "パターンに一致する箇所が見つかりませんでした", original_text=text
            )

        def _replace_match(m: re.Match) -> str:
            """正規表現のマッチオブジェクトから変数を抽出し、出力トークン列に代入して置換後文字列を生成する。

            Parameters
            ----------
            m : re.Match
                パターン一致箇所を表すマッチオブジェクト。

            Returns
            -------
            str
                変数が展開された置換後文字列。
            """
            # キャプチャされた変数の辞書を作成
            var_dict: Dict[str, str] = {}
            for idx, var_name in self.var_id_mapping.items():
                group_name = f"g_{idx}"
                var_dict[var_name] = m.group(group_name)

            # 出力トークン列を展開
            out_parts: List[str] = []
            for tok in self.output_tokens:
                if not tok.is_var:
                    out_parts.append(tok.content)
                else:
                    out_parts.append(var_dict.get(tok.content, ""))
            return "".join(out_parts)

        new_text = self.pattern_regex.sub(_replace_match, text)

        if new_text != text:
            return TransformResult.successful(
                new_text, f"パターンマッチ変換完了 ({len(matches)}箇所)"
            )

        return TransformResult.unchanged(text, "置換前後のテキストに変化はありませんでした")
