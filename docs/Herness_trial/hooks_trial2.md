# ハーネス実践: ruff format/lint フックの記録

## 概要
Pythonファイル(*.py)を Write または Edit ツールで作成/編集した直後に、`ruff format` と `ruff check --fix` を自動実行する `PostToolUse` フックを `.claude/settings.json` に追加した。既存の `PreToolUse`(rm -rf禁止、[[hooks_trial]])は変更していない。

## 作業の流れ

1. **要件確認・ツール選定**
   - ユーザー要望: 「Pythonファイル作成/編集後に、lintとformatterを実行させるhooksを設定したい」
   - プロジェクトにはlint/formatterが未導入だったため、`AskUserQuestion` で選択肢を提示し、`ruff`(format+lintを1ツールで賄える)を採用。

2. **ruffの導入**
   - `uv add --dev ruff` を実行してruffを開発依存に追加。
   - `pyproject.toml` に `[tool.ruff]` セクションを追加(`line-length = 100`, `target-version = "py314"`)。
   - `uv run ruff --version` で導入を確認。

3. **フックコマンドの設計**
   - Windows環境かつユーザー指定によりPowerShell(`shell: "powershell"`)でコマンドを構築。
   - hook入力(stdinのJSON)から `[Console]::In.ReadToEnd() | ConvertFrom-Json` で `tool_input.file_path` を取得し、`.py` で終わるファイルのみ対象に `uv run ruff format` → `uv run ruff check --fix` を実行。

4. **パイプテストでの事故と復旧**
   - 最初のパイプテストで実プロジェクトファイル(`src/webcam_security/camera.py`)を直接対象にしてしまい、意図せずreformatしてしまった。
   - `git diff` で変更が無害な整形のみと確認した上で、`git checkout --` で即座に元へ戻した。
   - 以降のテストはスクラッチディレクトリに作成したダミーPythonファイルに対して実施するよう方針を修正。

5. **動作検証**
   - スクラッチファイルに未使用import・崩れた書式(`def   foo( x,y ):` 等)を仕込み、フックコマンドをパイプテスト。
     - `ruff format` によるフォーマット修正、`ruff check --fix` による未使用importの自動削除を確認。
     - 未使用変数(F841)のような安全に自動修正できない警告は `remaining` として残り、コマンドの終了コードは1になる(PostToolUseとしては非ブロッキングでユーザーに可視化されるのみ)。

6. **設定ファイルへの反映で発生した問題**
   - `Edit` ツールで `.claude/settings.json` に `PostToolUse` ブロックを追記しようとしたところ、「Unterminated string」というJSON検証エラーで失敗(内容自体は正しいJSONだったが、Editツールの検証で通らなかった)。
   - 対策として、追記後の全体JSONをスクラッチファイルに書き出し、`uv run python -c "import json; json.load(...)"` で構文の妥当性を先に確認。
   - 妥当性を確認した上で `Write` ツールでファイル全体を書き換えることで反映に成功。

7. **実フックの発火確認**
   - スクラッチのPythonファイルを `Edit` ツールで実際に編集し、`def   bar( x,y ):` のような崩れた書式が `def bar(x, y):` に自動整形されることを確認。フックが実環境で正しく発火・動作することを確認できた。
   - テスト用の一時ファイルは作業後に削除。

## 最終的な設定(`.claude/settings.json` 抜粋)

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "shell": "powershell",
            "command": "（stdinのJSONからtool_input.file_pathを取得し、.pyファイルのみruff format→ruff check --fixを実行。詳細は.claude/settings.jsonを参照）",
            "statusMessage": "ruffでformat/lintを実行中..."
          }
        ]
      }
    ],
    "PreToolUse": [ "（rm -rf禁止フック。変更なし。詳細はhooks_trial.md参照）" ]
  }
}
```

## 学んだこと・注意点

- `uv add` はコマンド実行時点で `pyproject.toml` を書き換えるため、その後に同ファイルへ `Edit` する場合は必ず再読み込みしてから編集する必要がある(state stale エラーの原因になる)。
- hookのパイプテストは、実プロジェクトファイルではなく必ずスクラッチ領域のダミーファイルを使うべき。実ファイルを対象にすると、テストのつもりが本番の変更になってしまう。
- `Edit` ツールの設定ファイル検証でJSONが正当なのにエラーになるケースがあった。その場合は対象JSON全体を一度スクラッチに書き出し、`uv run python -c "import json; json.load(...)"` 等で構文を独立検証してから `Write` で書き込むと安全。
- PostToolUseフックのコマンドが非ゼロ終了しても(例: ruffが自動修正できない警告が残る場合)、ツール実行自体はブロックされず、警告がユーザーに可視化されるだけ。

## 関連ファイル
- `.claude/settings.json` — 実際のhooks設定(PostToolUse/PreToolUse両方)
- `pyproject.toml` — ruffの依存追加と `[tool.ruff]` 設定
- [[hooks_trial]] — rm -rf禁止フックの記録
