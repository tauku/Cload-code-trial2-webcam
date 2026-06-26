# Windows防犯カメラ 次期開発計画（通知機能）

## 背景
[plan.md](plan.md)に記載の通り、防犯カメラ本体（カメラ入力・動体検知・録画・ライブビュー・
ストレージ管理）は要件定義〜ドキュメント作成まで全フェーズが完了し、完成している。
[docs/camera_function_development/design.md](docs/camera_function_development/design.md) §7では
将来の拡張ポイントとして`notifier.py`の挿入箇所・想定インターフェースが既に設計に残されているが、
通知機能自体は本プロジェクトでは未実装。

## 通知方式の決定
検知時のスマートフォンへの通知手段として、メール／LINE／Discordを比較検討した結果、
**Discord Webhookを使用する**方針で合意した。

- LINE Notifyは2025年3月末で新規連携が終了しており利用不可。同等の機能を実現するには
  LINE Messaging API（Bot登録・サーバー側応答処理が必要）が必要となり実装コストが高い
- Discord Webhookは認証込みのURLへのHTTP POST一回で送信でき、検知時のスナップショット
  画像も添付可能。Discordモバイルアプリでプッシュ通知も受け取れる
- メール（SMTP）と比較しても実装難易度は同程度だが、スマホでの即時性・視認性は
  Discordの方が優れる

## 将来的な拡張の可能性
- いずれ、チャットボットを利用した通知機能（例: Discord Bot化、LINE Messaging API Bot等）
  を作成する可能性がある。Webhookによる一方向通知だけでなく、ユーザーからの応答
  （例: 録画確認コマンド、誤検知報告など）を受け付けられる双方向のやり取りを想定
- 現時点では構想段階であり、本フェーズではDiscord Webhookによる一方向通知の実装を優先する

## 開発体制
- 防犯カメラ本体は完成済みのため、通知機能（および将来のチャットボット機能）の開発は
  **別ブランチで実施する**。mainブランチの安定性を保ったまま、通知機能を独立して
  開発・テストできるようにする
- **進捗**: `feature/discord-notifier`ブランチを作成済み。以降の作業は本ブランチで行う。

## 開発フローの全体方針
[plan.md](plan.md)で採用した方針を踏襲する。

- 原則は順次進行（要件定義→設計→実装→テスト→レビュー→ドキュメント作成）とするが、
  **テスト・レビューで問題が発覚した場合は、該当する設計・実装フェーズに戻って修正する
  反復的なフローとする。**
- 各フェーズの終了時には、そのフェーズの完了条件を満たしていることを確認してから次フェーズへ進む。

```
要件定義 → 設計 → 実装 → テスト → レビュー → ドキュメント作成
              ↑________________|（NGの場合は設計/実装に戻る）
```

- 成果物ドキュメントは`docs/notification_function_development/`配下に保存する
  （`docs/camera_function_development/`は`plan.md`実行時専用のため、本計画用に新設する）。

## フェーズ詳細

### 1. 要件定義
ユーザーの要求から、どのような機能を作成するか検討・合意するフェーズ。

検討項目:
- 通知タイミング（検知開始時のみ／検知開始・終了の両方）
- 通知内容（テキストのみ／検知時刻・カメラ情報の付記／スナップショット画像の添付有無）
- Discord Webhook URLの取得方法・管理方法（`config.toml`の`[notification]`セクション、
  リポジトリへの誤コミット防止）
- 通知失敗時の挙動（録画・検知などの主機能を止めない）

完了条件: 上記の機能要件・非機能要件が一覧化され、ユーザーと合意できていること。

**進捗: 完了**。通知タイミング（検知開始時のみ）、通知内容（テキスト＋スナップショット画像）、
Webhook URL管理方法（環境変数）、送信失敗時の挙動（ログ記録のみ・リトライなし）を
ユーザーと合意し、[docs/notification_function_development/requirements.md](docs/notification_function_development/requirements.md)
にまとめた。

### 2. 設計
要件定義で合意した内容を、どのような方法で実装するか検討・決定するフェーズ。
[design.md](docs/camera_function_development/design.md) §7で既に決定済みの拡張ポイント
（挿入箇所＝`main.py`の検知開始/検知終了タイミング、想定インターフェース＝
`notifier`モジュールへの委譲、設定＝`config.toml`の`[notification]`セクション）を
踏襲・具体化する形で設計する。

検討項目:
- `notifier.py`のクラス/関数構成、`main.py`との接続方法
- Discord Webhook送信の実装方法（HTTPライブラリの選定、画像添付方法）
- 異常系設計（Webhook送信失敗時のリトライ有無、タイムアウト、ログ出力）
- セキュリティ設計（Webhook URLの管理方法、`.gitignore`対象にするか）

完了条件: 設計内容がドキュメント化され、要件定義の各項目を満たす設計になっていること。

