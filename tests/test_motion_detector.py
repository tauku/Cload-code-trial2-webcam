"""motion_detector.pyのテスト。"""

import numpy as np

from webcam_security.motion_detector import MotionDetector


def _solid_frame(value: int) -> np.ndarray:
    """単色のテスト用フレーム(100x100, BGR)を生成する。"""
    return np.full((100, 100, 3), value, dtype=np.uint8)


def test_detect_最初のフレームは比較対象がないためFalse() -> None:
    """初回呼び出しでは動体検知を行わずFalseを返すことを確認する。"""
    detector = MotionDetector(sensitivity=25)

    assert detector.detect(_solid_frame(0)) is False


def test_detect_同一フレームが続く場合はFalse() -> None:
    """変化のないフレームが続く場合は動体なしと判定されることを確認する。"""
    detector = MotionDetector(sensitivity=25)
    detector.detect(_solid_frame(100))

    assert detector.detect(_solid_frame(100)) is False


def test_detect_大きく変化したフレームはTrue() -> None:
    """前フレームと大きく異なるフレームは動体ありと判定されることを確認する。"""
    detector = MotionDetector(sensitivity=25)
    detector.detect(_solid_frame(0))

    assert detector.detect(_solid_frame(255)) is True


def test_detect_感度を下げると微小な変化を検知しなくなる() -> None:
    """sensitivity（閾値）を大きくすると、わずかな輝度変化では検知しないことを確認する。"""
    detector = MotionDetector(sensitivity=200)
    detector.detect(_solid_frame(100))

    assert detector.detect(_solid_frame(110)) is False
