"""recorder.pyのテスト。"""

from pathlib import Path

import numpy as np
import pytest

from webcam_security.recorder import Recorder, RecorderError


def _frame(width: int, height: int) -> np.ndarray:
    """テスト用フレームを生成する。"""
    return np.zeros((height, width, 3), dtype=np.uint8)


def test_start_録画ファイルが作成される(tmp_path: Path) -> None:
    """start()で保存先ディレクトリに録画ファイルが作成されることを確認する。"""
    recorder = Recorder(directory=tmp_path, fps=20.0, frame_size=(64, 48))

    output_path = recorder.start()

    assert recorder.is_recording is True
    assert output_path.parent == tmp_path
    recorder.stop()
    assert output_path.exists()


def test_write_停止後にファイルサイズが0より大きい(tmp_path: Path) -> None:
    """write()で書き込んだフレームがファイルに反映されることを確認する。"""
    recorder = Recorder(directory=tmp_path, fps=20.0, frame_size=(64, 48))
    output_path = recorder.start()

    for _ in range(5):
        recorder.write(_frame(64, 48))
    recorder.stop()

    assert output_path.stat().st_size > 0


def test_write_開始前に呼ぶとRecorderError(tmp_path: Path) -> None:
    """start()を呼ぶ前にwrite()するとRecorderErrorが発生することを確認する。"""
    recorder = Recorder(directory=tmp_path, fps=20.0, frame_size=(64, 48))

    with pytest.raises(RecorderError):
        recorder.write(_frame(64, 48))


def test_stop_開始していなくても例外にならない(tmp_path: Path) -> None:
    """録画未開始の状態でstop()を呼んでも例外が発生しないことを確認する。"""
    recorder = Recorder(directory=tmp_path, fps=20.0, frame_size=(64, 48))

    recorder.stop()

    assert recorder.is_recording is False


def test_start_保存先ディレクトリが存在しない場合は作成される(tmp_path: Path) -> None:
    """保存先ディレクトリが存在しない場合に自動作成されることを確認する。"""
    target_dir = tmp_path / "nested" / "recordings"
    recorder = Recorder(directory=target_dir, fps=20.0, frame_size=(64, 48))

    recorder.start()
    recorder.stop()

    assert target_dir.is_dir()
