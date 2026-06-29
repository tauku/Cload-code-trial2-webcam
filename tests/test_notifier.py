"""notifier.pyのテスト。

実際にDiscordへHTTPを送信せずに検証するため、requests.postおよびcv2.imencodeをモックする。
MotionNotifier.notify_if_due()はバックグラウンドスレッドで送信処理を行うため、
各テストではスレッドの完了を待ってからアサーションする。
"""

from __future__ import annotations

import threading
from unittest.mock import MagicMock, patch

import numpy as np
import requests

from webcam_security import notifier

_WEBHOOK_URL = "https://discord.com/api/webhooks/dummy/token"


def _wait_for_threads(timeout: float = 2.0) -> None:
    """MotionNotifier.notify_if_due()が起動したバックグラウンドスレッドの完了を待つ。

    notifier._send向けのdaemonスレッドが残っていれば、それらのjoin()を待つ。
    スレッド判定はdaemon属性のみで行う（review.md 🟡#7対応。CPython実装依存の
    name.startswith("Thread-")判定は使用しない）。
    """
    for thread in threading.enumerate():
        if thread is threading.current_thread():
            continue
        if thread.daemon:
            thread.join(timeout=timeout)


def _make_notifier(
    snapshot_interval_seconds: float = 3.0,
    rate_limit_window_seconds: float = 60.0,
    rate_limit_max_count: int = 10,
) -> notifier.MotionNotifier:
    """テスト用のMotionNotifierを組み立てるヘルパー。"""
    return notifier.MotionNotifier(
        _WEBHOOK_URL,
        snapshot_interval_seconds,
        rate_limit_window_seconds,
        rate_limit_max_count,
    )


def test_notify_if_due_正常系でrequests_postが正しい引数で呼ばれる() -> None:
    """正常系: 初回呼び出しでrequests.postが正しいURL・files・dataで呼び出されることを確認する。"""
    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    target = _make_notifier()
    fake_response = MagicMock()
    fake_response.raise_for_status.return_value = None

    with (
        patch("webcam_security.notifier.cv2.imencode") as mock_imencode,
        patch("webcam_security.notifier.requests.post", return_value=fake_response) as mock_post,
    ):
        fake_buffer = np.array([1, 2, 3], dtype=np.uint8)
        mock_imencode.return_value = (True, fake_buffer)

        target.notify_if_due(frame, now=0.0)
        _wait_for_threads()

    mock_post.assert_called_once()
    call_args, call_kwargs = mock_post.call_args

    # 第一引数（位置引数）にWebhook URLが渡されていること
    assert call_args[0] == _WEBHOOK_URL

    # dataにテキスト本文(content)が含まれていること
    assert "content" in call_kwargs["data"]
    assert "動体を検知しました" in call_kwargs["data"]["content"]

    # filesに画像データ(JPEGエンコード結果)が添付されていること
    assert "file" in call_kwargs["files"]
    filename, file_bytes, content_type = call_kwargs["files"]["file"]
    assert filename == "snapshot.jpg"
    assert file_bytes == fake_buffer.tobytes()
    assert content_type == "image/jpeg"

    # タイムアウトが設定されていること
    assert call_kwargs["timeout"] > 0


def test_notify_if_due_間隔未経過なら2回目の呼び出しはスキップされる() -> None:
    """送信間隔: 初回送信後、間隔未経過の2回目呼び出しではrequests.postが呼ばれないことを確認する。"""
    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    target = _make_notifier(snapshot_interval_seconds=3.0)
    fake_response = MagicMock()
    fake_response.raise_for_status.return_value = None

    with (
        patch("webcam_security.notifier.cv2.imencode") as mock_imencode,
        patch("webcam_security.notifier.requests.post", return_value=fake_response) as mock_post,
    ):
        mock_imencode.return_value = (True, np.array([1, 2, 3], dtype=np.uint8))

        target.notify_if_due(frame, now=0.0)
        _wait_for_threads()
        target.notify_if_due(frame, now=1.0)  # 間隔(3.0秒)未経過
        _wait_for_threads()

    mock_post.assert_called_once()