**進捗: 完了**。HTTP送信に`requests`、Webhook URL管理に`.env`+`python-dotenv`を採用し、
`notifier.py`の公開インターフェース・`main.py`への組み込み箇所（検知開始時の`recorder is None`分岐）・
異常系・セキュリティ設計を
[docs/notification_function_development/design.md](docs/notification_function_development/design.md)
にまとめた。

### 3. 実装
設計に基づき、実際にコーディングを行うフェーズ。

方針:
- パッケージ追加は`uv add`を使用し、`pip install`は使用しない
- 設計で定めたモジュール単位で実装を進める

完了条件: 設計通りに主要機能が動作する状態になっていること。

**進捗: 完了**。`uv add requests python-dotenv`で依存を追加し、`src/webcam_security/notifier.py`
を新規実装。`config.py`に`NotificationConfig`（`[notification]`セクションは省略可能、既定`enabled=False`）
を追加し、`config.toml`に`[notification]`セクションを追加。`main.py`で`load_dotenv()`・
`DISCORD_WEBHOOK_URL`の検証・検知開始時(`recorder is None`分岐)の通知呼び出しを組み込んだ。
`.env.example`を追加し、`.gitignore`に`.env`を追加。既存のpytest 32件は全てパスすることを確認済み。

### 4. テスト
**test-engineer**が担当。
実装されたものが要件定義の要件を満たしているか、設計通り実装できているかをテストするフェーズ。

内容:
- 単体テスト: `uv run pytest`で実行。Discordへの実際のHTTP送信は行わず、モック化する
- 結合テスト: 検知→通知呼び出しの連携動作確認
- 異常系テスト: Webhook送信失敗・タイムアウト時のハンドリング確認

完了条件: 要件定義の機能・非機能要件を満たし、テストが全てパスしていること。
不合格の場合は実装または設計フェーズに戻って修正する。

**進捗: 完了**。`test-engineer`エージェントが`tests/test_notifier.py`（新規6件）、
`tests/test_config.py`・`tests/test_main.py`への追加（各3件）を実施し、`requests.post`・
`cv2.imencode`をモック化して実際のDiscordへの送信は行わずに検証した。既存32件と合わせて
**44件全てパス**。詳細は
[docs/notification_function_development/test_report.md](docs/notification_function_development/test_report.md)。
さらにユーザー側のPC・USBカメラ・実Discordサーバーによる実機E2Eテスト（4項目）も実施し、
**全項目パス**。

### 5. レビュー
**python-code-reviewer**が担当。
テスト完了したコードをレビューして、改善点やリスクなどをドキュメントにまとめるフェーズ。

観点:
- バグ・正確性、セキュリティリスク（Webhook URLの取り扱い等）、パフォーマンス
- 改善点・リスクをレビュー結果としてドキュメント化

完了条件: 致命的な問題が解消されていること。軽微な改善点は対応事項として記録し、
必要に応じて実装フェーズに戻る。

**進捗: 完了**。`python-code-reviewer`エージェントによるレビューを実施し、
[docs/notification_function_development/review.md](docs/notification_function_development/review.md)
にまとめた。致命的な問題はなし。重要な問題2点
（`config.py`の`enabled`のbool型検証漏れ、録画失敗時にも通知が送られる仕様の確認）が
見つかったが、ユーザー判断により**録画失敗時も通知する現状の挙動を仕様として確定**し、
**bool型検証漏れは今回は修正せず記録のみ**として、軽微な改善提案5点と合わせて
**今回は修正せず、いずれ対応する事項として記録した上でレビューを完了**とする。

### 6. ドキュメント作成
**doc-writer**が担当。
テスト・レビューの結果を受けて、コード内にdocstringを記載したり、README.mdに
通知機能の設定方法・操作方法を追記するフェーズ。

完了条件: README記載内容に従って第三者が通知機能をセットアップ・操作できることを
確認できる状態であること。

**進捗: 完了**。`doc-writer`エージェントにより、`notifier.py`/`config.py`/`main.py`の
docstring（Example・Args・Raises等）を補完し、`README.md`を更新した。
`.env`セットアップ手順、`config.toml`の`[notification].enabled`、ディレクトリ構成への
`notifier.py`/`.env.example`追加、既知の制限事項（検知終了時は通知しない・リトライなし・
双方向通知は未対応）を記載。旧`docs/design.md`等への古いリンクも
`docs/camera_function_development/`配下への移動に合わせて修正した。
`uv run pytest`44件、全てパス（ドキュメントのみの変更でロジックは未変更）。
これにより通知機能の開発フェーズ1〜6がすべて完了した。

## リスク
- Discord Webhook URLの漏洩（リポジトリへの誤コミット、ログ出力への混入）
- Discord側の障害・レート制限発生時の挙動
- 通知処理の失敗・遅延が録画・検知などの主機能の動作を妨げないこと

## 次のステップ
全フェーズ完了。Discord Webhook通知機能はマージ可能な状態になった。
