# 設計ドキュメント

## 概要

Setup-Repositoryプロジェクトの責任分離リファクタリングとテストカバレッジ向上を実現するための包括的な設計です。現在のモノリシックな構造から、責任が明確に分離された保守性の高いアーキテクチャへの移行を行います。

## アーキテクチャ

### 現在のアーキテクチャの問題点

```
現在の問題:
├── 責任重複: 4件の重複関数
├── 大きなモジュール: 5つのモジュールが8関数以上
├── テストカバレッジ不足: 66.18% (目標: 80%)
└── 品質ゲート不備: 継続的監視体制なし
```

### 目標アーキテクチャ

```
リファクタリング後:
├── 責任分離完了: 重複解消、適切なモジュール分割
├── 包括的テストスイート: 80%以上のカバレッジ
├── 品質ゲート強化: 自動監視・アラート機能
└── 継続的改善体制: 月次レビュー・メトリクス監視
```

## コンポーネントと インターフェース

### Phase 1: 責任重複解消コンポーネント

#### 1.1 プラットフォーム検出統一
```python
# 統一後のインターフェース
from setup_repo.platform_detector import detect_platform

# 削除対象: utils.py の detect_platform()
# 移行先: platform_detector.py の detect_platform()
```

**影響範囲:**
- `src/setup_repo/utils.py` (関数削除)
- `src/setup_repo/sync.py` (インポート変更)
- その他の呼び出し箇所

#### 1.2 UV環境管理統一
```python
# 統一後のインターフェース
from setup_repo.uv_installer import ensure_uv

# 削除対象: python_env.py の ensure_uv()
# 移行先: uv_installer.py の ensure_uv()
```

#### 1.3 エラーレポート統一
```python
# 統一後のインターフェース
from setup_repo.quality_logger import save_error_report

# 機能差分分析後の統一インターフェース設計
class ErrorReporter:
    def save_report(self, error_data: dict, report_type: str) -> bool
    def get_report_path(self, report_type: str) -> Path
```

### Phase 2: モジュール分割コンポーネント

#### 2.1 Quality Logger分割
```
quality_logger.py (19関数) → 3モジュール:

quality_logger.py (8関数):
├── setup_quality_logging()
├── get_quality_logger()
├── log_quality_event()
├── log_quality_summary()
├── configure_logging()
├── set_log_level()
├── cleanup_old_logs()
└── get_log_file_path()

quality_errors.py (6関数):
├── QualityError (class)
├── QualityWarning (class)
├── handle_quality_error()
├── format_error_message()
├── log_exception()
└── create_error_report()

quality_formatters.py (5関数):
├── ColoredFormatter (class)
├── JSONFormatter (class)
├── format_log_message()
├── add_color_codes()
└── strip_color_codes()
```

#### 2.2 CI Error Handler分割
```
ci_error_handler.py (11関数) → 2モジュール:

ci_environment.py (5関数):
├── detect_ci_environment()
├── get_system_info()
├── collect_environment_vars()
├── get_ci_metadata()
└── is_ci_environment()

ci_error_handler.py (6関数):
├── handle_ci_error()
├── generate_error_report()
├── send_notification()
├── save_error_report()
├── format_ci_error()
└── cleanup_error_reports()
```

#### 2.3 Logging Config分割
```
logging_config.py (11関数) → 2モジュール:

logging_config.py (6関数):
├── setup_logging()
├── get_log_config()
├── configure_environment_logging()
├── set_global_log_level()
├── reset_logging_config()
└── validate_log_config()

logging_handlers.py (5関数):
├── TeeHandler (class)
├── RotatingFileHandler (class)
├── ColoredConsoleHandler (class)
├── create_file_handler()
└── create_console_handler()
```

#### 2.4 Quality Metrics分割
```
quality_metrics.py (11関数) → 2モジュール:

quality_metrics.py (6関数):
├── calculate_quality_score()
├── get_quality_metrics()
├── generate_quality_report()
├── compare_quality_trends()
├── save_metrics_report()
└── load_historical_metrics()

quality_collectors.py (5関数):
├── collect_ruff_metrics()
├── collect_mypy_metrics()
├── collect_pytest_metrics()
├── collect_coverage_metrics()
└── parse_tool_output()
```