def test_notify_if_due_間隔経過後の呼び出しは再度送信される() -> None:
    """送信間隔: 間隔経過後に呼び出すと再度requests.postが呼ばれることを確認する。"""
    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    target = _make_notifier(snapshot_interval_seconds=3.0)
    fake_response = MagicMock()
    fake_response.raise_for_status.return_value = None

    with (
        patch("webcam_security.notifier.cv2.imencode") as mock_imencode,
        patch("webcam_security.notifier.requests.post", return_value=fake_response) as mock_post,
    ):
        mock_imencode.return_value = (True, np.array([1, 2, 3], dtype=np.uint8))

        target.notify_if_due(frame, now=0.0)
        _wait_for_threads()
        target.notify_if_due(frame, now=1.0)  # 間隔未経過(スキップ)
        _wait_for_threads()
        target.notify_if_due(frame, now=3.5)  # 間隔(3.0秒)経過
        _wait_for_threads()

    assert mock_post.call_count == 2


def test_notify_if_due_レート制限上限到達後はスキップされログが出る(capsys: object) -> None:
    """送信数上限: 時間窓内に上限回数送信した後の呼び出しはスキップされ、標準エラー出力にログが出ることを確認する。"""
    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    # 間隔0秒・時間窓60秒・上限2回 として、間隔の影響を受けずにレート制限のみ検証する
    target = _make_notifier(
        snapshot_interval_seconds=0.0, rate_limit_window_seconds=60.0, rate_limit_max_count=2
    )
    fake_response = MagicMock()
    fake_response.raise_for_status.return_value = None

    with (
        patch("webcam_security.notifier.cv2.imencode") as mock_imencode,
        patch("webcam_security.notifier.requests.post", return_value=fake_response) as mock_post,
    ):
        mock_imencode.return_value = (True, np.array([1, 2, 3], dtype=np.uint8))

        target.notify_if_due(frame, now=0.0)
        _wait_for_threads()
        target.notify_if_due(frame, now=1.0)
        _wait_for_threads()
        target.notify_if_due(frame, now=2.0)  # 上限(2回)に到達済みのためスキップ
        _wait_for_threads()

    assert mock_post.call_count == 2
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    assert "通知エラー" in captured.err
    assert "上限" in captured.err


def test_notify_if_due_時間窓を過ぎれば再度送信できる() -> None:
    """送信数上限: 時間窓を過ぎたタイムスタンプは除去され、再度送信できることを確認する。"""
    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    target = _make_notifier(
        snapshot_interval_seconds=0.0, rate_limit_window_seconds=10.0, rate_limit_max_count=1
    )
    fake_response = MagicMock()
    fake_response.raise_for_status.return_value = None

    with (
        patch("webcam_security.notifier.cv2.imencode") as mock_imencode,
        patch("webcam_security.notifier.requests.post", return_value=fake_response) as mock_post,
    ):
        mock_imencode.return_value = (True, np.array([1, 2, 3], dtype=np.uint8))

        target.notify_if_due(frame, now=0.0)
        _wait_for_threads()
        target.notify_if_due(frame, now=1.0)  # 時間窓(10秒)内かつ上限(1回)到達のためスキップ
        _wait_for_threads()
        target.notify_if_due(frame, now=20.0)  # 時間窓を過ぎているため再度送信できる
        _wait_for_threads()

    assert mock_post.call_count == 2


def test_reset_呼び出し後は間隔を無視して即時送信される() -> None:
    """reset(): 呼び出し後の次回notify_if_dueが、間隔未経過であっても即時送信されることを確認する。"""
    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    target = _make_notifier(snapshot_interval_seconds=3.0)
    fake_response = MagicMock()
    fake_response.raise_for_status.return_value = None

    with (
        patch("webcam_security.notifier.cv2.imencode") as mock_imencode,
        patch("webcam_security.notifier.requests.post", return_value=fake_response) as mock_post,
    ):
        mock_imencode.return_value = (True, np.array([1, 2, 3], dtype=np.uint8))

        target.notify_if_due(frame, now=0.0)
        _wait_for_threads()
        target.reset()
        target.notify_if_due(frame, now=0.5)  # 間隔(3.0秒)未経過だがreset済みのため即時送信される
        _wait_for_threads()

    assert mock_post.call_count == 2


