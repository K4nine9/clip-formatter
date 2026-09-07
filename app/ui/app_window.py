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
from app.ui.tray import SystemTrayManager

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
        self.geometry("620x740")
        self.minsize(560, 640)

        # 内部状態
        self.is_active = self.config.is_active
        self._is_preview_expanded = False

        # クリップボード監視 & ホットキーリスナーの初期化
        self.monitor = ClipboardMonitor()
        self.hotkey_listener = GlobalHotkeyListener(
            hotkey_str=self.config.hotkey,
            on_triggered_callback=self._toggle_active_from_hotkey,
            undo_hotkey_str=self.config.hotkey_undo,
            on_undo_callback=self._on_undo_from_hotkey,
        )

        self._build_ui()
        self._start_services()

        # システムトレイ常駐の初期化
        self.tray_manager = SystemTrayManager(self)
        self.tray_manager.start()

        # 終了イベントのフック (×ボタン押下時はトレイに最小化)
        self.protocol("WM_DELETE_WINDOW", self._on_window_close_request)

    def _build_ui(self) -> None:
        """GUIレイアウトを構築する。"""
        # 1. プリセット管理バー
        preset_bar = ctk.CTkFrame(self)
        preset_bar.pack(fill="x", padx=16, pady=(10, 4))

        ctk.CTkLabel(
            preset_bar,
            text="プリセット:",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(side="left", padx=(12, 6), pady=6)

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
        self.preset_menu.pack(side="left", padx=(0, 6), pady=6)

        self.btn_save_preset = ctk.CTkButton(
            preset_bar,
            text="上書き保存",
            width=65,
            command=self._on_save_preset_clicked,
        )
        self.btn_save_preset.pack(side="left", padx=(0, 4), pady=6)

        self.btn_new_preset = ctk.CTkButton(
            preset_bar,
            text="＋新規",
            width=50,
            command=self._on_new_preset_clicked,
        )
        self.btn_new_preset.pack(side="left", padx=(0, 4), pady=6)

        self.btn_delete_preset = ctk.CTkButton(
            preset_bar,
            text="削除",
            width=45,
            fg_color="#C62828",
            hover_color="#B71C1C",
            command=self._on_delete_preset_clicked,
        )
        self.btn_delete_preset.pack(side="left", padx=(0, 10), pady=6)

        # 2. ヘッダーフレーム（有効/無効トグル & Undoボタン）
        self.header_frame = ctk.CTkFrame(self)
        self.header_frame.pack(fill="x", padx=16, pady=(2, 4))

        self.switch_var = ctk.BooleanVar(value=self.is_active)
        self.toggle_switch = ctk.CTkSwitch(
            self.header_frame,
            text=f"自動変換を有効化 ({self.config.hotkey.upper().replace('<', '').replace('>', '')})",
            font=ctk.CTkFont(size=13, weight="bold"),
            variable=self.switch_var,
            command=self._on_switch_toggled,
        )
        self.toggle_switch.pack(side="left", padx=14, pady=8)

        undo_hotkey_disp = self.config.hotkey_undo.upper().replace("<", "").replace(">", "")
        self.btn_undo = ctk.CTkButton(
            self.header_frame,
            text=f"↶ 元に戻す ({undo_hotkey_disp})",
            width=130,
            fg_color=("gray75", "gray30"),
            hover_color=("gray65", "gray40"),
            text_color=("gray10", "gray90"),
            command=self._on_undo_clicked,
        )
        self.btn_undo.pack(side="right", padx=12, pady=8)

        # 3. タブビュー
        self.tabview = ctk.CTkTabview(self, command=self._on_tab_changed)
        self.tabview.pack(fill="both", expand=True, padx=16, pady=4)

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

        # 4. リアルタイム変換テスト・プレビュー（折りたたみ式）
        self.preview_container = ctk.CTkFrame(self)
        self.preview_container.pack(fill="x", padx=16, pady=(4, 4))

        self.btn_toggle_preview = ctk.CTkButton(
            self.preview_container,
            text="▶ リアルタイム変換テスト・プレビュー (クリックで展開)",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="transparent",
            text_color=("gray30", "gray80"),
            hover_color=("gray85", "gray25"),
            anchor="w",
            command=self._toggle_preview_box,
        )
        self.btn_toggle_preview.pack(fill="x", padx=6, pady=4)

        # プレビュー展開用の中身フレーム
        self.preview_body = ctk.CTkFrame(self.preview_container, fg_color="transparent")

        # 入力テキストエリア
        ctk.CTkLabel(
            self.preview_body,
            text="テスト入力:",
            font=ctk.CTkFont(size=11, weight="bold"),
        ).pack(anchor="w", padx=8, pady=(2, 0))
        self.preview_input = ctk.CTkTextbox(self.preview_body, height=55)
        self.preview_input.pack(fill="x", padx=8, pady=(0, 4))
        self.preview_input.bind("<KeyRelease>", lambda e: self._update_preview())

        # 出力テキストエリア
        out_header_row = ctk.CTkFrame(self.preview_body, fg_color="transparent")
        out_header_row.pack(fill="x", padx=8, pady=(2, 0))
        ctk.CTkLabel(
            out_header_row,
            text="変換プレビュー結果:",
            font=ctk.CTkFont(size=11, weight="bold"),
        ).pack(side="left")

        btn_copy_res = ctk.CTkButton(
            out_header_row,
            text="結果をコピー",
            width=80,
            height=20,
            font=ctk.CTkFont(size=11),
            command=self._copy_preview_result,
        )
        btn_copy_res.pack(side="right")

        self.preview_output = ctk.CTkTextbox(self.preview_body, height=55)
        self.preview_output.pack(fill="x", padx=8, pady=(0, 8))

        # 5. ステータスバー
        self.status_frame = ctk.CTkFrame(self)
        self.status_frame.pack(fill="x", padx=16, pady=(4, 10))

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
        self.status_label.pack(fill="x", padx=12, pady=6)

    def _toggle_preview_box(self) -> None:
        """プレビュー枠の展開/折りたたみを切り替える。"""
        self._is_preview_expanded = not self._is_preview_expanded
        if self._is_preview_expanded:
            self.preview_body.pack(fill="x", padx=4, pady=2)
            self.btn_toggle_preview.configure(
                text="▼ リアルタイム変換テスト・プレビュー (クリックで閉じる)"
            )
            self._update_preview()
        else:
            self.preview_body.pack_forget()
            self.btn_toggle_preview.configure(
                text="▶ リアルタイム変換テスト・プレビュー (クリックで展開)"
            )

    def _on_tab_changed(self) -> None:
        """タブが切り替わったときの処理。"""
        if self._is_preview_expanded:
            self._update_preview()

    def _get_current_transformer(self):
        """現在選択されているタブのトランスフォーマーを取得する。"""
        current_tab = self.tabview.get()
        if current_tab == self.TAB_PRESET:
            return self.preset_tab.get_transformer()
        elif current_tab == self.TAB_LATEX:
            return self.latex_tab.get_transformer()
        else:
            return self.programmable_tab.get_transformer()

    def _update_preview(self) -> None:
        """プレビュー入力内容を現在のタブ設定で変換して結果を表示する。"""
        if not self._is_preview_expanded:
            return

        text = self.preview_input.get("1.0", "end-1c")
        if not text:
            self.preview_output.delete("1.0", "end")
            return

        transformer = self._get_current_transformer()
        if transformer is None:
            self.preview_output.delete("1.0", "end")
            self.preview_output.insert("1.0", "(ルールが無効または未設定です)")
            return

        try:
            res = transformer.transform(text)
            self.preview_output.delete("1.0", "end")
            if res.success and res.text is not None:
                self.preview_output.insert("1.0", res.text)
            elif res.status == "skip":
                self.preview_output.insert("1.0", f"(スキップ: {res.message})")
            elif res.status == "error":
                self.preview_output.insert("1.0", f"(エラー: {res.message})")
            else:
                self.preview_output.insert("1.0", res.text or text)
        except Exception as e:
            self.preview_output.delete("1.0", "end")
            self.preview_output.insert("1.0", f"(変換例外: {e})")

    def _copy_preview_result(self) -> None:
        """プレビュー結果をクリップボードにコピーする。"""
        res_text = self.preview_output.get("1.0", "end-1c")
        if res_text and not res_text.startswith("("):
            self.monitor.write_clipboard(res_text)
            show_toast(self, "プレビュー結果をコピーしました", level="success", duration_ms=1800)

    # --- プリセット管理 ---
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
        self._sync_all_tabs_to_config()
        if self.config.load_from_preset(choice):
            self._sync_all_tabs_from_config()
            self._update_status(f"プリセット「{choice}」を読み込みました", level="normal")
            self._update_preview()

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
            self._update_preview()

    # --- 監視サービス & ホットキー ---
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
        self.tray_manager.update_state()

    def toggle_active(self) -> None:
        """トレイ等から自動変換をトグルする。"""
        self.switch_var.set(not self.switch_var.get())
        self._on_switch_toggled()

    def _toggle_active_from_hotkey(self) -> None:
        """グローバルホットキー押下時に安全にGUIスレッドでトグルする。"""
        self.after(0, self.toggle_active)

    def _on_undo_from_hotkey(self) -> None:
        """グローバルUndoホットキー押下時のハンドラ。"""
        self.after(0, self._on_undo_clicked)

    def _on_undo_clicked(self) -> None:
        """直前の変換前テキストをクリップボードに復元する。"""
        restored = self.monitor.undo()
        if restored is not None:
            snippet = restored[:30] + ("..." if len(restored) > 30 else "")
            msg = f"元に戻しました (Undo): {snippet}"
            self._update_status(msg, level="success")
            show_toast(self, "クリップボードを元に戻しました (Undo)", level="success", duration_ms=2000)
        else:
            self._update_status("元に戻すテキストがありません", level="skip")
            show_toast(self, "元に戻すテキストがありません", level="skip", duration_ms=2000)

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

        transformer = self._get_current_transformer()
        if transformer is None:
            self._update_status("適用可能なルールが選択されていません", "skip")
            return

        result: Optional[TransformResult] = None
        try:
            result = transformer.transform(content)
        except Exception as e:
            logger.error("Error during transformation: %s", e, exc_info=True)
            self._update_status(f"変換エラー: {e}", "error")
            return

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

    # --- ウィンドウ表示/非表示 & システムトレイ制御 ---
    def show_window(self) -> None:
        """ウィンドウを再表示して最前面にする。"""
        self.deiconify()
        self.lift()
        self.focus_force()

    def hide_window(self) -> None:
        """ウィンドウを最小化して非表示（トレイ格納）にする。"""
        self.withdraw()

    def _on_window_close_request(self) -> None:
        """ウィンドウの×ボタンが押されたときのハンドラ。"""
        if getattr(self.config, "close_to_tray", True):
            self.hide_window()
            show_toast(self, "タスクトレイに最小化しました", level="normal", duration_ms=2000)
        else:
            self.really_quit()

    def really_quit(self) -> None:
        """アプリケーションを完全に終了する。"""
        logger.info("Closing application completely...")

        self._sync_all_tabs_to_config()
        self.config.save_to_preset(self.config.current_preset)
        save_config(self.config, self.config_path)

        self.hotkey_listener.stop()
        self.tray_manager.stop()
        self.destroy()
