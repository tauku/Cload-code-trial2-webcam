# Windows防犯カメラ 通知機能改良計画

## 背景
[plan2.md](plan2.md)に記載の通り、Discord Webhookによる動体検知通知機能は
要件定義〜ドキュメント作成まで全フェーズが完了している。
[docs/notification_function_development/review.md](docs/notification_function_development/review.md)
のレビュー結果を踏まえ、ユーザーより以下2点の改良を行う方針が示された。

## 改良ポイント

### 1. review.mdの指摘内容の反映
[review.md](docs/notification_function_development/review.md)で指摘された以下の事項について、
本改良でどこまで対応するかを要件定義フェーズで確定する。

- 🟠 重要な問題
  - `config.py` — `enabled`の`bool()`変換が文字列の型ミスを検知できない
    （ユーザー判断により「動体検知時の画像送信の改良と同時に対応する」と保留されていた事項）
- 🟡 軽微な問題・改善提案
  - `notifier.py` — `daemon=True`により終了時に送信中の通知が中断される可能性
  - `notifier.py` — エラーログにHTTPステータスコード等の詳細が残らない
  - `config.toml` — `enabled = true`がデフォルトでコミットされている点のドキュメント化
  - `main.py` — エラーメッセージの文字列結合が読みにくい
  - `tests/test_notifier.py` — スレッド判定がCPython実装依存

### 2. 通知のスナップショット作成タイミング・送付回数の修正
現状（[notifier.py](src/webcam_security/notifier.py)・[main.py](src/webcam_security/main.py)）では、
動体検知による録画開始時（`recorder is None`の分岐）に1回だけ、その瞬間のフレームを
スナップショットとして送信している。この挙動について、どのタイミング・何回送付するのが
適切かをユーザーの利用シーンに基づき要件定義フェーズで具体化する。

## 開発体制
[plan2.md](plan2.md)に続き、`feature/discord-notifier`ブランチ上で改良作業を継続する。

## 開発フローの全体方針
[plan.md](plan.md)・[plan2.md](plan2.md)で採用した方針を踏襲する。

- 原則は順次進行（要件定義→設計→実装→テスト→レビュー→ドキュメント作成）とするが、
  **テスト・レビューで問題が発覚した場合は、該当する設計・実装フェーズに戻って修正する
  反復的なフローとする。**
- 各フェーズの終了時には、そのフェーズの完了条件を満たしていることを確認してから次フェーズへ進む。

```
要件定義 → 設計 → 実装 → テスト → レビュー → ドキュメント作成
              ↑________________|（NGの場合は設計/実装に戻る）
```

- 成果物ドキュメントは`docs/notification_improvement_development/`配下に保存する
  （`docs/notification_function_development/`は`plan2.md`実行時専用のため、本計画用に新設する）。

## フェーズ詳細

### 1. 要件定義
ユーザーの要求から、どのような改良を行うか検討・合意するフェーズ。

検討項目:
- review.mdの🟠・🟡指摘事項のうち、本改良で対応する範囲（全件対応／優先度の高いものに絞る等）
- スナップショットを撮影するタイミング（検知開始時のまま／検知中の一定間隔／検知終了時の追加送付等）
- 通知の送付回数（検知1回につき1通のまま／クールダウン中の再検知時の扱い／連続検知時の送信頻度制限の必要性）
- 上記変更に伴う既存の要件定義・設計ドキュメント（[requirements.md](docs/notification_function_development/requirements.md)・
  [design.md](docs/notification_function_development/design.md)）との差分の扱い

完了条件: 上記の改良要件が一覧化され、ユーザーと合意できていること。

成果物: [requirements.md](docs/notification_improvement_development/requirements.md)

**進捗: 完了**。

### 2. 設計
要件定義で合意した改良内容を、どのような方法で実装するか検討・決定するフェーズ。

検討項目:
- `config.py`の型検証ヘルパーの設計（`enabled`をbool型のみに限定する方法）
- スナップショット送付タイミング・送付回数変更に伴う`main.py`・`notifier.py`のインターフェース変更
- 軽微な改善提案（スレッドjoin、エラーログ詳細化等）への対応方法

完了条件: 設計内容がドキュメント化され、要件定義の各項目を満たす設計になっていること。

成果物: [design.md](docs/notification_improvement_development/design.md)

**進捗: 完了**。

### 3. 実装
設計に基づき、実際にコーディングを行うフェーズ。

方針:
- パッケージ追加は`uv add`を使用し、`pip install`は使用しない
- 設計で定めた変更単位で既存コードを修正する

完了条件: 設計通りに改良内容が動作する状態になっていること。

成果物: `config.toml`・`config.py`・`notifier.py`（`MotionNotifier`クラスへ再設計）・`main.py`の変更。
`uv run pytest`実行結果は38件成功・6件失敗（`tests/test_notifier.py`が旧関数API
`notify_motion_detected`を前提にしているため。次フェーズ（テスト）でtest-engineerが
新API（`MotionNotifier`クラス）に合わせて更新する）。

**進捗: 完了**。

### 4. テスト
**test-engineer**が担当。
改良内容が要件定義の要件を満たしているか、設計通り実装できているかをテストするフェーズ。

内容:
- 単体テスト: `uv run pytest`で実行。既存テストの回帰確認と改良箇所の追加テスト
- 結合テスト: 改良後の検知→通知の連携動作確認
- 異常系テスト: 型検証強化やタイミング変更による既存異常系ハンドリングへの影響確認

完了条件: 要件定義の機能・非機能要件を満たし、テストが全てパスしていること。
不合格の場合は実装または設計フェーズに戻って修正する。

**進捗: 未着手**。

### 5. レビュー
**python-code-reviewer**が担当。
テスト完了したコードをレビューして、改善点やリスクなどをドキュメントにまとめるフェーズ。

観点:
- バグ・正確性、セキュリティリスク、パフォーマンス
- review.mdの指摘事項が意図通り解消されているか

完了条件: 致命的な問題が解消されていること。軽微な改善点は対応事項として記録し、
必要に応じて実装フェーズに戻る。

**進捗: 未着手**。

### 6. ドキュメント作成
**doc-writer**が担当。
テスト・レビューの結果を受けて、コード内docstringやREADME.mdの該当箇所を更新するフェーズ。

完了条件: README記載内容に従って第三者が改良後の通知機能をセットアップ・操作できることを
確認できる状態であること。

**進捗: 未着手**。

## リスク
- スナップショット送付タイミング・送付回数の変更により、Discord側のレート制限に
  抵触する可能性
- `enabled`の型検証強化により、既存の`config.toml`記述次第で起動不可になる
  （後方互換性）可能性
- 通知処理の変更が録画・検知などの主機能の動作を妨げないこと

## 次のステップ
フェーズ1（要件定義）から着手し、改良内容の詳細をユーザーと合意する。
