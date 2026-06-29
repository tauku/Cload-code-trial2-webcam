# Memory Index

- [webcam_securityのモジュール構成と異常系設計方針](project_webcam_security_architecture.md) — design.md/requirements.mdの要点、レビュー時の確認軸
- [webcam_securityレビューで見つかった再発しやすい問題パターン](feedback_webcam_security_review_findings.md) — OpenCV write()の検知不能性、bool/int/float型検証漏れ(3回再発)、unlink()の例外処理漏れ、notifier.py MotionNotifier化・join_pending・cooldown=0境界値
