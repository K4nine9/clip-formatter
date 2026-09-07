"""tests/test_config.py: 設定永続化の単体テスト"""

import json
import tempfile
import unittest
from pathlib import Path

from app.config import AppConfig, load_config, save_config


class TestConfig(unittest.TestCase):
    """設定読み書きのテスト"""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = Path(self.temp_dir.name) / "config.json"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_load_default_when_missing(self):
        cfg = load_config(self.config_path)
        self.assertEqual(cfg.round_digits, 2)
        self.assertFalse(cfg.is_active)
        self.assertEqual(cfg.hotkey, "<ctrl>+<alt>+x")

    def test_save_and_reload(self):
        cfg = AppConfig(
            is_active=True,
            active_tab="プログラマブルモード",
            round_digits=4,
            col_indices="2, 3",
            prog_delimiter="\t",
        )
        self.assertTrue(save_config(cfg, self.config_path))
        self.assertTrue(self.config_path.exists())

        loaded = load_config(self.config_path)
        self.assertTrue(loaded.is_active)
        self.assertEqual(loaded.active_tab, "プログラマブルモード")
        self.assertEqual(loaded.round_digits, 4)
        self.assertEqual(loaded.col_indices, "2, 3")
        self.assertEqual(loaded.prog_delimiter, "\t")

    def test_load_corrupted_file_falls_back_to_default(self):
        with open(self.config_path, "w", encoding="utf-8") as f:
            f.write("invalid json content")

        loaded = load_config(self.config_path)
        self.assertIsInstance(loaded, AppConfig)
        self.assertEqual(loaded.round_digits, 2)


if __name__ == "__main__":
    unittest.main()
