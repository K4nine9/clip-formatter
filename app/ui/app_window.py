"""CustomTkinter を用いた ClipFormatter のメインウィンドウモジュール。"""

import logging
from typing import Optional
import customtkinter as ctk

from app.config import AppConfig, DEFAULT_CONFIG_PATH, load_config, save_config
from app.core.hotkey import GlobalHotkeyListener
from app.core.monitor import ClipboardMonitor
from app.transformers.base import TransformResult
from app.ui.components.latex_tab import LatexTabFrame
from app.ui.components.preset_tab import PresetTabFrame
from app.ui.components.programmable_tab import ProgrammableTabFrame
from app.ui.toast import show_toast

logger = logging.getLogger(__name__)

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class ClipboardTransformerApp(ctk.CTk):
    """ClipFormatter デスクトップアプリケーションのメインウィンドウ。"""

    TAB_PRESET = "定型ルールモード"
    TAB_PROGRAMMABLE = "プログラマブルモード"
    TAB_LATEX = "LaTeXモード"

    def __init__(self, config_path=DEFAULT_CONFIG_PATH):
        super().__init__()

        self.config_path = config_path
        self.config: AppConfig = load_config(self.config_path)

        self.title("ClipFormatter")
        self.geometry("600x700")
        self.minsize(540, 620)

        # 内部状態
        self.is_active = self.config.is_active

        # クリップボード監視 & ホットキーリスナーの初期化
        self.monitor = ClipboardMonitor()
        self.hotkey_listener = GlobalHotkeyListener(
            hotkey_str=self.config.hotkey,
            on_triggered_callback=self._toggle_active_from_hotkey,
        )

        self._build_ui()
        self._start_services()

        # 終了イベントのフック
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _build_ui(self) -> None:
        """GUIレイアウトを構築する。"""
        # 1. プリセット管理バー
        preset_bar = ctk.CTkFrame(self)
        preset_bar.pack(fill="x", padx=16, pady=(12, 4))

        ctk.CTkLabel(
            preset_bar,
            text="プリセット:",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(side="left", padx=(12, 6), pady=8)

        preset_names = self.config.get_preset_names()
        cur_preset = self.config.current_preset
        if cur_preset not in preset_names and preset_names:
            cur_preset = preset_names[0]

        self.preset_menu = ctk.CTkOptionMenu(
            preset_bar,
            values=preset_names,
            width=160,
            command=self._on_preset_selected,
        )
        self.preset_menu.set(cur_preset)
        self.preset_menu.pack(side="left", padx=(0, 8), pady=8)

        self.btn_save_preset = ctk.CTkButton(
            preset_bar,
            text="上書き保存",
            width=65,
            command=self._on_save_preset_clicked,
        )
        self.btn_save_preset.pack(side="left", padx=(0, 6), pady=8)

        self.btn_new_preset = ctk.CTkButton(
            preset_bar,
            text="＋新規保存",
            width=65,
            command=self._on_new_preset_clicked,
        )
        self.btn_new_preset.pack(side="left", padx=(0, 6), pady=8)

        self.btn_delete_preset = ctk.CTkButton(
            preset_bar,
            text="削除",
            width=45,
            fg_color="#C62828",
            hover_color="#B71C1C",
            command=self._on_delete_preset_clicked,
        )
        self.btn_delete_preset.pack(side="left", padx=(0, 10), pady=8)

        # 2. ヘッダーフレーム（有効/無効トグル）
        self.header_frame = ctk.CTkFrame(self)
        self.header_frame.pack(fill="x", padx=16, pady=(4, 6))

        self.switch_var = ctk.BooleanVar(value=self.is_active)
        self.toggle_switch = ctk.CTkSwitch(
            self.header_frame,
            text=f"自動変換を有効化 (Hotkey: {self.config.hotkey.upper().replace('<', '').replace('>', '')})",
            font=ctk.CTkFont(size=13, weight="bold"),
            variable=self.switch_var,
            command=self._on_switch_toggled,
        )
        self.toggle_switch.pack(side="left", padx=14, pady=10)

        # 3. タブビュー
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=16, pady=6)

        tab_preset_container = self.tabview.add(self.TAB_PRESET)
        tab_prog_container = self.tabview.add(self.TAB_PROGRAMMABLE)
        tab_latex_container = self.tabview.add(self.TAB_LATEX)

        # タブコンポーネントの配置
        self.preset_tab = PresetTabFrame(tab_preset_container, config=self.config)
        self.preset_tab.pack(fill="both", expand=True)

        self.programmable_tab = ProgrammableTabFrame(tab_prog_container, config=self.config)
        self.programmable_tab.pack(fill="both", expand=True)

        self.latex_tab = LatexTabFrame(tab_latex_container, config=self.config)
        self.latex_tab.pack(fill="both", expand=True)

        # 保存されていたタブの復元
        valid_tabs = [self.TAB_PRESET, self.TAB_PROGRAMMABLE, self.TAB_LATEX]
        if self.config.active_tab in valid_tabs:
            try:
                self.tabview.set(self.config.active_tab)
            except Exception:
                pass

        # 4. ステータスバー
        self.status_frame = ctk.CTkFrame(self)
        self.status_frame.pack(fill="x", padx=16, pady=(6, 14))

        initial_msg = (
            "待機中: クリップボードの変更を監視しています"
            if self.is_active
            else "待機中: スイッチをONにすると変換が有効になります"
        )
        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text=initial_msg,
            font=ctk.CTkFont(size=12),
            text_color="gray",
            anchor="w",
        )
        self.status_label.pack(fill="x", padx=12, pady=8)

    def _sync_all_tabs_to_config(self) -> None:
        """現在の各タブの入力値を config オブジェクトへ同期する。"""
        self.config.is_active = self.switch_var.get()
        try:
            self.config.active_tab = self.tabview.get()
        except Exception:
            pass

        self.preset_tab.save_to_config(self.config)
        self.programmable_tab.save_to_config(self.config)
        self.latex_tab.save_to_config(self.config)

    def _sync_all_tabs_from_config(self) -> None:
        """config オブジェクトの値を各タブのUIへ反映する。"""
        self.preset_tab.load_from_config(self.config)
        self.programmable_tab.load_from_config(self.config)
        self.latex_tab.load_from_config(self.config)
        try:
            self.tabview.set(self.config.active_tab)
        except Exception:
            pass

    def _update_preset_menu(self) -> None:
        """プリセットドロップダウンの選択肢一覧を最新化する。"""
        names = self.config.get_preset_names()
        self.preset_menu.configure(values=names)
        if self.config.current_preset in names:
            self.preset_menu.set(self.config.current_preset)

    def _on_preset_selected(self, choice: str) -> None:
        """プリセットがドロップダウンで選択されたときの処理。"""
        # 現在の変更を保存してから切り替え
        self._sync_all_tabs_to_config()
        if self.config.load_from_preset(choice):
            self._sync_all_tabs_from_config()
            self._update_status(f"プリセット「{choice}」を読み込みました", level="normal")

    def _on_save_preset_clicked(self) -> None:
        """現在の設定を現在選択中のプリセットに上書き保存する。"""
        self._sync_all_tabs_to_config()
        cur = self.config.current_preset
        self.config.save_to_preset(cur)
        save_config(self.config, self.config_path)
        msg = f"プリセット「{cur}」を上書き保存しました"
        self._update_status(msg, level="success")
        show_toast(self, msg, level="success", duration_ms=2000)

    def _on_new_preset_clicked(self) -> None:
        """現在の設定を新しいプリセットとして保存する。"""
        dialog = ctk.CTkInputDialog(
            text="新しいプリセット名を入力してください:", title="プリセット新規作成"
        )
        new_name = dialog.get_input()
        if new_name and new_name.strip():
            name = new_name.strip()
            self._sync_all_tabs_to_config()
            self.config.save_to_preset(name)
            self._update_preset_menu()
            save_config(self.config, self.config_path)
            msg = f"プリセット「{name}」を新規作成しました"
            self._update_status(msg, level="success")
            show_toast(self, msg, level="success", duration_ms=2000)

    def _on_delete_preset_clicked(self) -> None:
        """現在選択中のプリセットを削除する。"""
        cur = self.config.current_preset
        names = self.config.get_preset_names()
        if len(names) <= 1:
            show_toast(self, "最後の1件のプリセットは削除できません", level="skip", duration_ms=2500)
            return

        if self.config.delete_preset(cur):
            self._update_preset_menu()
            self._sync_all_tabs_from_config()
            save_config(self.config, self.config_path)
            msg = f"プリセット「{cur}」を削除しました"
            self._update_status(msg, level="normal")
            show_toast(self, msg, level="normal", duration_ms=2000)

    def _start_services(self) -> None:
        """バックグラウンド監視サービスを開始する。"""
        self.hotkey_listener.start()
        self._schedule_clipboard_poll()

    def _schedule_clipboard_poll(self) -> None:
        """一定間隔でクリップボードをポーリングするタイマー。"""
        if self.is_active:
            self._process_clipboard()
        self.after(200, self._schedule_clipboard_poll)

    def _on_switch_toggled(self) -> None:
        """UIのトグルスイッチが切り替わったときのハンドラ。"""
        self.is_active = self.switch_var.get()
        self.config.is_active = self.is_active
        if self.is_active:
            self._update_status("自動変換を有効化しました（監視中）", level="success")
        else:
            self._update_status("自動変換を無効化しました", level="normal")

    def _toggle_active_from_hotkey(self) -> None:
        """グローバルホットキー押下時に安全にGUIスレッドでトグルする。"""
        self.after(
            0,
            lambda: [
                self.switch_var.set(not self.switch_var.get()),
                self._on_switch_toggled(),
            ],
        )

    def _update_status(self, message: str, level: str = "normal") -> None:
        """ステータスバーの表示色とテキストを更新する。"""
        color_map = {
            "normal": ("gray40", "gray70"),
            "success": ("#2E7D32", "#4CAF50"),
            "skip": ("#EF6C00", "#FFA726"),
            "error": ("#C62828", "#EF5350"),
        }
        color = color_map.get(level, color_map["normal"])
        self.status_label.configure(text=message, text_color=color)

    def _process_clipboard(self) -> None:
        """クリップボードの変更を検知し、適切なトランスフォーマーで変換を実行する。"""
        content = self.monitor.check_clipboard()
        if content is None:
            return

        current_tab = self.tabview.get()
        result: Optional[TransformResult] = None

        if current_tab == self.TAB_PRESET:
            transformer = self.preset_tab.get_transformer()
            if transformer is None:
                self._update_status("定型ルールが選択されていません", "skip")
                return
            result = transformer.transform(content)
        elif current_tab == self.TAB_LATEX:
            transformer = self.latex_tab.get_transformer()
            if transformer is None:
                self._update_status("LaTeX設定が未完了です", "skip")
                return
            result = transformer.transform(content)
        else:
            transformer = self.programmable_tab.get_transformer()
            if transformer is None:
                self._update_status("プログラマブル設定が未完了です", "skip")
                return
            result = transformer.transform(content)

        if result is None:
            return

        # 変換成功時
        if result.success and result.text is not None and result.text != content:
            self.monitor.write_clipboard(result.text)
            msg = f"変換完了: {result.message}"
            self._update_status(msg, "success")
            show_toast(self, msg, level="success", duration_ms=2000)

        # スキップ時
        elif result.status == "skip":
            msg = f"スキップ: {result.message}"
            self._update_status(msg, "skip")
            show_toast(self, msg, level="skip", duration_ms=3000)

        # エラー時
        elif result.status == "error":
            msg = f"エラー: {result.message}"
            self._update_status(msg, "error")
            show_toast(self, msg, level="error", duration_ms=3500)

    def _on_closing(self) -> None:
        """ウィンドウ終了時に設定を保存し、リスナーを安全に停止する。"""
        logger.info("Closing application...")

        self._sync_all_tabs_to_config()
        # カレントプリセットにも最新状態を反映して保存
        self.config.save_to_preset(self.config.current_preset)
        save_config(self.config, self.config_path)

        self.hotkey_listener.stop()
        self.destroy()
