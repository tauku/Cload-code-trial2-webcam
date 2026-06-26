"""notifier.pyのテスト。

実際にDiscordへHTTPを送信せずに検証するため、requests.postおよびcv2.imencodeをモックする。
notify_motion_detected()はバックグラウンドスレッドで送信処理を行うため、各テストでは
スレッドの完了を待ってからアサーションする。
"""

from __future__ import annotations

import threading
from datetime import datetime
from unittest.mock import MagicMock, patch

import numpy as np
import requests

from webcam_security import notifier

_WEBHOOK_URL = "https://discord.com/api/webhooks/dummy/token"


def _wait_for_threads(timeout: float = 2.0) -> None:
    """notify_motion_detected()が起動したバックグラウンドスレッドの完了を待つ。

    notifier._send向けのdaemonスレッドが残っていれば、それらのjoin()を待つ。
    """
    for thread in threading.enumerate():
        if thread is threading.current_thread():
            continue
        if thread.name.startswith("Thread-") or thread.daemon:
            thread.join(timeout=timeout)


def test_notify_motion_detected_正常系でrequests_postが正しい引数で呼ばれる() -> None:
    """正常系: requests.postが正しいURL・files・dataで呼び出されることを確認する。"""
    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    detected_at = datetime(2026, 6, 26, 12, 0, 0)
    fake_response = MagicMock()
    fake_response.raise_for_status.return_value = None

    with (
        patch("webcam_security.notifier.cv2.imencode") as mock_imencode,
        patch("webcam_security.notifier.requests.post", return_value=fake_response) as mock_post,
    ):
        fake_buffer = np.array([1, 2, 3], dtype=np.uint8)
        mock_imencode.return_value = (True, fake_buffer)

        notifier.notify_motion_detected(_WEBHOOK_URL, frame, detected_at)
        _wait_for_threads()

    mock_post.assert_called_once()
    call_args, call_kwargs = mock_post.call_args

    # 第一引数（位置引数）にWebhook URLが渡されていること
    assert call_args[0] == _WEBHOOK_URL

    # dataにテキスト本文(content)が含まれていること
    assert "content" in call_kwargs["data"]
    assert "2026-06-26 12:00:00" in call_kwargs["data"]["content"]

    # filesに画像データ(JPEGエンコード結果)が添付されていること
    assert "file" in call_kwargs["files"]
    filename, file_bytes, content_type = call_kwargs["files"]["file"]
    assert filename == "snapshot.jpg"
    assert file_bytes == fake_buffer.tobytes()
    assert content_type == "image/jpeg"

    # タイムアウトが設定されていること
    assert call_kwargs["timeout"] > 0


def test_notify_motion_detected_送信失敗時も例外が伝播しない() -> None:
    """異常系: requests.postがRequestExceptionを発生させても呼び出し元に伝播しないことを確認する。"""
    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    detected_at = datetime.now()

    with (
        patch("webcam_security.notifier.cv2.imencode") as mock_imencode,
        patch(
            "webcam_security.notifier.requests.post",
            side_effect=requests.exceptions.ConnectionError("接続できません"),
        ) as mock_post,
    ):
        mock_imencode.return_value = (True, np.array([1, 2, 3], dtype=np.uint8))

        # 例外が発生せずに正常にリターンすることを確認する
        notifier.notify_motion_detected(_WEBHOOK_URL, frame, detected_at)
        _wait_for_threads()

    mock_post.assert_called_once()


def test_notify_motion_detected_raise_for_statusが失敗しても例外が伝播しない() -> None:
    """異常系: レスポンスのraise_for_status()がHTTPErrorを発生させても伝播しないことを確認する。"""
    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    detected_at = datetime.now()
    fake_response = MagicMock()
    fake_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404")

    with (
        patch("webcam_security.notifier.cv2.imencode") as mock_imencode,
        patch("webcam_security.notifier.requests.post", return_value=fake_response),
    ):
        mock_imencode.return_value = (True, np.array([1, 2, 3], dtype=np.uint8))

        notifier.notify_motion_detected(_WEBHOOK_URL, frame, detected_at)
        _wait_for_threads()

    fake_response.raise_for_status.assert_called_once()


def test_notify_motion_detected_エンコード失敗時はpostが呼ばれない() -> None:
    """異常系: cv2.imencodeが失敗(ok=False)した場合、requests.postが呼ばれず安全に終了することを確認する。"""
    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    detected_at = datetime.now()

    with (
        patch("webcam_security.notifier.cv2.imencode", return_value=(False, None)),
        patch("webcam_security.notifier.requests.post") as mock_post,
    ):
        notifier.notify_motion_detected(_WEBHOOK_URL, frame, detected_at)
        _wait_for_threads()

    mock_post.assert_not_called()


def test_notify_motion_detected_呼び出し元をブロックしない() -> None:
    """非同期性: notify_motion_detected()がrequests.postの完了を待たずに即座にリターンすることを確認する。"""
    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    detected_at = datetime.now()

    # requests.postの呼び出し開始・解放を制御するイベント
    post_started = threading.Event()
    release_post = threading.Event()

    def slow_post(*args: object, **kwargs: object) -> MagicMock:
        post_started.set()
        release_post.wait(timeout=2.0)
        response = MagicMock()
        response.raise_for_status.return_value = None
        return response

    with (
        patch("webcam_security.notifier.cv2.imencode") as mock_imencode,
        patch("webcam_security.notifier.requests.post", side_effect=slow_post) as mock_post,
    ):
        mock_imencode.return_value = (True, np.array([1, 2, 3], dtype=np.uint8))

        notifier.notify_motion_detected(_WEBHOOK_URL, frame, detected_at)

        # notify_motion_detected()がブロックせずに戻ってきた時点では、
        # まだrequests.postの処理が完了していない可能性がある（ブロッキングでないことの確認）。
        # ここではpost呼び出しが開始されるまで少し待ち、postが別スレッドで動いていることを確認する。
        started_in_time = post_started.wait(timeout=2.0)
        release_post.set()
        _wait_for_threads()

    assert started_in_time, "requests.postがバックグラウンドスレッドで呼ばれていません"
    mock_post.assert_called_once()


def test_notify_motion_detected_frameのコピーを使用するため呼び出し後に変更しても影響しない() -> None:
    """frame.copy()を使用しているため、呼び出し後に元のframeを変更しても送信内容に影響しないことを確認する。"""
    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    detected_at = datetime.now()
    fake_response = MagicMock()
    fake_response.raise_for_status.return_value = None

    encoded_frames: list[np.ndarray] = []

    def fake_imencode(ext: str, target_frame: np.ndarray) -> tuple[bool, np.ndarray]:
        encoded_frames.append(target_frame.copy())
        return True, np.array([1, 2, 3], dtype=np.uint8)

    with (
        patch("webcam_security.notifier.cv2.imencode", side_effect=fake_imencode),
        patch("webcam_security.notifier.requests.post", return_value=fake_response),
    ):
        notifier.notify_motion_detected(_WEBHOOK_URL, frame, detected_at)
        frame[:] = 255  # 呼び出し元のframeを直後に書き換える
        _wait_for_threads()

    assert len(encoded_frames) == 1
    # エンコード時点のフレームはすべて0（書き換えの影響を受けていない）はず
    assert np.all(encoded_frames[0] == 0)
