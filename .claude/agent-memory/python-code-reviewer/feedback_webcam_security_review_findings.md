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
   **2026-06-29追記（3回目の再発を確認）**: 通知機能改良で`enabled`は`_require_bool`化されたが、
   同時に追加された`NotificationConfig`の新規3項目（`snapshot_interval_seconds`/
   `rate_limit_window_seconds`/`rate_limit_max_count`）は従来通り`float()`/`int()`の
   ままで、この問題が再発していた（`float(True)==1.0`が範囲検証`<=0`もすり抜ける）。
   `_require_bool`のようなbool用ヘルパーが導入された際、**同じ変更の中で追加された
   数値項目側に「boolを拒否する」チェックが入っているか必ずセットで確認すること**。
   片方だけ直して終わりにしないこと。

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

7. **2026-06-29、`notifier.py`が関数からステートフルな`MotionNotifier`クラスへ再設計され、
   上記6.の`daemon=True`未joinの指摘が`join_pending()`で解消された**。
   `_threads: list[threading.Thread]`はメインループ（単一スレッド）からのみ読み書きされる
   設計で、バックグラウンドスレッド（`_send`）側は`_threads`に触れないためデータ競合はない。
   `join_pending(timeout)`は**`_threads`内の各スレッドに対して個別に`timeout`秒**を適用する
   実装（design.mdのdocstring通り）であり、複数スレッドが残っている終了時には
   `timeout × 残存スレッド数`まで待機が伸びる可能性がある点は仕様として把握しておくこと。
   **How to apply**: 今後`join_pending`系のタイムアウト設計を見る際は、「全体でtimeout秒」
   なのか「スレッドごとにtimeout秒」なのかをdocstring・実装の両方で確認すること。

8. **`cooldown_seconds`（`detection`設定）は`0`を許容する設計だが、`0`の場合は
   検知開始フレームでも`now - last_motion_at < cooldown_seconds`が`0 < 0`で`False`になり、
   通知（`MotionNotifier.notify_if_due`）が一度も呼ばれず`reset()`され続ける**。
   録画ロジックには影響しないが、通知機能が実質無効化される暗黙の境界値。
   **How to apply**: `main.py`のクールダウン判定とdetection/notificationの連携箇所を見る際は、
   `cooldown_seconds=0`のような境界値でどちらの機能が無効化されるか確認する。

関連: [[project-webcam-security-architecture]]