#### 2.5 Interactive Setup分割
```
interactive_setup.py (10関数) → 2モジュール:

interactive_setup.py (6関数):
├── run_interactive_setup()
├── setup_wizard()
├── handle_user_input()
├── display_setup_progress()
├── complete_setup()
└── save_setup_config()

setup_validators.py (4関数):
├── validate_github_credentials()
├── validate_directory_path()
├── validate_setup_prerequisites()
└── check_system_requirements()
```

### Phase 3: テストカバレッジ向上コンポーネント

#### 3.1 低カバレッジモジュール対応
```
新規テストファイル:
tests/unit/
├── test_cli.py (cli.py: 13.7% → 70%)
├── test_interactive_setup.py (interactive_setup.py: 16.4% → 60%)
├── test_git_operations.py (git_operations.py: 22.4% → 70%)
├── test_python_env.py (python_env.py: 24.0% → 60%)
├── test_uv_installer.py (uv_installer.py: 24.0% → 70%)
├── test_safety_check.py (safety_check.py: 27.9% → 70%)
└── test_vscode_setup.py (vscode_setup.py: 42.9% → 70%)
```

#### 3.2 統合テスト強化
```
tests/integration/
├── test_full_workflow.py (完全な同期ワークフロー)
├── test_error_scenarios.py (エラーハンドリングフロー)
└── test_cross_platform.py (クロスプラットフォーム)

tests/performance/
├── test_large_repos.py (大量リポジトリ処理)
└── test_error_recovery.py (エラー回復処理)
```

### Phase 4: 品質ゲート強化コンポーネント

#### 4.1 カバレッジ監視システム
```python
# scripts/coverage-monitor.py
class CoverageMonitor:
    def check_coverage_requirements(self) -> bool
    def generate_coverage_report(self) -> dict
    def send_coverage_alert(self, coverage: float) -> None
    def update_coverage_badge(self, coverage: float) -> None
```

#### 4.2 品質メトリクス監視
```python
# scripts/quality-monitor.py
class QualityMonitor:
    def collect_quality_metrics(self) -> dict
    def compare_with_baseline(self, metrics: dict) -> dict
    def generate_quality_trend_report(self) -> None
    def check_quality_gates(self) -> bool
```

## データモデル

### カバレッジデータモデル
```python
@dataclass
class CoverageReport:
    total_coverage: float
    module_coverage: Dict[str, float]
    missing_lines: Dict[str, List[int]]
    timestamp: datetime

@dataclass
class CoverageTarget:
    total_target: float = 80.0
    module_target: float = 60.0
    critical_module_target: float = 80.0
```

### リファクタリング進捗モデル
```python
@dataclass
class RefactoringProgress:
    phase: str
    completed_tasks: List[str]
    remaining_tasks: List[str]
    coverage_improvement: float
    quality_score: float
```

### 品質メトリクスモデル
```python
@dataclass
class QualityMetrics:
    ruff_score: float
    mypy_score: float
    test_coverage: float
    complexity_score: float
    maintainability_index: float
    timestamp: datetime
```

## エラーハンドリング

### リファクタリングエラー処理
```python
class RefactoringError(Exception):
    """リファクタリング固有のエラー"""
    pass

class ModuleSplitError(RefactoringError):
    """モジュール分割エラー"""
    pass

class DependencyUpdateError(RefactoringError):
    """依存関係更新エラー"""
    pass
```

### カバレッジエラー処理
```python
class CoverageError(Exception):
    """カバレッジ関連エラー"""
    pass

class CoverageThresholdError(CoverageError):
    """カバレッジ閾値エラー"""
    pass
```

### 段階的移行エラー処理
```python
def handle_migration_error(error: Exception, rollback_point: str) -> None:
    """移行エラー時のロールバック処理"""
    logger.error(f"Migration failed: {error}")
    rollback_to_checkpoint(rollback_point)
    raise MigrationError(f"Failed to migrate: {error}")
```

