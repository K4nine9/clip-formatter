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
            int_mode="pad",
            int_digits=5,
            dec_mode="pad",
            dec_digits=3,
            dec_overflow="truncate",
            col_indices="2, 3",
            prog_mode="pattern",
            prog_pattern_input="私は{a}時間で{b}つのりんご",
            prog_pattern_output="私は{b}時間で{a}つのりんご",
            prog_delimiter="\t",
        )
        self.assertTrue(save_config(cfg, self.config_path))
        self.assertTrue(self.config_path.exists())

        loaded = load_config(self.config_path)
        self.assertTrue(loaded.is_active)
        self.assertEqual(loaded.active_tab, "プログラマブルモード")
        self.assertEqual(loaded.int_mode, "pad")
        self.assertEqual(loaded.int_digits, 5)
        self.assertEqual(loaded.dec_mode, "pad")
        self.assertEqual(loaded.dec_digits, 3)
        self.assertEqual(loaded.dec_overflow, "truncate")
        self.assertEqual(loaded.col_indices, "2, 3")
        self.assertEqual(loaded.prog_mode, "pattern")
        self.assertEqual(loaded.prog_pattern_input, "私は{a}時間で{b}つのりんご")
        self.assertEqual(loaded.prog_pattern_output, "私は{b}時間で{a}つのりんご")
        self.assertEqual(loaded.prog_delimiter, "\t")

    def test_backward_compat_truncate_dec_mode(self):
        # 過去設定で dec_mode が "truncate" だった場合、dec_mode="round" かつ dec_overflow="truncate" に変換される
        old_data = {
            "is_active": False,
            "dec_mode": "truncate",
            "dec_digits": 4,
        }
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(old_data, f)

        loaded = load_config(self.config_path)
        self.assertEqual(loaded.dec_mode, "round")
        self.assertEqual(loaded.dec_overflow, "truncate")
        self.assertEqual(loaded.dec_digits, 4)

    def test_preset_operations(self):
        cfg = AppConfig()
        names = cfg.get_preset_names()
        self.assertIn("デフォルト", names)
        self.assertIn("LaTeX 表組み", names)

        # 現在の設定を変更して新しいプリセットとして保存
        cfg.int_mode = "pad"
        cfg.int_digits = 8
        cfg.save_to_preset("実験用")
        self.assertIn("実験用", cfg.get_preset_names())
        self.assertEqual(cfg.current_preset, "実験用")

        # 別のプリセットをロード
        cfg.load_from_preset("デフォルト")
        self.assertEqual(cfg.current_preset, "デフォルト")
        self.assertEqual(cfg.int_mode, "none")

        # 戻す
        cfg.load_from_preset("実験用")
        self.assertEqual(cfg.int_mode, "pad")
        self.assertEqual(cfg.int_digits, 8)

        # 削除
        self.assertTrue(cfg.delete_preset("実験用"))
        self.assertNotIn("実験用", cfg.get_preset_names())

    def test_latex_config_save_reload(self):
        cfg = AppConfig(
            active_tab="LaTeXモード",
            latex_mode="table",
            latex_table_delim="\t",
            latex_table_style="markdown",
            latex_table_highlight="max",
            latex_formula_direction="latex_to_plain",
            unwrap_enabled=True,
            hotkey_undo="<ctrl>+<alt>+u",
            close_to_tray=False,
        )
        self.assertTrue(save_config(cfg, self.config_path))
        loaded = load_config(self.config_path)
        self.assertEqual(loaded.active_tab, "LaTeXモード")
        self.assertEqual(loaded.latex_mode, "table")
        self.assertEqual(loaded.latex_table_delim, "\t")
        self.assertEqual(loaded.latex_table_style, "markdown")
        self.assertEqual(loaded.latex_table_highlight, "max")
        self.assertEqual(loaded.latex_formula_direction, "latex_to_plain")
        self.assertTrue(loaded.unwrap_enabled)
        self.assertEqual(loaded.hotkey_undo, "<ctrl>+<alt>+u")
        self.assertFalse(loaded.close_to_tray)

    def test_load_corrupted_file_falls_back_to_default(self):
        with open(self.config_path, "w", encoding="utf-8") as f:
            f.write("invalid json content")

        loaded = load_config(self.config_path)
        self.assertIsInstance(loaded, AppConfig)
        self.assertEqual(loaded.round_digits, 2)


if __name__ == "__main__":
    unittest.main()
