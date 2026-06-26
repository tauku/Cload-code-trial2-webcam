"""main.pyのテスト。

カメラ実機やGUIウィンドウを使わずに検証できる、設定エラー時の終了処理のみを対象とする。
実機を用いたメインループの動作確認はdocs/test_report.mdに記載する。
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from webcam_security.config import (
    AppConfig,
    CameraConfig,
    ConfigError,
    DetectionConfig,
    NotificationConfig,
    StorageConfig,
)
from webcam_security.main import main


def _build_app_config(notification_enabled: bool) -> AppConfig:
    """テスト用のAppConfigを組み立てるヘルパー。"""
    return AppConfig(
        detection=DetectionConfig(sensitivity=25, cooldown_seconds=5.0),
        storage=StorageConfig(directory=Path("recordings"), retention_days=7),
        camera=CameraConfig(device_index=0),
        notification=NotificationConfig(enabled=notification_enabled),
    )


def test_main_設定エラー時は終了コード1で終了する() -> None:
    """load_config()がConfigErrorを発生させた場合、終了コード1で終了することを確認する。"""
    with patch("webcam_security.main.load_config", side_effect=ConfigError("不正な設定")):
        with pytest.raises(SystemExit) as exc_info:
            main()

    assert exc_info.value.code == 1


def test_main_notification_enabledがtrueでWebhook未設定の場合は終了コード1で終了する() -> None:
    """notification.enabled=trueかつDISCORD_WEBHOOK_URL未設定の場合、終了コード1で終了することを確認する。"""
    config = _build_app_config(notification_enabled=True)

    with (
        patch("webcam_security.main.load_config", return_value=config),
        patch("webcam_security.main.load_dotenv"),
        patch.dict("os.environ", {}, clear=True),
    ):
        with pytest.raises(SystemExit) as exc_info:
            main()

    assert exc_info.value.code == 1


def test_main_notification_enabledがtrueでもWebhook設定済みならrunが呼ばれる() -> None:
    """notification.enabled=trueでもDISCORD_WEBHOOK_URLが設定済みなら、run()が呼び出されることを確認する。"""
    config = _build_app_config(notification_enabled=True)

    with (
        patch("webcam_security.main.load_config", return_value=config),
        patch("webcam_security.main.load_dotenv"),
        patch.dict("os.environ", {"DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/x/y"}, clear=True),
        patch("webcam_security.main.run") as mock_run,
    ):
        main()

    mock_run.assert_called_once_with(config, "https://discord.com/api/webhooks/x/y")


def test_main_notification_enabledがfalseならWebhook未設定でも正常にrunが呼ばれる() -> None:
    """notification.enabled=falseの場合、DISCORD_WEBHOOK_URLが未設定でもエラーにならずrun()が呼ばれることを確認する。"""
    config = _build_app_config(notification_enabled=False)

    with (
        patch("webcam_security.main.load_config", return_value=config),
        patch("webcam_security.main.load_dotenv"),
        patch.dict("os.environ", {}, clear=True),
        patch("webcam_security.main.run") as mock_run,
    ):
        main()

    mock_run.assert_called_once_with(config, None)
