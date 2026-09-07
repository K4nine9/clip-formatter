"""区切り文字を安全・直感的に選択・指定するための共通UIコンポーネント。"""

from typing import Callable, Optional
import customtkinter as ctk


class DelimiterSelector(ctk.CTkFrame):
    """基本記号（カンマ、タブ、空白、コロン等）のドロップダウンおよびカスタム入力フレーム。"""

    DELIM_MAP = {
        "カンマ (,)": ",",
        "タブ (\\t)": "\t",
        "半角スペース ( )": " ",
        "全角スペース (　)": "　",
        "コロン (:)": ":",
        "セミコロン (;)": ";",
        "ピリオド (.)": ".",
        "その他 (カスタム)": "__custom__",
    }

    REVERSE_MAP = {v: k for k, v in DELIM_MAP.items() if v != "__custom__"}

    def __init__(
        self,
        master,
        default_delimiter: str = ",",
        on_changed: Optional[Callable[[str], None]] = None,
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.on_changed = on_changed

        self.opt_menu = ctk.CTkOptionMenu(
            self,
            values=list(self.DELIM_MAP.keys()),
            width=140,
            command=self._on_option_selected,
        )
        self.opt_menu.pack(side="left", padx=(0, 8))

        self.custom_entry = ctk.CTkEntry(self, width=60, placeholder_text="文字")
        self.custom_entry.pack(side="left")

        self.set_delimiter(default_delimiter)

    def _on_option_selected(self, choice: str) -> None:
        if choice == "その他 (カスタム)":
            self.custom_entry.configure(state="normal")
            self.custom_entry.focus()
        else:
            self.custom_entry.configure(state="disabled")

        if self.on_changed:
            self.on_changed(self.get_delimiter())

    def get_delimiter(self) -> str:
        """現在選択・入力されている区切り文字列を返す。"""
        choice = self.opt_menu.get()
        if choice == "その他 (カスタム)":
            val = self.custom_entry.get()
            return val if val else ","
        return self.DELIM_MAP.get(choice, ",")

    def set_delimiter(self, delim: str) -> None:
        """外部から区切り文字を設定してUIを同期する。"""
        if delim in self.REVERSE_MAP:
            label = self.REVERSE_MAP[delim]
            self.opt_menu.set(label)
            self.custom_entry.delete(0, "end")
            self.custom_entry.configure(state="disabled")
        else:
            self.opt_menu.set("その他 (カスタム)")
            self.custom_entry.configure(state="normal")
            self.custom_entry.delete(0, "end")
            self.custom_entry.insert(0, delim)

    def configure_state(self, state: str) -> None:
        """コンポーネント全体の活性 (normal) / 非活性 (disabled) を切り替える。"""
        self.opt_menu.configure(state=state)
        if state == "disabled":
            self.custom_entry.configure(state="disabled")
        else:
            if self.opt_menu.get() == "その他 (カスタム)":
                self.custom_entry.configure(state="normal")
            else:
                self.custom_entry.configure(state="disabled")
