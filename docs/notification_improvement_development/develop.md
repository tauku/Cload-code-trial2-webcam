# 実装ファイル一覧（通知機能改良）

[設計書](design.md)に基づき実装した各ファイルの概要をまとめる。本書は
[既存のdevelop.md](../notification_function_development/develop.md)に対する
**変更点のみ**を記載する差分ドキュメントである。

## プロジェクト設定

| ファイル | 概要 |
|---|---|
| `config.toml` | `[notification]`セクションに`snapshot_interval_seconds`(3秒)・`rate_limit_window_seconds`(60秒)・`rate_limit_max_count`(10通)の3項目を追加 |

## `src/webcam_security/` 配下

| ファイル | 概要 |
|---|---|
| `notifier.py`（再設計） | 関数`notify_motion_detected`を廃止し、状態を持つ`MotionNotifier`クラスを新設。`notify_if_due(frame, now)`が送信間隔・送信数上限(レート制限)を判定し、満たしていれば内部の`_dispatch`が`threading.Thread`でバックグラウンド送信する。送信数上限に達した場合は送信をスキップし標準エラー出力にログを残す。`reset()`で検知終了時に間隔の基準時刻をクリアし、次回検知開始時に即時送信されるようにする。`join_pending()`で終了時に送信中のスレッドを待つ。内部関数`_send`は`HTTPError`発生時に`status_code`をログへ含めるよう変更 |
| `config.py`（変更） | `NotificationConfig`に`snapshot_interval_seconds`・`rate_limit_window_seconds`・`rate_limit_max_count`（いずれもデフォルト値あり、省略可能）を追加。`enabled`の検証を`bool()`から`_require_bool`（`isinstance`による厳密な型チェック）に変更し、TOMLの記述ミス（文字列の`"false"`等）を検知できるようにした。新規3項目には0以下の値を拒否する範囲検証を追加 |
| `main.py`（変更） | 通知の発火条件を「録画中(`recorder is not None`)」から「検知継続中（`last_motion_at`からクールダウン未経過）」に変更。これにより録画失敗時も通知する既存の挙動を保ったまま、検知継続中は`MotionNotifier.notify_if_due`を毎フレーム呼び出し、間隔・上限を満たした時だけ実際に送信されるようにした。クールダウン経過後は`reset()`を呼び、次回検知開始時の即時送信を保証する。終了処理(`finally`)で`motion_notifier.join_pending()`を呼び、送信中の通知スレッドを待つようにした。設定エラーメッセージの文字列結合に読点を追加し可読性を改善 |

## モジュール間の関係
[既存design.md](../notification_function_development/design.md)で示された
「`main.py`はWebhook送信の具体的な実装を知らず、`notifier`モジュールに委譲する」という
方針は変更していない。送信タイミング・レート制限の状態管理が`MotionNotifier`インスタンスに
集約された点が今回の変更点。

## review.md指摘事項への対応状況
- 🟠#1（`enabled`のbool型検証）・🟡#3（終了時のスレッドjoin）・🟡#4（HTTPエラー詳細ログ）・
  🟡#6（エラーメッセージの文字列結合）は本実装で対応済み。
- 🟡#5（README記載）はドキュメント作成フェーズ、🟡#7（テストのスレッド判定簡略化）は
  テストフェーズでそれぞれ対応する（[requirements.md](requirements.md) §2参照）。

## スコープ外（今回未実装）
- 検知終了時の追加通知
- 上限到達によりスキップした通知の、上限解除後のまとめ送信
- 送信失敗時のリトライ
