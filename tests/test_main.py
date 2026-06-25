"""main.pyのテスト。

カメラ実機やGUIウィンドウを使わずに検証できる、設定エラー時の終了処理のみを対象とする。
実機を用いたメインループの動作確認はdocs/test_report.mdに記載する。
"""

from unittest.mock import patch

import pytest

from webcam_security.config import ConfigError
from webcam_security.main import main


def test_main_設定エラー時は終了コード1で終了する() -> None:
    """load_config()がConfigErrorを発生させた場合、終了コード1で終了することを確認する。"""
    with patch("webcam_security.main.load_config", side_effect=ConfigError("不正な設定")):
        with pytest.raises(SystemExit) as exc_info:
            main()

    assert exc_info.value.code == 1
