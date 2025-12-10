# API変更ログ

## バージョン 1.1.0 - リファクタリング版

### 発行日: 2025年1月

### 概要

Setup-Repositoryプロジェクトの大規模リファクタリングに伴うAPI変更の詳細ログです。責任分離の徹底とテストカバレッジ向上を目的として、モジュール分割と重複解消を実施しました。

---

## 破壊的変更 (Breaking Changes)

### 1. モジュール分割による構造変更

#### 1.1 Quality Logger分割

**影響度: 高**

`quality_logger.py` (19関数) が以下の3つのモジュールに分割されました：

##### 削除された関数 (quality_logger.pyから移動)

| 関数名 | 移動先モジュール | 新しいインポートパス |
|--------|------------------|---------------------|
| `QualityError` | quality_errors.py | `from setup_repo.quality_errors import QualityError` |
| `QualityWarning` | quality_errors.py | `from setup_repo.quality_errors import QualityWarning` |
| `handle_quality_error` | quality_errors.py | `from setup_repo.quality_errors import handle_quality_error` |
| `format_error_message` | quality_errors.py | `from setup_repo.quality_errors import format_error_message` |
| `log_exception` | quality_errors.py | `from setup_repo.quality_errors import log_exception` |
| `create_error_report` | quality_errors.py | `from setup_repo.quality_errors import create_error_report` |
| `ColoredFormatter` | quality_formatters.py | `from setup_repo.quality_formatters import ColoredFormatter` |
| `JSONFormatter` | quality_formatters.py | `from setup_repo.quality_formatters import JSONFormatter` |
| `format_log_message` | quality_formatters.py | `from setup_repo.quality_formatters import format_log_message` |
| `add_color_codes` | quality_formatters.py | `from setup_repo.quality_formatters import add_color_codes` |
| `strip_color_codes` | quality_formatters.py | `from setup_repo.quality_formatters import strip_color_codes` |

##### 残存する関数 (quality_logger.pyに継続)

| 関数名 | 説明 |
|--------|------|
| `setup_quality_logging` | 品質ログ設定の初期化 |
| `get_quality_logger` | 品質ロガーの取得 |
| `log_quality_event` | 品質イベントのログ記録 |
| `log_quality_summary` | 品質サマリーのログ記録 |
| `configure_logging` | ログ設定の構成 |
| `set_log_level` | ログレベルの設定 |
| `cleanup_old_logs` | 古いログファイルのクリーンアップ |
| `get_log_file_path` | ログファイルパスの取得 |

#### 1.2 CI Error Handler分割

**影響度: 中**

`ci_error_handler.py` (11関数) が以下の2つのモジュールに分割されました：

##### 削除された関数 (ci_error_handler.pyから移動)

| 関数名 | 移動先モジュール | 新しいインポートパス |
|--------|------------------|---------------------|
| `detect_ci_environment` | ci_environment.py | `from setup_repo.ci_environment import detect_ci_environment` |
| `get_system_info` | ci_environment.py | `from setup_repo.ci_environment import get_system_info` |
| `collect_environment_vars` | ci_environment.py | `from setup_repo.ci_environment import collect_environment_vars` |
| `get_ci_metadata` | ci_environment.py | `from setup_repo.ci_environment import get_ci_metadata` |
| `is_ci_environment` | ci_environment.py | `from setup_repo.ci_environment import is_ci_environment` |

##### 残存する関数 (ci_error_handler.pyに継続)

| 関数名 | 説明 |
|--------|------|
| `handle_ci_error` | CIエラーの処理 |
| `generate_error_report` | エラーレポートの生成 |
| `send_notification` | 通知の送信 |
| `save_error_report` | エラーレポートの保存 |
| `format_ci_error` | CIエラーのフォーマット |
| `cleanup_error_reports` | エラーレポートのクリーンアップ |

#### 1.3 Logging Config分割

**影響度: 中**

`logging_config.py` (11関数) が以下の2つのモジュールに分割されました：

##### 削除された関数 (logging_config.pyから移動)

