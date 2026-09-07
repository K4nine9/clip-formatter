"""tests/test_monitor.py: クリップボード監視ロジックの単体テスト"""

import unittest
from unittest.mock import patch
from app.core.monitor import ClipboardMonitor


class TestClipboardMonitor(unittest.TestCase):
    """ClipboardMonitor のロジックテスト（pyperclip はモック）"""

    def setUp(self):
        self.received_texts = []
        self.monitor = ClipboardMonitor(
            on_change_callback=lambda t: self.received_texts.append(t)
        )

    @patch("pyperclip.paste")
    def test_new_text_detection(self, mock_paste):
        mock_paste.return_value = "hello world"
        result = self.monitor.check_clipboard()
        self.assertEqual(result, "hello world")
        self.assertEqual(self.received_texts, ["hello world"])

    @patch("pyperclip.paste")
    def test_duplicate_text_ignored(self, mock_paste):
        mock_paste.return_value = "same text"
        self.monitor.check_clipboard()
        self.received_texts.clear()

        # 同一テキストで再度チェック
        result = self.monitor.check_clipboard()
        self.assertIsNone(result)
        self.assertEqual(self.received_texts, [])

    @patch("pyperclip.paste")
    def test_self_written_loop_prevention(self, mock_paste):
        # 自プロセスが書き込んだ内容を記録
        self.monitor.record_written_text("transformed text")

        # その直後にクリップボードから同一内容が取得されてもスキップされる
        mock_paste.return_value = "transformed text"
        result = self.monitor.check_clipboard()
        self.assertIsNone(result)
        self.assertEqual(self.received_texts, [])

        # 別のテキストがコピーされたら検知される
        mock_paste.return_value = "new user text"
        result2 = self.monitor.check_clipboard()
        self.assertEqual(result2, "new user text")
        self.assertEqual(self.received_texts, ["new user text"])

    @patch("pyperclip.paste")
    def test_clipboard_exception_suppressed(self, mock_paste):
        mock_paste.side_effect = Exception("Clipboard locked by OS")
        result = self.monitor.check_clipboard()
        self.assertIsNone(result)
        self.assertEqual(self.received_texts, [])


if __name__ == "__main__":
    unittest.main()
