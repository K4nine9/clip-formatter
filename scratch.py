import re
import threading
import customtkinter as ctk
import pyperclip
from pynput import keyboard

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class ClipboardTransformerApp(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("ClipFormatter")
        self.geometry("540x620")
        self.resizable(False, False)

        # 内部状態
        self.is_active = False
        self.last_clipboard = ""
        self.last_written = ""

        self._build_ui()
        self._start_global_hotkey()
        self._start_clipboard_monitor()

    def _build_ui(self):
        # メインスイッチ（有効/無効）
        self.header_frame = ctk.CTkFrame(self)
        self.header_frame.pack(fill="x", padx=16, pady=(16, 8))

        self.switch_var = ctk.BooleanVar(value=False)
        self.toggle_switch = ctk.CTkSwitch(
            self.header_frame,
            text="自動変換を有効化 (Hotkey: Ctrl+Alt+X)",
            font=ctk.CTkFont(size=14, weight="bold"),
            variable=self.switch_var,
            command=self._on_switch_toggled,
        )
        self.toggle_switch.pack(side="left", padx=12, pady=12)

        # モード選択タブ
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=16, pady=8)

        self.tab_preset = self.tabview.add("定型ルールモード")
        self.tab_programmable = self.tabview.add("プログラマブルモード")

        self._build_preset_tab()
        self._build_programmable_tab()

        # ステータスバー / ログ表示
        self.status_frame = ctk.CTkFrame(self)
        self.status_frame.pack(fill="x", padx=16, pady=(8, 16))

        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="待機中: スイッチをONにすると変換が有効になります",
            font=ctk.CTkFont(size=12),
            text_color="gray",
            anchor="w",
        )
        self.status_label.pack(fill="x", padx=12, pady=8)

    def _build_preset_tab(self):
        # プリセット1: 有効桁数・小数丸め
        self.rule_round_var = ctk.BooleanVar(value=True)
        chk_round = ctk.CTkCheckBox(
            self.tab_preset,
            text="数値 / パーセントの小数点丸め",
            variable=self.rule_round_var,
        )
        chk_round.pack(anchor="w", padx=12, pady=(12, 4))

        round_opt_frame = ctk.CTkFrame(self.tab_preset, fg_color="transparent")
        round_opt_frame.pack(fill="x", padx=32, pady=(0, 12))

        ctk.CTkLabel(round_opt_frame, text="小数点以下桁数:").pack(
            side="left", padx=(0, 8)
        )
        self.round_digits_entry = ctk.CTkEntry(round_opt_frame, width=60)
        self.round_digits_entry.insert(0, "2")
        self.round_digits_entry.pack(side="left")

        # プリセット2: カラム抽出
        self.rule_col_var = ctk.BooleanVar(value=False)
        chk_col = ctk.CTkCheckBox(
            self.tab_preset,
            text="特定列の抽出 (複数行対応)",
            variable=self.rule_col_var,
        )
        chk_col.pack(anchor="w", padx=12, pady=(8, 4))

        col_opt_frame = ctk.CTkFrame(self.tab_preset, fg_color="transparent")
        col_opt_frame.pack(fill="x", padx=32, pady=(0, 12))

        ctk.CTkLabel(col_opt_frame, text="区切り:").grid(
            row=0, column=0, sticky="w", pady=4
        )
        self.col_delim_entry = ctk.CTkEntry(col_opt_frame, width=60)
        self.col_delim_entry.insert(0, ",")
        self.col_delim_entry.grid(row=0, column=1, sticky="w", padx=8, pady=4)

        ctk.CTkLabel(
            col_opt_frame, text="抽出列番号 (1始まり、カンマ区切り):"
        ).grid(row=1, column=0, sticky="w", pady=4)
        self.col_indices_entry = ctk.CTkEntry(col_opt_frame, width=120)
        self.col_indices_entry.insert(0, "1, -1")
        self.col_indices_entry.grid(row=1, column=1, sticky="w", padx=8, pady=4)

    def _build_programmable_tab(self):
        desc = (
            "入力パターンと出力テンプレートを変数名で指定します。\n"
            "例: 入力「a,b,c,d,e」 出力「{e}, {b}, {c}, {d}, {a}」\n"
            "入力データがルールに合わない場合は自動でスキップされます。"
        )
        ctk.CTkLabel(
            self.tab_programmable,
            text=desc,
            justify="left",
            text_color="gray70",
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w", padx=12, pady=8)

        # 区切り文字
        sep_frame = ctk.CTkFrame(self.tab_programmable, fg_color="transparent")
        sep_frame.pack(fill="x", padx=12, pady=4)
        ctk.CTkLabel(sep_frame, text="区切り文字:").pack(side="left", padx=(0, 8))
        self.prog_delim_entry = ctk.CTkEntry(sep_frame, width=80)
        self.prog_delim_entry.insert(0, ",")
        self.prog_delim_entry.pack(side="left")

        # 入力フォーマット（変数リスト）
        ctk.CTkLabel(
            self.tab_programmable, text="入力フォーマット（変数名定義）:"
        ).pack(anchor="w", padx=12, pady=(8, 2))
        self.prog_input_entry = ctk.CTkEntry(self.tab_programmable)
        self.prog_input_entry.insert(0, "a, b, c, d, e")
        self.prog_input_entry.pack(fill="x", padx=12, pady=(0, 8))

        # 出力フォーマット
        ctk.CTkLabel(
            self.tab_programmable, text="出力テンプレート（{変数名}で指定）:"
        ).pack(anchor="w", padx=12, pady=(8, 2))
        self.prog_output_entry = ctk.CTkEntry(self.tab_programmable)
        self.prog_output_entry.insert(0, "{e}, {b}, {c}, {d}, {a}")
        self.prog_output_entry.pack(fill="x", padx=12, pady=(0, 12))

    # --- 動作ロジック ---

    def _on_switch_toggled(self):
        self.is_active = self.switch_var.get()
        state = "有効" if self.is_active else "無効"
        self._update_status(f"ステータス: 自動変換は {state} です", "normal")

    def toggle_active_via_hotkey(self):
        # pynput のリスナースレッドから安全にGUIスレッドへ反映
        self.after(
            0,
            lambda: [
                self.switch_var.set(not self.switch_var.get()),
                self._on_switch_toggled(),
            ],
        )

    def _update_status(self, message: str, level: str = "normal"):
        color = "gray"
        if level == "success":
            color = "#4CAF50"
        elif level == "skip":
            color = "#FF9800"
        elif level == "error":
            color = "#F44336"

        self.status_label.configure(text=message, text_color=color)

    def _start_global_hotkey(self):
        def for_canonical(f):
            return lambda k: f(l.canonical(k))

        # Hotkey: Ctrl + Alt + X
        hotkey_dict = {"<ctrl>+<alt>+x": self.toggle_active_via_hotkey}
        listener = keyboard.GlobalHotKeys(hotkey_dict)
        listener_thread = threading.Thread(target=listener.start, daemon=True)
        listener_thread.start()

    def _start_clipboard_monitor(self):
        def poll():
            if self.is_active:
                self._process_clipboard()
            self.after(200, poll)

        self.after(200, poll)

    def _process_clipboard(self):
        try:
            content = pyperclip.paste()
        except Exception:
            return

        # 前回の内容、または自分が書き込んだ直後のテキストはスキップ
        if (
            not content
            or content == self.last_clipboard
            or content == self.last_written
        ):
            return

        self.last_clipboard = content
        current_tab = self.tabview.get()

        if current_tab == "定型ルールモード":
            new_text, msg, level = self._apply_preset(content)
        else:
            new_text, msg, level = self._apply_programmable(content)

        if new_text is not None and new_text != content:
            self.last_written = new_text
            pyperclip.copy(new_text)
            self._update_status(f"変換成功: {msg}", "success")
        elif level == "skip":
            self._update_status(f"スキップ: {msg}", "skip")

    # --- 変換エンジン ---

    def _apply_preset(self, text: str):
        transformed = text
        applied_rules = []

        # 1. 小数点丸め (例: 95.2251% -> 95.22%)
        if self.rule_round_var.get():
            try:
                digits = int(self.round_digits_entry.get().strip())

                def repl(match):
                    num = float(match.group(1))
                    is_pct = match.group(2) or ""
                    return f"{num:.{digits}f}{is_pct}"

                pattern = r"([-+]?\d*\.\d+)(%)?"
                if re.search(pattern, transformed):
                    transformed = re.sub(pattern, repl, transformed)
                    applied_rules.append(f"小数{digits}桁丸め")
            except ValueError:
                pass

        # 2. 列抽出
        if self.rule_col_var.get():
            delim = self.col_delim_entry.get()
            raw_indices = self.col_indices_entry.get().split(",")
            try:
                # 1-based index (正なら index-1, 負ならそのまま)
                indices = []
                for idx in raw_indices:
                    i = int(idx.strip())
                    indices.append(i - 1 if i > 0 else i)

                lines = transformed.strip().splitlines()
                extracted_lines = []
                valid_line_count = 0
                for line in lines:
                    parts = [p.strip() for p in line.split(delim)]
                    try:
                        extracted = [parts[i] for i in indices]
                        extracted_lines.append(", ".join(extracted))
                        valid_line_count += 1
                    except IndexError:
                        extracted_lines.append(line)

                if valid_line_count > 0:
                    transformed = "\n".join(extracted_lines)
                    applied_rules.append("列抽出")
            except ValueError:
                pass

        if applied_rules:
            return transformed, ", ".join(applied_rules), "normal"
        return None, "適用可能な定型ルールがありません", "skip"

    def _apply_programmable(self, text: str):
        delim = self.prog_delim_entry.get()
        raw_vars = [
            v.strip() for v in self.prog_input_entry.get().split(delim) if v.strip()
        ]
        template = self.prog_output_entry.get()

        if not raw_vars:
            return None, "入力フォーマットが空です", "skip"

        # 複数行の場合は1行ずつ処理
        lines = text.strip().splitlines()
        result_lines = []

        for line_num, line in enumerate(lines, 1):
            parts = [p.strip() for p in line.split(delim)]
            if len(parts) != len(raw_vars):
                return (
                    None,
                    f"{line_num}行目の要素数が一致しません (期待: {len(raw_vars)}, 実際: {len(parts)})",
                    "skip",
                )

            var_map = dict(zip(raw_vars, parts))
            try:
                # {var} 形式の置換
                formatted = template.format_map(var_map)
                result_lines.append(formatted)
            except KeyError as e:
                return None, f"未定義の変数があります: {e}", "skip"

        return "\n".join(result_lines), "変数テンプレート適用完了", "normal"


if __name__ == "__main__":
    app = ClipboardTransformerApp()
    app.mainloop()