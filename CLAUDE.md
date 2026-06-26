#　windows用防犯カメラ作成
##　プロジェクト概要
windows上で動作する、USBカメラを用いた防犯カメラ機能を開発するプロジェクト

##　技術スタック
- Python 3.14.6
- パッケージ管理　：uv (pipは使用しない)
- テスト　pytest

##　開発ルール
- 回答は日本語で行う
- コメントとドキュメントは日本語で記述する
- パッケージの追加は'uv add'を使う
- スクリプト実行は'uv run python'を使う
- テスト実行は、'uv run pytest'を使う
- pip installは絶対に使わないこと

##　ディレクトリ構成
- src/ : メインのソースコード
- tests/: テストコード
- docs/ :ドキュメント
- docs/camera_function_development/ : plan.md実行時のドキュメント
- docs/notification_function_development/ : plan2.md実行時のドキュメント
- docs/notification_improvement_development/ : plan3.md実行時のドキュメント
- docs/interrupt_report : 日をまたいだ作業再開用の一時レポート
- prompt_history/ :claudeに入力したプロンプトの履歴　Claudeは確認不要

