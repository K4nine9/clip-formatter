"""クリップボード監視およびループ防止制御モジュール。"""

import hashlib
import logging
from typing import Callable, Optional
import pyperclip

logger = logging.getLogger(__name__)


class ClipboardMonitor:
    """クリップボードの変更を監視し、新規テキストの検知・自作書き換えループ防止を行うクラス。

    SPEC:
        - 自プロセスがクリップボードを上書きした際、同一テキストを再検知して無限ループに陥ることを防ぐ。
        - クリップボードのOSロック競合時は例外を握りつぶして次回に再試行。
        - テキスト以外のデータはスキップ。
    """

    def __init__(self, on_change_callback: Optional[Callable[[str], None]] = None):
        """
        Args:
            on_change_callback: 新しいテキストが検知された際に呼び出されるコールバック関数。
        """
        self.on_change_callback = on_change_callback
        self._last_read_hash: Optional[str] = None
        self._last_written_hash: Optional[str] = None
        self._last_read_text: str = ""

    @staticmethod
    def _compute_hash(text: str) -> str:
        """テキストのSHA-256ハッシュ値を計算する。"""
        return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()

    def record_written_text(self, text: str) -> None:
        """自プロセスがクリップボードに書き込んだテキストを記録し、次回検知ループを防止する。"""
        h = self._compute_hash(text)
        self._last_written_hash = h
        self._last_read_hash = h
        self._last_read_text = text

    def check_clipboard(self) -> Optional[str]:
        """クリップボードの内容を1回チェックする。

        新しいテキストが検知された場合、そのテキストを返し、コールバックが設定されていれば実行する。
        同一テキスト、自作書き込み、非テキスト、またはアクセスエラーの場合は None を返す。
        """
        try:
            content = pyperclip.paste()
        except Exception as e:
            # クリップボードのOSロック競合や非テキストデータによる例外は握りつぶして次回再試行
            logger.debug("Clipboard access error (suppressed): %s", e)
            return None

        if not content or not isinstance(content, str):
            return None

        content_hash = self._compute_hash(content)

        # 直前書き込みキャッシュ、または直前読み取りキャッシュと一致する場合はスキップ
        if content_hash == self._last_written_hash or content_hash == self._last_read_hash:
            return None

        # 新規テキスト検知
        self._last_read_hash = content_hash
        self._last_read_text = content
        # 書き込みキャッシュは新しいユーザーコピーによってリセット
        self._last_written_hash = None

        if self.on_change_callback:
            self.on_change_callback(content)

        return content

    def write_clipboard(self, text: str) -> bool:
        """クリップボードにテキストを書き込み、直前書き込みキャッシュを更新する。

        Returns:
            bool: 書き込みに成功したかどうか。
        """
        try:
            self.record_written_text(text)
            pyperclip.copy(text)
            return True
        except Exception as e:
            logger.error("Failed to write to clipboard: %s", e)
            return False