| 関数名 | 移動先モジュール | 新しいインポートパス |
|--------|------------------|---------------------|
| `TeeHandler` | logging_handlers.py | `from setup_repo.logging_handlers import TeeHandler` |
| `RotatingFileHandler` | logging_handlers.py | `from setup_repo.logging_handlers import RotatingFileHandler` |
| `ColoredConsoleHandler` | logging_handlers.py | `from setup_repo.logging_handlers import ColoredConsoleHandler` |
| `create_file_handler` | logging_handlers.py | `from setup_repo.logging_handlers import create_file_handler` |
| `create_console_handler` | logging_handlers.py | `from setup_repo.logging_handlers import create_console_handler` |

##### 残存する関数 (logging_config.pyに継続)

| 関数名 | 説明 |
|--------|------|
| `setup_logging` | ログ設定の初期化 |
| `get_log_config` | ログ設定の取得 |
| `configure_environment_logging` | 環境別ログ設定 |
| `set_global_log_level` | グローバルログレベル設定 |
| `reset_logging_config` | ログ設定のリセット |
| `validate_log_config` | ログ設定の検証 |

#### 1.4 Quality Metrics分割

**影響度: 中**

`quality_metrics.py` (11関数) が以下の2つのモジュールに分割されました：

##### 削除された関数 (quality_metrics.pyから移動)

| 関数名 | 移動先モジュール | 新しいインポートパス |
|--------|------------------|---------------------|
| `collect_ruff_metrics` | quality_collectors.py | `from setup_repo.quality_collectors import collect_ruff_metrics` |
| `collect_mypy_metrics` / `collect_pyright_metrics` | quality_collectors.py | `from setup_repo.quality_collectors import collect_mypy_metrics` |
| `collect_pytest_metrics` | quality_collectors.py | `from setup_repo.quality_collectors import collect_pytest_metrics` |
| `collect_coverage_metrics` | quality_collectors.py | `from setup_repo.quality_collectors import collect_coverage_metrics` |
| `parse_tool_output` | quality_collectors.py | `from setup_repo.quality_collectors import parse_tool_output` |

##### 残存する関数 (quality_metrics.pyに継続)

| 関数名 | 説明 |
|--------|------|
| `calculate_quality_score` | 品質スコアの計算 |
| `get_quality_metrics` | 品質メトリクスの取得 |
| `generate_quality_report` | 品質レポートの生成 |
| `compare_quality_trends` | 品質トレンドの比較 |
| `save_metrics_report` | メトリクスレポートの保存 |
| `load_historical_metrics` | 履歴メトリクスの読み込み |

#### 1.5 Interactive Setup分割

**影響度: 低**

`interactive_setup.py` (10関数) が以下の2つのモジュールに分割されました：

##### 削除された関数 (interactive_setup.pyから移動)

| 関数名 | 移動先モジュール | 新しいインポートパス |
|--------|------------------|---------------------|
| `validate_github_credentials` | setup_validators.py | `from setup_repo.setup_validators import validate_github_credentials` |
| `validate_directory_path` | setup_validators.py | `from setup_repo.setup_validators import validate_directory_path` |
| `validate_setup_prerequisites` | setup_validators.py | `from setup_repo.setup_validators import validate_setup_prerequisites` |
| `check_system_requirements` | setup_validators.py | `from setup_repo.setup_validators import check_system_requirements` |

##### 残存する関数 (interactive_setup.pyに継続)

| 関数名 | 説明 |
|--------|------|
| `run_interactive_setup` | インタラクティブセットアップの実行 |
| `setup_wizard` | セットアップウィザード |
| `handle_user_input` | ユーザー入力の処理 |
| `display_setup_progress` | セットアップ進捗の表示 |
| `complete_setup` | セットアップの完了 |
| `save_setup_config` | セットアップ設定の保存 |

### 2. 重複関数の削除

#### 2.1 プラットフォーム検出統一

**影響度: 低**

| 削除された関数 | 削除元モジュール | 統一先モジュール |
|----------------|------------------|------------------|
| `detect_platform` | utils.py | platform_detector.py |

**変更内容:**

```python
# 変更前 (削除済み)
from setup_repo.utils import detect_platform

# 変更後
from setup_repo.platform_detector import detect_platform
```

