"""クリップボード監視およびループ防止制御モジュール。"""

import hashlib
import logging
from typing import Callable, Optional
import pyperclip

logger = logging.getLogger(__name__)


class ClipboardMonitor:
    """クリップボードの変更を監視し、新規テキストの検知・自作書き換えループ防止を行うクラス。

    Parameters
    ----------
    on_change_callback : Optional[Callable[[str], None]], optional
        新しいテキストが検知された際に呼び出されるコールバック関数。デフォルトは None。

    Notes
    -----
    - 自プロセスがクリップボードを上書きした際、同一テキストを再検知して無限ループに陥ることを防ぎます。
    - OSのクリップボードロック競合時の例外は握りつぶして次回ポーリング時に再試行します。
    - 画像等の非テキストデータは安全にスキップされます。
    """

    def __init__(self, on_change_callback: Optional[Callable[[str], None]] = None):
        """ClipboardMonitor を初期化する。

        Parameters
        ----------
        on_change_callback : Optional[Callable[[str], None]], optional
            新規クリップボードテキスト検知時のコールバック。デフォルトは None。
        """
        self.on_change_callback = on_change_callback
        self._last_read_hash: Optional[str] = None
        self._last_written_hash: Optional[str] = None
        self._last_read_text: str = ""
        self._last_original_text: Optional[str] = None

    @staticmethod
    def _compute_hash(text: str) -> str:
        """テキストのSHA-256ハッシュ値を計算する。

        Parameters
        ----------
        text : str
            ハッシュ計算対象のテキスト。

        Returns
        -------
        str
            SHA-256 16進数ハッシュ文字列。
        """
        return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()

    def record_written_text(self, text: str) -> None:
        """自プロセスがクリップボードに書き込んだテキストを記録し、次回検知ループを防止する。

        Parameters
        ----------
        text : str
            書き込んだテキスト。

        Returns
        -------
        None
        """
        h = self._compute_hash(text)
        self._last_written_hash = h
        self._last_read_hash = h
        self._last_read_text = text

    def check_clipboard(self) -> Optional[str]:
        """クリップボードの内容を1回チェックし、新規テキストがあれば取得する。

        Returns
        -------
        Optional[str]
            新しく検知されたテキスト。同一テキスト、自作書き込み、非テキスト、エラー時は None。

        Notes
        -----
        新規テキストが検知された場合、`on_change_callback` が設定されていれば実行されます。
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
        self._last_original_text = content
        # 書き込みキャッシュは新しいユーザーコピーによってリセット
        self._last_written_hash = None

        if self.on_change_callback:
            self.on_change_callback(content)

        return content

    def write_clipboard(self, text: str) -> bool:
        """クリップボードにテキストを書き込み、直前書き込みキャッシュを更新する。

        Parameters
        ----------
        text : str
            クリップボードへ書き込むテキスト。

        Returns
        -------
        bool
            書き込みに成功したかどうか。
        """
        try:
            self.record_written_text(text)
            pyperclip.copy(text)
            return True
        except Exception as e:
            logger.error("Failed to write to clipboard: %s", e)
            return False

    def undo(self) -> Optional[str]:
        """直前の変換前テキストをクリップボードに復元する。

        Returns
        -------
        Optional[str]
            復元された元のテキスト。復元対象が存在しない場合は None。
        """
        if not self._last_original_text:
            return None
        orig = self._last_original_text
        self._last_original_text = None
        if self.write_clipboard(orig):
            return orig
        return None

    def can_undo(self) -> bool:
        """元に戻せるテキストが存在するかどうかを判定する。

        Returns
        -------
        bool
            Undo 可能なテキストがキャッシュにあれば True、なければ False。
        """
        return bool(self._last_original_text)
