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


def test_load_config_notification_enabledのみの場合は新規3項目がデフォルト値になる(
    tmp_path: Path,
) -> None:
    """[notification]セクションがenabledのみの場合、snapshot_interval_seconds等が
    デフォルト値(3.0 / 60.0 / 10)になることを確認する（既存config.tomlとの後方互換性）。"""
    config_path = tmp_path / "config.toml"
    config_path.write_text(_VALID_TOML + "\n[notification]\nenabled = true\n", encoding="utf-8")

    config = load_config(config_path)

    assert config.notification.snapshot_interval_seconds == 3.0
    assert config.notification.rate_limit_window_seconds == 60.0
    assert config.notification.rate_limit_max_count == 10


def test_load_config_notificationセクション省略時も新規3項目がデフォルト値になる(
    tmp_path: Path,
) -> None:
    """[notification]セクション自体を省略した場合も、新規3項目がデフォルト値になることを確認する。"""
    config_path = tmp_path / "config.toml"
    config_path.write_text(_VALID_TOML, encoding="utf-8")

    config = load_config(config_path)

    assert config.notification.snapshot_interval_seconds == 3.0
    assert config.notification.rate_limit_window_seconds == 60.0
    assert config.notification.rate_limit_max_count == 10


def test_load_config_notification新規3項目を明示指定すると正しく読み込まれる(
    tmp_path: Path,
) -> None:
    """snapshot_interval_seconds等の新規3項目を明示指定した場合、正しく読み込まれることを確認する。"""
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        _VALID_TOML
        + "\n[notification]\n"
        + "enabled = true\n"
        + "snapshot_interval_seconds = 5\n"
        + "rate_limit_window_seconds = 30\n"
        + "rate_limit_max_count = 4\n",
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.notification.snapshot_interval_seconds == 5.0
    assert config.notification.rate_limit_window_seconds == 30.0
    assert config.notification.rate_limit_max_count == 4


def test_load_config_notification_enabledに文字列を指定するとConfigError(
    tmp_path: Path,
) -> None:
    """enabled = "false"のような文字列(TOMLとしては文字列型)を指定した場合、
    ConfigErrorが発生することを確認する（review.md 🟠#1の修正確認）。"""
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        _VALID_TOML + '\n[notification]\nenabled = "false"\n', encoding="utf-8"
    )

    with pytest.raises(ConfigError):
        load_config(config_path)


def test_load_config_notification_enabledに整数を指定するとConfigError(
    tmp_path: Path,
) -> None:
    """enabled = 1のような整数(bool型でない)を指定した場合、ConfigErrorが発生することを確認する。"""
    config_path = tmp_path / "config.toml"
    config_path.write_text(_VALID_TOML + "\n[notification]\nenabled = 1\n", encoding="utf-8")

    with pytest.raises(ConfigError):
        load_config(config_path)


@pytest.mark.parametrize(
    "invalid_notification_toml",
    [
        # snapshot_interval_secondsが0
        "\n[notification]\nenabled = true\nsnapshot_interval_seconds = 0\n",
        # snapshot_interval_secondsが負数
        "\n[notification]\nenabled = true\nsnapshot_interval_seconds = -1\n",
        # rate_limit_window_secondsが0
        "\n[notification]\nenabled = true\nrate_limit_window_seconds = 0\n",
        # rate_limit_window_secondsが負数
        "\n[notification]\nenabled = true\nrate_limit_window_seconds = -1\n",
        # rate_limit_max_countが0
        "\n[notification]\nenabled = true\nrate_limit_max_count = 0\n",
        # rate_limit_max_countが負数
        "\n[notification]\nenabled = true\nrate_limit_max_count = -1\n",
    ],
)
def test_load_config_notification新規3項目に0以下の値を指定するとConfigError(
    tmp_path: Path, invalid_notification_toml: str
) -> None:
    """snapshot_interval_seconds等の新規3項目に0以下の値を指定した場合、
    ConfigErrorが発生することを確認する。"""
    config_path = tmp_path / "config.toml"
    config_path.write_text(_VALID_TOML + invalid_notification_toml, encoding="utf-8")

    with pytest.raises(ConfigError):
        load_config(config_path)