def test_join_pending_送信中のスレッドを待つ() -> None:
    """join_pending(): 送信中のバックグラウンドスレッドの完了を待つことを確認する。"""
    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    target = _make_notifier()

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

        target.notify_if_due(frame, now=0.0)

        # notify_if_due()がブロックせずに戻ってきた時点では、まだrequests.postの
        # 処理が完了していない可能性がある（ブロッキングでないことの確認）。
        started_in_time = post_started.wait(timeout=2.0)
        release_post.set()
        target.join_pending(timeout=2.0)

    assert started_in_time, "requests.postがバックグラウンドスレッドで呼ばれていません"
    mock_post.assert_called_once()


def test_notify_if_due_送信失敗時も例外が伝播しない() -> None:
    """異常系: requests.postがRequestExceptionを発生させても呼び出し元に伝播しないことを確認する。"""
    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    target = _make_notifier()

    with (
        patch("webcam_security.notifier.cv2.imencode") as mock_imencode,
        patch(
            "webcam_security.notifier.requests.post",
            side_effect=requests.exceptions.ConnectionError("接続できません"),
        ) as mock_post,
    ):
        mock_imencode.return_value = (True, np.array([1, 2, 3], dtype=np.uint8))

        # 例外が発生せずに正常にリターンすることを確認する
        target.notify_if_due(frame, now=0.0)
        _wait_for_threads()

    mock_post.assert_called_once()


def test_notify_if_due_raise_for_statusが失敗しても例外が伝播せずstatus_codeがログに残る(
    capsys: object,
) -> None:
    """異常系: HTTPError発生時に例外が伝播せず、ログにstatus_codeが含まれることを確認する。"""
    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    target = _make_notifier()
    fake_response = MagicMock()
    fake_response.status_code = 404
    http_error = requests.exceptions.HTTPError("404")
    http_error.response = fake_response
    fake_response.raise_for_status.side_effect = http_error

    with (
        patch("webcam_security.notifier.cv2.imencode") as mock_imencode,
        patch("webcam_security.notifier.requests.post", return_value=fake_response),
    ):
        mock_imencode.return_value = (True, np.array([1, 2, 3], dtype=np.uint8))

        target.notify_if_due(frame, now=0.0)
        _wait_for_threads()

    fake_response.raise_for_status.assert_called_once()
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    assert "通知エラー" in captured.err
    assert "404" in captured.err


def test_notify_if_due_エンコード失敗時はpostが呼ばれない() -> None:
    """異常系: cv2.imencodeが失敗(ok=False)した場合、requests.postが呼ばれず安全に終了することを確認する。"""
    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    target = _make_notifier()

    with (
        patch("webcam_security.notifier.cv2.imencode", return_value=(False, None)),
        patch("webcam_security.notifier.requests.post") as mock_post,
    ):
        target.notify_if_due(frame, now=0.0)
        _wait_for_threads()

    mock_post.assert_not_called()


def test_notify_if_due_frameのコピーを使用するため呼び出し後に変更しても影響しない() -> None:
    """frame.copy()を使用しているため、呼び出し後に元のframeを変更しても送信内容に影響しないことを確認する。"""
    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    target = _make_notifier()
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
        target.notify_if_due(frame, now=0.0)
        frame[:] = 255  # 呼び出し元のframeを直後に書き換える
        _wait_for_threads()

    assert len(encoded_frames) == 1
    # エンコード時点のフレームはすべて0（書き換えの影響を受けていない）はず
    assert np.all(encoded_frames[0] == 0)