#### 2.2 UV環境管理統一

**影響度: 低**

| 削除された関数 | 削除元モジュール | 統一先モジュール |
|----------------|------------------|------------------|
| `ensure_uv` | python_env.py | uv_installer.py |

**変更内容:**

```python
# 変更前 (削除済み)
from setup_repo.python_env import ensure_uv

# 変更後
from setup_repo.uv_installer import ensure_uv
```

#### 2.3 エラーレポート統一

**影響度: 低**

| 統一された関数 | 統一先モジュール | 説明 |
|----------------|------------------|------|
| `save_error_report` | quality_logger.py | CI Error HandlerとQuality Loggerの実装を統一 |

---

## 新機能 (New Features)

### 1. 移行チェックポイント機能

**新規モジュール:** `migration_checkpoint.py`

#### 追加されたクラス・関数

| 名前 | 種類 | 説明 |
|------|------|------|
| `MigrationCheckpoint` | クラス | 移行チェックポイントの管理 |
| `MigrationError` | 例外クラス | 移行関連のエラー |
| `handle_migration_error` | 関数 | 移行エラー時のロールバック処理 |

#### MigrationCheckpointクラスのメソッド

| メソッド名 | 戻り値 | 説明 |
|------------|--------|------|
| `create_checkpoint(phase, description)` | str | チェックポイントの作成 |
| `rollback_to_checkpoint(checkpoint_id)` | None | 指定チェックポイントへのロールバック |
| `list_checkpoints()` | List[Dict] | チェックポイント一覧の取得 |
| `cleanup_checkpoints(keep_latest)` | None | 古いチェックポイントのクリーンアップ |
| `get_checkpoint_info(checkpoint_id)` | Optional[Dict] | チェックポイント情報の取得 |

### 2. 後方互換性機能

**新規モジュール:** `compatibility.py`

#### 追加されたクラス・関数

| 名前 | 種類 | 説明 |
|------|------|------|
| `QualityLoggerCompatibility` | クラス | Quality Logger分割の互換性 |
| `CIErrorHandlerCompatibility` | クラス | CI Error Handler分割の互換性 |
| `LoggingConfigCompatibility` | クラス | Logging Config分割の互換性 |
| `QualityMetricsCompatibility` | クラス | Quality Metrics分割の互換性 |
| `InteractiveSetupCompatibility` | クラス | Interactive Setup分割の互換性 |
| `create_compatibility_aliases` | 関数 | 互換性エイリアスの作成 |
| `show_migration_guide` | 関数 | 移行ガイドの表示 |
| `check_deprecated_imports` | 関数 | 非推奨インポートのチェック |

---

## 非推奨機能 (Deprecated Features)

### 1. レガシーインポートパス

以下のインポートパスは非推奨となり、`DeprecationWarning`が発行されます：

#### Quality Logger関連

```python
# 非推奨 (DeprecationWarning発行)
from setup_repo.quality_logger import QualityError
from setup_repo.quality_logger import ColoredFormatter

# 推奨
from setup_repo.quality_errors import QualityError
from setup_repo.quality_formatters import ColoredFormatter
```

#### CI Error Handler関連

```python
# 非推奨 (DeprecationWarning発行)
from setup_repo.ci_error_handler import detect_ci_environment

# 推奨
from setup_repo.ci_environment import detect_ci_environment
```

#### その他のモジュール

同様に、分割されたすべてのモジュールで古いインポートパスは非推奨となります。

### 2. 削除予定の互換性機能

以下の機能は将来のバージョンで削除予定です：

- レガシー互換性モジュール (`*_legacy`)
- 非推奨警告付きエイリアス
- 自動インポートリダイレクト機能

**削除予定バージョン:** 2.0.0

---

## 移行ガイダンス

### 1. 必須対応事項

#### 高優先度 (即座に対応)

1. **Quality Logger分割**: エラー処理とフォーマッター関数のインポート更新
2. **重複関数削除**: `utils.detect_platform`と`python_env.ensure_uv`の更新

#### 中優先度 (1-2週間以内)

