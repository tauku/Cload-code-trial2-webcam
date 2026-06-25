# 実装ファイル一覧（Windows防犯カメラ）

[設計書](design.md)に基づき実装した各ファイルの概要をまとめる。

## プロジェクト設定

| ファイル | 概要 |
|---|---|
| `pyproject.toml` | プロジェクト定義。依存に`opencv-python`、開発依存に`pytest`を追加済み |
| `config.toml` | アプリの動作設定（検知感度・クールダウン秒数・保存先・保持日数・カメラ番号） |
| `.gitignore` | `.venv/`・`recordings/`等をリポジトリ管理対象から除外 |

## `src/webcam_security/` 配下

| ファイル | 概要 |
|---|---|
| `__init__.py` | パッケージ初期化。`main.py`の`main`関数を再エクスポートし、CLIエントリポイント（`pyproject.toml`の`project.scripts`）から呼び出せるようにする |
| `config.py` | `config.toml`を読み込み、`DetectionConfig`/`StorageConfig`/`CameraConfig`/`AppConfig`に変換・検証する。値が不正な場合は`ConfigError`を発生させる |
| `camera.py` | `cv2.VideoCapture`をラップする`Camera`クラス。コンテキストマネージャでオープン/解放を行い、フレーム取得失敗時は`CameraError`を発生させる |
| `motion_detector.py` | `MotionDetector`クラス。前フレームとのグレースケール差分を二値化し、変化ピクセル数が閾値を超えたら動体ありと判定する |
| `recorder.py` | `Recorder`クラス。`cv2.VideoWriter`でMP4ファイルへ録画を開始/書き込み/停止する。失敗時は`RecorderError`を発生させる |
| `live_view.py` | `cv2.imshow`によるライブビュー表示、`cv2.waitKey`による`q`キー押下判定、ウィンドウ解放を行う関数群 |
| `storage_cleaner.py` | 指定ディレクトリ内の録画ファイル(`*.mp4`)のうち、保持日数を超えたものを削除する`clean_old_recordings`関数 |
| `main.py` | CLIエントリポイント。設定読み込み→カメラオープン→メインループ（ライブビュー表示・動体検知・録画開始/停止・定期クリーンアップ）→終了処理を統括する |

## モジュール間の関係
`main.py`が各モジュールを呼び出すオーケストレーターであり、他モジュール同士は
直接依存しない（[design.md](design.md) §2のアーキテクチャ方針通り）。

## 未実装（将来拡張予定）
- `notifier.py`: 検知時の外部通知。[design.md](design.md) §7に拡張ポイントを記載済みで、
  MVPでは実装しない。
