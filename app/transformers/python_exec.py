"""Pythonスクリプト実行による完全プログラマブル変換器モジュール。

安全なサンドボックス環境下でユーザー定義のPythonスクリプトを実行し、
変数の型チェック、出力バリデーション、例外安全を担保してテキストを加工・整形します。
"""

from dataclasses import dataclass
import datetime
import json
import logging
import math
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import unicodedata

from app.transformers.base import BaseTransformer, TransformResult
from app.transformers.pattern import tokenize_pattern

logger = logging.getLogger(__name__)

# スクリプト実行時に提供する安全な組み込み関数群（ファイル操作や外部プロセス実行等の危険関数を除外）
SAFE_BUILTINS: Dict[str, Any] = {
    "abs": abs,
    "all": all,
    "any": any,
    "bin": bin,
    "bool": bool,
    "chr": chr,
    "dict": dict,
    "divmod": divmod,
    "enumerate": enumerate,
    "filter": filter,
    "float": float,
    "format": format,
    "frozenset": frozenset,
    "hasattr": hasattr,
    "hex": hex,
    "int": int,
    "isinstance": isinstance,
    "issubclass": issubclass,
    "iter": iter,
    "len": len,
    "list": list,
    "map": map,
    "max": max,
    "min": min,
    "next": next,
    "oct": oct,
    "ord": ord,
    "pow": pow,
    "print": lambda *args, **kwargs: None,  # 標準出力への出力を抑止
    "range": range,
    "repr": repr,
    "reversed": reversed,
    "round": round,
    "set": set,
    "slice": slice,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "zip": zip,
}

# ユーザーが自由に利用できる便利モジュール
SAFE_MODULES: Dict[str, Any] = {
    "math": math,
    "re": re,
    "datetime": datetime,
    "json": json,
    "unicodedata": unicodedata,
}


def sanitize_result(val: Any) -> str:
    """出力変数 result の型をチェックし、安全に文字列化する。

    - str: そのまま
    - int, float, bool: str() で変換
    - list, tuple, set: 各要素を文字列化して改行結合
    - dict: JSON形式（インデント付き）または str() で変換
    - その他オブジェクト: str() で安全に変換
    """
    if val is None:
        return ""
    if isinstance(val, str):
        return val
    if isinstance(val, (int, float, bool)):
        return str(val)
    if isinstance(val, (list, tuple, set)):
        return "\n".join(str(item) for item in val)
    if isinstance(val, dict):
        try:
            return json.dumps(val, ensure_ascii=False, indent=2)
        except Exception:
            return str(val)
    return str(val)


def execute_user_script(script: str, scope: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[str]]:
    """ユーザーが入力したPythonスクリプトを実行し、result変数の値を検証・抽出する。

    Args:
        script: 実行するPythonコード。
        scope: スクリプトに渡す変数辞書。

    Returns:
        (success, result_str, error_message)
    """
    if not script or not script.strip():
        return False, None, "スクリプトが入力されていません"

    # 実行スコープの作成
    exec_scope: Dict[str, Any] = {
        "__builtins__": SAFE_BUILTINS,
        **SAFE_MODULES,
        **scope,
    }

    try:
        # スクリプトをコンパイル（構文エラーやインデントエラーの検出）
        compiled = compile(script, "<clip_formatter_script>", "exec")
        exec(compiled, exec_scope)
    except SyntaxError as e:
        line_info = f" (行 {e.lineno})" if e.lineno is not None else ""
        return False, None, f"構文エラー{line_info}: {e.msg}"
    except BaseException as e:
        # ゼロ除算、型エラー、未定義参照などを安全に捕捉
        err_type = type(e).__name__
        return False, None, f"実行時エラー ({err_type}): {e}"

    if "result" not in exec_scope:
        return False, None, "出力結果が 'result' 変数に代入されていません (例: result = f'...')"

    raw_result = exec_scope["result"]
    result_str = sanitize_result(raw_result)
    return True, result_str, None


