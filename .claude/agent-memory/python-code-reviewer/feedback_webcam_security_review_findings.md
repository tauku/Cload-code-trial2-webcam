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

関連: [[project-webcam-security-architecture]]
