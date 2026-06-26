# webcam-security

Windows上で動作する、USBカメラを用いた防犯カメラです。常時録画は行わず、
**動体検知時のみ録画**することでディスク容量を節約しつつ、検知時の映像を記録します。

## 主な機能

- USBカメラ（1台）からのリアルタイム映像取得
- フレーム差分による動体検知（感度は設定ファイルで調整可能）
- 動体検知時のみのMP4録画（検知が一定時間途切れたら録画停止）
- ライブビューウィンドウでの映像確認
- 保持期間（既定7日）を超えた録画ファイルの自動削除

詳細な要件・設計は [docs/requirements.md](docs/requirements.md)、
[docs/design.md](docs/design.md) を参照してください。

## 動作環境

- Windows
- Python 3.14.6 以上
- USBカメラ（Webカメラ）1台
- パッケージ管理: [uv](https://docs.astral.sh/uv/)（`pip`は使用しません）

## セットアップ

1. [uv](https://docs.astral.sh/uv/getting-started/installation/) をインストールします。
2. 依存パッケージを同期します。

   ```powershell
   uv sync
   ```

   `opencv-python` 等の依存パッケージが `.venv` 配下にインストールされます。

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
```

| セクション | 項目 | 説明 |
|---|---|---|
| `detection` | `sensitivity` | フレーム差分を二値化する際の閾値。値が小さいほど微小な変化にも反応する高感度設定になります。カメラの設置環境（照明・振動等）に応じて調整してください。 |
| `detection` | `cooldown_seconds` | 動体検知が途切れてから録画を停止するまでの待機秒数。 |
| `storage` | `directory` | 録画ファイル（`.mp4`）の保存先ディレクトリ。相対パスの場合、起動時のカレントディレクトリ基準で解釈されます。 |
| `storage` | `retention_days` | 録画ファイルの保持日数。この日数を超えたファイルは起動時および一定間隔ごとに自動削除されます。 |
| `camera` | `device_index` | 使用するUSBカメラのデバイス番号。通常は `0`（PCに1台のみ接続している場合）です。 |

設定ファイルが存在しない、項目が不足している、または値の範囲が不正な場合は、
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
│   └── storage_cleaner.py    # 保持期間超過ファイルの自動削除
├── tests/                  # テストコード（pytest）
├── docs/                   # ドキュメント（要件定義・設計・テスト結果・レビュー結果等）
├── prompt_history/         # Claudeに入力したプロンプトの履歴
├── config.toml             # アプリの動作設定
└── recordings/             # 録画ファイルの保存先（既定。.gitignore対象）
```

## 開発者向け情報

### テストの実行

```powershell
uv run pytest
```

実機（USBカメラ）やGUIウィンドウを使わずに検証できるよう、`cv2.VideoCapture`・
`cv2.imshow` 等はテスト内でモックしています。詳細は
[docs/test_report.md](docs/test_report.md) を参照してください。

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
- **通知機能は未実装**: 動体検知時にデスクトップ通知やメール等で知らせる機能は
  現時点では実装されていません。録画によって検知の記録のみを残します。
  将来追加する場合の拡張ポイントは [docs/design.md](docs/design.md) の
  §7「将来の拡張ポイント: 通知モジュール」に記載されています。
- **GUI常駐・システムトレイ常駐は非対応**: コマンドラインからの手動起動・停止を
  前提としています。
- そのほか既知の課題・改善提案は [docs/review.md](docs/review.md) を参照してください。