## テスト戦略

### テスト階層
```
テスト階層:
├── Unit Tests (単体テスト)
│   ├── 各モジュールの関数・クラステスト
│   ├── モック使用による依存関係分離
│   └── エッジケース・異常系テスト
├── Integration Tests (統合テスト)
│   ├── モジュール間連携テスト
│   ├── エンドツーエンドワークフローテスト
│   └── 外部依存関係テスト
└── Performance Tests (パフォーマンステスト)
    ├── 大量データ処理テスト
    ├── メモリ使用量テスト
    └── 実行時間テスト
```

### テスト実装パターン
```python
# パラメータ化テスト
@pytest.mark.parametrize("platform,expected", [
    ("windows", "windows"),
    ("linux", "linux"),
    ("darwin", "macos"),
])
def test_platform_detection(platform, expected):
    with patch('platform.system', return_value=platform):
        assert detect_platform() == expected

# モックを使用した外部依存テスト
@patch('requests.get')
def test_github_api_success(mock_get):
    mock_get.return_value.json.return_value = {"name": "test"}
    result = get_repositories("user", "token")
    assert result[0]["name"] == "test"

# エラーハンドリングテスト
def test_config_load_error_handling():
    with patch('builtins.open', side_effect=IOError):
        config = load_config_safely()
        assert config == {}  # デフォルト値
```

### カバレッジ目標とマイルストーン
```
カバレッジマイルストーン:
├── Week 1: 重複解消完了 (カバレッジ維持: 66%)
├── Week 2: モジュール分割完了 (カバレッジ維持: 66%)
├── Week 3: テスト更新完了 (カバレッジ: 70%)
├── Week 4: 低カバレッジ改善完了 (カバレッジ: 75%)
├── Week 5: 統合テスト強化完了 (カバレッジ: 80%)
└── Week 6: 品質向上・最終調整完了 (カバレッジ: 85%)
```

## 実装フェーズ

### Phase 1: 責任重複解消 (Week 1)
- 重複関数の特定と分析
- 統一インターフェースの設計
- 段階的な重複解消
- インポート文の更新

### Phase 2: モジュール分割 (Week 2)
- 大きなモジュールの責任分析
- 分割設計と新モジュール作成
- 既存コードの移行
- インターフェース調整

### Phase 3: テスト更新 (Week 3)
- 分割されたモジュールのテスト作成
- 既存テストの更新・移行
- カバレッジ測定・検証

### Phase 4-6: カバレッジ向上 (Week 4-6)
- 低カバレッジモジュールの優先改善
- 統合テストの強化
- パフォーマンステストの追加
- 品質ゲートの強化

## 移行戦略

### 後方互換性維持
```python
# 段階的移行のためのdeprecation警告
import warnings

def old_function():
    warnings.warn(
        "old_function is deprecated, use new_module.new_function instead",
        DeprecationWarning,
        stacklevel=2
    )
    return new_module.new_function()
```

### ロールバック戦略
```python
# チェックポイント機能
class MigrationCheckpoint:
    def create_checkpoint(self, phase: str) -> str
    def rollback_to_checkpoint(self, checkpoint_id: str) -> None
    def cleanup_checkpoints(self) -> None
```

## 品質保証

### 自動化された品質チェック
```yaml
# CI/CD パイプライン統合
quality_gates:
  - ruff_check: "uv run ruff check ."
    - mypy_check: "uv run basedpyright src/"
  - test_execution: "uv run pytest"
  - coverage_check: "uv run pytest --cov=src/setup_repo --cov-fail-under=80"
  - quality_metrics: "uv run python scripts/quality-monitor.py"
```

### 継続的監視
```python
# 品質メトリクス監視
def monitor_quality_trends():
    """品質トレンドの継続的監視"""
    current_metrics = collect_quality_metrics()
    baseline_metrics = load_baseline_metrics()

    if quality_degraded(current_metrics, baseline_metrics):
        send_quality_alert(current_metrics)

    update_quality_dashboard(current_metrics)
```
