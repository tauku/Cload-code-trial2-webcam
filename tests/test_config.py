"""config.pyのテスト。"""

from pathlib import Path

import pytest

from webcam_security.config import ConfigError, load_config

_VALID_TOML = """
[detection]
sensitivity = 25
cooldown_seconds = 5

[storage]
directory = "recordings"
retention_days = 7

[camera]
device_index = 0
"""


def test_load_config_正常系(tmp_path: Path) -> None:
    """正しいconfig.tomlから値を読み込めることを確認する。"""
    config_path = tmp_path / "config.toml"
    config_path.write_text(_VALID_TOML, encoding="utf-8")

    config = load_config(config_path)

    assert config.detection.sensitivity == 25
    assert config.detection.cooldown_seconds == 5
    assert config.storage.directory == Path("recordings")
    assert config.storage.retention_days == 7
    assert config.camera.device_index == 0


def test_load_config_ファイルが存在しない場合はConfigError(tmp_path: Path) -> None:
    """設定ファイルが存在しない場合にConfigErrorが発生することを確認する。"""
    config_path = tmp_path / "missing.toml"

    with pytest.raises(ConfigError):
        load_config(config_path)


def test_load_config_項目が不足している場合はConfigError(tmp_path: Path) -> None:
    """必須項目が欠けている場合にConfigErrorが発生することを確認する。"""
    config_path = tmp_path / "config.toml"
    config_path.write_text("[detection]\nsensitivity = 25\n", encoding="utf-8")

    with pytest.raises(ConfigError):
        load_config(config_path)


@pytest.mark.parametrize(
    "invalid_field_toml",
    [
        # sensitivityが0以下
        """
        [detection]
        sensitivity = 0
        cooldown_seconds = 5
        [storage]
        directory = "recordings"
        retention_days = 7
        [camera]
        device_index = 0
        """,
        # cooldown_secondsが負数
        """
        [detection]
        sensitivity = 25
        cooldown_seconds = -1
        [storage]
        directory = "recordings"
        retention_days = 7
        [camera]
        device_index = 0
        """,
        # retention_daysが0以下
        """
        [detection]
        sensitivity = 25
        cooldown_seconds = 5
        [storage]
        directory = "recordings"
        retention_days = 0
        [camera]
        device_index = 0
        """,
        # device_indexが負数
        """
        [detection]
        sensitivity = 25
        cooldown_seconds = 5
        [storage]
        directory = "recordings"
        retention_days = 7
        [camera]
        device_index = -1
        """,
    ],
)
def test_load_config_境界値の不正値はConfigError(tmp_path: Path, invalid_field_toml: str) -> None:
    """各設定値が許容範囲外の場合にConfigErrorが発生することを確認する。"""
    config_path = tmp_path / "config.toml"
    config_path.write_text(invalid_field_toml, encoding="utf-8")

    with pytest.raises(ConfigError):
        load_config(config_path)


def test_load_config_notificationセクションが無い場合はenabledがFalse(tmp_path: Path) -> None:
    """[notification]セクションを省略した場合、enabledがFalseになることを確認する（既存設定との後方互換性）。"""
    config_path = tmp_path / "config.toml"
    config_path.write_text(_VALID_TOML, encoding="utf-8")

    config = load_config(config_path)

    assert config.notification.enabled is False


def test_load_config_notification_enabledがtrueの場合は正しく読み込まれる(tmp_path: Path) -> None:
    """[notification]セクションでenabled = trueを指定した場合、正しく読み込まれることを確認する。"""
    config_path = tmp_path / "config.toml"
    config_path.write_text(_VALID_TOML + "\n[notification]\nenabled = true\n", encoding="utf-8")

    config = load_config(config_path)

    assert config.notification.enabled is True


def test_load_config_notification_enabledがfalseの場合は正しく読み込まれる(tmp_path: Path) -> None:
    """[notification]セクションでenabled = falseを明示した場合、Falseとして読み込まれることを確認する。"""
    config_path = tmp_path / "config.toml"
    config_path.write_text(_VALID_TOML + "\n[notification]\nenabled = false\n", encoding="utf-8")

    config = load_config(config_path)

    assert config.notification.enabled is False
