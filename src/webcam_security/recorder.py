"""動体検知時の録画を行うモジュール。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

_FOURCC = "mp4v"


class RecorderError(Exception):
    """録画ファイルのオープンまたは書き込みに失敗した場合に発生する例外。"""


class Recorder:
    """検知中のフレームをMP4ファイルへ録画する。

    Example:
        >>> recorder = Recorder(Path("recordings"), fps=20.0, frame_size=(640, 480))
        >>> path = recorder.start()
        >>> recorder.write(frame)
        >>> recorder.stop()
    """

    def __init__(self, directory: Path, fps: float, frame_size: tuple[int, int]) -> None:
        """Recorderを初期化する。

        Args:
            directory: 録画ファイルの保存先ディレクトリ。
            fps: 録画する映像のフレームレート。
            frame_size: (幅, 高さ)。
        """
        self._directory = directory
        self._fps = fps
        self._frame_size = frame_size
        self._writer: cv2.VideoWriter | None = None

    @property
    def is_recording(self) -> bool:
        """録画中かどうか。"""
        return self._writer is not None

    def start(self) -> Path:
        """録画を開始し、出力先のファイルパスを返す。

        Raises:
            RecorderError: 録画ファイルを開けなかった場合。
        """
        self._directory.mkdir(parents=True, exist_ok=True)
        filename = datetime.now().strftime("%Y%m%d_%H%M%S.mp4")
        output_path = self._directory / filename

        fourcc = cv2.VideoWriter.fourcc(*_FOURCC)
        writer = cv2.VideoWriter(str(output_path), fourcc, self._fps, self._frame_size)
        if not writer.isOpened():
            raise RecorderError(f"録画ファイルを開けませんでした: {output_path}")

        self._writer = writer
        return output_path

    def write(self, frame: np.ndarray) -> None:
        """録画中のファイルにフレームを書き込む。

        Raises:
            RecorderError: 録画が開始されていない場合。
        """
        if self._writer is None:
            raise RecorderError("録画が開始されていません")
        self._writer.write(frame)

    def stop(self) -> None:
        """録画を停止し、ファイルを確定する。"""
        if self._writer is not None:
            self._writer.release()
            self._writer = None
