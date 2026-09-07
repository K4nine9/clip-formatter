"""アプリケーション設定のデータモデルおよび永続化（JSON）モジュール。"""

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Union

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path("config.json")


@dataclass
class AppConfig:
    """アプリケーションのユーザー設定モデル。"""

    is_active: bool = False
    active_tab: str = "定型ルールモード"
    hotkey: str = "<ctrl>+<alt>+x"

    # 定型ルール設定
    round_enabled: bool = True
    round_digits: int = 2
    col_enabled: bool = False
    col_delimiter: str = ","
    col_indices: str = "1, -1"

    # プログラマブル設定
    prog_delimiter: str = ","
    prog_input_vars: str = "a, b, c, d, e"
    prog_output_template: str = "{e}, {b}, {c}, {d}, {a}"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppConfig":
        """辞書データから安全にインスタンスを生成する（未知のキーは無視、欠落キーはデフォルト値）。"""
        field_names = set(cls.__dataclass_fields__.keys())
        filtered = {k: v for k, v in data.items() if k in field_names}
        return cls(**filtered)


def load_config(filepath: Union[str, Path] = DEFAULT_CONFIG_PATH) -> AppConfig:
    """設定ファイル（JSON）から設定を読み込む。ファイルが存在しない場合はデフォルト設定を返す。"""
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
    """設定をファイル（JSON）に書き込む。"""
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
