"""定型ルールモードのタブUIコンポーネント。"""

from typing import Optional
import customtkinter as ctk

from app.config import AppConfig
from app.transformers.preset import ColumnExtractTransformer, PresetTransformer


class PresetTabFrame(ctk.CTkFrame):
    """定型ルール（数値丸め、ゼロ埋め、列抽出）を設定するタブフレーム。"""

    def __init__(self, master, config: AppConfig, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.config = config
        self._build_ui()
        self.load_from_config(config)

    def _build_ui(self) -> None:
        # 1. 小数点丸めルール
        self.round_enabled_var = ctk.BooleanVar(value=True)
        self.chk_round = ctk.CTkCheckBox(
            self,
            text="数値 / パーセントの小数点丸め",
            font=ctk.CTkFont(size=13, weight="bold"),
            variable=self.round_enabled_var,
            command=self._on_field_changed,
        )
        self.chk_round.pack(anchor="w", padx=12, pady=(12, 4))

        round_opt_frame = ctk.CTkFrame(self, fg_color="transparent")
        round_opt_frame.pack(fill="x", padx=32, pady=(0, 8))

        ctk.CTkLabel(round_opt_frame, text="小数点以下桁数:").pack(
            side="left", padx=(0, 8)
        )
        self.round_digits_entry = ctk.CTkEntry(round_opt_frame, width=60)
        self.round_digits_entry.pack(side="left")

        # 2. 数字ゼロ埋め（パディング）ルール
        self.pad_enabled_var = ctk.BooleanVar(value=False)
        self.chk_pad = ctk.CTkCheckBox(
            self,
            text="数字のゼロ埋め (小数点以上・以下パディング)",
            font=ctk.CTkFont(size=13, weight="bold"),
            variable=self.pad_enabled_var,
            command=self._on_field_changed,
        )
        self.chk_pad.pack(anchor="w", padx=12, pady=(8, 4))

        pad_opt_frame = ctk.CTkFrame(self, fg_color="transparent")
        pad_opt_frame.pack(fill="x", padx=32, pady=(0, 8))

        ctk.CTkLabel(pad_opt_frame, text="整数部桁数:").pack(side="left", padx=(0, 6))
        self.pad_int_entry = ctk.CTkEntry(pad_opt_frame, width=50)
        self.pad_int_entry.pack(side="left", padx=(0, 16))

        ctk.CTkLabel(pad_opt_frame, text="小数部桁数:").pack(side="left", padx=(0, 6))
        self.pad_dec_entry = ctk.CTkEntry(pad_opt_frame, width=50)
        self.pad_dec_entry.pack(side="left")

        # 3. 列抽出ルール
        self.col_enabled_var = ctk.BooleanVar(value=False)
        self.chk_col = ctk.CTkCheckBox(
            self,
            text="特定列の抽出 (複数行対応)",
            font=ctk.CTkFont(size=13, weight="bold"),
            variable=self.col_enabled_var,
            command=self._on_field_changed,
        )
        self.chk_col.pack(anchor="w", padx=12, pady=(8, 4))

        col_opt_frame = ctk.CTkFrame(self, fg_color="transparent")
        col_opt_frame.pack(fill="x", padx=32, pady=(0, 12))

        ctk.CTkLabel(col_opt_frame, text="区切り文字:").grid(
            row=0, column=0, sticky="w", pady=4
        )
        self.col_delim_entry = ctk.CTkEntry(col_opt_frame, width=60)
        self.col_delim_entry.grid(row=0, column=1, sticky="w", padx=8, pady=4)

        ctk.CTkLabel(
            col_opt_frame, text="抽出列番号 (1始まり、カンマ区切り):"
        ).grid(row=1, column=0, sticky="w", pady=4)
        self.col_indices_entry = ctk.CTkEntry(col_opt_frame, width=140)
        self.col_indices_entry.grid(row=1, column=1, sticky="w", padx=8, pady=4)

    def _on_field_changed(self) -> None:
        pass

    def load_from_config(self, config: AppConfig) -> None:
        """設定値からUI状態を初期化する。"""
        self.round_enabled_var.set(config.round_enabled)
        self.round_digits_entry.delete(0, "end")
        self.round_digits_entry.insert(0, str(config.round_digits))

        self.pad_enabled_var.set(getattr(config, "pad_enabled", False))
        self.pad_int_entry.delete(0, "end")
        self.pad_int_entry.insert(0, str(getattr(config, "pad_int_digits", 3)))
        self.pad_dec_entry.delete(0, "end")
        self.pad_dec_entry.insert(0, str(getattr(config, "pad_dec_digits", 2)))

        self.col_enabled_var.set(config.col_enabled)
        self.col_delim_entry.delete(0, "end")
        self.col_delim_entry.insert(0, config.col_delimiter)

        self.col_indices_entry.delete(0, "end")
        self.col_indices_entry.insert(0, config.col_indices)

    def save_to_config(self, config: AppConfig) -> None:
        """現在のUI状態を設定モデルへ保存する。"""
        config.round_enabled = self.round_enabled_var.get()
        try:
            config.round_digits = max(0, int(self.round_digits_entry.get().strip()))
        except ValueError:
            pass

        config.pad_enabled = self.pad_enabled_var.get()
        try:
            config.pad_int_digits = max(0, int(self.pad_int_entry.get().strip()))
        except ValueError:
            config.pad_int_digits = 0

        try:
            config.pad_dec_digits = max(0, int(self.pad_dec_entry.get().strip()))
        except ValueError:
            config.pad_dec_digits = 0

        config.col_enabled = self.col_enabled_var.get()
        delim = self.col_delim_entry.get()
        config.col_delimiter = delim if delim else ","
        config.col_indices = self.col_indices_entry.get().strip()

    def get_transformer(self) -> Optional[PresetTransformer]:
        """現在のUI入力から PresetTransformer インスタンスを構築して返す。"""
        round_enabled = self.round_enabled_var.get()
        pad_enabled = self.pad_enabled_var.get()
        col_enabled = self.col_enabled_var.get()

        if not round_enabled and not pad_enabled and not col_enabled:
            return None

        try:
            digits = max(0, int(self.round_digits_entry.get().strip()))
        except ValueError:
            digits = 2

        try:
            pad_int = max(0, int(self.pad_int_entry.get().strip()))
        except ValueError:
            pad_int = 0

        try:
            pad_dec = max(0, int(self.pad_dec_entry.get().strip()))
        except ValueError:
            pad_dec = 0

        delim = self.col_delim_entry.get() or ","
        raw_indices = self.col_indices_entry.get().strip()
        try:
            indices = ColumnExtractTransformer.parse_indices_string(raw_indices)
        except Exception:
            indices = [1, -1]

        return PresetTransformer(
            round_enabled=round_enabled,
            round_digits=digits,
            pad_enabled=pad_enabled,
            pad_int_digits=pad_int,
            pad_dec_digits=pad_dec,
            col_enabled=col_enabled,
            col_delimiter=delim,
            col_indices=indices,
        )
