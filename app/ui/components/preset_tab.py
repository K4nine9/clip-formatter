"""定型ルールモードのタブUIコンポーネント。"""

from typing import Optional
import customtkinter as ctk

from app.config import AppConfig
from app.transformers.preset import ColumnExtractTransformer, PresetTransformer
from app.ui.components.delimiter_selector import DelimiterSelector


class PresetTabFrame(ctk.CTkFrame):
    """定型ルール（整数部/小数部フォーマット、列抽出）を設定するタブフレーム。"""

    # 整数部モード
    INT_NONE = "none"
    INT_PAD = "pad"

    # 小数部モード
    DEC_NONE = "none"
    DEC_ROUND = "round"
    DEC_PAD = "pad"

    # 超過時処理
    OVERFLOW_ROUND = "round"
    OVERFLOW_TRUNCATE = "truncate"

    OVERFLOW_LABEL_MAP = {
        "四捨五入": OVERFLOW_ROUND,
        "切り捨て": OVERFLOW_TRUNCATE,
    }
    OVERFLOW_VALUE_MAP = {
        OVERFLOW_ROUND: "四捨五入",
        OVERFLOW_TRUNCATE: "切り捨て",
    }

    def __init__(self, master, config: AppConfig, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.config = config
        self._build_ui()
        self.load_from_config(config)

    def _build_ui(self) -> None:
        # =======================================================
        # 1. 整数部（小数点以上）ルール
        # =======================================================
        int_header = ctk.CTkFrame(self, fg_color="transparent")
        int_header.pack(fill="x", padx=12, pady=(10, 2))
        ctk.CTkLabel(
            int_header,
            text="【整数部ルール（小数点以上）】",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=("gray20", "gray85"),
        ).pack(anchor="w")

        self.int_mode_var = ctk.StringVar(value=self.INT_NONE)

        int_radio_frame = ctk.CTkFrame(self, fg_color="transparent")
        int_radio_frame.pack(fill="x", padx=24, pady=2)

        self.rb_int_none = ctk.CTkRadioButton(
            int_radio_frame,
            text="変更しない",
            font=ctk.CTkFont(size=12),
            variable=self.int_mode_var,
            value=self.INT_NONE,
            command=self._on_int_mode_changed,
        )
        self.rb_int_none.pack(side="left", padx=(0, 20))

        self.rb_int_pad = ctk.CTkRadioButton(
            int_radio_frame,
            text="ゼロ埋め (パディング)",
            font=ctk.CTkFont(size=12, weight="bold"),
            variable=self.int_mode_var,
            value=self.INT_PAD,
            command=self._on_int_mode_changed,
        )
        self.rb_int_pad.pack(side="left")

        # 整数部オプション
        int_opt_frame = ctk.CTkFrame(self, fg_color="transparent")
        int_opt_frame.pack(fill="x", padx=48, pady=(2, 8))
        ctk.CTkLabel(int_opt_frame, text="整数部桁数:").pack(side="left", padx=(0, 6))
        self.int_digits_entry = ctk.CTkEntry(int_opt_frame, width=50)
        self.int_digits_entry.pack(side="left")

        # 区切り線 1
        ctk.CTkFrame(self, height=2, fg_color=("gray80", "gray30")).pack(
            fill="x", padx=16, pady=4
        )

        # =======================================================
        # 2. 小数部（小数点以下）ルール
        # =======================================================
        dec_header = ctk.CTkFrame(self, fg_color="transparent")
        dec_header.pack(fill="x", padx=12, pady=(6, 2))
        ctk.CTkLabel(
            dec_header,
            text="【小数部ルール（小数点以下）】",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=("gray20", "gray85"),
        ).pack(anchor="w")

        self.dec_mode_var = ctk.StringVar(value=self.DEC_ROUND)

        dec_radio_frame = ctk.CTkFrame(self, fg_color="transparent")
        dec_radio_frame.pack(fill="x", padx=24, pady=2)

        self.rb_dec_none = ctk.CTkRadioButton(
            dec_radio_frame,
            text="変更しない",
            font=ctk.CTkFont(size=12),
            variable=self.dec_mode_var,
            value=self.DEC_NONE,
            command=self._on_dec_mode_changed,
        )
        self.rb_dec_none.pack(side="left", padx=(0, 16))

        self.rb_dec_round = ctk.CTkRadioButton(
            dec_radio_frame,
            text="小数丸めモード (可変長)",
            font=ctk.CTkFont(size=12, weight="bold"),
            variable=self.dec_mode_var,
            value=self.DEC_ROUND,
            command=self._on_dec_mode_changed,
        )
        self.rb_dec_round.pack(side="left", padx=(0, 16))

        self.rb_dec_pad = ctk.CTkRadioButton(
            dec_radio_frame,
            text="ゼロ埋めモード (固定長)",
            font=ctk.CTkFont(size=12, weight="bold"),
            variable=self.dec_mode_var,
            value=self.DEC_PAD,
            command=self._on_dec_mode_changed,
        )
        self.rb_dec_pad.pack(side="left")

        # 小数部オプションフレーム（桁数 & 超過時処理ドロップダウン）
        dec_opt_frame = ctk.CTkFrame(self, fg_color="transparent")
        dec_opt_frame.pack(fill="x", padx=48, pady=(4, 8))

        ctk.CTkLabel(dec_opt_frame, text="小数点以下桁数:").pack(side="left", padx=(0, 6))
        self.dec_digits_entry = ctk.CTkEntry(dec_opt_frame, width=50)
        self.dec_digits_entry.pack(side="left", padx=(0, 20))

        ctk.CTkLabel(dec_opt_frame, text="桁数超過時の処理:").pack(side="left", padx=(0, 6))
        self.dec_overflow_menu = ctk.CTkOptionMenu(
            dec_opt_frame,
            values=["四捨五入", "切り捨て"],
            width=90,
            command=self._on_overflow_changed,
        )
        self.dec_overflow_menu.pack(side="left")

        # 区切り線 2
        ctk.CTkFrame(self, height=2, fg_color=("gray80", "gray30")).pack(
            fill="x", padx=16, pady=4
        )

        # =======================================================
        # 3. 列抽出ルール（チェックボックス）
        # =======================================================
        col_header = ctk.CTkFrame(self, fg_color="transparent")
        col_header.pack(fill="x", padx=12, pady=(6, 2))
        ctk.CTkLabel(
            col_header,
            text="【列抽出ルール（他ルールと併用可能）】",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=("gray20", "gray85"),
        ).pack(anchor="w")

        self.col_enabled_var = ctk.BooleanVar(value=False)
        self.chk_col = ctk.CTkCheckBox(
            self,
            text="特定列の抽出 (複数行対応)",
            font=ctk.CTkFont(size=12, weight="bold"),
            variable=self.col_enabled_var,
            command=self._on_col_toggled,
        )
        self.chk_col.pack(anchor="w", padx=24, pady=(4, 4))

        col_opt_frame = ctk.CTkFrame(self, fg_color="transparent")
        col_opt_frame.pack(fill="x", padx=48, pady=(0, 6))

        delim_row = ctk.CTkFrame(col_opt_frame, fg_color="transparent")
        delim_row.pack(fill="x", pady=2)
        ctk.CTkLabel(delim_row, text="区切り文字:").pack(side="left", padx=(0, 8))
        self.col_delim_selector = DelimiterSelector(delim_row, default_delimiter=",")
        self.col_delim_selector.pack(side="left")

        idx_row = ctk.CTkFrame(col_opt_frame, fg_color="transparent")
        idx_row.pack(fill="x", pady=2)
        ctk.CTkLabel(
            idx_row, text="抽出列番号 (1始まり、カンマ区切り):"
        ).pack(side="left", padx=(0, 8))
        self.col_indices_entry = ctk.CTkEntry(idx_row, width=120)
        self.col_indices_entry.pack(side="left")

        # 区切り線 3
        ctk.CTkFrame(self, height=2, fg_color=("gray80", "gray30")).pack(
            fill="x", padx=16, pady=4
        )

        # =======================================================
        # 4. 改行・ハイフン除去ルール (PDFコピペ用)
        # =======================================================
        unwrap_header = ctk.CTkFrame(self, fg_color="transparent")
        unwrap_header.pack(fill="x", padx=12, pady=(4, 2))
        ctk.CTkLabel(
            unwrap_header,
            text="【テキスト整形（PDFコピペ・論文読解用）】",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=("gray20", "gray85"),
        ).pack(anchor="w")

        self.unwrap_enabled_var = ctk.BooleanVar(value=False)
        self.chk_unwrap = ctk.CTkCheckBox(
            self,
            text="不要な行末改行・ハイフンを結合する (Unwrap)",
            font=ctk.CTkFont(size=12, weight="bold"),
            variable=self.unwrap_enabled_var,
        )
        self.chk_unwrap.pack(anchor="w", padx=24, pady=(4, 8))

        self._update_entry_states()

    def _on_int_mode_changed(self) -> None:
        self._update_entry_states()

    def _on_dec_mode_changed(self) -> None:
        self._update_entry_states()

    def _on_overflow_changed(self, choice: str) -> None:
        pass

    def _on_col_toggled(self) -> None:
        self._update_entry_states()

    def _update_entry_states(self) -> None:
        """現在の選択状態に応じて各入力エントリの活性/非活性を切り替える。"""
        # 整数部
        int_state = "normal" if self.int_mode_var.get() == self.INT_PAD else "disabled"
        self.int_digits_entry.configure(state=int_state)

        # 小数部
        dec_state = "disabled" if self.dec_mode_var.get() == self.DEC_NONE else "normal"
        self.dec_digits_entry.configure(state=dec_state)
        self.dec_overflow_menu.configure(state=dec_state)

        # 列抽出
        col_state = "normal" if self.col_enabled_var.get() else "disabled"
        self.col_delim_selector.configure_state(col_state)
        self.col_indices_entry.configure(state=col_state)

    def load_from_config(self, config: AppConfig) -> None:
        """設定値からUI状態を初期化する。"""
        int_mode = getattr(config, "int_mode", self.INT_NONE)
        int_digits = getattr(config, "int_digits", 3)
        dec_mode = getattr(config, "dec_mode", self.DEC_ROUND)
        dec_digits = getattr(config, "dec_digits", 2)
        dec_overflow = getattr(config, "dec_overflow", self.OVERFLOW_ROUND)

        # 後方互換対応
        if dec_mode == "truncate":
            dec_mode = self.DEC_ROUND
            dec_overflow = self.OVERFLOW_TRUNCATE

        self.int_mode_var.set(int_mode)
        self.int_digits_entry.delete(0, "end")
        self.int_digits_entry.insert(0, str(int_digits))

        self.dec_mode_var.set(dec_mode)
        self.dec_digits_entry.delete(0, "end")
        self.dec_digits_entry.insert(0, str(dec_digits))

        overflow_label = self.OVERFLOW_VALUE_MAP.get(dec_overflow, "四捨五入")
        self.dec_overflow_menu.set(overflow_label)

        self.col_enabled_var.set(config.col_enabled)
        self.col_delim_selector.set_delimiter(config.col_delimiter)

        self.col_indices_entry.delete(0, "end")
        self.col_indices_entry.insert(0, config.col_indices)

        self.unwrap_enabled_var.set(getattr(config, "unwrap_enabled", False))

        self._update_entry_states()

    def save_to_config(self, config: AppConfig) -> None:
        """現在のUI状態を設定モデルへ保存する。"""
        int_mode = self.int_mode_var.get()
        dec_mode = self.dec_mode_var.get()
        dec_overflow = self.OVERFLOW_LABEL_MAP.get(
            self.dec_overflow_menu.get(), self.OVERFLOW_ROUND
        )

        config.int_mode = int_mode
        config.dec_mode = dec_mode
        config.dec_overflow = dec_overflow

        try:
            config.int_digits = max(0, int(self.int_digits_entry.get().strip()))
        except ValueError:
            config.int_digits = 0

        try:
            config.dec_digits = max(0, int(self.dec_digits_entry.get().strip()))
        except ValueError:
            config.dec_digits = 0

        # 後方互換性用フィールドの同期
        config.pad_enabled = (int_mode == self.INT_PAD or dec_mode == self.DEC_PAD)
        config.round_enabled = (dec_mode == self.DEC_ROUND)
        config.round_digits = config.dec_digits
        config.pad_int_digits = config.int_digits
        config.pad_dec_digits = config.dec_digits

        config.col_enabled = self.col_enabled_var.get()
        config.col_delimiter = self.col_delim_selector.get_delimiter()
        config.col_indices = self.col_indices_entry.get().strip()

        config.unwrap_enabled = self.unwrap_enabled_var.get()

    def get_transformer(self) -> Optional[PresetTransformer]:
        """現在のUI入力から PresetTransformer インスタンスを構築して返す。"""
        int_mode = self.int_mode_var.get()
        dec_mode = self.dec_mode_var.get()
        dec_overflow = self.OVERFLOW_LABEL_MAP.get(
            self.dec_overflow_menu.get(), self.OVERFLOW_ROUND
        )
        col_enabled = self.col_enabled_var.get()
        unwrap_enabled = self.unwrap_enabled_var.get()

        num_active = (int_mode == self.INT_PAD) or (dec_mode != self.DEC_NONE)
        if not num_active and not col_enabled and not unwrap_enabled:
            return None

        try:
            int_digits = max(0, int(self.int_digits_entry.get().strip()))
        except ValueError:
            int_digits = 0

        try:
            dec_digits = max(0, int(self.dec_digits_entry.get().strip()))
        except ValueError:
            dec_digits = 0

        delim = self.col_delim_selector.get_delimiter()
        raw_indices = self.col_indices_entry.get().strip()
        try:
            indices = ColumnExtractTransformer.parse_indices_string(raw_indices)
        except Exception:
            indices = [1, -1]

        return PresetTransformer(
            int_mode=int_mode,
            int_digits=int_digits,
            dec_mode=dec_mode,
            dec_digits=dec_digits,
            dec_overflow=dec_overflow,
            col_enabled=col_enabled,
            col_delimiter=delim,
            col_indices=indices,
            unwrap_enabled=unwrap_enabled,
        )
