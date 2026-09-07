"""プログラマブルモードのタブUIコンポーネント。"""

from typing import Optional, Union
import customtkinter as ctk

from app.config import AppConfig
from app.transformers.base import BaseTransformer
from app.transformers.pattern import PatternTransformer
from app.transformers.template import TemplateTransformer
from app.ui.components.delimiter_selector import DelimiterSelector


class ProgrammableTabFrame(ctk.CTkFrame):
    """プログラマブル（文脈パターンマッチ / 区切り文字展開）を設定するタブフレーム。"""

    MODE_PATTERN = "パターンマッチ形式"
    MODE_DELIMITER = "区切り文字形式"

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
            values=[self.MODE_PATTERN, self.MODE_DELIMITER],
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

        # デフォルト表示
        self._update_container_visibility()

    def _on_mode_switched(self, selected_mode: str) -> None:
        """モード切り替え時のUI表示更新。"""
        self._update_container_visibility()

    def _update_container_visibility(self) -> None:
        """現在の選択モードに応じてコンテナを表示/非表示にする。"""
        mode = self.mode_var.get()
        if mode == self.MODE_PATTERN:
            self.delim_container.pack_forget()
            self.pattern_container.pack(fill="both", expand=True)
        else:
            self.pattern_container.pack_forget()
            self.delim_container.pack(fill="both", expand=True)

    def load_from_config(self, config: AppConfig) -> None:
        """設定値からUI状態を初期化する。"""
        # モード選択
        is_pattern = getattr(config, "prog_mode", "pattern") == "pattern"
        selected_mode = self.MODE_PATTERN if is_pattern else self.MODE_DELIMITER
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

        self._update_container_visibility()

    def save_to_config(self, config: AppConfig) -> None:
        """現在のUI状態を設定モデルへ保存する。"""
        config.prog_mode = "pattern" if self.mode_var.get() == self.MODE_PATTERN else "delimiter"
        config.prog_pattern_input = self.pattern_input_entry.get().strip()
        config.prog_pattern_output = self.pattern_output_entry.get().strip()

        config.prog_delimiter = self.delim_selector.get_delimiter()
        config.prog_input_vars = self.delim_input_entry.get().strip()
        config.prog_output_template = self.delim_output_entry.get().strip()

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
        else:
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