1. **CI Error Handler分割**: CI環境検出関数のインポート更新
2. **Logging Config分割**: カスタムハンドラーのインポート更新
3. **Quality Metrics分割**: データ収集関数のインポート更新

#### 低優先度 (1ヶ月以内)

1. **Interactive Setup分割**: 検証関数のインポート更新
2. **非推奨警告の解消**: 全ての`DeprecationWarning`の対応

### 2. 推奨対応手順

1. **現状調査**: 影響範囲の特定
2. **テスト環境での検証**: 変更の動作確認
3. **段階的更新**: モジュール単位での更新
4. **テスト実行**: 各段階でのテスト確認
5. **本番適用**: 最終的な適用

### 3. 自動化ツール

#### インポート更新スクリプト

```bash
# プロジェクトルートで実行
python scripts/update-imports.py
```

#### 非推奨警告チェック

```bash
# 非推奨警告を表示してテスト実行
python -W default::DeprecationWarning -m pytest
```

---

## 互換性マトリックス

### Python バージョン

| Python バージョン | サポート状況 | 備考 |
|-------------------|--------------|------|
| 3.9 | ✅ サポート | 最小要求バージョン |
| 3.10 | ✅ サポート | 推奨 |
| 3.11 | ✅ サポート | 推奨 |
| 3.12 | ✅ サポート | 推奨 |
| 3.13 | ✅ サポート | 最新 |

### 依存関係

| パッケージ | 変更前バージョン | 変更後バージョン | 変更内容 |
|------------|------------------|------------------|----------|
| pytest | ^7.0.0 | ^7.0.0 | 変更なし |
| ruff | ^0.1.0 | ^0.1.0 | 変更なし |
| mypy | ^1.0.0 | ^1.0.0 | 変更なし |
| basedpyright | ^1.0.0 | ^1.0.0 | 変更なし |

---

## テスト影響

### 新規テストファイル

| テストファイル | 対象モジュール | カバレッジ目標 |
|----------------|----------------|----------------|
| `test_migration_checkpoint.py` | migration_checkpoint.py | 95% |
| `test_compatibility.py` | compatibility.py | 95% |
| `test_quality_errors.py` | quality_errors.py | 95% |
| `test_quality_formatters.py` | quality_formatters.py | 95% |
| `test_ci_environment.py` | ci_environment.py | 95% |
| `test_logging_handlers.py` | logging_handlers.py | 95% |
| `test_quality_collectors.py` | quality_collectors.py | 95% |
| `test_setup_validators.py` | setup_validators.py | 95% |

### 更新されたテストファイル

既存のテストファイルも分割に合わせて更新されています。

---

## パフォーマンス影響

### インポート時間

- **改善**: モジュール分割により必要な機能のみをインポート可能
- **影響**: 初回インポート時の若干の遅延（互換性機能による）

### メモリ使用量

- **改善**: 未使用機能のメモリ使用量削減
- **影響**: 互換性機能による若干のメモリ増加

### 実行時間

- **変更なし**: 実行時のパフォーマンスに影響なし

---

## セキュリティ影響

### 新規セキュリティ機能

- チェックポイント機能による安全なロールバック
- 段階的移行による破壊的変更の回避

### セキュリティ考慮事項

- チェックポイントファイルの適切な権限設定が必要
- 一時ファイルの安全な削除

---

## 今後の計画

### バージョン 1.2.0 (予定)

- 互換性機能の改善
- 追加のテストカバレッジ向上
- パフォーマンス最適化

### バージョン 2.0.0 (予定)

- 互換性機能の削除
- 完全な新アーキテクチャへの移行
- 追加の破壊的変更

---

## サポート情報

### 問い合わせ先

- **GitHub Issues**: バグ報告・機能要求
- **移行サポート**: `docs/migration-guide.md`参照
- **API リファレンス**: 各モジュールのdocstring参照

### 関連ドキュメント

- [移行ガイド](migration-guide.md)
- [アーキテクチャドキュメント](architecture.md)
- [テスト戦略](testing-strategy.md)

---

**最終更新日**: 2025年1月
**ドキュメントバージョン**: 1.0
**対象リリース**: Setup-Repository v1.1.0
