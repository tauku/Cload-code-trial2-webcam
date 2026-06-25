"""live_view.pyのテスト。

GUIウィンドウを実際に開かずに検証するため、cv2のGUI関連関数をモックする。
"""

from unittest.mock import patch

import numpy as np

from webcam_security import live_view


def test_show_imshowが呼ばれる() -> None:
    """show()がcv2.imshowを呼び出すことを確認する。"""
    frame = np.zeros((10, 10, 3), dtype=np.uint8)

    with patch("webcam_security.live_view.cv2.imshow") as mock_imshow:
        live_view.show(frame)

    mock_imshow.assert_called_once()
    assert mock_imshow.call_args.args[1] is frame


def test_poll_quit_key_qキー押下でTrue() -> None:
    """'q'キーが押された場合にTrueを返すことを確認する。"""
    with patch("webcam_security.live_view.cv2.waitKey", return_value=ord("q")):
        assert live_view.poll_quit_key() is True


def test_poll_quit_key_他のキーはFalse() -> None:
    """'q'以外のキーが押された場合にFalseを返すことを確認する。"""
    with patch("webcam_security.live_view.cv2.waitKey", return_value=ord("a")):
        assert live_view.poll_quit_key() is False


def test_close_destroyAllWindowsが呼ばれる() -> None:
    """close()がcv2.destroyAllWindowsを呼び出すことを確認する。"""
    with patch("webcam_security.live_view.cv2.destroyAllWindows") as mock_destroy:
        live_view.close()

    mock_destroy.assert_called_once()
