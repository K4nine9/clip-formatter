"""LaTeXモードのタブUIコンポーネント。"""

from typing import Optional
import customtkinter as ctk

from app.config import AppConfig
from app.transformers.base import BaseTransformer
from app.transformers.latex import LatexFormulaTransformer, LatexTableTransformer
from app.ui.components.delimiter_selector import DelimiterSelector


class LatexTabFrame(ctk.CTkFrame):
    """LaTeX 表組み変換および数式双方向変換を設定するタブフレーム。"""

    MODE_TABLE = "table"
    MODE_FORMULA = "formula"

    STYLE_LABEL_MAP = {
        "booktabs (学術推奨)": LatexTableTransformer.STYLE_BOOKTABS,
        "standard (\\hline)": LatexTableTransformer.STYLE_STANDARD,
        "本体のみ (& と \\\\)": LatexTableTransformer.STYLE_BODY_ONLY,
        "Markdown 表 (| Col1 | Col2 |)": LatexTableTransformer.STYLE_MARKDOWN,
    }
    STYLE_VALUE_MAP = {v: k for k, v in STYLE_LABEL_MAP.items()}

    HIGHLIGHT_LABEL_MAP = {
        "強調なし": LatexTableTransformer.HIGHLIGHT_NONE,
        "列ごとの最大値を太字 (Max)": LatexTableTransformer.HIGHLIGHT_MAX,
        "列ごとの最小値を太字 (Min)": LatexTableTransformer.HIGHLIGHT_MIN,
    }
    HIGHLIGHT_VALUE_MAP = {v: k for k, v in HIGHLIGHT_LABEL_MAP.items()}

    ENV_LABEL_MAP = {
        "インライン ($ ... $)": LatexFormulaTransformer.ENV_INLINE,
        "ディスプレイ (\\[ ... \\])": LatexFormulaTransformer.ENV_DISPLAY,
        "囲みなし": LatexFormulaTransformer.ENV_NONE,
    }
    ENV_VALUE_MAP = {v: k for k, v in ENV_LABEL_MAP.items()}

    def __init__(self, master, config: AppConfig, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.config = config
        self._build_ui()
        self.load_from_config(config)

    def _build_ui(self) -> None:
        # 1. サブモード切り替えラジオボタン
        mode_header = ctk.CTkFrame(self, fg_color="transparent")
        mode_header.pack(fill="x", padx=12, pady=(10, 4))
        ctk.CTkLabel(
            mode_header,
            text="【LaTeX 変換モード選択】",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=("gray20", "gray85"),
        ).pack(anchor="w")

        self.latex_mode_var = ctk.StringVar(value=self.MODE_TABLE)

        mode_radio_frame = ctk.CTkFrame(self, fg_color="transparent")
        mode_radio_frame.pack(fill="x", padx=24, pady=2)

        self.rb_table = ctk.CTkRadioButton(
            mode_radio_frame,
            text="表組み (Table) 変換",
            font=ctk.CTkFont(size=12, weight="bold"),
            variable=self.latex_mode_var,
            value=self.MODE_TABLE,
            command=self._on_mode_changed,
        )
        self.rb_table.pack(side="left", padx=(0, 24))

        self.rb_formula = ctk.CTkRadioButton(
            mode_radio_frame,
            text="数式 (Formula) 双方向変換",
            font=ctk.CTkFont(size=12, weight="bold"),
            variable=self.latex_mode_var,
            value=self.MODE_FORMULA,
            command=self._on_mode_changed,
        )
        self.rb_formula.pack(side="left")

        # 区切り線
        ctk.CTkFrame(self, height=2, fg_color=("gray80", "gray30")).pack(
            fill="x", padx=16, pady=8
        )

        # =======================================================
        # 2. 表組み設定エリア
        # =======================================================
        self.table_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.table_frame.pack(fill="x", padx=16, pady=2)

        # 区切り文字
        delim_row = ctk.CTkFrame(self.table_frame, fg_color="transparent")
        delim_row.pack(fill="x", pady=3)
        ctk.CTkLabel(delim_row, text="入力区切り文字:").pack(side="left", padx=(0, 8))
        self.table_delim_selector = DelimiterSelector(delim_row, default_delimiter="\t")
        self.table_delim_selector.pack(side="left")

        # スタイル選択
        style_row = ctk.CTkFrame(self.table_frame, fg_color="transparent")
        style_row.pack(fill="x", pady=3)
        ctk.CTkLabel(style_row, text="表スタイル:").pack(side="left", padx=(0, 8))
        self.table_style_menu = ctk.CTkOptionMenu(
            style_row,
            values=list(self.STYLE_LABEL_MAP.keys()),
            width=210,
        )
        self.table_style_menu.pack(side="left")

        # 列配置 (Alignment)
        align_row = ctk.CTkFrame(self.table_frame, fg_color="transparent")
        align_row.pack(fill="x", pady=3)
        ctk.CTkLabel(align_row, text="列揃え (Alignment):").pack(side="left", padx=(0, 8))
        self.table_align_menu = ctk.CTkOptionMenu(
            align_row,
            values=["自動推定 (数値r/文字列l)", "一括中央揃え (c)", "一括左揃え (l)", "一括右揃え (r)"],
            width=210,
        )
        self.table_align_menu.pack(side="left")

        # 最良値の太字化
        hl_row = ctk.CTkFrame(self.table_frame, fg_color="transparent")
        hl_row.pack(fill="x", pady=3)
        ctk.CTkLabel(hl_row, text="最良値の太字化:").pack(side="left", padx=(0, 8))
        self.table_hl_menu = ctk.CTkOptionMenu(
            hl_row,
            values=list(self.HIGHLIGHT_LABEL_MAP.keys()),
            width=210,
        )
        self.table_hl_menu.pack(side="left")

        # オプション（ヘッダー・丸め）
        opt_row = ctk.CTkFrame(self.table_frame, fg_color="transparent")
        opt_row.pack(fill="x", pady=3)

        self.table_header_var = ctk.BooleanVar(value=True)
        self.chk_table_header = ctk.CTkCheckBox(
            opt_row,
            text="先頭行をヘッダーとして扱う",
            variable=self.table_header_var,
        )
        self.chk_table_header.pack(side="left", padx=(0, 16))

        round_row = ctk.CTkFrame(self.table_frame, fg_color="transparent")
        round_row.pack(fill="x", pady=3)

        self.table_round_var = ctk.BooleanVar(value=False)
        self.chk_table_round = ctk.CTkCheckBox(
            round_row,
            text="表内の数値を自動丸め:",
            variable=self.table_round_var,
            command=self._on_table_round_toggled,
        )
        self.chk_table_round.pack(side="left", padx=(0, 8))

        ctk.CTkLabel(round_row, text="小数桁数:").pack(side="left", padx=(0, 4))
        self.table_digits_entry = ctk.CTkEntry(round_row, width=45)
        self.table_digits_entry.pack(side="left")

        # =======================================================
        # 3. 数式設定エリア
        # =======================================================
        self.formula_frame = ctk.CTkFrame(self, fg_color="transparent")

        # 変換方向
        dir_header = ctk.CTkLabel(
            self.formula_frame,
            text="変換方向:",
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        dir_header.pack(anchor="w", pady=(0, 4))

        self.formula_dir_var = ctk.StringVar(value=LatexFormulaTransformer.DIR_PLAIN_TO_LATEX)
        self.seg_dir = ctk.CTkSegmentedButton(
            self.formula_frame,
            values=["手打ち数式 → LaTeX数式", "LaTeX数式 → 手打ち数式"],
            command=self._on_formula_dir_changed,
        )
        self.seg_dir.set("手打ち数式 → LaTeX数式")
        self.seg_dir.pack(fill="x", pady=(0, 12))

        # 数式環境
        env_row = ctk.CTkFrame(self.formula_frame, fg_color="transparent")
        env_row.pack(fill="x", pady=4)
        ctk.CTkLabel(env_row, text="LaTeX数式環境:").pack(side="left", padx=(0, 8))
        self.formula_env_menu = ctk.CTkOptionMenu(
            env_row,
            values=list(self.ENV_LABEL_MAP.keys()),
            width=180,
        )
        self.formula_env_menu.pack(side="left")

        # ガイド表示
        guide_box = ctk.CTkFrame(self.formula_frame, fg_color=("gray90", "gray20"))
        guide_box.pack(fill="x", pady=(12, 0))
        guide_text = (
            "【変換可能な記法例】\n"
            "・分数: 1 / (2x)  =>  \\frac{1}{2x}\n"
            "・べき乗: x^2, (a+b)^n  =>  x^{2}, (a+b)^{n}\n"
            "・平方根: sqrt(x)  =>  \\sqrt{x}\n"
            "・ギリシャ文字: alpha, beta, theta  =>  \\alpha, \\beta, \\theta\n"
            "・記号: * => \\cdot,  +- => \\pm"
        )
        ctk.CTkLabel(
            guide_box,
            text=guide_text,
            font=ctk.CTkFont(size=11),
            text_color=("gray40", "gray70"),
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=10, pady=8)

        self._on_mode_changed()

    def _on_mode_changed(self) -> None:
        mode = self.latex_mode_var.get()
        if mode == self.MODE_TABLE:
            self.formula_frame.pack_forget()
            self.table_frame.pack(fill="x", padx=16, pady=2)
        else:
            self.table_frame.pack_forget()
            self.formula_frame.pack(fill="x", padx=16, pady=2)

    def _on_table_round_toggled(self) -> None:
        state = "normal" if self.table_round_var.get() else "disabled"
        self.table_digits_entry.configure(state=state)

    def _on_formula_dir_changed(self, val: str) -> None:
        if val == "手打ち数式 → LaTeX数式":
            self.formula_dir_var.set(LatexFormulaTransformer.DIR_PLAIN_TO_LATEX)
            self.formula_env_menu.configure(state="normal")
        else:
            self.formula_dir_var.set(LatexFormulaTransformer.DIR_LATEX_TO_PLAIN)
            self.formula_env_menu.configure(state="disabled")

    def load_from_config(self, config: AppConfig) -> None:
        mode = getattr(config, "latex_mode", self.MODE_TABLE)
        self.latex_mode_var.set(mode)

        # 表組み
        delim = getattr(config, "latex_table_delim", "\t")
        self.table_delim_selector.set_delimiter(delim)

        style = getattr(config, "latex_table_style", LatexTableTransformer.STYLE_BOOKTABS)
        self.table_style_menu.set(self.STYLE_VALUE_MAP.get(style, "booktabs (学術推奨)"))

        align = getattr(config, "latex_table_align", "auto")
        if align == "auto":
            self.table_align_menu.set("自動推定 (数値r/文字列l)")
        elif align == "c":
            self.table_align_menu.set("一括中央揃え (c)")
        elif align == "l":
            self.table_align_menu.set("一括左揃え (l)")
        elif align == "r":
            self.table_align_menu.set("一括右揃え (r)")

        hl = getattr(config, "latex_table_highlight", LatexTableTransformer.HIGHLIGHT_NONE)
        self.table_hl_menu.set(self.HIGHLIGHT_VALUE_MAP.get(hl, "強調なし"))

        self.table_header_var.set(getattr(config, "latex_table_header", True))
        self.table_round_var.set(getattr(config, "latex_table_round", False))
        self.table_digits_entry.delete(0, "end")
        self.table_digits_entry.insert(0, str(getattr(config, "latex_table_digits", 2)))
        self._on_table_round_toggled()

        # 数式
        direction = getattr(config, "latex_formula_direction", LatexFormulaTransformer.DIR_PLAIN_TO_LATEX)
        self.formula_dir_var.set(direction)
        if direction == LatexFormulaTransformer.DIR_PLAIN_TO_LATEX:
            self.seg_dir.set("手打ち数式 → LaTeX数式")
        else:
            self.seg_dir.set("LaTeX数式 → 手打ち数式")

        env = getattr(config, "latex_formula_env", LatexFormulaTransformer.ENV_INLINE)
        self.formula_env_menu.set(self.ENV_VALUE_MAP.get(env, "インライン ($ ... $)"))

        self._on_mode_changed()

    def save_to_config(self, config: AppConfig) -> None:
        config.latex_mode = self.latex_mode_var.get()
        config.latex_table_delim = self.table_delim_selector.get_delimiter()
        config.latex_table_style = self.STYLE_LABEL_MAP.get(
            self.table_style_menu.get(), LatexTableTransformer.STYLE_BOOKTABS
        )

        align_choice = self.table_align_menu.get()
        if "中央" in align_choice:
            config.latex_table_align = "c"
        elif "左" in align_choice:
            config.latex_table_align = "l"
        elif "右" in align_choice:
            config.latex_table_align = "r"
        else:
            config.latex_table_align = "auto"

        config.latex_table_highlight = self.HIGHLIGHT_LABEL_MAP.get(
            self.table_hl_menu.get(), LatexTableTransformer.HIGHLIGHT_NONE
        )

        config.latex_table_header = self.table_header_var.get()
        config.latex_table_round = self.table_round_var.get()
        try:
            config.latex_table_digits = max(0, int(self.table_digits_entry.get().strip()))
        except ValueError:
            config.latex_table_digits = 2

        config.latex_formula_direction = self.formula_dir_var.get()
        config.latex_formula_env = self.ENV_LABEL_MAP.get(
            self.formula_env_menu.get(), LatexFormulaTransformer.ENV_INLINE
        )

    def get_transformer(self) -> Optional[BaseTransformer]:
        mode = self.latex_mode_var.get()
        if mode == self.MODE_TABLE:
            delim = self.table_delim_selector.get_delimiter()
            style = self.STYLE_LABEL_MAP.get(
                self.table_style_menu.get(), LatexTableTransformer.STYLE_BOOKTABS
            )
            align_choice = self.table_align_menu.get()
            if "中央" in align_choice:
                align = "c"
            elif "左" in align_choice:
                align = "l"
            elif "右" in align_choice:
                align = "r"
            else:
                align = "auto"

            highlight = self.HIGHLIGHT_LABEL_MAP.get(
                self.table_hl_menu.get(), LatexTableTransformer.HIGHLIGHT_NONE
            )

            round_digits = None
            if self.table_round_var.get():
                try:
                    round_digits = max(0, int(self.table_digits_entry.get().strip()))
                except ValueError:
                    round_digits = 2

            return LatexTableTransformer(
                delimiter=delim,
                style=style,
                alignment=align,
                has_header=self.table_header_var.get(),
                round_digits=round_digits,
                highlight_best=highlight,
            )
        else:
            direction = self.formula_dir_var.get()
            env = self.ENV_LABEL_MAP.get(
                self.formula_env_menu.get(), LatexFormulaTransformer.ENV_INLINE
            )
            return LatexFormulaTransformer(
                direction=direction,
                env=env,
            )
