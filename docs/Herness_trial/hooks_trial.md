# ハーネス実践: hooks設定の記録

## 概要
Claude Codeのhooks機能を使い、`rm -rf`系の破壊的なコマンドをBashツール実行前にブロックする`PreToolUse`フックを `.claude/settings.json` に設定した。

## 作業の流れ

1. **ブランチ作成**
   - `main` から `ハーネス実践` ブランチを作成。
   - `.claude/settings.json`(当時は空ファイル)をコミットし、リモートにプッシュ。
   - その後 `feature/discord-notifier` ブランチに切り替え、ここでhooksの設定作業を実施。

2. **要件確認**
   - ユーザー要望: 「rm -rfコマンドを禁止するhooksを設定したい」
   - `update-config` skillを使用してhooks設定方針を確認。

3. **環境調査**
   - `.claude/settings.json` は0バイトの空ファイルだった。
   - `jq` は未インストール、`python`はWindowsストアのスタブで実体なし、`grep`(GNU, PCRE対応)は利用可能と判明。
   - → jq/python に依存せず、`grep -P`(肯定後読み等)のみで完結する実装方針に変更。

4. **検知ロジックの設計とテスト**
   - stdinで渡されるhook入力JSONから `grep -oP '(?<="command":")[^"]*'` でBashコマンド文字列を抽出。
   - `;`, `&`, `|` で区切られたコマンドチェーンのうち `rm` (または `sudo rm`) を含むセグメントだけを抽出。
   - そのセグmoment内に「再帰オプション(`-r`/`-R`を含む短縮形、または`--recursive`)」と「強制オプション(`-f`を含む短縮形、または`--force`)」が**両方**存在する場合のみブロック対象と判定。
   - 以下のテストケースで動作確認済み:
     - ブロックされる例: `rm -rf /tmp/foo`, `rm -fr /tmp/foo`, `rm -rfv /tmp/foo`, `sudo rm -rf /`, `rm --recursive --force /tmp`, `rm -r -f /tmp`, `cd /tmp && rm -rf foo`
     - ブロックされない例(誤検知なし): `ls -la`, `git status`, `rm file.txt`, `rm -f somefile`, `rm -r somedir`(片方のフラグのみ), `echo rm -rf is dangerous`(rmが文頭/区切り直後でない文字列出力), `rm -r foo; ls -f`(別コマンドにまたがるフラグの誤結合なし)

5. **設定の反映**
   - `.claude/settings.json` に以下の構造で `PreToolUse` フック(matcher: `Bash`)を追加。
   - 検知時は `hookSpecificOutput.permissionDecision: "deny"` を返し、Bashツールの実行をブロックする。

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "shell": "bash",
            "command": "（rm -rf 検知用シェルワンライナー。詳細は .claude/settings.json を参照）",
            "statusMessage": "rm -rf チェック中..."
          }
        ]
      }
    ]
  }
}
```

6. **検証**
   - PowerShellの `ConvertFrom-Json` でJSON構文の妥当性を確認(OK)。
   - PowerShellでJSONをパースして実際の `command` 文字列を取り出し、Git Bash上で生のhook入力JSON相当のペイロードをパイプして再テスト。設定ファイルに書き込んだ実体のコマンドが意図通り動作することを確認。

## 学んだこと・注意点

- このプロジェクトの環境には `jq` と実体のある `python` が無いため、hooksのワンライナーは `grep`(PCRE対応)とPOSIXシェルの組み込み機能のみで組む必要がある。
- Windowsの `python`/`python3` はストアアプリのスタブを指しており、実行すると `Python` とだけ出力して終了コード49を返す(実体なし)。hooksや自動化スクリプトでpythonに依存する場合は事前に実体確認が必要。
- このフックはあくまで安全網であり、変数展開や難読化されたコマンド、別名(alias)経由の `rm` 等までは検知できない。完全なセキュリティ境界ではない。
- 設定変更を即座に有効化するには `/hooks` を一度開く(または再起動する)必要がある場合がある。

## 関連ファイル
- `.claude/settings.json` — 実際のhooks設定
