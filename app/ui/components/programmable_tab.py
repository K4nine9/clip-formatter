"""プログラマブルモードのタブUIコンポーネント。"""

from typing import Optional
import customtkinter as ctk

from app.config import AppConfig
from app.transformers.template import TemplateTransformer


class ProgrammableTabFrame(ctk.CTkFrame):
    """プログラマブル（変数テンプレート展開）を設定するタブフレーム。"""

    def __init__(self, master, config: AppConfig, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.config = config
        self._build_ui()
        self.load_from_config(config)

    def _build_ui(self) -> None:
        desc = (
            "入力パターンと出力テンプレートを変数名で指定します。\n"
            "例: 入力「a, b, c, d, e」 出力「{e}, {b}, {c}, {d}, {a}」\n"
            "入力データがルールに合わない場合は自動でスキップされます。"
        )
        self.desc_label = ctk.CTkLabel(
            self,
            text=desc,
            justify="left",
            text_color=("gray50", "gray70"),
            font=ctk.CTkFont(size=12),
        )
        self.desc_label.pack(anchor="w", padx=12, pady=8)

        # 区切り文字
        sep_frame = ctk.CTkFrame(self, fg_color="transparent")
        sep_frame.pack(fill="x", padx=12, pady=4)
        ctk.CTkLabel(sep_frame, text="区切り文字:").pack(side="left", padx=(0, 8))
        self.delim_entry = ctk.CTkEntry(sep_frame, width=80)
        self.delim_entry.pack(side="left")

        # 入力フォーマット（変数リスト）
        ctk.CTkLabel(
            self, text="入力フォーマット（変数名定義）:", font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=12, pady=(8, 2))
        self.input_entry = ctk.CTkEntry(self)
        self.input_entry.pack(fill="x", padx=12, pady=(0, 8))

        # 出力フォーマット
        ctk.CTkLabel(
            self, text="出力テンプレート（{変数名}で指定）:", font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=12, pady=(8, 2))
        self.output_entry = ctk.CTkEntry(self)
        self.output_entry.pack(fill="x", padx=12, pady=(0, 12))

    def load_from_config(self, config: AppConfig) -> None:
        """設定値からUI状態を初期化する。"""
        self.delim_entry.delete(0, "end")
        self.delim_entry.insert(0, config.prog_delimiter)

        self.input_entry.delete(0, "end")
        self.input_entry.insert(0, config.prog_input_vars)

        self.output_entry.delete(0, "end")
        self.output_entry.insert(0, config.prog_output_template)

    def save_to_config(self, config: AppConfig) -> None:
        """現在のUI状態を設定モデルへ保存する。"""
        delim = self.delim_entry.get()
        config.prog_delimiter = delim if delim else ","
        config.prog_input_vars = self.input_entry.get().strip()
        config.prog_output_template = self.output_entry.get().strip()

    def get_transformer(self) -> Optional[TemplateTransformer]:
        """現在のUI入力から TemplateTransformer インスタンスを構築して返す。"""
        delim = self.delim_entry.get() or ","
        raw_vars = self.input_entry.get().strip()
        template = self.output_entry.get().strip()

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
