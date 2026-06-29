# 設計書（通知機能改良）

[要件定義書](requirements.md)で合意した要件を実現するための設計をまとめる。
本書は[既存のdesign.md](../notification_function_development/design.md)に対する
**変更点・追加点のみ**を記載する差分ドキュメントである。

## 1. 技術選定
追加のパッケージは不要。送信数上限（レート制限）の管理には標準ライブラリの
`collections.deque`を使用する（古いタイムスタンプを先頭から効率的に除去できるため）。

## 2. アーキテクチャ（モジュール構成）

```
src/webcam_security/
├── main.py     # ループ構造を変更（検知継続中の通知呼び出し・終了時のjoin処理を追加）
├── config.py   # [notification]セクションに3項目追加、enabledの型検証を強化
└── notifier.py # notify_motion_detected()関数を廃止し、MotionNotifierクラスを新設
```

### 2.1 `notifier.py` — `MotionNotifier`クラス（新設）

検知継続中の送信タイミング管理と送信数上限の管理という**状態を持つ処理**になるため、
既存の`Camera`・`Recorder`・`MotionDetector`と同様にクラスとして実装する
（既存の関数`notify_motion_detected`は廃止する）。

```python
class MotionNotifier:
    def __init__(
        self,
        webhook_url: str,
        snapshot_interval_seconds: float,
        rate_limit_window_seconds: float,
        rate_limit_max_count: int,
    ) -> None: ...

    def notify_if_due(self, frame: np.ndarray, now: float) -> None:
        """検知継続中に呼び出す。送信間隔・送信数上限を満たしていれば
        スナップショットをDiscordへ非同期送信し、それ以外は何もしない。"""

    def reset(self) -> None:
        """検知終了時に呼び出す。次回検知開始時に即時送信されるよう、
        送信間隔の基準時刻をクリアする。"""

    def join_pending(self, timeout: float = 2.0) -> None:
        """終了処理(main.pyのfinally)で呼び出す。送信中の通知スレッドを待つ
        （review.md 🟡#3対応）。"""
```

- `notify_if_due`内部では`self._last_sent_at`（直前送信時刻、`time.monotonic()`基準）を保持し、
  `self._last_sent_at is None or now - self._last_sent_at >= snapshot_interval_seconds`の場合のみ送信する。
  `_last_sent_at`が`None`の場合（検知開始直後）は即時送信される。
- 送信前に`self._sent_history`（`deque[float]`）から`rate_limit_window_seconds`より古い
  タイムスタンプを除去し、残数が`rate_limit_max_count`以上なら送信をスキップし、
  標準エラー出力に`"通知エラー: 送信数の上限に達したため通知をスキップしました"`を出力する
  （要件3.3）。
- 実際の送信は内部関数`_send`（既存ロジックをそのまま移植）にスレッドを渡して非同期実行し、
  生成した`threading.Thread`を`self._threads`に保持する（`join_pending`で利用）。

### 2.2 `main.py` — メインループの変更

`MotionNotifier`の生成は`config.notification.enabled`かつ`webhook_url`がある場合のみ行う
（既存方針を継続）。

```python
motion_notifier = (
    MotionNotifier(
        webhook_url,
        config.notification.snapshot_interval_seconds,
        config.notification.rate_limit_window_seconds,
        config.notification.rate_limit_max_count,
    )
    if config.notification.enabled and webhook_url
    else None
)
```

