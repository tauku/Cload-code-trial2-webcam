# webcam-security

Windows上で動作する、USBカメラを用いた防犯カメラです。常時録画は行わず、
**動体検知時のみ録画**することでディスク容量を節約しつつ、検知時の映像を記録します。

## 主な機能

- USBカメラ（1台）からのリアルタイム映像取得
- フレーム差分による動体検知（感度は設定ファイルで調整可能）
- 動体検知時のみのMP4録画（検知が一定時間途切れたら録画停止）
- ライブビューウィンドウでの映像確認
- 保持期間（既定7日）を超えた録画ファイルの自動削除
- 動体検知中（検知が継続しクールダウン未経過の間）、スナップショット画像付きで
  Discordへ一定間隔ごとに繰り返し通知（任意機能。設定で有効/無効を切替可能。
  送信間隔・送信数上限も設定可能）

詳細な要件・設計は [docs/camera_function_development/requirements.md](docs/camera_function_development/requirements.md)、
[docs/camera_function_development/design.md](docs/camera_function_development/design.md) を参照してください。
Discord通知機能については
[docs/notification_function_development/requirements.md](docs/notification_function_development/requirements.md)、
[docs/notification_function_development/design.md](docs/notification_function_development/design.md)
を参照してください。さらに、通知のスナップショット送信タイミング・送信数上限
（レート制限）等の改良内容については
[docs/notification_improvement_development/requirements.md](docs/notification_improvement_development/requirements.md)、
[docs/notification_improvement_development/design.md](docs/notification_improvement_development/design.md)
を参照してください。

## 動作環境

