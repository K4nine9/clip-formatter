"""pystray を利用したシステムトレイ常駐管理モジュール。"""

import logging
import threading
from typing import TYPE_CHECKING, Optional
from PIL import Image, ImageDraw
import pystray

if TYPE_CHECKING:
    from app.ui.app_window import ClipboardTransformerApp

logger = logging.getLogger(__name__)


def create_tray_icon_image() -> Image.Image:
    """トレイ表示用のクリップボード風アイコン画像を生成する。"""
    width = 64
    height = 64
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # クリップボード本体（青紫色の角丸四角形）
    draw.rounded_rectangle(
        [(10, 14), (54, 58)],
        radius=6,
        fill=(30, 136, 229, 255),  # Material Blue
        outline=(21, 101, 192, 255),
        width=2,
    )

    # クリップ部分（上部の金具）
    draw.rounded_rectangle(
        [(22, 6), (42, 18)],
        radius=3,
        fill=(224, 224, 224, 255),
        outline=(117, 117, 117, 255),
        width=2,
    )

    # 用紙の線（テキストを模した白い横線）
    draw.line([(18, 26), (46, 26)], fill=(255, 255, 255, 240), width=3)
    draw.line([(18, 36), (46, 36)], fill=(255, 255, 255, 240), width=3)
    draw.line([(18, 46), (36, 46)], fill=(255, 255, 255, 240), width=3)

    return image


class SystemTrayManager:
    """システムトレイ（タスクトレイ）常駐とコンテキストメニューを管理するクラス。"""

    def __init__(self, app: "ClipboardTransformerApp"):
        self.app = app
        self._icon: Optional[pystray.Icon] = None
        self._thread: Optional[threading.Thread] = None

    def _create_menu(self) -> pystray.Menu:
        """トレイアイコンの右クリックメニューを構築する。"""
        return pystray.Menu(
            pystray.MenuItem(
                "ウィンドウを表示",
                self._on_show_window,
                default=True,
            ),
            pystray.MenuItem(
                "自動変換を有効化",
                self._on_toggle_active,
                checked=lambda item: self.app.is_active,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "終了",
                self._on_quit,
            ),
        )

    def _on_show_window(self, icon=None, item=None) -> None:
        """メインウィンドウを最前面に再表示する。"""
        self.app.after(0, self.app.show_window)

    def _on_toggle_active(self, icon=None, item=None) -> None:
        """トレイメニューから自動変換の有効/無効を切り替える。"""
        self.app.after(0, self.app.toggle_active)

    def _on_quit(self, icon=None, item=None) -> None:
        """アプリケーションを完全に終了する。"""
        logger.info("Quit requested from system tray.")
        self.stop()
        self.app.after(0, self.app.really_quit)

    def start(self) -> None:
        """システムトレイ常駐を開始する。"""
        if self._icon is not None:
            return

        try:
            image = create_tray_icon_image()
            menu = self._create_menu()
            self._icon = pystray.Icon(
                name="ClipFormatter",
                icon=image,
                title="ClipFormatter (クリップボード自動整形)",
                menu=menu,
            )
            # バックグラウンドスレッドで実行
            self._thread = threading.Thread(
                target=self._icon.run, daemon=True, name="SystemTrayThread"
            )
            self._thread.start()
            logger.info("System tray icon started.")
        except Exception as e:
            logger.error("Failed to start system tray icon: %s", e)
            self._icon = None

    def update_state(self) -> None:
        """アイコンのメニュー状態（チェック状態等）を更新する。"""
        if self._icon:
            self._icon.update_menu()

    def stop(self) -> None:
        """トレイアイコンを停止・消去する。"""
        if self._icon is not None:
            try:
                self._icon.stop()
            except Exception as e:
                logger.error("Error stopping tray icon: %s", e)
            finally:
                self._icon = None
                self._thread = None
                logger.info("System tray icon stopped.")
