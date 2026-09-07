"""tests/test_monitor.py: ClipboardMonitor および Undo 機能の単体テスト"""

import unittest
from unittest.mock import patch

from app.core.monitor import ClipboardMonitor


class TestClipboardMonitor(unittest.TestCase):
    """ClipboardMonitor の検知および Undo 機能のテスト"""

    def setUp(self):
        """テスト用の ClipboardMonitor インスタンスを初期化する。

        Returns
        -------
        None
        """
        self.monitor = ClipboardMonitor()

    @patch("pyperclip.paste")
    @patch("pyperclip.copy")
    def test_detection_and_undo(self, mock_copy, mock_paste):
        """クリップボード変更の検知、書き込み、および Undo 操作による元テキスト復元を検証する。

        Parameters
        ----------
        mock_copy : MagicMock
            pyperclip.copy のモックオブジェクト。
        mock_paste : MagicMock
            pyperclip.paste のモックオブジェクト。

        Returns
        -------
        None
        """
        # 1. ユーザーがテキストをコピーしたとシミュレート
        mock_paste.return_value = "元のテキスト Original Text"
        read_text = self.monitor.check_clipboard()
        self.assertEqual(read_text, "元のテキスト Original Text")
        self.assertTrue(self.monitor.can_undo())

        # 2. アプリが変換後テキストを書き込み
        self.monitor.write_clipboard("変換後テキスト Transformed Text")
        mock_copy.assert_called_with("変換後テキスト Transformed Text")

        # 3. Undoを実行
        restored = self.monitor.undo()
        self.assertEqual(restored, "元のテキスト Original Text")
        mock_copy.assert_called_with("元のテキスト Original Text")

        # 4. Undo後は元に戻す対象がクリアされる
        self.assertFalse(self.monitor.can_undo())
        self.assertIsNone(self.monitor.undo())


if __name__ == "__main__":
    unittest.main()
