"""pynput を利用したグローバルホットキー監視モジュール。"""

import logging
import threading
from typing import Callable, Optional
from pynput import keyboard

logger = logging.getLogger(__name__)


class GlobalHotkeyListener:
    """システム全体のキーボード入力を監視し、指定ホットキーでコールバックを実行するリスナー。"""

    DEFAULT_HOTKEY = "<ctrl>+<alt>+x"

    def __init__(
        self,
        hotkey_str: str = DEFAULT_HOTKEY,
        on_triggered_callback: Optional[Callable[[], None]] = None,
    ):
        """
        Args:
            hotkey_str: pynput形式のホットキー文字列（例: '<ctrl>+<alt>+x'）。
            on_triggered_callback: ホットキー押下時に呼び出すコールバック関数。
        """
        self.hotkey_str = hotkey_str
        self.on_triggered_callback = on_triggered_callback
        self._listener: Optional[keyboard.GlobalHotKeys] = None
        self._thread: Optional[threading.Thread] = None

    def _on_hotkey_activated(self) -> None:
        """ホットキーが検知されたときに実行される内部メソッド。"""
        logger.info("Global hotkey triggered: %s", self.hotkey_str)
        if self.on_triggered_callback:
            try:
                self.on_triggered_callback()
            except Exception as e:
                logger.error("Error in hotkey callback: %s", e, exc_info=True)

    def start(self) -> None:
        """ホットキーリスナーをバックグラウンドスレッドで起動する。"""
        if self._listener is not None:
            logger.warning("Hotkey listener is already running.")
            return

        try:
            hotkey_mapping = {self.hotkey_str: self._on_hotkey_activated}
            self._listener = keyboard.GlobalHotKeys(hotkey_mapping)
            self._thread = threading.Thread(
                target=self._listener.run, daemon=True, name="GlobalHotkeyListenerThread"
            )
            self._thread.start()
            logger.info("Started global hotkey listener for '%s'", self.hotkey_str)
        except Exception as e:
            logger.error("Failed to start hotkey listener for '%s': %s", self.hotkey_str, e)
            self._listener = None

    def stop(self) -> None:
        """ホットキーリスナーを停止する。"""
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception as e:
                logger.error("Error stopping hotkey listener: %s", e)
            finally:
                self._listener = None
                self._thread = None
                logger.info("Stopped global hotkey listener.")
