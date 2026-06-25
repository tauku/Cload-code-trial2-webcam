"""storage_cleaner.pyのテスト。"""

import os
from datetime import datetime, timedelta
from pathlib import Path

from webcam_security.storage_cleaner import clean_old_recordings


def _touch_with_age(path: Path, days_old: int, now: datetime) -> None:
    """指定した経過日数になるようファイルの更新日時を設定する。"""
    path.write_bytes(b"dummy")
    timestamp = (now - timedelta(days=days_old)).timestamp()
    os.utime(path, (timestamp, timestamp))


def test_保持日数を超えたファイルは削除される(tmp_path: Path) -> None:
    """retention_daysを超えた古いファイルが削除されることを確認する。"""
    now = datetime.now()
    old_file = tmp_path / "old.mp4"
    _touch_with_age(old_file, days_old=10, now=now)

    removed = clean_old_recordings(tmp_path, retention_days=7, now=now)

    assert old_file in removed
    assert not old_file.exists()


def test_保持日数以内のファイルは削除されない(tmp_path: Path) -> None:
    """retention_days以内の新しいファイルは削除されないことを確認する。"""
    now = datetime.now()
    recent_file = tmp_path / "recent.mp4"
    _touch_with_age(recent_file, days_old=1, now=now)

    removed = clean_old_recordings(tmp_path, retention_days=7, now=now)

    assert removed == []
    assert recent_file.exists()


def test_mp4以外のファイルは対象外(tmp_path: Path) -> None:
    """拡張子が.mp4以外のファイルは削除対象にならないことを確認する。"""
    now = datetime.now()
    other_file = tmp_path / "old.txt"
    _touch_with_age(other_file, days_old=10, now=now)

    removed = clean_old_recordings(tmp_path, retention_days=7, now=now)

    assert removed == []
    assert other_file.exists()


def test_ディレクトリが存在しない場合は空リストを返す(tmp_path: Path) -> None:
    """保存先ディレクトリが存在しない場合に空リストを返すことを確認する。"""
    missing_dir = tmp_path / "missing"

    removed = clean_old_recordings(missing_dir, retention_days=7)

    assert removed == []
