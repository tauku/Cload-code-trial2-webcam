# レビュー結果（Discord Webhook通知機能）

`python-code-reviewer`エージェントにより、Discord Webhook通知機能の新規・変更分
（`src/webcam_security/notifier.py`（新規） / `config.py`（変更） / `main.py`（変更） /
`config.toml` / `.env.example` / `.gitignore` / `tests/test_notifier.py`（新規） /
`tests/test_config.py`・`tests/test_main.py`（追加分））を
バグ・セキュリティ・パフォーマンスの観点でレビューした。

前提として[requirements.md](requirements.md)・[design.md](design.md)・
[test_report.md](test_report.md)を確認済み。防犯カメラ本体側の既存レビュー
（[docs/camera_function_development/review.md](../camera_function_development/review.md)）
で指摘された問題パターン（OpenCV API特有の落とし穴、bool/int型検証漏れ等）も踏まえて確認した。

## 🔴 致命的な問題
なし。

## 🟠 重要な問題

### 1. `config.py` — `enabled`の`bool()`変換が文字列の型ミスを検知できない
`load_config`の129行目:

```python
notification = NotificationConfig(enabled=bool(notification_raw.get("enabled", False)))
```

`int()`/`float()`変換とは異なり、`bool()`は「真偽として評価可能な値」を常に
受け入れてしまうため、TOMLの記述ミスを検知できない。具体的には、ユーザーが
クォートを付けて`enabled = "false"`と書いてしまった場合（TOML的には文字列）、
`bool("false")`は空文字列でない限り`True`になるため、**「無効化したつもりが
実際は有効化される」**という、意図と正反対の挙動になる。実際に確認:

```python
>>> bool("false")
True
```

これは既存メモリに記録されている「`int()`/`float()`がbool値をすり抜けさせる」
パターンの逆方向（文字列が`bool()`をすり抜けて意図通りに変換されない）であり、
本プロジェクトのconfig.py検証ロジック全体に共通する弱点と言える。

→ 対応: `isinstance(value, bool)`で明示的に型を確認するか、許容する値を
`True`/`False`の実際の`bool`型のみに限定する検証ヘルパーを導入する。
（例: `if not isinstance(raw_enabled, bool): raise ConfigError(...)`）

### 2. `main.py` 76-77行目 — 録画開始に失敗していても通知が送られる
```python
if recorder is None:
    recorder = Recorder(config.storage.directory, fps, (width, height))
    try:
        recorder.start()
    except RecorderError as e:
        print(f"録画エラー: {e}", file=sys.stderr)
        recorder = None
    if config.notification.enabled and webhook_url:
        notifier.notify_motion_detected(webhook_url, frame, datetime.now())
```

`recorder.start()`が`RecorderError`で失敗し`recorder = None`に戻された
ケースでも、その直後の通知ブロックはインデントが揃っているだけで`try/except`
の外にあるため、条件を問わず無条件に実行される。つまり、**録画が実際には
開始できていない（ディスクフルや権限エラー等）状況でも、Discordには
「検知しました」という通知とスナップショットが送られてしまう**。

要件上「検知開始時のみ通知する」とあり、録画成否は通知条件として明記
されていないため厳密には要件違反ではないが、防犯カメラの利用シーンを
考えると、録画に失敗した検知についてユーザーに気づかせる用途としては
「通知は届くが録画ファイルは存在しない」という不整合が運用上混乱を招く
可能性がある。

→ 対応: 録画失敗時にも通知を送る方が望ましいのか（「録画は失敗したが検知は
あった」と知らせる目的なら現状の挙動で問題ない）、それとも録画成功時のみ
通知すべきかをユーザーに確認し、必要であれば`recorder is not None`の
条件を通知呼び出しに追加する。**仕様判断であり実装ミスではない可能性もある
ため、確認が必要。**

## 🟡 軽微な問題・改善提案

### 3. `notifier.py` — `daemon=True`によりプロセス終了時に送信中の通知が中断される可能性
`notify_motion_detected`が起動するスレッドは`daemon=True`のため、メインプロセスが
（`q`キーやCtrl+Cで）終了する際、送信処理（`requests.post`）の途中であっても
スレッドは強制終了され、通知が送信されないまま終わる可能性がある。
動体検知直後にプログラムが終了するケースは稀だが、`main.py`の`finally`ブロックに
進行中の通知スレッドを`join()`で待つ処理は無い。

→ 対応: 必須ではないが、終了処理時に進行中の通知スレッド一覧を短いタイムアウト付きで
`join()`する仕組みを`run()`の`finally`に追加すると、終了直前の検知も確実に通知できる。
要件2.4「主機能を妨げない」を優先する設計判断であれば現状のままでも問題ない
（**運用上の優先度を確認した上で対応するかどうかを判断**）。

### 4. `notifier.py` 56-57行目 — エラーログにHTTPステータスコード等の詳細が残らない
```python
except requests.exceptions.RequestException as e:
    print(f"通知エラー: Discordへの送信に失敗しました ({type(e).__name__})", file=sys.stderr)
```
例外の型名のみをログ出力しており、Webhook URLを含めない設計（要件2.3・design.md §4）
は適切に守られている。一方で、`response.raise_for_status()`が`HTTPError`を出した
場合でも型名（`HTTPError`）のみで、実際のステータスコード（401/404/429等）が
ログに残らないため、運用時のトラブルシュート（Webhook URLの失効か、レート制限か等の
切り分け）がしづらい。

→ 対応: `HTTPError`発生時は`e.response.status_code`をログに含める
（Webhook URL自体ではないため機密情報の漏洩にはならない）。
例: `f"通知エラー: Discordへの送信に失敗しました ({type(e).__name__}, status={getattr(e.response, 'status_code', None)})"`

