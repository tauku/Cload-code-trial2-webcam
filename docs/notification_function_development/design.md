# 設計書（Discord通知機能）

[要件定義書](requirements.md)で合意した要件を実現するための設計をまとめる。
本機能は[docs/camera_function_development/design.md](../camera_function_development/design.md) §7で
残されていた拡張ポイント（挿入箇所・想定インターフェース・設定方法）を踏襲・具体化する。

## 1. 技術選定

| 項目 | 選定 | 理由 |
|---|---|---|
| HTTP送信 | `requests` (`uv add requests`) | Discord Webhookへの画像添付にはmultipart/form-data送信が必要。標準ライブラリの`urllib.request`では多段の手動実装が必要になるが、`requests`なら`files`引数だけで簡潔に実装できる |
| Webhook URLの管理 | `.env`ファイル + `python-dotenv` (`uv add python-dotenv`) | OS環境変数のみだとWindowsでの永続化（`setx`）が煩雑なため、`.env`（`.gitignore`対象）から`DISCORD_WEBHOOK_URL`を読み込む方式とする |
| 通知の非同期化 | `threading.Thread`（daemon） | 要件3.1「通知処理がメインループを妨げない」を満たすため、HTTP送信をバックグラウンドスレッドで実行し、メインループ（カメラ読み取り・録画書き込み）をブロックしない |

## 2. アーキテクチャ（モジュール構成）

`docs/camera_function_development/design.md`で計画済みの`notifier.py`を実装する。

```
src/webcam_security/
├── main.py     # load_dotenv()でDISCORD_WEBHOOK_URLを読み込み、検知開始時にnotifierへ委譲
├── config.py   # [notification]セクション（enabledのみ）を追加
└── notifier.py # 新規追加。Discord Webhookへの通知送信を担当
```

`main.py`はWebhook URLを保持するだけで具体的な送信方法（multipart構築・HTTPライブラリ）を知らず、
`notifier`モジュールに委譲する（[docs/camera_function_development/design.md](../camera_function_development/design.md) §7の方針通り）。

### 2.1 公開インターフェース（`notifier.py`）

```python
def notify_motion_detected(webhook_url: str, frame: np.ndarray, detected_at: datetime) -> None:
    """検知開始を非同期でDiscordに通知する。例外は内部で捕捉しログ出力のみ行う。"""
```

- `frame`はその時点のカメラフレーム（スナップショット用）。スレッドに渡す前に`frame.copy()`し、
  メインループ側が後続フレームで上書きしても送信内容に影響しないようにする
- 関数内で`threading.Thread(target=_send, args=(...), daemon=True).start()`し、即座に呼び出し元へ返る
- `_send`内で`cv2.imencode(".jpg", frame)`によりJPEGエンコードし、`requests.post`で
  `data={"content": ...}` / `files={"file": (...)}`として送信する

### 2.2 メインループへの組み込み（`main.py`）

- 起動時に`load_dotenv()`を呼び、`os.environ.get("DISCORD_WEBHOOK_URL")`でURLを取得する
- `config.notification.enabled`が`True`かつURLが取得できた場合のみ通知を行う
- 挿入箇所は[design.md §2.1](../camera_function_development/design.md)で示された「検知開始」タイミング、
  すなわち`if recorder is None:`で新規録画を開始する分岐の直後（「検知開始時のみ通知」の要件に対応）

### 2.3 設定（`config.toml`）

`[notification]`セクションを新設する。Webhook URL自体は機密情報のため**含めない**
（要件2.3、`.env`で管理）。

```toml
[notification]
enabled = true
```

### 2.4 環境変数（`.env`、`.gitignore`対象に追加）

```
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/xxxx/xxxx
```

- `.env.example`（値はダミー）をリポジトリにコミットし、セットアップ手順をREADMEに記載する
  （ドキュメント作成フェーズで対応）

## 3. 異常系設計

| 異常 | 挙動 |
|---|---|
| `config.notification.enabled = true`だが`.env`に`DISCORD_WEBHOOK_URL`が未設定 | `main.py`起動時に検証し、設定エラーとしてエラーログを出力して終了する（既存の`ConfigError`と同様の扱い） |
| Discord Webhookへの送信失敗（タイムアウト・接続エラー・4xx/5xxレスポンス） | `notifier.py`内で`requests.exceptions.RequestException`を捕捉し、標準エラー出力にログを残すのみ。リトライは行わない（要件2.4）。録画・検知のメインループには影響しない |
| JPEGエンコード失敗 | `_send`内で捕捉し、エラーログを出力して送信を中断する（メインループには伝播させない） |

`requests.post`には`timeout=5.0`を指定し、ネットワーク不調時でもスレッドが無期限に
残留しないようにする。

## 4. セキュリティ設計

- `DISCORD_WEBHOOK_URL`は`.env`でのみ管理し、`config.toml`・ログ・例外メッセージに
  生の値を含めない（例外ログには「送信失敗」とだけ出力し、URLは出力しない）
- `.env`を`.gitignore`に追加し、`.env.example`（ダミー値）のみをコミットする

## 5. 要件との対応確認

- 検知開始時のみ通知: §2.2（`recorder is None`分岐への組み込み）
- テキスト＋スナップショット画像: §2.1（`cv2.imencode`でのJPEG添付）
- Webhook URLを環境変数で管理: §1, §2.4
- 送信失敗時はログのみ・リトライなし: §3
- 主機能を妨げない: §1（`threading.Thread`による非同期化）、§3（`timeout`指定）
