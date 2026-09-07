"""軽量トースト通知ウィンドウおよびステータス表示モジュール。"""

from typing import Optional
import customtkinter as ctk


class ToastNotification(ctk.CTkToplevel):
    """画面隅または親ウィンドウ上に一時表示される軽量トースト通知。

    CustomTkinter の CTkToplevel を用い、枠なしウィンドウとして一定時間表示後に自動消去される。
    """

    COLOR_MAP = {
        "success": ("#2E7D32", "#E8F5E9"),   # border/bg or accent
        "skip": ("#EF6C00", "#FFF3E0"),      # オレンジ
        "error": ("#C62828", "#FFEBEE"),     # 赤
        "info": ("#1565C0", "#E3F2FD"),      # 青
    }

    def __init__(
        self,
        parent: ctk.CTk,
        message: str,
        level: str = "info",
        duration_ms: int = 2500,
    ):
        """
        Args:
            parent: 親となるCTkウィンドウ。
            message: 表示する通知メッセージ。
            level: 通知レベル ('success', 'skip', 'error', 'info')。
            duration_ms: 通知を表示するミリ秒数。
        """
        super().__init__(parent)

        self.parent = parent
        self.duration_ms = duration_ms

        # ウィンドウ装飾を取り払い、常に最前面
        self.overrideredirect(True)
        self.attributes("-topmost", True)

        accent_color, light_bg = self.COLOR_MAP.get(level, self.COLOR_MAP["info"])

        # コンテナフレーム
        self.container = ctk.CTkFrame(
            self,
            corner_radius=8,
            border_width=2,
            border_color=accent_color,
            fg_color=("gray95", "gray20"),
        )
        self.container.pack(fill="both", expand=True, padx=2, pady=2)

        icon = "ℹ️"
        if level == "success":
            icon = "✅"
        elif level == "skip":
            icon = "⚠️"
        elif level == "error":
            icon = "❌"

        self.label = ctk.CTkLabel(
            self.container,
            text=f"{icon} {message}",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=accent_color,
            wraplength=360,
            justify="left",
        )
        self.label.pack(padx=16, pady=10)

        # ウィンドウ位置を親ウィンドウの中央下部に配置
        self._position_toast()

        # 指定時間後に消去
        self.after(self.duration_ms, self._dismiss)

    def _position_toast(self) -> None:
        """親ウィンドウの下部中央にトーストを配置する。"""
        self.update_idletasks()
        req_width = self.winfo_reqwidth()
        req_height = self.winfo_reqheight()

        try:
            parent_x = self.parent.winfo_rootx()
            parent_y = self.parent.winfo_rooty()
            parent_w = self.parent.winfo_width()
            parent_h = self.parent.winfo_height()

            pos_x = parent_x + (parent_w - req_width) // 2
            pos_y = parent_y + parent_h - req_height - 60
        except Exception:
            # 親ウィンドウ座標取得失敗時は画面中央下部
            screen_w = self.winfo_screenwidth()
            screen_h = self.winfo_screenheight()
            pos_x = (screen_w - req_width) // 2
            pos_y = screen_h - req_height - 100

        self.geometry(f"+{pos_x}+{pos_y}")

    def _dismiss(self) -> None:
        """トーストを破棄する。"""
        try:
            self.destroy()
        except Exception:
            pass


def show_toast(
    parent: ctk.CTk,
    message: str,
    level: str = "info",
    duration_ms: int = 2500,
) -> Optional[ToastNotification]:
    """トースト通知を表示するヘルパー関数。安全に例外をハンドリングする。"""
    try:
        return ToastNotification(parent, message, level=level, duration_ms=duration_ms)
    except Exception:
        return None
