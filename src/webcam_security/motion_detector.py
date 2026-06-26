"""フレーム差分による動体検知を行うモジュール。"""

from __future__ import annotations

import cv2
import numpy as np

_MIN_MOTION_AREA = 500  # 動体と判定する最小ピクセル数


class MotionDetector:
    """前フレームとの差分から動体を検知する。

    入力フレームをグレースケール化・ガウシアンブライで平滑化した上で
    直前のフレームと差分を取り、二値化後の変化ピクセル数が一定数
    （`_MIN_MOTION_AREA`）を超えた場合に動体ありと判定する。

    Example:
        >>> detector = MotionDetector(sensitivity=25)
        >>> detector.detect(frame1)  # 初回はFalse
        False
        >>> detector.detect(frame2)  # frame1との差分で判定
        True
    """

    def __init__(self, sensitivity: int) -> None:
        """MotionDetectorを初期化する。

        Args:
            sensitivity: フレーム差分を二値化する際の閾値。小さいほど高感度。
        """
        self._sensitivity = sensitivity
        self._previous_gray: np.ndarray | None = None

    def detect(self, frame: np.ndarray) -> bool:
        """フレームを入力し、前フレームとの比較で動体を検知したかどうかを返す。

        最初の呼び出しは比較対象のフレームがないため常にFalseを返す。

        Args:
            frame: 判定対象のフレーム画像（BGR形式のnumpy配列）。

        Returns:
            動体を検知した場合はTrue、検知しなかった場合（初回呼び出し含む）
            はFalse。
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
