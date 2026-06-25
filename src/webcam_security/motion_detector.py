"""フレーム差分による動体検知を行うモジュール。"""

from __future__ import annotations

import cv2
import numpy as np

_MIN_MOTION_AREA = 500  # 動体と判定する最小ピクセル数


class MotionDetector:
    """前フレームとの差分から動体を検知する。"""

    def __init__(self, sensitivity: int) -> None:
        """
        Args:
            sensitivity: フレーム差分を二値化する際の閾値。小さいほど高感度。
        """
        self._sensitivity = sensitivity
        self._previous_gray: np.ndarray | None = None

    def detect(self, frame: np.ndarray) -> bool:
        """フレームを入力し、前フレームとの比較で動体を検知したかどうかを返す。

        最初の呼び出しは比較対象のフレームがないため常にFalseを返す。
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if self._previous_gray is None:
            self._previous_gray = gray
            return False

        diff = cv2.absdiff(self._previous_gray, gray)
        self._previous_gray = gray

        _, thresholded = cv2.threshold(diff, self._sensitivity, 255, cv2.THRESH_BINARY)
        motion_pixels = int(cv2.countNonZero(thresholded))
        return motion_pixels >= _MIN_MOTION_AREA
