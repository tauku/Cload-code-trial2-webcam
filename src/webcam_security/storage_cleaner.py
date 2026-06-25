"""保持期間を超えた録画ファイルを自動削除するモジュール。"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path


def clean_old_recordings(
    directory: Path, retention_days: int, now: datetime | None = None
) -> list[Path]:
    """保持期間を超えた録画ファイル(.mp4)を削除する。

    Args:
        directory: 録画ファイルの保存先ディレクトリ。存在しない場合は何もしない。
        retention_days: 保持日数。最終更新日時からこの日数を超えたファイルを削除する。
        now: 現在時刻（テスト用に注入可能。省略時は実時刻）。

    Returns:
        削除したファイルのパス一覧。
    """
    if not directory.is_dir():
        return []

    now = now or datetime.now()
    cutoff = now - timedelta(days=retention_days)

    removed: list[Path] = []
    for path in directory.glob("*.mp4"):
        modified_at = datetime.fromtimestamp(path.stat().st_mtime)
        if modified_at < cutoff:
            path.unlink()
            removed.append(path)

    return removed
