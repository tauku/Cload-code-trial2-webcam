"""USBカメラの入出力を扱うモジュール。"""

from __future__ import annotations

from types import TracebackType

import cv2
import numpy as np


class CameraError(Exception):
    """カメラのオープンまたはフレーム取得に失敗した場合に発生する例外。"""


class Camera:
    """USBカメラをラップし、オープン・フレーム取得・解放を行う。

    コンテキストマネージャ(`with`文)に対応しており、`with`ブロックを
    抜ける際に自動でカメラを解放する。

    Example:
        >>> with Camera(device_index=0) as camera:
        ...     frame = camera.read()
        ...     fps = camera.get_fps()
    """

    def __init__(self, device_index: int) -> None:
        """Cameraを初期化する。

        Args:
            device_index: 使用するUSBカメラのデバイス番号
                （`cv2.VideoCapture`に渡すインデックス。通常は0から始まる）。
        """
        self._device_index = device_index
        self._capture: cv2.VideoCapture | None = None

    def open(self) -> None:
        """カメラをオープンする。

        Raises:
            CameraError: カメラのオープンに失敗した場合。
        """
        capture = cv2.VideoCapture(self._device_index)
        if not capture.isOpened():
            capture.release()
            raise CameraError(
                f"カメラ(device_index={self._device_index})を開けませんでした"
            )
        self._capture = capture

    def read(self) -> np.ndarray:
        """フレームを1枚取得する。

        Returns:
            取得したフレーム画像（BGR形式のnumpy配列）。

        Raises:
            CameraError: カメラが未オープン、またはフレーム取得に失敗した場合
                （切断の可能性がある）。
        """
        if self._capture is None:
            raise CameraError("カメラがオープンされていません")

        ok, frame = self._capture.read()
        if not ok:
            raise CameraError("カメラからのフレーム取得に失敗しました（切断の可能性）")
        return frame

    def get_fps(self, default: float = 20.0) -> float:
        """カメラのFPSを取得する。取得できない場合はdefaultを返す。

        Args:
            default: FPSが取得できない場合（0以下や未オープン時）に返す既定値。

        Returns:
            カメラのフレームレート（取得できない場合はdefault）。
        """
        if self._capture is None:
            return default
        fps = self._capture.get(cv2.CAP_PROP_FPS)
        return fps if fps and fps > 0 else default

    def release(self) -> None:
        """カメラを解放する。"""
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    def __enter__(self) -> Camera:
        self.open()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.release()
