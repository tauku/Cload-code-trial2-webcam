---
name: feedback-webcam-security-review-findings
description: webcam_securityコードレビューで発見した再発しやすい問題パターン（OpenCV特有の落とし穴、bool/int型検証漏れ等）
metadata:
  type: feedback
---

2026-06-26のレビューで発見した、このコードベース特有の注意点。次回以降のレビューで再確認すべきポイント。

1. **OpenCVの`VideoWriter.write()`は失敗を例外も戻り値も返さない**。
   `recorder.py`の`RecorderError`は`self._writer is None`の場合のみ発生し、ディスク容量不足等の実書き込み失敗を検知できていない可能性が高い。
   **Why**: OpenCVのAPI仕様上、write()は戻り値を持たない（Noneを返す）ため、デザイン上想定している「書き込み失敗検知→録画中断」が実装レベルで本当に機能するか要確認。
   **How to apply**: recorder.py関連の変更があれば、書き込み失敗検知の実効性を毎回疑うこと。`writer.isOpened()`チェックや出力ファイルサイズ監視等の代替手段が入っているか確認する。

2. **`config.py`のint()/float()変換はbool値をすり抜けさせる**（Pythonの`bool`は`int`サブクラスのため`int(True)==1`でTypeError/ValueErrorが出ない）。
   **Why**: tomllibはTOMLの`true`/`false`をPythonの`bool`として返すため、設定ミス（型違い）が静かに通ってしまう。
   **How to apply**: config.py系の検証ロジックを見るたびに、`isinstance(value, bool)`チェックの有無を確認する。

3. **`storage_cleaner.py`の`path.unlink()`に例外処理がない**。1ファイルの削除失敗（録画中のロック等）で残りのファイル削除処理全体が止まる。
   **Why**: design.md §4は異常系で「ループ継続」を方針としているが、クリーンアップ処理にはこの方針が及んでいなかった。
   **How to apply**: storage_cleaner.py / main.pyのクリーンアップ呼び出し箇所を見るときは、個別ファイルの例外がループ全体を止めないか確認する。

4. **このプロジェクトはconfig.tomlをローカル管理者のみが編集する前提**（外部入力ではない）。パストラバーサルやインジェクションの脅威度は低いが、design.md §5で「OSのファイルアクセス権限に委ねる」と明記されているため、過度に厳格な入力検証を要求しない（要件で合意済みのスコープ外事項）。
   **How to apply**: config.toml由来の値（particularly storage.directory）に対する検証強化の提案は「軽微・提案」レベルに留め、致命的扱いしない。

5. **`config.py`の`bool()`変換は逆方向の罠もある**（2026-06-26、通知機能レビューで発見）。
   `NotificationConfig.enabled=bool(notification_raw.get("enabled", False))`のように
   真偽値設定項目を`bool()`でキャストすると、TOMLの記述ミスで文字列（例: `enabled = "false"`）が
   渡された場合に`bool("false")`が`True`になり、**「無効化したつもりが有効化される」**という
   意図と正反対の挙動になる。`int()`/`float()`がbool値をすり抜ける（上記2.）の逆方向で、
   こちらは「文字列が`bool()`をすり抜けて型ミスを検知できない」パターン。
   **Why**: `bool()`はPythonの真偽評価規則に従うため、空文字列以外の文字列・0以外の数値は
   常に`True`になる。TOML側で意図せずクォートを付けてしまう設定ミスを検知できない。
   **How to apply**: config.py内でTOMLの`true`/`false`（bool型）を読む箇所は、`bool()`での
   キャストではなく`isinstance(value, bool)`で型を確認しているか確認する。文字列が来た場合に
   ConfigErrorを出すべき。

6. **`notifier.py`（Discord Webhook通知機能、2026-06-26新規）の設計上の注意点**。
   `threading.Thread(daemon=True)`でHTTP送信を非同期化しており、メインループをブロックしない
   設計は適切。ただし`daemon=True`のため、プロセス終了時に送信中の通知スレッドが`join()`されず
   強制終了される可能性がある（要件2.4「主機能を妨げない」を優先した設計判断であり、バグでは
   ないが将来このスレッドをjoinする変更が入った場合は意図的な仕様変更か確認すること）。
   また、`frame.copy()`をスレッド起動前に行っている点は、メインループが同じ`frame`変数を
   次フレームで上書きする実装と整合しており適切（このパターンは他のスナップショット系機能を
   追加する際にも踏襲すべき）。
   **How to apply**: notifier.py関連の変更時は、(a) Webhook URLがログ・例外メッセージに
   生値で出力されていないか、(b) frameを参照渡しのままスレッドに渡していないか、を確認する。

関連: [[project-webcam-security-architecture]]
