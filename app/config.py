"""アプリケーション設定のデータモデルおよび永続化（JSON）モジュール。"""

import copy
import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Union

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path("config.json")


def get_default_presets() -> Dict[str, Dict[str, Any]]:
    """組み込みの初期プリセット辞書を生成して返す。

    Returns
    -------
    dict[str, dict[str, Any]]
        プリセット名をキー、設定辞書を値とする辞書。
    """
    return {
        "デフォルト": {
            "active_tab": "定型ルールモード",
            "int_mode": "none",
            "int_digits": 3,
            "dec_mode": "round",
            "dec_digits": 2,
            "dec_overflow": "round",
            "col_enabled": False,
            "unwrap_enabled": False,
        },
        "LaTeX 表組み": {
            "active_tab": "LaTeXモード",
            "latex_mode": "table",
            "latex_table_delim": "\t",
            "latex_table_style": "booktabs",
            "latex_table_align": "auto",
            "latex_table_header": True,
            "latex_table_round": False,
            "latex_table_digits": 2,
        },
        "LaTeX 数式変換": {
            "active_tab": "LaTeXモード",
            "latex_mode": "formula",
            "latex_formula_direction": "plain_to_latex",
            "latex_formula_env": "inline",
        },
        "PDF 改行結合 (Unwrap)": {
            "active_tab": "定型ルールモード",
            "unwrap_enabled": True,
            "int_mode": "none",
            "dec_mode": "none",
            "col_enabled": False,
        },
        "プログラマブル": {
            "active_tab": "プログラマブルモード",
            "prog_mode": "pattern",
            "prog_pattern_input": "私は{a}時間で{b}つのりんごを食べました",
            "prog_pattern_output": "私は{b}時間で{a}つのりんごを食べました",
        },
        "Python スクリプト計算": {
            "active_tab": "プログラマブルモード",
            "prog_mode": "script",
            "prog_script_input_mode": "pattern",
            "prog_script_pattern": "単価{price}円、数量{qty}個",
            "prog_script_code": "# 変数 price, qty が使用可能\ntotal = int(price) * int(qty)\nresult = f'合計金額: {total:,}円 (税込: {int(total * 1.1):,}円)'",
        },
    }


