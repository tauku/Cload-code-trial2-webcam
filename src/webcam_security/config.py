"""設定ファイル(config.toml)の読み込みと検証を行うモジュール。"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path


class ConfigError(Exception):
    """設定ファイルが存在しない、または内容が不正な場合に発生する例外。"""


@dataclass(frozen=True)
class DetectionConfig:
    """動体検知に関する設定値。

    Attributes:
        sensitivity: フレーム差分を二値化する際の閾値。値が小さいほど
            微小な変化にも反応しやすくなる（高感度）。
        cooldown_seconds: 動体検知が途切れてから録画を停止するまでの
            待機秒数。
    """

    sensitivity: int
    cooldown_seconds: float


@dataclass(frozen=True)
class StorageConfig:
    """録画ファイルの保存・保持に関する設定値。

    Attributes:
        directory: 録画ファイル(.mp4)の保存先ディレクトリ。
        retention_days: 録画ファイルの保持日数。これを超えたファイルは
            `storage_cleaner.clean_old_recordings`により自動削除される。
    """

    directory: Path
    retention_days: int


@dataclass(frozen=True)
class CameraConfig:
    """カメラに関する設定値。

    Attributes:
        device_index: 使用するUSBカメラのデバイス番号
            （`cv2.VideoCapture`に渡すインデックス）。
    """

    device_index: int


@dataclass(frozen=True)
class NotificationConfig:
    """Discord通知に関する設定値。

    Webhook URLなどの機密情報は`config.toml`では管理しない（`.env`の
    `DISCORD_WEBHOOK_URL`で管理する）。`[notification]`セクションは
    省略可能で、省略した場合は通知を無効として扱う。

    Attributes:
        enabled: 検知時のDiscord通知を有効にするかどうか。
    """

    enabled: bool


@dataclass(frozen=True)
class AppConfig:
    """アプリケーション全体の設定値。

    `load_config`によって生成される、検証済みの設定値のまとまり。

    Attributes:
        detection: 動体検知に関する設定値。
        storage: 録画ファイルの保存・保持に関する設定値。
        camera: カメラに関する設定値。
        notification: Discord通知に関する設定値。
    """

    detection: DetectionConfig
    storage: StorageConfig
    camera: CameraConfig
    notification: NotificationConfig


def load_config(path: Path) -> AppConfig:
    """config.tomlを読み込み、検証済みの設定値を返す。

    Args:
        path: config.tomlのパス。

    Returns:
        検証済みのAppConfig。

    Raises:
        ConfigError: ファイルが存在しない、項目が不足している、
            または値の形式・範囲が不正な場合。

    Example:
        >>> from pathlib import Path
        >>> config = load_config(Path("config.toml"))
        >>> config.detection.sensitivity
        25
    """
    if not path.is_file():
        raise ConfigError(f"設定ファイルが見つかりません: {path}")

    with path.open("rb") as f:
        raw = tomllib.load(f)

    try:
        detection_raw = raw["detection"]
        storage_raw = raw["storage"]
        camera_raw = raw["camera"]

        detection = DetectionConfig(
            sensitivity=int(detection_raw["sensitivity"]),
            cooldown_seconds=float(detection_raw["cooldown_seconds"]),
        )
        storage = StorageConfig(
            directory=Path(str(storage_raw["directory"])),
            retention_days=int(storage_raw["retention_days"]),
        )
        camera = CameraConfig(device_index=int(camera_raw["device_index"]))
        notification_raw = raw.get("notification", {})
        notification = NotificationConfig(enabled=bool(notification_raw.get("enabled", False)))
    except KeyError as e:
        raise ConfigError(f"設定項目が不足しています: {e}") from e
    except (TypeError, ValueError) as e:
        raise ConfigError(f"設定値の形式が不正です: {e}") from e

    if detection.sensitivity <= 0:
        raise ConfigError("detection.sensitivityは正の値である必要があります")
    if detection.cooldown_seconds < 0:
        raise ConfigError("detection.cooldown_secondsは0以上である必要があります")
    if storage.retention_days <= 0:
        raise ConfigError("storage.retention_daysは正の値である必要があります")
    if camera.device_index < 0:
        raise ConfigError("camera.device_indexは0以上である必要があります")

    return AppConfig(
        detection=detection, storage=storage, camera=camera, notification=notification
    )
