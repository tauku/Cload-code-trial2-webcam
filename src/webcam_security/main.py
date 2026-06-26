"""Windows防犯カメラのCLIエントリポイント。"""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from webcam_security import live_view, notifier
from webcam_security.camera import Camera, CameraError
from webcam_security.config import AppConfig, ConfigError, load_config
from webcam_security.motion_detector import MotionDetector
from webcam_security.recorder import Recorder, RecorderError
from webcam_security.storage_cleaner import clean_old_recordings

_DEFAULT_CONFIG_PATH = Path("config.toml")
_CLEANUP_INTERVAL_SECONDS = 3600.0


def run(config: AppConfig, webhook_url: str | None = None) -> None:
    """ライブビュー表示と動体検知録画のメインループを実行する。

    カメラ切断等でCameraErrorが発生した場合は呼び出し元に伝播し、
    プログラムを安全終了させる。録画の書き込み失敗(RecorderError)は
    ここで捕捉し、ライブビューとループは継続する。

    Args:
        config: `load_config`で読み込まれた検証済みのアプリケーション設定。
        webhook_url: Discord Webhook URL。`config.notification.enabled`が
            `True`かつ本値が指定されている場合のみ、検知開始時に通知を送信する。

    Raises:
        CameraError: カメラのオープンまたはフレーム取得に失敗した場合
            （切断の可能性がある）。

    Example:
        >>> config = load_config(Path("config.toml"))
        >>> run(config)  # 'q'キーまたはCtrl+Cまでブロックする
    """
    detector = MotionDetector(sensitivity=config.detection.sensitivity)
    recorder: Recorder | None = None
    last_motion_at: float | None = None
    last_cleanup_at = 0.0

    with Camera(config.camera.device_index) as camera:
        first_frame = camera.read()
        height, width = first_frame.shape[:2]
        fps = camera.get_fps()

        try:
            while True:
                now = time.monotonic()

                if now - last_cleanup_at >= _CLEANUP_INTERVAL_SECONDS:
                    clean_old_recordings(
                        config.storage.directory, config.storage.retention_days
                    )
                    last_cleanup_at = now

                frame = camera.read()
                live_view.show(frame)

                if detector.detect(frame):
                    last_motion_at = now
                    if recorder is None:
                        recorder = Recorder(config.storage.directory, fps, (width, height))
                        try:
                            recorder.start()
                        except RecorderError as e:
                            print(f"録画エラー: {e}", file=sys.stderr)
                            recorder = None
                        if config.notification.enabled and webhook_url:
                            notifier.notify_motion_detected(webhook_url, frame, datetime.now())

                if recorder is not None:
                    try:
                        recorder.write(frame)
                    except RecorderError as e:
                        print(f"録画エラー: {e}", file=sys.stderr)
                        recorder.stop()
                        recorder = None
                    else:
                        assert last_motion_at is not None
                        if now - last_motion_at >= config.detection.cooldown_seconds:
                            recorder.stop()
                            recorder = None

                if live_view.poll_quit_key():
                    break
        finally:
            if recorder is not None:
                recorder.stop()
            live_view.close()


def main() -> None:
    """CLIエントリポイント。`uv run python -m webcam_security.main`で起動する。

    カレントディレクトリの`config.toml`（および`.env`）を読み込み、
    メインループ(`run`)を実行する。設定エラー・カメラエラーが発生した場合は
    標準エラー出力にメッセージを出し、終了コード1で終了する。`Ctrl+C`による
    中断は正常終了として扱う。
    """
    load_dotenv()

    try:
        config = load_config(_DEFAULT_CONFIG_PATH)
    except ConfigError as e:
        print(f"設定エラー: {e}", file=sys.stderr)
        sys.exit(1)

    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if config.notification.enabled and not webhook_url:
        print(
            "設定エラー: notification.enabledがtrueですが"
            "DISCORD_WEBHOOK_URLが設定されていません（.envを確認してください）",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        run(config, webhook_url)
    except CameraError as e:
        print(f"カメラエラー: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("終了します")


if __name__ == "__main__":
    main()
