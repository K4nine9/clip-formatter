"""ProgrammableTabFrame の初期化・設定ロード・トランスフォーマー生成テスト。"""

import unittest
from unittest.mock import MagicMock
import customtkinter as ctk

from app.config import AppConfig
from app.transformers.pattern import PatternTransformer
from app.transformers.python_exec import PythonScriptTransformer
from app.transformers.template import TemplateTransformer
from app.ui.components.programmable_tab import ProgrammableTabFrame


class TestProgrammableTabFrame(unittest.TestCase):
    """ProgrammableTabFrame のロジックテスト（UI要素の生成・トランスフォーマー生成）。"""

    @classmethod
    def setUpClass(cls):
        """テストクラス全体の初期化を行い、ヘッドレス環境でのTkinterインスタンスを生成する。

        Returns
        -------
        None
        """
        # ヘッドレス環境での Tkinter 初期化テスト
        try:
            cls.root = ctk.CTk()
            cls.root.withdraw()
        except Exception:
            cls.root = None

    @classmethod
    def tearDownClass(cls):
        """テストクラス全体の終了処理を行い、Tkinterインスタンスを破棄する。

        Returns
        -------
        None
        """
        if cls.root:
            cls.root.destroy()

    def setUp(self):
        """各テストケース実行前の事前準備を行い、GUIが利用不可の場合はスキップする。

        Returns
        -------
        None
        """
        if not self.root:
            self.skipTest("GUI display not available")
        self.config = AppConfig()

    def test_get_transformer_pattern_mode(self):
        """パターン置換モードで正しく PatternTransformer が生成されることを検証する。

        Returns
        -------
        None
        """
        self.config.prog_mode = "pattern"
        self.config.prog_pattern_input = "私は{a}時間"
        self.config.prog_pattern_output = "私は{a}分"
        frame = ProgrammableTabFrame(self.root, self.config)

        transformer = frame.get_transformer()
        self.assertIsInstance(transformer, PatternTransformer)
        res = transformer.transform("私は2時間")
        self.assertTrue(res.success)
        self.assertEqual(res.text, "私は2分")

    def test_get_transformer_delimiter_mode(self):
        """区切り文字モードで正しく TemplateTransformer が生成されることを検証する。

        Returns
        -------
        None
        """
        self.config.prog_mode = "delimiter"
        self.config.prog_delimiter = ","
        self.config.prog_input_vars = "a, b"
        self.config.prog_output_template = "{b}-{a}"
        frame = ProgrammableTabFrame(self.root, self.config)

        transformer = frame.get_transformer()
        self.assertIsInstance(transformer, TemplateTransformer)
        res = transformer.transform("foo, bar")
        self.assertTrue(res.success)
        self.assertEqual(res.text, "bar-foo")

    def test_get_transformer_script_mode_pattern(self):
        """スクリプトモード（パターン入力）で PythonScriptTransformer が正しく生成されることを検証する。

        Returns
        -------
        None
        """
        self.config.prog_mode = "script"
        self.config.prog_script_input_mode = "pattern"
        self.config.prog_script_pattern = "単価{price}円、数量{qty}個"
        self.config.prog_script_code = "result = f'{int(price) * int(qty)}円'"
        frame = ProgrammableTabFrame(self.root, self.config)

        transformer = frame.get_transformer()
        self.assertIsInstance(transformer, PythonScriptTransformer)
        res = transformer.transform("単価200円、数量3個")
        self.assertTrue(res.success)
        self.assertEqual(res.text, "600円")

    def test_get_transformer_script_mode_full_text(self):
        """スクリプトモード（全文入力）で PythonScriptTransformer が正しく生成されることを検証する。

        Returns
        -------
        None
        """
        self.config.prog_mode = "script"
        self.config.prog_script_input_mode = "full_text"
        self.config.prog_script_code = "result = f'行数: {len(lines)}'"
        frame = ProgrammableTabFrame(self.root, self.config)

        transformer = frame.get_transformer()
        self.assertIsInstance(transformer, PythonScriptTransformer)
        res = transformer.transform("line1\nline2\nline3")
        self.assertTrue(res.success)
        self.assertEqual(res.text, "行数: 3")

    def test_sample_insertion(self):
        """サンプルスクリプト選択時にエディタへサンプルコードが正しく挿入されることを検証する。

        Returns
        -------
        None
        """
        frame = ProgrammableTabFrame(self.root, self.config)
        sample_key = "四則演算・金額計算"
        frame._on_sample_selected(sample_key)
        code = frame.script_textbox.get("1.0", "end-1c")
        self.assertIn("total", code)
        self.assertIn("result", code)


if __name__ == "__main__":
    unittest.main()
