# 実装ファイル一覧（Discord Webhook通知機能）

[設計書](design.md)に基づき実装した各ファイルの概要をまとめる。

## プロジェクト設定

| ファイル | 概要 |
|---|---|
| `pyproject.toml` | 依存に`requests`（Discord WebhookへのHTTP送信）・`python-dotenv`（`.env`読み込み）を追加済み |
| `config.toml` | `[notification]`セクション（`enabled`）を追加。Webhook URL自体は含めない |
| `.env.example` | `DISCORD_WEBHOOK_URL`のテンプレート（ダミー値）。実際の`.env`は`.gitignore`対象 |
| `.gitignore` | `.env`を追加し、Webhook URLがリポジトリにコミットされないようにした |

## `src/webcam_security/` 配下

| ファイル | 概要 |
|---|---|
| `notifier.py`（新規） | `notify_motion_detected(webhook_url, frame, detected_at)`を公開。`threading.Thread`でバックグラウンド送信し、メインループをブロックしない。内部の`_send`で`cv2.imencode`によりJPEGエンコードし、`requests.post`でテキスト＋スナップショット画像をmultipart送信する。送信失敗・エンコード失敗は標準エラー出力にログを出すのみで例外を伝播させない（リトライなし） |
| `config.py`（変更） | `NotificationConfig`（`enabled: bool`）を追加。`[notification]`セクションは省略可能で、省略時は`enabled=False`（既存`config.toml`との後方互換性） |
| `main.py`（変更） | `main()`で`load_dotenv()`を呼び`DISCORD_WEBHOOK_URL`環境変数を取得。`notification.enabled=true`なのに未設定の場合は設定エラーとして終了コード1。`run()`の検知開始タイミング（`recorder is None`分岐の直後）で`notifier.notify_motion_detected`を呼び出す |

## モジュール間の関係
[design.md](../camera_function_development/design.md) §7で計画されていた拡張ポイント通り、
`main.py`はWebhook送信の具体的な実装を知らず、`notifier`モジュールに委譲する。
`notifier.py`は他モジュールに依存しない（`config.py`/`main.py`からのみ参照される）。

## スコープ外（今回未実装）
- 検知終了時の通知
- 送信失敗時のリトライ
- チャットボット化・双方向通知（[plan2.md](../../plan2.md)の将来拡張を参照）
