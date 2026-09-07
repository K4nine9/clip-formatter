"""変換器の基底クラスおよび結果データモデルの定義モジュール。"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class TransformResult:
    """テキスト変換処理の結果を保持するデータクラス。

    Attributes:
        success: 変換が有効に適用されたかどうか（元のテキストから変更があったか）。
        text: 変換後のテキスト。スキップや失敗時は None または元のテキスト。
        message: 結果ステータスメッセージ（成功理由、スキップ理由、エラー内容など）。
        status: 状態ラベル ('success', 'skip', 'error', 'neutral')。
    """

    success: bool
    text: Optional[str]
    message: str
    status: str = "neutral"

    @classmethod
    def successful(cls, text: str, message: str) -> "TransformResult":
        """変換成功時のインスタンスを生成するヘルパー。"""
        return cls(success=True, text=text, message=message, status="success")

    @classmethod
    def skipped(cls, reason: str, original_text: Optional[str] = None) -> "TransformResult":
        """スキップ時のインスタンスを生成するヘルパー。"""
        return cls(success=False, text=original_text, message=reason, status="skip")

    @classmethod
    def error(cls, error_msg: str, original_text: Optional[str] = None) -> "TransformResult":
        """エラー発生時のインスタンスを生成するヘルパー。"""
        return cls(success=False, text=original_text, message=error_msg, status="error")

    @classmethod
    def unchanged(cls, text: str, message: str = "変更なし") -> "TransformResult":
        """変換対象外・変更なしのインスタンスを生成するヘルパー。"""
        return cls(success=False, text=text, message=message, status="neutral")


class BaseTransformer(ABC):
    """すべてのテキスト変換器が実装すべき基底インターフェース。"""

    @abstractmethod
    def transform(self, text: str) -> TransformResult:
        """与えられたテキストを変換し、結果を返す。

        Args:
            text: 変換対象の入力テキスト。

        Returns:
            TransformResult: 変換成否、変換後テキスト、メッセージを含む結果オブジェクト。
        """
        raise NotImplementedError
