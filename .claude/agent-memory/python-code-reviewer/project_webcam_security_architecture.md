---
name: project-webcam-security-architecture
description: Windows防犯カメラプロジェクトのモジュール構成と異常系設計方針（design.md/requirements.mdの要点）
metadata:
  type: project
---

`src/webcam_security/`配下のモジュール構成と責務分担、異常系の設計方針。

- `config.py`: config.tomlを読み込みdataclass(frozen=True)の`AppConfig`(`DetectionConfig`/`StorageConfig`/`CameraConfig`)に変換。不正値は`ConfigError`で起動時に終了。
- `camera.py`: `Camera`クラスがcv2.VideoCaptureをラップ。コンテキストマネージャ対応(`__enter__`/`__exit__`)。読み取り失敗は`CameraError`（切断扱い）。
- `motion_detector.py`: `MotionDetector`がフレーム差分＋閾値二値化で動体検知。`_MIN_MOTION_AREA=500`px固定（解像度依存、設定ファイル化されていない）。
- `recorder.py`: `Recorder`がcv2.VideoWriterでMP4録画。`is_recording`プロパティで状態確認可。
- `live_view.py`: cv2.imshow/cv2.waitKeyの薄いラッパー関数群（クラスなし）。
- `storage_cleaner.py`: `clean_old_recordings(directory, retention_days, now=None)`でmtime基準に古いファイルを削除。`now`引数はテスト用注入。
- `main.py`: `run(config)`がメインループを統合。`CameraError`は伝播させて安全終了、`RecorderError`はその場で捕捉してループ継続。

**異常系の設計方針（design.md §4）**:
- カメラ切断・オープン失敗 → 例外を捕捉しエラーログ出力後、安全終了（自動再接続なし）
- 録画書き込み失敗（ディスク容量不足等） → 録画のみ中断、メインループ・ライブビューは継続
- config.toml不正 → 起動時に検証してエラー終了

**Why**: MVPスコープは単一USBカメラのみ、通知機能なし、保持期間7日固定（設定可）。将来`notifier.py`を追加予定（検知開始/終了タイミングがmain.pyの同一箇所に拡張ポイントとして用意されている）。

**How to apply**: このプロジェクトのコードレビュー時は、設計書§4の異常系方針と実装が一致しているかを必ず確認する。特に「ループ継続」を要求される箇所で例外が無捕捉のまま伝播していないか確認すること。関連: [[feedback_webcam_security_review_findings]]
