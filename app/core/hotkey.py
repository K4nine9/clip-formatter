"""pynput を利用したグローバルホットキー監視モジュール。"""

import logging
import threading
from typing import Callable, Optional
from pynput import keyboard

logger = logging.getLogger(__name__)


class GlobalHotkeyListener:
    """システム全体のキーボード入力を監視し、指定ホットキーでコールバックを実行するリスナー。

    Parameters
    ----------
    hotkey_str : str, optional
        トグル用ホットキー文字列（例: '<ctrl>+<alt>+x'）。デフォルトは '<ctrl>+<alt>+x'。
    on_triggered_callback : Optional[Callable[[], None]], optional
        トグル押下時に呼び出すコールバック関数。デフォルトは None。
    undo_hotkey_str : Optional[str], optional
        Undo用ホットキー文字列（例: '<ctrl>+<alt>+z'）。デフォルトは '<ctrl>+<alt>+z'。
    on_undo_callback : Optional[Callable[[], None]], optional
        Undo押下時に呼び出すコールバック関数。デフォルトは None。
    """

    DEFAULT_HOTKEY = "<ctrl>+<alt>+x"
    DEFAULT_UNDO_HOTKEY = "<ctrl>+<alt>+z"

    def __init__(
        self,
        hotkey_str: str = DEFAULT_HOTKEY,
        on_triggered_callback: Optional[Callable[[], None]] = None,
        undo_hotkey_str: Optional[str] = DEFAULT_UNDO_HOTKEY,
        on_undo_callback: Optional[Callable[[], None]] = None,
    ):
        """GlobalHotkeyListener を初期化する。"""
        self.hotkey_str = hotkey_str
        self.on_triggered_callback = on_triggered_callback
        self.undo_hotkey_str = undo_hotkey_str
        self.on_undo_callback = on_undo_callback
        self._listener: Optional[keyboard.GlobalHotKeys] = None
        self._thread: Optional[threading.Thread] = None

    def _on_hotkey_activated(self) -> None:
        """トグル用ホットキーが検知されたときに実行される内部ハンドラ。

        Returns
        -------
        None
        """
        logger.info("Global hotkey triggered: %s", self.hotkey_str)
        if self.on_triggered_callback:
            try:
                self.on_triggered_callback()
            except Exception as e:
                logger.error("Error in hotkey callback: %s", e, exc_info=True)

    def _on_undo_activated(self) -> None:
        """Undo用ホットキーが検知されたときに実行される内部ハンドラ。

        Returns
        -------
        None
        """
        logger.info("Global undo hotkey triggered: %s", self.undo_hotkey_str)
        if self.on_undo_callback:
            try:
                self.on_undo_callback()
            except Exception as e:
                logger.error("Error in undo hotkey callback: %s", e, exc_info=True)

    def start(self) -> None:
        """ホットキーリスナーをバックグラウンドスレッドで起動する。

        Returns
        -------
        None
        """
        if self._listener is not None:
            logger.warning("Hotkey listener is already running.")
            return

        try:
            hotkey_mapping = {self.hotkey_str: self._on_hotkey_activated}
            if self.undo_hotkey_str and self.on_undo_callback:
                hotkey_mapping[self.undo_hotkey_str] = self._on_undo_activated

            self._listener = keyboard.GlobalHotKeys(hotkey_mapping)
            self._thread = threading.Thread(
                target=self._listener.run, daemon=True, name="GlobalHotkeyListenerThread"
            )
            self._thread.start()
            logger.info("Started global hotkey listener for '%s'", list(hotkey_mapping.keys()))
        except Exception as e:
            logger.error("Failed to start hotkey listener: %s", e)
            self._listener = None

    def stop(self) -> None:
        """ホットキーリスナーを安全に停止する。

        Returns
        -------
        None
        """
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception as e:
                logger.error("Error stopping hotkey listener: %s", e)
            finally:
                self._listener = None
                self._thread = None
                logger.info("Stopped global hotkey listener.")
