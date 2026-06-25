"""camera.pyのテスト。

実機のUSBカメラがない環境でも検証できるよう、cv2.VideoCaptureをモックする。
実機による動作確認はdocs/test_report.mdに記載する。
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from webcam_security.camera import Camera, CameraError


def test_open_カメラを開けない場合はCameraError() -> None:
    """isOpened()がFalseを返す場合、open()がCameraErrorを発生させることを確認する。"""
    fake_capture = MagicMock()
    fake_capture.isOpened.return_value = False

    with patch("webcam_security.camera.cv2.VideoCapture", return_value=fake_capture):
        camera = Camera(device_index=0)
        with pytest.raises(CameraError):
            camera.open()


def test_read_未オープン時はCameraError() -> None:
    """open()を呼ぶ前にread()するとCameraErrorが発生することを確認する。"""
    camera = Camera(device_index=0)

    with pytest.raises(CameraError):
        camera.read()


def test_read_フレーム取得に失敗した場合はCameraError() -> None:
    """VideoCapture.read()がFalseを返す場合（切断等）、CameraErrorが発生することを確認する。"""
    fake_capture = MagicMock()
    fake_capture.isOpened.return_value = True
    fake_capture.read.return_value = (False, None)

    with patch("webcam_security.camera.cv2.VideoCapture", return_value=fake_capture):
        camera = Camera(device_index=0)
        camera.open()
        with pytest.raises(CameraError):
            camera.read()


def test_read_正常時はフレームを返す() -> None:
    """フレーム取得に成功した場合、そのフレームを返すことを確認する。"""
    expected_frame = np.zeros((10, 10, 3), dtype=np.uint8)
    fake_capture = MagicMock()
    fake_capture.isOpened.return_value = True
    fake_capture.read.return_value = (True, expected_frame)

    with patch("webcam_security.camera.cv2.VideoCapture", return_value=fake_capture):
        camera = Camera(device_index=0)
        camera.open()
        frame = camera.read()

    assert frame is expected_frame


def test_get_fps_取得できない場合はdefaultを返す() -> None:
    """カメラがFPSを報告しない(0を返す)場合、defaultを返すことを確認する。"""
    fake_capture = MagicMock()
    fake_capture.isOpened.return_value = True
    fake_capture.get.return_value = 0

    with patch("webcam_security.camera.cv2.VideoCapture", return_value=fake_capture):
        camera = Camera(device_index=0)
        camera.open()

        assert camera.get_fps(default=20.0) == 20.0


def test_release_解放後にreadするとCameraError() -> None:
    """release()後にread()を呼ぶとCameraErrorが発生することを確認する。"""
    fake_capture = MagicMock()
    fake_capture.isOpened.return_value = True

    with patch("webcam_security.camera.cv2.VideoCapture", return_value=fake_capture):
        camera = Camera(device_index=0)
        camera.open()
        camera.release()

        with pytest.raises(CameraError):
            camera.read()


def test_with文でオープンと解放が行われる() -> None:
    """コンテキストマネージャとして使うとopen/releaseが呼ばれることを確認する。"""
    fake_capture = MagicMock()
    fake_capture.isOpened.return_value = True

    with patch("webcam_security.camera.cv2.VideoCapture", return_value=fake_capture):
        with Camera(device_index=0) as camera:
            assert camera._capture is fake_capture

    fake_capture.release.assert_called()
