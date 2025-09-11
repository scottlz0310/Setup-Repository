# リファクタリングタスクチェックリスト

## 🎯 Phase 1: 重複解消

### ✅ Task 1.1: detect_platform()重複解消
- [ ] `utils.py`の`detect_platform()`削除
- [ ] `sync.py`のインポート更新
- [ ] 他の呼び出し箇所の更新
- [ ] テスト実行・確認

### ✅ Task 1.2: ensure_uv()重複解消
- [ ] `python_env.py`の`ensure_uv()`削除
- [ ] `uv_installer`への統一
- [ ] 依存関係の更新
- [ ] テスト実行・確認

### ✅ Task 1.3: save_error_report()重複解消
- [ ] 機能差分の分析
- [ ] 統一インターフェース設計
- [ ] 重複コード削除
- [ ] テスト実行・確認

## 🔧 Phase 2: モジュール分割

### ✅ Task 2.1: quality_logger.py分割
- [ ] `quality_errors.py`作成
- [ ] `quality_formatters.py`作成
- [ ] 関数の移動・整理
- [ ] インポート文の更新
- [ ] テスト分割・作成

### ✅ Task 2.2: ci_error_handler.py分割
- [ ] `ci_environment.py`作成
- [ ] 関数の移動・整理
- [ ] インポート文の更新
- [ ] テスト分割・作成

### ✅ Task 2.3: logging_config.py分割
- [ ] `logging_handlers.py`作成
- [ ] 関数の移動・整理
- [ ] インポート文の更新
- [ ] テスト分割・作成

### ✅ Task 2.4: quality_metrics.py分割
- [ ] `quality_collectors.py`作成
- [ ] 関数の移動・整理
- [ ] インポート文の更新
- [ ] テスト分割・作成

### ✅ Task 2.5: interactive_setup.py分割
- [ ] `setup_validators.py`作成
- [ ] 関数の移動・整理
- [ ] インポート文の更新
- [ ] テスト分割・作成

## 🧪 Phase 3: テスト更新

### ✅ Task 3.1: 新モジュールテスト作成
- [ ] 新しいテストファイル作成
- [ ] 既存テストの移動
- [ ] カバレッジ確認
- [ ] テスト実行

### ✅ Task 3.2: 統合テスト更新
- [ ] インポートパス更新
- [ ] モック調整
- [ ] CI/CD実行確認
- [ ] 品質ゲート通過確認

## 🧪 Phase 4: テストカバレッジ向上

### ✅ Task 4.1: 基盤モジュールテスト
- [ ] `test_config.py` 拡張
- [ ] `test_utils.py` 新規作成
- [ ] `test_platform_detector.py` 新規作成
- [ ] カバレッジ25%達成確認

### ✅ Task 4.2: API層テスト
- [ ] `test_github_api.py` 新規作成
- [ ] `test_git_operations.py` 新規作成
- [ ] `test_cli.py` 新規作成
- [ ] カバレッジ50%達成確認

### ✅ Task 4.3: セットアップ・同期テスト
- [ ] `test_sync.py` 新規作成
- [ ] `test_setup.py` 新規作成
- [ ] `test_interactive_setup.py` 新規作成
- [ ] 統合テスト拡張

### ✅ Task 4.4: 品質管理テスト
- [ ] `test_quality_logger.py` 新規作成
- [ ] `test_quality_metrics.py` 拡張
- [ ] `test_quality_trends.py` 拡張
- [ ] カバレッジ70%達成確認

### ✅ Task 4.5: 環境・ツールテスト
- [ ] `test_python_env.py` 新規作成
- [ ] `test_uv_installer.py` 新規作成
- [ ] `test_vscode_setup.py` 新規作成
- [ ] `test_safety_check.py` 新規作成

### ✅ Task 4.6: CI/CD・ログテスト
- [ ] `test_ci_error_handler.py` 新規作成
- [ ] `test_logging_config.py` 新規作成
- [ ] カバレッジ80%達成確認

## 📋 最終チェック

### 品質保証
- [ ] 全テスト通過
- [ ] カバレッジ80%以上達成
- [ ] 全モジュール60%以上
- [ ] Ruffリンティング通過
- [ ] MyPy型チェック通過
- [ ] 後方互換性確認
- [ ] テスト実行時間5分以内

### ドキュメント
- [ ] README更新
- [ ] API変更ログ作成
- [ ] アーキテクチャ図更新
- [ ] 開発者ガイド更新

### 最終確認
- [ ] 全機能の動作確認
- [ ] パフォーマンステスト
- [ ] セキュリティチェック
- [ ] リリースノート作成
