"""ライブビューウィンドウの表示を行うモジュール。"""

from __future__ import annotations

import cv2
import numpy as np

_WINDOW_NAME = "Webcam Security - Live View"


def show(frame: np.ndarray) -> None:
    """フレームをライブビューウィンドウに表示する。"""
    cv2.imshow(_WINDOW_NAME, frame)


def poll_quit_key(delay_ms: int = 1) -> bool:
    """キー入力をポーリングし、'q'が押されたかどうかを返す。"""
    return cv2.waitKey(delay_ms) & 0xFF == ord("q")


def close() -> None:
    """ライブビューウィンドウを閉じる。"""
    cv2.destroyAllWindows()
