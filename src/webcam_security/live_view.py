"""ライブビューウィンドウの表示を行うモジュール。"""

from __future__ import annotations

import cv2
import numpy as np

_WINDOW_NAME = "Webcam Security - Live View"


def show(frame: np.ndarray) -> None:
    """フレームをライブビューウィンドウに表示する。

    Args:
        frame: 表示するフレーム画像（BGR形式のnumpy配列）。

    Example:
        >>> show(frame)
        >>> poll_quit_key()
        False
    """
    cv2.imshow(_WINDOW_NAME, frame)


def poll_quit_key(delay_ms: int = 1) -> bool:
    """キー入力をポーリングし、'q'が押されたかどうかを返す。

    内部で`cv2.waitKey`を呼び出すため、`show`でウィンドウが表示された
    状態で呼び出す必要がある（ウィンドウのイベント処理も兼ねるため）。

    Args:
        delay_ms: キー入力を待つ時間（ミリ秒）。既定値は1ms。

    Returns:
        'q'キーが押された場合はTrue、それ以外はFalse。
    """
    return cv2.waitKey(delay_ms) & 0xFF == ord("q")


def close() -> None:
    """ライブビューウィンドウを閉じる。

    `cv2.destroyAllWindows`を呼び出し、表示中のすべてのウィンドウを破棄する。
    """
    cv2.destroyAllWindows()
