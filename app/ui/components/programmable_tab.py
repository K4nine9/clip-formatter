"""プログラマブルモードのタブUIコンポーネント。"""

from typing import Optional, Union
import customtkinter as ctk

from app.config import AppConfig
from app.transformers.base import BaseTransformer
from app.transformers.pattern import PatternTransformer
from app.transformers.python_exec import PythonScriptTransformer
from app.transformers.template import TemplateTransformer
from app.ui.components.delimiter_selector import DelimiterSelector


class ProgrammableTabFrame(ctk.CTkFrame):
    """プログラマブル（文脈パターンマッチ / 区切り文字展開 / Pythonスクリプト）を設定するタブフレーム。"""

    MODE_PATTERN = "パターンマッチ形式"
    MODE_DELIMITER = "区切り文字形式"
    MODE_SCRIPT = "Pythonスクリプト形式"

    SCRIPT_IN_PATTERN = "パターンマッチ"
    SCRIPT_IN_DELIMITER = "区切り文字"
    SCRIPT_IN_FULL_TEXT = "テキスト全文"

    # クイックサンプルコード定義
    SAMPLE_SCRIPTS = {
        "四則演算・金額計算": (
            "# 変数 price, qty が使用可能\n"
            "total = int(price) * int(qty)\n"
            "tax = int(total * 0.1)\n"
            "result = f'小計: {total:,}円 (税込: {total + tax:,}円)'"
        ),
        "条件分岐 (if/else)": (
            "# 変数 score が使用可能\n"
            "s = float(score)\n"
            "if s >= 80:\n"
            "    rank = '優 (Pass)'\n"
            "elif s >= 60:\n"
            "    rank = '良 (Pass)'\n"
            "else:\n"
            "    rank = '不可 (Fail)'\n"
            "result = f'得点: {s:.1f} ➔ 判定: {rank}'"
        ),
        "テキスト全文集計 (合計・平均)": (
            "# 変数 lines (行リスト), text (全文) が使用可能\n"
            "nums = [float(line.strip()) for line in lines if line.strip()]\n"
            "if nums:\n"
            "    total = sum(nums)\n"
            "    avg = total / len(nums)\n"
            "    result = f'件数: {len(nums)}\n合計: {total:.2f}\n平均: {avg:.2f}'\n"
            "else:\n"
            "    result = '数値が見つかりませんでした'"
        ),
        "行番号・プレフィックス付与": (
            "# 変数 lines が使用可能\n"
            "out_lines = [f'{i+1:03d}: {line}' for i, line in enumerate(lines)]\n"
            "result = '\\n'.join(out_lines)"
        ),
    }

    def __init__(self, master, config: AppConfig, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.config = config
        self._build_ui()
        self.load_from_config(config)

    def _build_ui(self) -> None:
        # モード選択セグメントボタン
        self.mode_var = ctk.StringVar(value=self.MODE_PATTERN)
        self.mode_selector = ctk.CTkSegmentedButton(
            self,
            values=[self.MODE_PATTERN, self.MODE_DELIMITER, self.MODE_SCRIPT],
            variable=self.mode_var,
            command=self._on_mode_switched,
        )
        self.mode_selector.pack(fill="x", padx=12, pady=(10, 6))

        # --- 1. パターンマッチ形式用コンテナ ---
        self.pattern_container = ctk.CTkFrame(self, fg_color="transparent")

        desc_pattern = (
            "文章中の特定箇所を変数 {var} でキャプチャして置換・並び替えます。\n"
            "例: 入力「私は{a}時間で{b}つのりんご」 出力「私は{b}時間で{a}つのりんご」\n"
            "※「{」や「}」を文字として含める場合は「\\{」または「{{」と記述します。"
        )
        ctk.CTkLabel(
            self.pattern_container,
            text=desc_pattern,
            justify="left",
            text_color=("gray50", "gray70"),
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w", padx=12, pady=(4, 8))

        ctk.CTkLabel(
            self.pattern_container,
            text="入力パターン (変数: {変数名}, エスケープ: \\{ または {{):",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(anchor="w", padx=12, pady=(6, 2))
        self.pattern_input_entry = ctk.CTkEntry(self.pattern_container)
        self.pattern_input_entry.pack(fill="x", padx=12, pady=(0, 8))

        ctk.CTkLabel(
            self.pattern_container,
            text="出力テンプレート ({変数名} で展開):",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(anchor="w", padx=12, pady=(6, 2))
        self.pattern_output_entry = ctk.CTkEntry(self.pattern_container)
        self.pattern_output_entry.pack(fill="x", padx=12, pady=(0, 8))

        # --- 2. 区切り文字形式用コンテナ ---
        self.delim_container = ctk.CTkFrame(self, fg_color="transparent")

        desc_delim = (
            "区切り文字で分割されたデータを変数名にマッピングして展開します。\n"
            "例: 入力「a, b, c, d, e」 出力「{e}, {b}, {c}, {d}, {a}」\n"
            "入力データがルールに合わない場合は自動でスキップされます。"
        )
        ctk.CTkLabel(
            self.delim_container,
            text=desc_delim,
            justify="left",
            text_color=("gray50", "gray70"),
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w", padx=12, pady=(4, 8))

        sep_frame = ctk.CTkFrame(self.delim_container, fg_color="transparent")
        sep_frame.pack(fill="x", padx=12, pady=4)
        ctk.CTkLabel(sep_frame, text="区切り文字:").pack(side="left", padx=(0, 8))
        self.delim_selector = DelimiterSelector(sep_frame, default_delimiter=",")
        self.delim_selector.pack(side="left")

        ctk.CTkLabel(
            self.delim_container,
            text="入力フォーマット（変数名定義）:",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(anchor="w", padx=12, pady=(6, 2))
        self.delim_input_entry = ctk.CTkEntry(self.delim_container)
        self.delim_input_entry.pack(fill="x", padx=12, pady=(0, 8))

        ctk.CTkLabel(
            self.delim_container,
            text="出力テンプレート（{変数名}で指定）:",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(anchor="w", padx=12, pady=(6, 2))
        self.delim_output_entry = ctk.CTkEntry(self.delim_container)
        self.delim_output_entry.pack(fill="x", padx=12, pady=(0, 8))

        # --- 3. Pythonスクリプト形式用コンテナ ---
        self.script_container = ctk.CTkFrame(self, fg_color="transparent")

        # 簡単な使い方・説明枠
        desc_box = ctk.CTkFrame(self.script_container, corner_radius=6)
        desc_box.pack(fill="x", padx=12, pady=(2, 8))
        desc_script = (
            "【Pythonスクリプトモードの使い方】\n"
            "・入力形式で定義した変数（a, b, ...）や、text（全文）、lines（行リスト）が利用できます。\n"
            "・出力結果を必ず「result = ...」変数に代入してください（f-string も自由に使用可能）。\n"
            "・利用可能モジュール: math, re, datetime, json, unicodedata (構文エラー時も安全に保護)"
        )
        ctk.CTkLabel(
            desc_box,
            text=desc_script,
            justify="left",
            text_color=("gray60", "gray80"),
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=10, pady=6)

        # 入力形式セレクタ
        in_mode_frame = ctk.CTkFrame(self.script_container, fg_color="transparent")
        in_mode_frame.pack(fill="x", padx=12, pady=(2, 4))
        ctk.CTkLabel(
            in_mode_frame,
            text="入力形式:",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(side="left", padx=(0, 8))

        self.script_in_mode_var = ctk.StringVar(value=self.SCRIPT_IN_PATTERN)
        self.script_in_mode_selector = ctk.CTkSegmentedButton(
            in_mode_frame,
            values=[self.SCRIPT_IN_PATTERN, self.SCRIPT_IN_DELIMITER, self.SCRIPT_IN_FULL_TEXT],
            variable=self.script_in_mode_var,
            command=self._on_script_in_mode_switched,
        )
        self.script_in_mode_selector.pack(side="left", fill="x", expand=True)

        # 入力定義エリア（動的切替）
        self.script_pattern_box = ctk.CTkFrame(self.script_container, fg_color="transparent")
        ctk.CTkLabel(
            self.script_pattern_box,
            text="入力パターン (変数: {変数名}):",
            font=ctk.CTkFont(size=11, weight="bold"),
        ).pack(anchor="w", padx=12, pady=(4, 2))
        self.script_pattern_entry = ctk.CTkEntry(self.script_pattern_box)
        self.script_pattern_entry.pack(fill="x", padx=12, pady=(0, 4))

        self.script_delim_box = ctk.CTkFrame(self.script_container, fg_color="transparent")
        s_delim_sub = ctk.CTkFrame(self.script_delim_box, fg_color="transparent")
        s_delim_sub.pack(fill="x", padx=12, pady=(4, 2))
        ctk.CTkLabel(s_delim_sub, text="区切り:").pack(side="left", padx=(0, 6))
        self.script_delim_selector = DelimiterSelector(s_delim_sub, default_delimiter=",")
        self.script_delim_selector.pack(side="left", padx=(0, 12))
        ctk.CTkLabel(s_delim_sub, text="変数定義:").pack(side="left", padx=(0, 6))
        self.script_delim_vars_entry = ctk.CTkEntry(s_delim_sub)
        self.script_delim_vars_entry.pack(side="left", fill="x", expand=True)

        self.script_full_box = ctk.CTkFrame(self.script_container, fg_color="transparent")
        ctk.CTkLabel(
            self.script_full_box,
            text="※パターン定義は不要です。スクリプト内で変数 text (全文文字列) や lines (各行リスト) を参照できます。",
            text_color=("gray50", "gray70"),
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=12, pady=4)

        # スクリプト入力欄のヘッダー（ラベル ＋ サンプル挿入ドロップダウン）
        code_header = ctk.CTkFrame(self.script_container, fg_color="transparent")
        code_header.pack(fill="x", padx=12, pady=(6, 2))
        ctk.CTkLabel(
            code_header,
            text="Python スクリプト (出力は result = ... に代入):",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(side="left")

        self.sample_menu = ctk.CTkOptionMenu(
            code_header,
            values=["サンプルコード挿入..."] + list(self.SAMPLE_SCRIPTS.keys()),
            command=self._on_sample_selected,
            width=160,
            font=ctk.CTkFont(size=11),
        )
        self.sample_menu.pack(side="right")

        # 複数行コードエディタ
        self.script_textbox = ctk.CTkTextbox(
            self.script_container,
            height=150,
            font=ctk.CTkFont(family="Consolas", size=12),
            wrap="none",
        )
        self.script_textbox.pack(fill="both", expand=True, padx=12, pady=(2, 8))

        # 初期表示の更新
        self._update_container_visibility()
        self._update_script_input_box_visibility()

    def _on_mode_switched(self, selected_mode: str) -> None:
        """モード切り替え時のUI表示更新。"""
        self._update_container_visibility()

    def _on_script_in_mode_switched(self, selected_in_mode: str) -> None:
        """スクリプト入力形式切り替え時のUI表示更新。"""
        self._update_script_input_box_visibility()

    def _on_sample_selected(self, choice: str) -> None:
        """サンプルコードが選択された時の自動入力。"""
        if choice in self.SAMPLE_SCRIPTS:
            code = self.SAMPLE_SCRIPTS[choice]
            self.script_textbox.delete("1.0", "end")
            self.script_textbox.insert("1.0", code)
            # 選択メニューを初期表示に戻す
            self.sample_menu.set("サンプルコード挿入...")

    def _update_container_visibility(self) -> None:
        """現在の選択モードに応じてコンテナを表示/非表示にする。"""
        mode = self.mode_var.get()
        self.pattern_container.pack_forget()
        self.delim_container.pack_forget()
        self.script_container.pack_forget()

        if mode == self.MODE_PATTERN:
            self.pattern_container.pack(fill="both", expand=True)
        elif mode == self.MODE_DELIMITER:
            self.delim_container.pack(fill="both", expand=True)
        else:
            self.script_container.pack(fill="both", expand=True)

    def _update_script_input_box_visibility(self) -> None:
        """スクリプトモード内の入力定義ボックスの表示/非表示を切り替える。"""
        in_mode = self.script_in_mode_var.get()
        self.script_pattern_box.pack_forget()
        self.script_delim_box.pack_forget()
        self.script_full_box.pack_forget()

        if in_mode == self.SCRIPT_IN_PATTERN:
            self.script_pattern_box.pack(fill="x", after=self.script_in_mode_selector.master)
        elif in_mode == self.SCRIPT_IN_DELIMITER:
            self.script_delim_box.pack(fill="x", after=self.script_in_mode_selector.master)
        else:
            self.script_full_box.pack(fill="x", after=self.script_in_mode_selector.master)

    def load_from_config(self, config: AppConfig) -> None:
        """設定値からUI状態を初期化する。"""
        # モード選択
        p_mode = getattr(config, "prog_mode", "pattern")
        if p_mode == "script":
            selected_mode = self.MODE_SCRIPT
        elif p_mode == "delimiter":
            selected_mode = self.MODE_DELIMITER
        else:
            selected_mode = self.MODE_PATTERN
        self.mode_var.set(selected_mode)
        self.mode_selector.set(selected_mode)

        # パターン設定
        self.pattern_input_entry.delete(0, "end")
        self.pattern_input_entry.insert(0, getattr(config, "prog_pattern_input", ""))

        self.pattern_output_entry.delete(0, "end")
        self.pattern_output_entry.insert(0, getattr(config, "prog_pattern_output", ""))

        # 区切り文字設定
        self.delim_selector.set_delimiter(config.prog_delimiter)
        self.delim_input_entry.delete(0, "end")
        self.delim_input_entry.insert(0, config.prog_input_vars)
        self.delim_output_entry.delete(0, "end")
        self.delim_output_entry.insert(0, config.prog_output_template)

        # スクリプト設定
        s_in = getattr(config, "prog_script_input_mode", "pattern")
        if s_in == "delimiter":
            self.script_in_mode_var.set(self.SCRIPT_IN_DELIMITER)
            self.script_in_mode_selector.set(self.SCRIPT_IN_DELIMITER)
        elif s_in == "full_text":
            self.script_in_mode_var.set(self.SCRIPT_IN_FULL_TEXT)
            self.script_in_mode_selector.set(self.SCRIPT_IN_FULL_TEXT)
        else:
            self.script_in_mode_var.set(self.SCRIPT_IN_PATTERN)
            self.script_in_mode_selector.set(self.SCRIPT_IN_PATTERN)

        self.script_pattern_entry.delete(0, "end")
        self.script_pattern_entry.insert(0, getattr(config, "prog_script_pattern", ""))

        self.script_delim_selector.set_delimiter(getattr(config, "prog_script_delimiter", ","))
        self.script_delim_vars_entry.delete(0, "end")
        self.script_delim_vars_entry.insert(0, getattr(config, "prog_script_vars", ""))

        self.script_textbox.delete("1.0", "end")
        self.script_textbox.insert("1.0", getattr(config, "prog_script_code", ""))

        self._update_container_visibility()
        self._update_script_input_box_visibility()

    def save_to_config(self, config: AppConfig) -> None:
        """現在のUI状態を設定モデルへ保存する。"""
        mode = self.mode_var.get()
        if mode == self.MODE_SCRIPT:
            config.prog_mode = "script"
        elif mode == self.MODE_DELIMITER:
            config.prog_mode = "delimiter"
        else:
            config.prog_mode = "pattern"

        config.prog_pattern_input = self.pattern_input_entry.get().strip()
        config.prog_pattern_output = self.pattern_output_entry.get().strip()

        config.prog_delimiter = self.delim_selector.get_delimiter()
        config.prog_input_vars = self.delim_input_entry.get().strip()
        config.prog_output_template = self.delim_output_entry.get().strip()

        # スクリプト設定
        s_in = self.script_in_mode_var.get()
        if s_in == self.SCRIPT_IN_DELIMITER:
            config.prog_script_input_mode = "delimiter"
        elif s_in == self.SCRIPT_IN_FULL_TEXT:
            config.prog_script_input_mode = "full_text"
        else:
            config.prog_script_input_mode = "pattern"

        config.prog_script_pattern = self.script_pattern_entry.get().strip()
        config.prog_script_delimiter = self.script_delim_selector.get_delimiter()
        config.prog_script_vars = self.script_delim_vars_entry.get().strip()
        config.prog_script_code = self.script_textbox.get("1.0", "end-1c").strip()

    def get_transformer(self) -> Optional[BaseTransformer]:
        """現在のUI入力および選択モードから適切な Transformer を構築して返す。"""
        mode = self.mode_var.get()

        if mode == self.MODE_PATTERN:
            inp_pattern = self.pattern_input_entry.get().strip()
            out_template = self.pattern_output_entry.get().strip()
            if not inp_pattern:
                return None
            try:
                return PatternTransformer(
                    input_pattern=inp_pattern,
                    output_template=out_template,
                )
            except Exception:
                return None
        elif mode == self.MODE_DELIMITER:
            delim = self.delim_selector.get_delimiter()
            raw_vars = self.delim_input_entry.get().strip()
            template = self.delim_output_entry.get().strip()

            if not raw_vars or not template:
                return None

            try:
                return TemplateTransformer(
                    var_names=raw_vars,
                    template=template,
                    delimiter=delim,
                )
            except Exception:
                return None
        else:
            # スクリプトモード
            code = self.script_textbox.get("1.0", "end-1c").strip()
            if not code:
                return None

            s_in = self.script_in_mode_var.get()
            if s_in == self.SCRIPT_IN_PATTERN:
                inp_mode = PythonScriptTransformer.MODE_PATTERN
                pattern_val = self.script_pattern_entry.get().strip()
                return PythonScriptTransformer(
                    input_mode=inp_mode,
                    script_code=code,
                    pattern_input=pattern_val,
                )
            elif s_in == self.SCRIPT_IN_DELIMITER:
                inp_mode = PythonScriptTransformer.MODE_DELIMITER
                delim_val = self.script_delim_selector.get_delimiter()
                vars_val = self.script_delim_vars_entry.get().strip()
                return PythonScriptTransformer(
                    input_mode=inp_mode,
                    script_code=code,
                    delimiter=delim_val,
                    var_names=vars_val,
                )
            else:
                inp_mode = PythonScriptTransformer.MODE_FULL_TEXT
                return PythonScriptTransformer(
                    input_mode=inp_mode,
                    script_code=code,
                )
