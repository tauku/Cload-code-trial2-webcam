"""Discord Webhookへの検知通知を行うモジュール。

動体検知開始時に、検知時刻とスナップショット画像をDiscordの指定Webhookへ
非同期（バックグラウンドスレッド）で送信する。送信失敗時はログ出力のみを行い、
呼び出し元（メインループ）には例外を伝播させない（要件2.4「主機能を妨げない」）。
"""

from __future__ import annotations

import sys
import threading
from datetime import datetime

import cv2
import numpy as np
import requests

_REQUEST_TIMEOUT_SECONDS = 5.0


def notify_motion_detected(webhook_url: str, frame: np.ndarray, detected_at: datetime) -> None:
    """動体検知開始をDiscordに非同期で通知する。

    HTTP送信をバックグラウンドスレッド（`daemon=True`）で実行するため、
    呼び出し元（メインループ）をブロックしない。スレッドに渡す前に`frame`を
    `copy()`しているため、呼び出し元がループ内で同じ`frame`変数を後続フレームで
    上書きしても、送信されるスナップショットには影響しない。送信に失敗した場合は
    標準エラー出力にログを残すのみで、リトライは行わない（呼び出し元には例外を
    伝播しない。要件2.4）。

    なお、本関数は検知**開始**時のみ呼び出すことを想定している。検知終了時の
    通知は要件上スコープ外であり、本関数では行わない。

    Args:
        webhook_url: 送信先のDiscord Webhook URL。`.env`の
            `DISCORD_WEBHOOK_URL`から取得した値を渡すことを想定している
            （Webhook URL自体は本関数内でログに出力されない）。
        frame: 検知時のカメラフレーム（スナップショットとして添付する）。
            BGR形式の`numpy.ndarray`（`cv2.VideoCapture.read()`が返す形式）。
        detected_at: 検知開始時刻。

    Example:
        >>> from datetime import datetime
        >>> notify_motion_detected(webhook_url, frame, datetime.now())
        >>> # 戻り値を待たずに即座に制御が返る（送信はバックグラウンドで継続）
    """
    snapshot = frame.copy()
    thread = threading.Thread(
        target=_send, args=(webhook_url, snapshot, detected_at), daemon=True
    )
    thread.start()


def _send(webhook_url: str, frame: np.ndarray, detected_at: datetime) -> None:
    """スナップショット付きの通知メッセージをDiscord Webhookへ送信する（内部関数）。

    `notify_motion_detected`が起動するバックグラウンドスレッドの実行本体。
    画像エンコードの失敗、およびHTTP送信時の例外（タイムアウト・接続エラー・
    Discord側のエラーレスポンス等）はいずれもこの関数内で捕捉し、標準エラー出力に
    ログを出すのみで呼び出し元には伝播させない。

    Args:
        webhook_url: 送信先のDiscord Webhook URL。
        frame: 添付するスナップショット画像（BGR形式）。呼び出し元の
            `notify_motion_detected`で既に`copy()`済みであることを前提とする。
        detected_at: 検知開始時刻（通知メッセージの本文に整形して含める）。
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
    except requests.exceptions.RequestException as e:
        print(f"通知エラー: Discordへの送信に失敗しました ({type(e).__name__})", file=sys.stderr)