- Windows
- Python 3.14.6 以上
- USBカメラ（Webカメラ）1台
- パッケージ管理: [uv](https://docs.astral.sh/uv/)（`pip`は使用しません）

## セットアップ

> **重要**: リポジトリにコミットされている `config.toml` は
> `notification.enabled = true`（Discord通知が有効）の状態になっています。
> そのため、**`.env` を用意せずに `uv sync` の後すぐ起動すると、後述の
> 「Discord通知機能を使う場合」の設定が完了するまで設定エラーで起動できません**。
> 通知機能を使わない場合は、`config.toml` の `notification.enabled` を
> `false` に変更してください（この場合 `.env` は不要です）。

1. [uv](https://docs.astral.sh/uv/getting-started/installation/) をインストールします。
2. 依存パッケージを同期します。

   ```powershell
   uv sync
   ```

   `opencv-python` 等の依存パッケージが `.venv` 配下にインストールされます。

### Discord通知機能を使う場合（既定で有効）

動体検知中にDiscordへ通知を送りたい場合は、以下の手順で設定します。
**前述の通り `config.toml` の `notification.enabled` は既定で `true` のため、
通知機能を使わない場合を除き、この手順は実質必須です。**
通知機能を使わない場合はこの手順は不要です（`config.toml` の
`notification.enabled` を `false` に変更すれば通知は行われず、`.env` も
不要になります）。

1. `.env.example` を `.env` にコピーします。

   ```powershell
   Copy-Item .env.example .env
   ```

2. コピーした `.env` を開き、`DISCORD_WEBHOOK_URL` に通知先のDiscord
   Webhook URLを設定します。

   ```
   DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/xxxx/xxxx
   ```

   `.env` は `.gitignore` 対象のため、設定したWebhook URLがリポジトリに
   コミットされることはありません。

3. `config.toml` の `[notification]` セクションで `enabled = true` を設定します
   （リポジトリ既定の `config.toml` では既に `true` になっているため、通常は
   変更不要です）。

   ```toml
   [notification]
   enabled = true
   ```

   `enabled = false` にすると通知機能自体が無効になり、`.env` の設定は
   不要です。**`enabled = true` にもかかわらず `.env` に
   `DISCORD_WEBHOOK_URL` が設定されていない場合は、起動時に設定エラーとなり
   プログラムが終了します**。

## 使い方

### 起動

プロジェクトルートに配置されている `config.toml` を設定したうえで、以下のコマンドで起動します。

```powershell
uv run python -m webcam_security.main
```

または、`pyproject.toml` の `project.scripts` に登録済みのコマンドでも起動できます。

```powershell
uv run webcam-security
```

### 操作方法

- 起動するとライブビューウィンドウにカメラ映像がリアルタイム表示されます。
- 動体を検知すると `recordings/` ディレクトリ（既定）に自動で録画が開始され、
  検知が途切れてから `cooldown_seconds` 秒後に録画が停止します。
- 終了するには、ライブビューウィンドウを選択した状態で **`q` キー** を押すか、
  コンソール上で **`Ctrl+C`** を入力します。いずれの場合もカメラとウィンドウの
  リソースは安全に解放されます。

### config.toml の設定項目

プロジェクトルートの `config.toml` でアプリの動作を設定します。

```toml
[detection]
sensitivity = 25      # フレーム差分の閾値（小さいほど高感度）
cooldown_seconds = 5  # 検知が途切れてから録画停止までの待機秒数

[storage]
directory = "recordings"
retention_days = 7

[camera]
device_index = 0

[notification]
enabled = true
snapshot_interval_seconds = 3   # 検知中にスナップショットを送信する間隔(秒)
rate_limit_window_seconds = 60  # 送信数上限を計算する時間窓(秒)
rate_limit_max_count = 10       # 上記時間窓内に送信できる通知の最大数
```

| セクション | 項目 | 説明 |
|---|---|---|
| `detection` | `sensitivity` | フレーム差分を二値化する際の閾値。値が小さいほど微小な変化にも反応する高感度設定になります。カメラの設置環境（照明・振動等）に応じて調整してください。 |
| `detection` | `cooldown_seconds` | 動体検知が途切れてから録画を停止するまでの待機秒数。 |
| `storage` | `directory` | 録画ファイル（`.mp4`）の保存先ディレクトリ。相対パスの場合、起動時のカレントディレクトリ基準で解釈されます。 |
| `storage` | `retention_days` | 録画ファイルの保持日数。この日数を超えたファイルは起動時および一定間隔ごとに自動削除されます。 |
| `camera` | `device_index` | 使用するUSBカメラのデバイス番号。通常は `0`（PCに1台のみ接続している場合）です。 |
| `notification` | `enabled` | 動体検知中のDiscord通知を有効にするかどうか。`true`の場合、`.env`の`DISCORD_WEBHOOK_URL`が必須になります（未設定時は起動時エラー）。省略した場合は`false`扱いです。値は`true`/`false`のTOMLブールリテラルで記述する必要があり、`"false"`のような文字列で記述すると起動時エラーになります。 |
| `notification` | `snapshot_interval_seconds` | 動体検知が継続している間（クールダウン未経過の間）、スナップショットをDiscordへ送信する間隔（秒）。検知開始時は間隔に関わらず即時に1枚送信されます。省略時は`3`。 |
| `notification` | `rate_limit_window_seconds` | 送信数上限（レート制限）を計算する時間窓（秒）。`rate_limit_max_count`とあわせて、一定時間内に送信できる通知数を制限します。省略時は`60`。 |
| `notification` | `rate_limit_max_count` | `rate_limit_window_seconds`の時間窓内に送信できる通知の最大数。これを超える送信はスキップされ、標準エラー出力にログが残ります（Discordへの代替通知・まとめ送信は行いません）。省略時は`10`。 |

`[notification]`セクション自体、および`snapshot_interval_seconds`・
`rate_limit_window_seconds`・`rate_limit_max_count`の3項目はいずれも省略可能です
（省略時は上記のデフォルト値が使われ、既存の`config.toml`との後方互換性があります）。

設定ファイルが存在しない、項目が不足している、または値の範囲・型が不正な場合は、
起動時にエラーメッセージを表示して終了します。

## ディレクトリ構成

```
.
├── src/webcam_security/   # メインのソースコード
│   ├── main.py              # CLIエントリポイント（メインループ）
│   ├── config.py             # config.tomlの読み込み・検証
│   ├── camera.py             # USBカメラの入出力ラッパー
│   ├── motion_detector.py    # フレーム差分による動体検知
│   ├── recorder.py           # MP4録画の開始/書き込み/停止
│   ├── live_view.py          # ライブビューウィンドウの表示
│   ├── storage_cleaner.py    # 保持期間超過ファイルの自動削除
│   └── notifier.py           # Discord Webhookへの検知通知（非同期送信）
├── tests/                  # テストコード（pytest）
├── docs/                   # ドキュメント（要件定義・設計・テスト結果・レビュー結果等）
│   ├── camera_function_development/         # 防犯カメラ本体の開発ドキュメント
│   ├── notification_function_development/   # Discord通知機能の開発ドキュメント
│   └── notification_improvement_development/ # Discord通知機能の改良（間隔送信・レート制限等）の開発ドキュメント
├── prompt_history/         # Claudeに入力したプロンプトの履歴
├── config.toml             # アプリの動作設定
├── .env.example            # Discord Webhook URL設定のテンプレート（.envとしてコピーして使用）
└── recordings/             # 録画ファイルの保存先（既定。.gitignore対象）
```

## 開発者向け情報

### テストの実行

```powershell
uv run pytest
```

実機（USBカメラ）やGUIウィンドウを使わずに検証できるよう、`cv2.VideoCapture`・
`cv2.imshow` 等はテスト内でモックしています。Discord通知機能についても
`requests.post`をモックする単体テストに加え、実機での送信確認（E2Eテスト）も
実施済みです。詳細は以下を参照してください。

- 防犯カメラ本体: [docs/camera_function_development/test_report.md](docs/camera_function_development/test_report.md) /
  [docs/camera_function_development/review.md](docs/camera_function_development/review.md)
- Discord通知機能（初期実装）: [docs/notification_function_development/requirements.md](docs/notification_function_development/requirements.md) /
  [docs/notification_function_development/design.md](docs/notification_function_development/design.md) /
  [docs/notification_function_development/test_report.md](docs/notification_function_development/test_report.md) /
  [docs/notification_function_development/review.md](docs/notification_function_development/review.md)
- Discord通知機能の改良（間隔送信・レート制限等）: [docs/notification_improvement_development/requirements.md](docs/notification_improvement_development/requirements.md) /
  [docs/notification_improvement_development/design.md](docs/notification_improvement_development/design.md) /
  [docs/notification_improvement_development/develop.md](docs/notification_improvement_development/develop.md) /
  [docs/notification_improvement_development/test_report.md](docs/notification_improvement_development/test_report.md) /
  [docs/notification_improvement_development/review.md](docs/notification_improvement_development/review.md)

### 開発ルール

- 回答・コメント・ドキュメントは日本語で記述します。
- パッケージ管理には `uv` を使用し、`pip install` は使用しません。
  - パッケージ追加: `uv add <package>`
  - スクリプト実行: `uv run python ...`
  - テスト実行: `uv run pytest`

詳細は [CLAUDE.md](CLAUDE.md) を参照してください。

## 既知の制限事項

- **単一カメラのみ対応**: 複数のUSBカメラを同時に監視する機能はありません
  （`camera.device_index` で指定した1台のみを使用します）。
- **Discord通知は検知継続中のみ**: 動体検知が継続している間（クールダウン未経過の間）、
  `snapshot_interval_seconds`の間隔でDiscordへ繰り返し通知します（検知開始時は
  間隔に関わらず即時に1枚送信されます）。検知**終了**時（クールダウン経過後）の
  追加通知は行いません（要件判断によるものです）。また、`rate_limit_window_seconds`・
  `rate_limit_max_count`で設定した送信数上限を超える通知はスキップされ、標準エラー
  出力にログが残るのみで、Discordへの代替通知・まとめ送信は行いません。
- **通知送信の失敗時にリトライは行いません**: Discordへの送信に失敗した場合は
  標準エラー出力にログを記録するのみで、再送は行いません。再送機構を実装しても
  USBカメラ・Windows PCという構成上有効に機能しないと判断し、スコープ外としています。
  詳細は [docs/notification_function_development/requirements.md](docs/notification_function_development/requirements.md)
  を参照してください。
- **チャットボット化・双方向通知は未対応**: Discord側からの操作（録画の停止指示等）は
  できません。一方向の通知のみです。
- **GUI常駐・システムトレイ常駐は非対応**: コマンドラインからの手動起動・停止を
  前提としています。
- そのほか既知の課題・改善提案は
  [docs/camera_function_development/review.md](docs/camera_function_development/review.md)、
  [docs/notification_function_development/review.md](docs/notification_function_development/review.md)、
  [docs/notification_improvement_development/review.md](docs/notification_improvement_development/review.md)
  を参照してください。
