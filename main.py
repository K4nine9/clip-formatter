"""ClipFormatter エントリーポイントスクリプト。"""

import logging
import sys
from pathlib import Path

# プロジェクトルートディレクトリを sys.path に追加
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.app_window import ClipboardTransformerApp


def setup_logging() -> None:
    """ロギングの初期設定を行う。

    Returns
    -------
    None
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s",
        datefmt="%H:%M:%S",
    )


def main() -> None:
    """アプリケーションのメイン実行関数。ロギングを設定しGUIを起動する。

    Returns
    -------
    None
    """
    setup_logging()
    logger = logging.getLogger("ClipFormatter")
    logger.info("ClipFormatter を起動しています...")

    try:
        app = ClipboardTransformerApp()
        app.mainloop()
    except KeyboardInterrupt:
        logger.info("ユーザーによって終了されました。")
    except Exception as e:
        logger.critical("予期せぬエラーが発生しました: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
