"""変換器の基底クラスおよび結果データモデルの定義モジュール。"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class TransformResult:
    """テキスト変換処理の結果を保持するデータクラス。

    Parameters
    ----------
    success : bool
        変換が有効に適用されたかどうか（元のテキストから変更があったか）。
    text : Optional[str]
        変換後のテキスト。スキップや失敗時は None または元のテキスト。
    message : str
        結果ステータスメッセージ（成功理由、スキップ理由、エラー内容など）。
    status : str
        状態ラベル ('success', 'skip', 'error', 'neutral')。デフォルトは 'neutral'。
    """

    success: bool
    text: Optional[str]
    message: str
    status: str = "neutral"

    @classmethod
    def successful(cls, text: str, message: str) -> "TransformResult":
        """変換成功時の TransformResult インスタンスを生成する。

        Parameters
        ----------
        text : str
            変換後のテキスト。
        message : str
            成功理由や処理件数などを表すメッセージ。

        Returns
        -------
        TransformResult
            success=True, status='success' の結果オブジェクト。
        """
        return cls(success=True, text=text, message=message, status="success")

    @classmethod
    def skipped(cls, reason: str, original_text: Optional[str] = None) -> "TransformResult":
        """変換スキップ時の TransformResult インスタンスを生成する。

        Parameters
        ----------
        reason : str
            変換をスキップした理由。
        original_text : Optional[str]
            変換前の元テキスト。

        Returns
        -------
        TransformResult
            success=False, status='skip' の結果オブジェクト。
        """
        return cls(success=False, text=original_text, message=reason, status="skip")

    @classmethod
    def error(cls, error_msg: str, original_text: Optional[str] = None) -> "TransformResult":
        """エラー発生時の TransformResult インスタンスを生成する。

        Parameters
        ----------
        error_msg : str
            発生したエラー内容の説明。
        original_text : Optional[str]
            変換前の元テキスト。

        Returns
        -------
        TransformResult
            success=False, status='error' の結果オブジェクト。
        """
        return cls(success=False, text=original_text, message=error_msg, status="error")

    @classmethod
    def unchanged(cls, text: str, message: str = "変更なし") -> "TransformResult":
        """変換対象外またはテキストに変更がなかった時の TransformResult インスタンスを生成する。

        Parameters
        ----------
        text : str
            入力テキスト（変更なし）。
        message : str
            変更なしの理由メッセージ。デフォルトは '変更なし'。

        Returns
        -------
        TransformResult
            success=False, status='neutral' の結果オブジェクト。
        """
        return cls(success=False, text=text, message=message, status="neutral")


class BaseTransformer(ABC):
    """すべてのテキスト変換器が実装すべき抽象基底クラス。"""

    @abstractmethod
    def transform(self, text: str) -> TransformResult:
        """与えられたテキストを特定のルールに基づいて変換する。

        Parameters
        ----------
        text : str
            変換対象の入力テキスト。

        Returns
        -------
        TransformResult
            変換成否、変換後テキスト、メッセージを含む結果オブジェクト。

        Notes
        -----
        派生クラスでは例外を外側に漏らさず、安全に TransformResult.skipped や
        TransformResult.error などを返すように実装してください。
        """
        raise NotImplementedError