### 5. `config.toml` — `enabled = true`がデフォルトでコミットされている
リポジトリの`config.toml`自体は`.gitignore`対象外（要件2.3で意図的な設計）であり、
そこに`enabled = true`が直接書かれている。新規にこのリポジトリをクローンした
利用者が`.env`を用意せずに起動すると、`main.py`の起動時チェックにより
即座に終了コード1で停止する（設計上想定通りの安全側フォールバックであり、
バグではない）。ただし、初見の利用者にとっては「config.tomlだけ見て動かそうとして
原因不明のエラーで落ちる」という体験になりうる。

→ 対応: 問題ではないが、README等のセットアップ手順に「`.env`の準備が必須」
であることを明記しておくと利用者の混乱を防げる（ドキュメント側で対応済みか確認）。

### 6. `main.py` 117-123行目 — エラーメッセージの文字列結合
```python
print(
    "設定エラー: notification.enabledがtrueですが"
    "DISCORD_WEBHOOK_URLが設定されていません（.envを確認してください）",
    file=sys.stderr,
)
```
隣接文字列リテラルの暗黙連結により「trueですがDISCORD_WEBHOOK_URLが」と
読点・スペースなしで連結されてしまい、出力されるメッセージの可読性がやや低い。
機能上の問題はないが、ユーザー（運用者）がエラーメッセージを読む場面なので
読みやすさは多少影響する。

→ 対応: 文字列の間に半角スペースまたは読点を補う
（例: `"...enabledがtrueですが、DISCORD_WEBHOOK_URLが..."`）。

### 7. `tests/test_notifier.py` — `_wait_for_threads`のスレッド判定がCPython実装依存
```python
if thread.name.startswith("Thread-") or thread.daemon:
    thread.join(timeout=timeout)
```
`threading.Thread(daemon=True)`で生成されたスレッドは`thread.daemon`が`True`に
なるため、実質`or thread.daemon`の条件だけで捕捉できる。`name.startswith("Thread-")`
は冗長で、デフォルト名の付け方（CPythonの実装詳細）に依存している。
現状のテストは全て通っており実害はないが、保守性の観点で簡潔にできる。

→ 対応: `if thread.daemon: thread.join(timeout=timeout)`のみで十分。

## ✅ 良い点

- **Webhook URLの機密情報管理が要件・設計通り徹底されている**: `config.toml`に
  URLを含めない、ログ・例外メッセージにもURL生値を一切出力しない、`.env`を
  `.gitignore`に追加、`.env.example`はダミー値のみ、という設計が実装レベルで
  一貫して守られている。`notifier.py`のログ出力（型名のみ）を確認したが、
  Webhook URLが漏れる経路は見当たらなかった。
- **`frame.copy()`によるスレッド安全性への配慮**: メインループが同じ`frame`変数を
  次のループで上書きする実装であることを踏まえ、スレッドに渡す前に`frame.copy()`
  している点は的確。`test_notifier.py`でこの挙動を専用テストで検証している点も良い。
- **`threading.Thread(daemon=True)`による非同期化が要件3.1（主機能への影響回避）を
  満たす設計として適切**。`requests.post`に`timeout=5.0`を指定しており、
  ネットワーク不調時にスレッドが無期限に残留するリスクにも対応している。
- **異常系（送信失敗・エンコード失敗・HTTPエラー）が全て`_send`内で捕捉され、
  呼び出し元（メインループ）に伝播しない設計が徹底されている**。
  `test_notifier.py`でこれらの異常系を個別にテストしている点も評価できる。
- **`config.py`の`[notification]`セクション省略時の後方互換性**
  （`enabled=False`が既定値）が適切に実装・テストされている。
- **起動時バリデーション**（`enabled=true`なのに`DISCORD_WEBHOOK_URL`未設定）を
  `main()`内で明示的にチェックし、実行時の予期せぬ失敗より早期に検出している。

## まとめ・優先対応

致命的な問題はなく、Webhook URLの機密情報管理というセキュリティ上最も重要な
観点は要件・設計通り徹底されており、十分な単体テスト・実機E2Eテストでも
裏付けられている。

🟠の2点について対応を推奨する。

- **#1（`config.py`のbool型検証漏れ）**: 既存の防犯カメラ本体のレビューで
  指摘されたbool/int型検証パターンの逆ケースであり、修正コストが低い割に
  「設定ミスが静かに反転する」という気づきにくい不具合を防げるため、優先的に
  対応することを推奨する。
- **#2（録画失敗時にも通知が送られる）**: 実装ミスというより仕様判断の
  グレーゾーンのため、まずユーザーに「録画失敗時も通知すべきか」の意図を
  確認し、その結果に応じて対応するかどうかを決めるのが適切。

🟡の軽微な提案（#3〜#7）は、いずれも現状の挙動を大きく損なうものではないため、
今後の改修や気づいたタイミングで取り込む程度で問題ない。

## ユーザー判断（2026-06-26）

- **#2（録画失敗時の通知）**: **現状のまま**とする。録画に失敗した場合でも
  「検知はあった」という事実をユーザーに気づかせる価値があるため、
  `recorder is not None`の条件は追加しない。仕様として確定。
- **#1（`enabled`のbool型検証漏れ）**: **今回は修正しない**。記録のみとし、
  対応事項として残す。`config.toml`は`true`/`false`のTOMLブールリテラルで
  記述する前提のため実害は低いと判断。
　　※動体検知時の画像送信に、後ほど改良を加える予定なのでそこで同時に対応する予定