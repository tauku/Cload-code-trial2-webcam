"""Discord Webhookへの検知通知を行うモジュール。"""

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

    HTTP送信をバックグラウンドスレッドで実行するため、呼び出し元（メインループ）を
    ブロックしない。送信に失敗した場合は標準エラー出力にログを残すのみで、
    リトライは行わない（呼び出し元には伝播しない）。

    Args:
        webhook_url: 送信先のDiscord Webhook URL。
        frame: 検知時のカメラフレーム（スナップショットとして添付する）。
        detected_at: 検知開始時刻。

    Example:
        >>> notify_motion_detected(webhook_url, frame, datetime.now())
    """
    snapshot = frame.copy()
    thread = threading.Thread(
        target=_send, args=(webhook_url, snapshot, detected_at), daemon=True
    )
    thread.start()


def _send(webhook_url: str, frame: np.ndarray, detected_at: datetime) -> None:
    """スナップショット付きの通知メッセージをDiscord Webhookへ送信する。"""
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