ループ内の通知呼び出しは、**「録画中(`recorder is not None`)」ではなく
「検知継続中（`last_motion_at`からクールダウン未経過）」を基準に判定する**。
これにより、録画失敗（`RecorderError`）時にも通知を送る既存の挙動
（[review.md 🟠#2のユーザー判断](../notification_function_development/review.md)）を崩さずに、
検知継続中のスナップショット間隔送信を実現できる。

```python
if detector.detect(frame):
    last_motion_at = now
    if recorder is None:
        recorder = Recorder(config.storage.directory, fps, (width, height))
        try:
            recorder.start()
        except RecorderError as e:
            print(f"録画エラー: {e}", file=sys.stderr)
            recorder = None

if last_motion_at is not None and now - last_motion_at < config.detection.cooldown_seconds:
    if motion_notifier is not None:
        motion_notifier.notify_if_due(frame, now)
elif motion_notifier is not None:
    motion_notifier.reset()

if recorder is not None:
    try:
        recorder.write(frame)
    except RecorderError as e:
        print(f"録画エラー: {e}", file=sys.stderr)
        recorder.stop()
        recorder = None
    else:
        assert last_motion_at is not None
        if now - last_motion_at >= config.detection.cooldown_seconds:
            recorder.stop()
            recorder = None
```

- 検知開始時（`last_motion_at`更新直後）は`notify_if_due`内部の状態が初期値（`None`）のため
  即時送信される（要件3.1）。
- クールダウン未経過の間は毎フレーム`notify_if_due`を呼ぶが、間隔未達であれば内部で
  即座にreturnするため、間隔を満たした時だけ実際の送信処理が走る。
- クールダウン経過後（検知が真に終了した最初のフレーム）から次の検知開始までの間、
  毎フレーム`reset()`を呼ぶ（呼び出し自体は安全・冪等）。これにより次回検知開始時の
  即時送信が保証される。
- クールダウン中の再検知（`detector.detect(frame)`が再度`True`になり`last_motion_at`が
  更新される場合）は、検知継続中の状態がそのまま延長されるだけであり、`notify_if_due`の
  間隔・上限カウントも継続して使われる（要件3.2「再検知という概念は別途設けない」）。

終了処理（`finally`）に`join_pending`呼び出しを追加する（review.md 🟡#3対応）。

```python
finally:
    if recorder is not None:
        recorder.stop()
    if motion_notifier is not None:
        motion_notifier.join_pending()
    live_view.close()
```

## 3. 設定（`config.toml` / `config.py`）

### 3.1 `config.toml`

`[notification]`セクションに3項目を追加する。

```toml
[notification]
enabled = true
snapshot_interval_seconds = 3   # 検知中にスナップショットを送信する間隔(秒)
rate_limit_window_seconds = 60  # 送信数上限を計算する時間窓(秒)
rate_limit_max_count = 10       # 上記時間窓内に送信できる通知の最大数
```

### 3.2 `config.py`

`NotificationConfig`に3フィールドを追加し、デフォルト値で後方互換性を保つ
（既存の`enabled`のみの`config.toml`でも動作する）。

```python
@dataclass(frozen=True)
class NotificationConfig:
    enabled: bool
    snapshot_interval_seconds: float = 3.0
    rate_limit_window_seconds: float = 60.0
    rate_limit_max_count: int = 10
```

`load_config`内の読み込み・検証を以下のように変更する。

```python
def _require_bool(value: object, field_name: str) -> bool:
    """boolフィールドの型を厳密に検証する。

    `bool()`は文字列等を常に真偽値へ変換してしまい、TOMLの記述ミス
    （例: クォート付きの`enabled = "false"`）を検知できないため、
    `isinstance`による明示的な型チェックに置き換える（review.md 🟠#1対応）。
    """
    if not isinstance(value, bool):
        raise ConfigError(f"{field_name}はbool型(true/false)である必要があります")
    return value


# load_config内
notification_raw = raw.get("notification", {})
notification = NotificationConfig(
    enabled=_require_bool(notification_raw.get("enabled", False), "notification.enabled"),
    snapshot_interval_seconds=float(notification_raw.get("snapshot_interval_seconds", 3.0)),
    rate_limit_window_seconds=float(notification_raw.get("rate_limit_window_seconds", 60.0)),
    rate_limit_max_count=int(notification_raw.get("rate_limit_max_count", 10)),
)
```

範囲検証を既存の`if`群に追加する。

```python
if notification.snapshot_interval_seconds <= 0:
    raise ConfigError("notification.snapshot_interval_secondsは正の値である必要があります")
if notification.rate_limit_window_seconds <= 0:
    raise ConfigError("notification.rate_limit_window_secondsは正の値である必要があります")
if notification.rate_limit_max_count <= 0:
    raise ConfigError("notification.rate_limit_max_countは正の値である必要があります")
```

### 3.3 デフォルト値の根拠
- `snapshot_interval_seconds = 3`: 要件定義フェーズでユーザーと合意した値。
- `rate_limit_window_seconds = 60` / `rate_limit_max_count = 10`: 設計フェーズでの提案
  （60秒間に最大10通）をユーザーと合意済み。3秒間隔と組み合わせると、検知が長時間
  継続しても最初の約30秒はほぼ毎回送信され、それ以降はスキップされる。

## 4. review.md指摘事項への詳細対応

| No. | 対応箇所 | 設計 |
|---|---|---|
| 🟠#1 | `config.py` | §3.2の`_require_bool`で対応 |
| 🟡#3 | `notifier.py`/`main.py` | §2.1の`join_pending`、§2.2の`finally`呼び出しで対応 |
| 🟡#4 | `notifier.py` `_send` | `requests.exceptions.HTTPError`を`RequestException`より先に捕捉し、`e.response.status_code`をログに含める（下記コード例） |
| 🟡#5 | README | ドキュメント作成フェーズで「`.env`の準備が必須」であることを明記（本フェーズでは対応しない） |
| 🟡#6 | `main.py` | エラーメッセージの文字列リテラルの間に読点を補う（下記コード例） |
| 🟡#7 | `tests/test_notifier.py` | テストフェーズで`thread.daemon`判定のみに簡略化（本フェーズでは対応しない） |

🟡#4の`_send`内エラーハンドリング:

```python
try:
    response = requests.post(...)
    response.raise_for_status()
except requests.exceptions.HTTPError as e:
    status = e.response.status_code if e.response is not None else None
    print(
        f"通知エラー: Discordへの送信に失敗しました ({type(e).__name__}, status={status})",
        file=sys.stderr,
    )
except requests.exceptions.RequestException as e:
    print(f"通知エラー: Discordへの送信に失敗しました ({type(e).__name__})", file=sys.stderr)
```

🟡#6の`main.py`エラーメッセージ:

```python
print(
    "設定エラー: notification.enabledがtrueですが、"
    "DISCORD_WEBHOOK_URLが設定されていません（.envを確認してください）",
    file=sys.stderr,
)
```

## 5. 異常系設計（追加分）

| 異常 | 挙動 |
|---|---|
| 送信数上限に到達した状態で検知が継続している | `notify_if_due`が送信をスキップし、標準エラー出力にログを残す。次の時間窓に入り上限が解除されれば送信を再開する |
| `config.toml`の`notification.enabled`に文字列（例: `"false"`）が記述されている | `_require_bool`が`ConfigError`を発生させ、起動時に設定エラーとして停止する（既存の`ConfigError`ハンドリングに従う） |
| `snapshot_interval_seconds`等に0以下の値が指定されている | `load_config`が`ConfigError`を発生させ、起動時に停止する |
| プロセス終了時に通知スレッドが送信中 | `join_pending(timeout=2.0)`で待機する。タイムアウトを超えても強制終了は妨げない（`daemon=True`のまま） |

## 6. 要件との対応確認

- review.md指摘事項（🟠1点・🟡5点）: §4（🟡#5・#7はドキュメント・テストフェーズで対応）
- スナップショット送付タイミング（開始時即時＋3秒間隔）: §2.1, §2.2
- 送付回数の上限（レート制限）: §2.1, §3
- 上限到達時はログのみ・スキップ: §2.1, §5
- 既存ドキュメントとの差分のみ記載: 本書全体（[既存design.md](../notification_function_development/design.md)は変更しない）
