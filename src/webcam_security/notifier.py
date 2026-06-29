"""Discord Webhookへの検知通知を行うモジュール。

動体検知が継続している間、検知時刻とスナップショット画像をDiscordの指定Webhookへ
一定間隔ごとに非同期（バックグラウンドスレッド）で送信する。送信失敗時はログ出力のみを行い、
呼び出し元（メインループ）には例外を伝播させない（要件2.4「主機能を妨げない」）。
"""

from __future__ import annotations

import sys
import threading
from collections import deque
from datetime import datetime

import cv2
import numpy as np
import requests

_REQUEST_TIMEOUT_SECONDS = 5.0


class MotionNotifier:
    """検知継続中のスナップショット送信間隔・送信数上限(レート制限)を管理する。

    検知開始時に呼び出し元が`notify_if_due`を呼ぶと即時に送信され、以降は
    `snapshot_interval_seconds`間隔でのみ実際の送信が行われる。さらに
    `rate_limit_window_seconds`間に送信できる通知数を`rate_limit_max_count`で
    制限し、超過分は送信せずログ出力のみ行う。
    """

    def __init__(
        self,
        webhook_url: str,
        snapshot_interval_seconds: float,
        rate_limit_window_seconds: float,
        rate_limit_max_count: int,
    ) -> None:
        """MotionNotifierを生成する。

        Args:
            webhook_url: 送信先のDiscord Webhook URL。
            snapshot_interval_seconds: 検知継続中にスナップショットを送信する間隔(秒)。
            rate_limit_window_seconds: 送信数上限を計算する時間窓(秒)。
            rate_limit_max_count: 上記時間窓内に送信できる通知の最大数。
        """
        self._webhook_url = webhook_url
        self._snapshot_interval_seconds = snapshot_interval_seconds
        self._rate_limit_window_seconds = rate_limit_window_seconds
        self._rate_limit_max_count = rate_limit_max_count
        self._last_sent_at: float | None = None
        self._sent_history: deque[float] = deque()
        self._threads: list[threading.Thread] = []

    def notify_if_due(self, frame: np.ndarray, now: float) -> None:
        """検知継続中に呼び出す。送信間隔・送信数上限を満たしていれば送信する。

        送信間隔未達の場合は何もしない。送信数上限に達している場合は送信を
        スキップし、標準エラー出力にログを残す。

        Args:
            frame: 現在のカメラフレーム（スナップショット用）。BGR形式の
                `numpy.ndarray`。
            now: `time.monotonic()`基準の現在時刻。送信間隔・レート制限の
                判定に使用する（実時刻ではない）。
        """
        if (
            self._last_sent_at is not None
            and now - self._last_sent_at < self._snapshot_interval_seconds
        ):
            return

        self._prune_history(now)
        if len(self._sent_history) >= self._rate_limit_max_count:
            print(
                "通知エラー: 送信数の上限に達したため通知をスキップしました",
                file=sys.stderr,
            )
            return

        self._last_sent_at = now
        self._sent_history.append(now)
        self._dispatch(frame)

    def reset(self) -> None:
        """検知終了時に呼び出す。次回検知開始時に即時送信されるようにする。"""
        self._last_sent_at = None

    def join_pending(self, timeout: float = 2.0) -> None:
        """終了処理時に呼び出す。送信中の通知スレッドを待つ。

        Args:
            timeout: 各スレッドを待つ最大秒数。
        """
        for thread in self._threads:
            thread.join(timeout=timeout)

    def _prune_history(self, now: float) -> None:
        while (
            self._sent_history
            and now - self._sent_history[0] > self._rate_limit_window_seconds
        ):
            self._sent_history.popleft()

    def _dispatch(self, frame: np.ndarray) -> None:
        snapshot = frame.copy()
        thread = threading.Thread(
            target=_send, args=(self._webhook_url, snapshot, datetime.now()), daemon=True
        )
        self._threads = [t for t in self._threads if t.is_alive()]
        self._threads.append(thread)
        thread.start()


def _send(webhook_url: str, frame: np.ndarray, detected_at: datetime) -> None:
    """スナップショット付きの通知メッセージをDiscord Webhookへ送信する（内部関数）。

    `MotionNotifier._dispatch`が起動するバックグラウンドスレッドの実行本体。
    画像エンコードの失敗、およびHTTP送信時の例外（タイムアウト・接続エラー・
    Discord側のエラーレスポンス等）はいずれもこの関数内で捕捉し、標準エラー出力に
    ログを出すのみで呼び出し元には伝播させない。

    Args:
        webhook_url: 送信先のDiscord Webhook URL。
        frame: 添付するスナップショット画像（BGR形式）。呼び出し元の
            `MotionNotifier._dispatch`で既に`copy()`済みであることを前提とする。
        detected_at: 撮影時刻（通知メッセージの本文に整形して含める）。
    """
    ok, buffer = cv2.imencode(".jpg", frame)
    if not ok:
        print("通知エラー: スナップショット画像のエンコードに失敗しました", file=sys.stderr)
        return

    content = f"動体を検知しました（{detected_at.strftime('%Y-%m-%d %H:%M:%S')}）"
    files = {"file": ("snapshot.jpg", buffer.tobytes(), "image/jpeg")}

    try:
        response = requests.post(
            webhook_url,
            data={"content": content},
            files=files,
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else None
        print(
            f"通知エラー: Discordへの送信に失敗しました ({type(e).__name__}, status={status})",
            file=sys.stderr,
        )
    except requests.exceptions.RequestException as e:
        print(f"通知エラー: Discordへの送信に失敗しました ({type(e).__name__})", file=sys.stderr)