class PythonScriptTransformer(BaseTransformer):
    """入力定義（パターンマッチ / 区切り文字 / テキスト全文）とPythonスクリプトを連携させた変換器。"""

    MODE_PATTERN = "pattern"
    MODE_DELIMITER = "delimiter"
    MODE_FULL_TEXT = "full_text"

    def __init__(
        self,
        input_mode: str = MODE_PATTERN,
        script_code: str = "",
        # パターンマッチ用
        pattern_input: str = "",
        # 区切り文字用
        delimiter: str = ",",
        var_names: Union[Sequence[str], str] = "",
    ):
        self.input_mode = input_mode
        self.script_code = script_code

        # パターンマッチ用
        self.pattern_input = pattern_input
        self.pattern_tokens = tokenize_pattern(pattern_input) if pattern_input else []
        self.var_id_mapping: Dict[int, str] = {}
        self.defined_pattern_vars = set()
        self.pattern_regex: Optional[re.Pattern] = None

        if self.input_mode == self.MODE_PATTERN and self.pattern_tokens:
            regex_parts: List[str] = []
            for idx, tok in enumerate(self.pattern_tokens):
                if not tok.is_var:
                    regex_parts.append(re.escape(tok.content))
                else:
                    self.var_id_mapping[idx] = tok.content
                    self.defined_pattern_vars.add(tok.content)
                    group_name = f"g_{idx}"
                    is_last = idx == (len(self.pattern_tokens) - 1)
                    capture_regex = "(.+)" if is_last else "(.+?)"
                    regex_parts.append(f"(?P<{group_name}>{capture_regex})")
            if regex_parts:
                self.pattern_regex = re.compile("".join(regex_parts), re.DOTALL)

        # 区切り文字用
        self.delimiter = delimiter
        if isinstance(var_names, str):
            if delimiter != "," and delimiter in var_names:
                self.var_names = [v.strip() for v in var_names.split(delimiter) if v.strip()]
            elif "," in var_names:
                self.var_names = [v.strip() for v in var_names.split(",") if v.strip()]
            else:
                self.var_names = [v.strip() for v in var_names.split(delimiter) if v.strip()]
        else:
            self.var_names = [v.strip() for v in var_names if v.strip()]

    def transform(self, text: str) -> TransformResult:
        if not text:
            return TransformResult.unchanged(text, "入力テキストが空です")

        if not self.script_code or not self.script_code.strip():
            return TransformResult.skipped("Pythonスクリプトが入力されていません", original_text=text)

        if self.input_mode == self.MODE_PATTERN:
            return self._transform_pattern(text)
        elif self.input_mode == self.MODE_DELIMITER:
            return self._transform_delimiter(text)
        else:
            return self._transform_full_text(text)

    def _transform_pattern(self, text: str) -> TransformResult:
        if not self.pattern_input:
            return TransformResult.skipped("入力パターンが指定されていません", original_text=text)

        if self.pattern_regex is None:
            return TransformResult.skipped("正規表現パターンの生成に失敗しました", original_text=text)

        matches = list(self.pattern_regex.finditer(text))
        if not matches:
            return TransformResult.skipped("パターンに一致する箇所が見つかりませんでした", original_text=text)

        first_error: Optional[str] = None

        def _replace_match(m: re.Match) -> str:
            nonlocal first_error
            if first_error is not None:
                return m.group(0)

            # キャプチャ変数の展開
            var_dict: Dict[str, str] = {}
            for idx, var_name in self.var_id_mapping.items():
                var_dict[var_name] = m.group(f"g_{idx}")

            # スコープの構築
            scope: Dict[str, Any] = {
                "text": text,
                "match_text": m.group(0),
                "vars": var_dict,
                **var_dict,
            }

            success, out_str, err = execute_user_script(self.script_code, scope)
            if not success:
                first_error = err
                return m.group(0)
            return out_str if out_str is not None else ""

        new_text = self.pattern_regex.sub(_replace_match, text)

        if first_error is not None:
            return TransformResult.skipped(first_error, original_text=text)

        if new_text != text:
            return TransformResult.successful(
                new_text, f"スクリプト実行・置換完了 ({len(matches)}箇所)"
            )
        return TransformResult.unchanged(text, "置換前後のテキストに変化はありませんでした")

    def _transform_delimiter(self, text: str) -> TransformResult:
        if not self.var_names:
            return TransformResult.skipped("入力変数が定義されていません", original_text=text)

        lines = text.splitlines(keepends=False)
        result_lines: List[str] = []
        expected_len = len(self.var_names)

        for line_num, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped:
                result_lines.append("")
                continue

            parts = [p.strip() for p in line.split(self.delimiter)]
            if len(parts) != expected_len:
                return TransformResult.skipped(
                    f"{line_num}行目の要素数が一致しません (期待: {expected_len}, 実際: {len(parts)})",
                    original_text=text,
                )

            var_map = dict(zip(self.var_names, parts))
            scope: Dict[str, Any] = {
                "line": line,
                "line_num": line_num,
                "parts": parts,
                "vars": var_map,
                **var_map,
            }

            success, out_str, err = execute_user_script(self.script_code, scope)
            if not success:
                return TransformResult.skipped(
                    f"{line_num}行目のスクリプト実行失敗: {err}",
                    original_text=text,
                )
            result_lines.append(out_str if out_str is not None else "")

        transformed_text = "\n".join(result_lines)
        return TransformResult.successful(transformed_text, "スクリプトによる区切り行変換完了")

    def _transform_full_text(self, text: str) -> TransformResult:
        lines = text.splitlines(keepends=False)
        scope: Dict[str, Any] = {
            "text": text,
            "lines": lines,
            "line_count": len(lines),
        }

        success, out_str, err = execute_user_script(self.script_code, scope)
        if not success:
            return TransformResult.skipped(f"スクリプト実行失敗: {err}", original_text=text)

        transformed_text = out_str if out_str is not None else ""
        if transformed_text != text:
            return TransformResult.successful(transformed_text, "スクリプトによる全文変換完了")
        return TransformResult.unchanged(text, "スクリプトの出力と入力テキストに変化はありませんでした")
