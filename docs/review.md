# レビュー結果（Windows防犯カメラ）

`python-code-reviewer`エージェントにより、`src/webcam_security/`配下の実装
（`config.py` / `camera.py` / `motion_detector.py` / `recorder.py` / `live_view.py` /
`storage_cleaner.py` / `main.py`）をバグ・セキュリティ・パフォーマンスの観点でレビューした。

## 🔴 致命的な問題
なし。

## 🟠 重要な問題

### 1. `storage_cleaner.py` — 削除中の例外で以降のファイルが処理されずに残る
`path.unlink()`が例外処理なしで呼ばれているため、録画中ファイルのロック等で
`OSError`/`PermissionError`が発生すると、その時点で関数全体が例外終了し、
以降の期限切れファイルが削除されずに残る。`main.py`側の呼び出しも`try/except`
で囲まれていないため、最悪メインループ自体が異常終了するリスクがある。

→ 対応: 1ファイルごとに`try/except OSError`で囲み、失敗してもループを継続する。

### 2. `recorder.py` — `VideoWriter.write()`の書き込み失敗を実質検知できていない可能性
OpenCVの`VideoWriter.write()`はディスク容量不足時でも例外を投げず、戻り値も持たない。
そのため現状の`RecorderError`は`self._writer is None`の場合のみ発生し、
design.mdが想定する「ディスク容量不足等での書き込み失敗の検知」が実機で本当に
機能するか**確認が必要**。

→ 対応: `writer.isOpened()`の事後確認や`shutil.disk_usage()`での事前チェック等、
代替の検知手段を検討し、実機でディスク容量不足を再現して動作確認する。

### 3. `config.py` — bool値がint/float検証をすり抜ける
`bool`は`int`のサブクラスのため、`sensitivity = true`のような誤記述が
`int(True) == 1`として型エラーにならず静かに通ってしまう。

→ 対応: `bool`を明示的に除外する検証ヘルパーを追加する。

## 🟡 軽微な問題・改善提案
4. `main.py`: 起動直後の1フレームが動体検知の基準フレームとして使われず、初回検知が1フレーム遅れる
5. `config.py`: `storage.directory`にパストラバーサル相当の値を許容（運用上のリスクは低い）
6. `main.py`: 設定ファイルパス`config.toml`がカレントディレクトリ依存
7. `motion_detector.py`: `_MIN_MOTION_AREA`(500px)が解像度に依存した固定値
8. `live_view.py`: `poll_quit_key()`が`show()`呼び出し前提に暗黙依存している

## ✅ 良い点
- `Camera`のコンテキストマネージャ活用、`finally`での確実なリソース解放
- `@dataclass(frozen=True)`によるイミュータブルな設定値
- 異常系の設計（design.md §4）とコードの対応が概ね一致
- `storage_cleaner.py`の`now`引数注入によるテスト容易性
- 型ヒント・docstring（Raises節含む）が一貫して整備されている

## まとめ・優先対応
致命的な問題はないが、🟠の3点（storage_cleanerの例外処理、recorderの書き込み失敗検知、
configのbool型検証）は実装フェーズへ戻って対応することを推奨する。
🟡の軽微な提案は対応事項として記録し、必要に応じて今後の改修で取り込む。