@dataclass
class AppConfig:
    """アプリケーションのユーザー設定モデル。

    Parameters
    ----------
    is_active : bool, optional
        自動変換が有効かどうか。デフォルトは False。
    active_tab : str, optional
        起動時に選択されるタブ名。デフォルトは '定型ルールモード'。
    hotkey : str, optional
        トグル用グローバルホットキー。デフォルトは '<ctrl>+<alt>+x'。
    hotkey_undo : str, optional
        Undo用グローバルホットキー。デフォルトは '<ctrl>+<alt>+z'。
    close_to_tray : bool, optional
        ×ボタン押下時にタスクトレイへ格納するかどうか。デフォルトは True。
    current_preset : str, optional
        現在選択中のプリセット名。デフォルトは 'デフォルト'。
    presets : dict[str, dict[str, Any]], optional
        保存されたプリセット辞書。
    """

    is_active: bool = False
    active_tab: str = "定型ルールモード"
    hotkey: str = "<ctrl>+<alt>+x"
    hotkey_undo: str = "<ctrl>+<alt>+z"
    close_to_tray: bool = True

    # プリセット管理
    current_preset: str = "デフォルト"
    presets: Dict[str, Dict[str, Any]] = field(default_factory=get_default_presets)

    # 定型ルール設定（整数部・小数部 独立設定、改行除去）
    int_mode: str = "none"  # "none", "pad"
    int_digits: int = 3
    dec_mode: str = "round"  # "none", "round", "pad"
    dec_digits: int = 2
    dec_overflow: str = "round"  # "round", "truncate"
    col_enabled: bool = False
    col_delimiter: str = ","
    col_indices: str = "1, -1"
    unwrap_enabled: bool = False  # PDF改行・ハイフン除去

    # プログラマブル設定
    prog_mode: str = "pattern"  # "pattern", "delimiter", "script"
    prog_pattern_input: str = "私は{a}時間で{b}つのりんごを食べました"
    prog_pattern_output: str = "私は{b}時間で{a}つのりんごを食べました"
    prog_delimiter: str = ","
    prog_input_vars: str = "a, b, c, d, e"
    prog_output_template: str = "{e}, {b}, {c}, {d}, {a}"

    # スクリプトモード設定
    prog_script_input_mode: str = "pattern"  # "pattern", "delimiter", "full_text"
    prog_script_pattern: str = "単価{price}円、数量{qty}個"
    prog_script_delimiter: str = ","
    prog_script_vars: str = "a, b"
    prog_script_code: str = "# 変数 price, qty (または a, b / text, lines) が使用可能\n# 出力結果を result 変数に代入してください\ntotal = int(price) * int(qty)\nresult = f'合計金額: {total:,}円 (税込: {int(total * 1.1):,}円)'"

    # LaTeXモード設定
    latex_mode: str = "table"  # "table" または "formula"
    latex_table_delim: str = "\t"
    latex_table_style: str = "booktabs"  # "booktabs", "standard", "body_only", "markdown"
    latex_table_align: str = "auto"  # "auto", "l", "c", "r"
    latex_table_header: bool = True
    latex_table_round: bool = False
    latex_table_digits: int = 2
    latex_table_highlight: str = "none"  # "none", "max", "min"
    latex_formula_direction: str = "plain_to_latex"  # "plain_to_latex", "latex_to_plain"
    latex_formula_env: str = "inline"  # "inline", "display", "none"

    # 後方互換用フィールド
    number_mode: str = "round"
    round_enabled: bool = True
    round_digits: int = 2
    pad_enabled: bool = False
    pad_int_digits: int = 3
    pad_dec_digits: int = 2

    def get_preset_names(self) -> List[str]:
        """登録されているプリセット名の一覧を返す。

        Returns
        -------
        list[str]
            プリセット名のリスト。
        """
        if not self.presets:
            self.presets = get_default_presets()
        return list(self.presets.keys())

    def save_to_preset(self, preset_name: str) -> None:
        """現在の設定値を指定プリセットとして保存・更新する。

        Parameters
        ----------
        preset_name : str
            保存先のプリセット名。

        Returns
        -------
        None
        """
        d = asdict(self)
        exclude_keys = {"presets", "current_preset", "is_active", "hotkey", "hotkey_undo", "close_to_tray"}
        preset_data = {k: v for k, v in d.items() if k not in exclude_keys}
        self.presets[preset_name] = copy.deepcopy(preset_data)
        self.current_preset = preset_name

    def load_from_preset(self, preset_name: str) -> bool:
        """指定プリセットの値を自身の設定に反映する。

        Parameters
        ----------
        preset_name : str
            読み込み対象のプリセット名。

        Returns
        -------
        bool
            読み込みが成功した場合は True、プリセットが存在しない場合は False。
        """
        if preset_name not in self.presets:
            return False
        preset_data = self.presets[preset_name]
        exclude_keys = {"presets", "current_preset", "is_active", "hotkey", "hotkey_undo", "close_to_tray"}
        for k, v in preset_data.items():
            if hasattr(self, k) and k not in exclude_keys:
                setattr(self, k, copy.deepcopy(v))
        self.current_preset = preset_name
        return True

    def delete_preset(self, preset_name: str) -> bool:
        """指定プリセットを削除する。

        Parameters
        ----------
        preset_name : str
            削除対象のプリセット名。

        Returns
        -------
        bool
            削除に成功した場合は True、最後の1件などで削除不可の場合は False。
        """
        if preset_name in self.presets and len(self.presets) > 1:
            del self.presets[preset_name]
            if self.current_preset == preset_name:
                self.current_preset = next(iter(self.presets.keys()))
                self.load_from_preset(self.current_preset)
            return True
        return False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppConfig":
        """辞書データから安全に AppConfig インスタンスを生成する。

        Parameters
        ----------
        data : dict[str, Any]
            JSON等から読み込まれた設定辞書。

        Returns
        -------
        AppConfig
            未知のキーは無視され、不足キーはデフォルト値で補完された設定インスタンス。
        """
        field_names = set(cls.__dataclass_fields__.keys())
        filtered = {k: v for k, v in data.items() if k in field_names}

        # 1. number_mode の推定（旧設定互換）
        if "number_mode" not in filtered:
            if filtered.get("pad_enabled", False):
                filtered["number_mode"] = "pad"
            elif filtered.get("round_enabled", False):
                filtered["number_mode"] = "round"
            else:
                filtered["number_mode"] = "none"

        # 2. int_mode / dec_mode の推定（旧設定互換）
        if "int_mode" not in filtered or "dec_mode" not in filtered:
            n_mode = filtered.get("number_mode", "round")
            if n_mode == "pad":
                filtered.setdefault("int_mode", "pad")
                filtered.setdefault("int_digits", filtered.get("pad_int_digits", 3))
                filtered.setdefault("dec_mode", "pad")
                filtered.setdefault("dec_digits", filtered.get("pad_dec_digits", 2))
            elif n_mode == "round":
                filtered.setdefault("int_mode", "none")
                filtered.setdefault("dec_mode", "round")
                filtered.setdefault("dec_digits", filtered.get("round_digits", 2))
            else:
                filtered.setdefault("int_mode", "none")
                filtered.setdefault("dec_mode", "none")

        # 3. dec_mode が "truncate" の場合の後方互換
        if filtered.get("dec_mode") == "truncate":
            filtered["dec_mode"] = "round"
            filtered["dec_overflow"] = "truncate"

        # 4. presets が空または未設定の場合の初期化
        if not filtered.get("presets"):
            filtered["presets"] = get_default_presets()

        return cls(**filtered)


def load_config(filepath: Union[str, Path] = DEFAULT_CONFIG_PATH) -> AppConfig:
    """設定ファイル（JSON）から設定を読み込む。

    Parameters
    ----------
    filepath : Union[str, Path], optional
        設定JSONファイルのパス。デフォルトは DEFAULT_CONFIG_PATH ('config.json')。

    Returns
    -------
    AppConfig
        読み込まれた設定オブジェクト。ファイルが存在しない場合や破損時はデフォルト設定。
    """
    path = Path(filepath)
    if not path.exists():
        logger.info("Config file '%s' not found. Using default config.", path)
        return AppConfig()

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info("Loaded config from '%s'", path)
        return AppConfig.from_dict(data)
    except Exception as e:
        logger.error("Failed to load config from '%s': %s. Using default config.", path, e)
        return AppConfig()


def save_config(config: AppConfig, filepath: Union[str, Path] = DEFAULT_CONFIG_PATH) -> bool:
    """設定オブジェクトをファイル（JSON）に書き込む。

    Parameters
    ----------
    config : AppConfig
        保存する設定オブジェクト。
    filepath : Union[str, Path], optional
        保存先ファイルのパス。デフォルトは DEFAULT_CONFIG_PATH ('config.json')。

    Returns
    -------
    bool
        保存に成功した場合は True、失敗時は False。
    """
    path = Path(filepath)
    try:
        data = asdict(config)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info("Saved config to '%s'", path)
        return True
    except Exception as e:
        logger.error("Failed to save config to '%s': %s", path, e)
        return False
