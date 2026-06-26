# テスト結果報告（Windows防犯カメラ）

## 1. 単体テスト

`uv run pytest` で実行。実機（USBカメラ）やGUIウィンドウを使わずに検証できるよう、
`cv2.VideoCapture`・`cv2.imshow`等はモックして検証した。

```
32 passed in 0.33s
```

| ファイル | テスト内容 |
|---|---|
| `tests/test_config.py` | `config.toml`の正常読み込み、ファイル不在・項目不足・各設定値の境界値（0以下/負数）でConfigErrorが発生することを確認 |
| `tests/test_motion_detector.py` | 初回フレームはFalse、無変化フレームはFalse、大きな変化はTrue、感度を下げると微小変化を検知しないことを確認 |
| `tests/test_recorder.py` | 録画ファイルの作成・書き込み・ファイルサイズ、未開始でのwrite()時のRecorderError、保存先ディレクトリの自動作成を確認 |
| `tests/test_storage_cleaner.py` | 保持日数超過ファイルの削除、保持日数以内のファイルの保持、`.mp4`以外を対象外とすること、ディレクトリ不在時の挙動を確認 |
| `tests/test_camera.py` | カメラオープン失敗・フレーム取得失敗時のCameraError、正常時のフレーム取得・FPS取得、`with`文での解放を確認（`cv2.VideoCapture`をモック） |
| `tests/test_live_view.py` | `show`/`poll_quit_key`/`close`が対応するcv2関数を正しく呼び出すことを確認（cv2のGUI関数をモック） |
| `tests/test_main.py` | 設定エラー時に終了コード1で終了することを確認 |

## 2. 結合テスト
`recorder.py`の「ファイル作成→複数フレーム書き込み→停止→ファイルサイズ確認」(`test_recorder.py`)
で、検知→録画→保存の連携の一部を実際のファイルI/Oとして検証済み。

## 3. 実機テスト（完了・2026-06-25実施）
ユーザー側のPCでUSBカメラを接続し、`uv run python -m webcam_security.main`を実行して
以下を確認。**全項目パス。**

- [x] ライブビューウィンドウに実際の映像が表示される
- [x] 動体検知時にのみ録画が開始され、`recordings/`配下にmp4ファイルが作成される
- [x] 検知が途切れてから`cooldown_seconds`後に録画が停止する
- [x] `q`キー押下、Ctrl+Cで安全に終了する
- [x] カメラを物理的に切断した際にCameraErrorで安全終了する
- [x] 長時間稼働時の安定性（メモリ・CPU使用率）

## 4. 異常系テスト
- カメラ切断・オープン失敗、録画書き込み失敗、設定不正の3パターンは単体テストでカバー済み
  （`test_camera.py`, `test_main.py`、`recorder.write()`の例外パスは`test_recorder.py`参照）
- 実際のディスク容量不足の再現テストは行っていない（モックでの`RecorderError`発生確認に留まる）
