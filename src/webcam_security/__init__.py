"""Windows防犯カメラ（USBカメラを用いた動体検知録画）のパッケージ。

`main`関数を再エクスポートし、`pyproject.toml`の`project.scripts`
（`webcam-security`コマンド）や`uv run python -m webcam_security.main`
から呼び出せるようにする。
"""

from webcam_security.main import main

__all__ = ["main"]
