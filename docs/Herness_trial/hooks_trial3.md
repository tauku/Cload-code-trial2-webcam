# ハーネス実践: 作業完了通知(Stopフック)の記録

## 概要
Claude Codeの作業完了時(`Stop`イベント)に、Windowsのトースト通知でユーザーに知らせる`Stop`フックを `.claude/settings.json` に追加した。既存の `PreToolUse`(rm -rf禁止、[[hooks_trial]])と `PostToolUse`(ruff format/lint、[[hooks_trial2]])は変更していない。

## 作業の流れ

1. **要件確認・通知方式の選定**
   - ユーザー要望: 「Claude Codeの作業完了時に、ユーザーに通知するhooksを設定したい」
   - `AskUserQuestion` で通知方式(Windowsトースト通知/サウンド/Discord Webhook)を提示し、「Windowsトースト通知」を採用。
   - `update-config` skillに、BurntToast等の外部モジュールを使わず `[Windows.UI.Notifications.ToastNotificationManager]` を直接呼び出す方式を指定して依頼。

2. **PowerShell 7(pwsh)での失敗**
   - 最初に `pwsh` で `[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime]` を実行したところ、`Unable to find type` エラーで失敗。
   - PowerShell 7(.NET Core版)はWindows PowerShell 5.1(Desktop版)と異なり、WinRT型のオンザフライ解決に対応していないことが判明。

3. **Windows PowerShell 5.1(`powershell.exe`)への切り替え**
   - `powershell.exe` を明示的に呼び出す方式に変更。
   - スクリプトファイル(`.ps1`)経由での実行はExecutionPolicyにより `UnauthorizedAccess` エラーで失敗したため、`-ExecutionPolicy Bypass -Command "..."` のインライン実行方式を採用。
   - `ToastNotificationManager.CreateToastNotifier()` に渡すAppIdには、実行中のpowershell.exe自身のパス(`(Get-Process -Id $PID).Path`)を使用(未登録のAUMIDでも実行ファイルパスをAppIdとして使えば通知可能)。

4. **bash経由のフックコマンドとしての組み立て**
   - hookの実行シェルは `bash`(Git Bash)を指定し、その中から `powershell.exe -Command "..."` を呼び出す構成。
   - PowerShell側の変数(`$template`, `$text`, `$toast`, `$appId`, `$PID`, `$null`)がbashに変数展開されないよう、すべて `\$` でエスケープ。
   - テスト時、コマンド全体をbashの単一引用符`'...'`で囲んでいたところ、PowerShellスクリプト内の`'text'`等の単一引用符と衝突してパースが壊れる事故が発生。ヒアドキュメントで一時スクリプトファイルに書き出してから実行する方式に切り替えて解決。

5. **動作検証**
   - 組み立てたコマンドを2回実行し、いずれも `AskUserQuestion` でユーザーに実際の画面表示を確認してもらい、「Claude Code / 作業が完了しました」というトースト通知が表示されることを確認済み。

6. **設定の反映**
   - `.claude/settings.json` に `Stop` フック(matcher無し、hookイベント全体に対して発火)を追加。
   - JSON全体をスクラッチファイルに書き出し `uv run python -c "import json; json.load(...)"` で構文検証してから、`Write` ツールで実ファイルに反映(前回の[[hooks_trial2]]と同じ安全手順)。

## 最終的な設定(`.claude/settings.json` 抜粋)

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "shell": "bash",
            "command": "powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command \"...ToastNotificationManagerを使った通知処理...\" 2>/dev/null",
            "statusMessage": "作業完了を通知中..."
          }
        ]
      }
    ],
    "PostToolUse": [ "（ruff format/lintフック。変更なし。詳細はhooks_trial2.md参照）" ],
    "PreToolUse": [ "（rm -rf禁止フック。変更なし。詳細はhooks_trial.md参照）" ]
  }
}
```

## 学んだこと・注意点

- PowerShell 7(pwsh)とWindows PowerShell 5.1(powershell.exe)はWinRT型の扱いが異なる。トースト通知のようなWinRT APIに依存する処理は `powershell.exe` を明示的に使う必要がある。
- `.ps1` ファイルの実行はExecutionPolicyの影響を受けやすい。ワンショットの用途では `-Command` によるインライン実行 + `-ExecutionPolicy Bypass` の方がシンプルで済む。
- bashのコマンド文字列中にPowerShellの `'...'` 文字列リテラルを埋め込む場合、外側をbashの単一引用符で囲むと衝突する。二重引用符 + `$` のエスケープ(`\$`)で組み立てるか、あるいはヒアドキュメントでファイル化してテストするのが安全。
- `Stop` イベントは応答が完了するたびに発火する(セッション終了時に限らない)ため、この種の通知フックは「一区切りついたとき」の合図として使える。

## 関連ファイル
- `.claude/settings.json` — 実際のhooks設定(Stop/PostToolUse/PreToolUse)
- [[hooks_trial]] — rm -rf禁止フックの記録
- [[hooks_trial2]] — ruff format/lintフックの記録
