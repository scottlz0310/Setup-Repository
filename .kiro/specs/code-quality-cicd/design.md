# Design Document

## Overview

This design ... ruff, basedpyright, pytest, uv を中心とした統合的なツールチェーンを構築します。

## Architecture

### 全体アーキテクチャ

```mermaid
graph TB
    subgraph "開発環境"
        A[開発者] --> B[Pre-commit Hooks]
                B --> C[Ruff + BasedPyright + Tests]
    end

    subgraph "CI/CDパイプライン"
        D[GitHub Actions] --> E[品質チェック]
        E --> F[セキュリティスキャン]
        F --> G[テスト実行]
        G --> H[カバレッジ測定]
                N[Ruff Linting] --> O[BasedPyright 型チェック]
                O --> P[Pytest テスト]
    end
 **BasedPyright**: 厳格な型チェック
    subgraph "依存関係管理"
        J[Dependabot] --> K[自動PR作成]
#### BasedPyright設定 (pyrightconfig.json)
        L --> M[互換性テスト]
    end
    - repo: local
    subgraph "品質保証"
            - id: basedpyright
                name: BasedPyright type checking
                entry: uv run basedpyright
                language: system
                pass_filenames: false
        P --> Q[Coverage報告]
    end

    C --> D
    I --> R[GitHub Releases]
    M --> D
```

### ツールチェーン統合

- **Ruff**: リンティング、フォーマッティング、インポート整理の統合ツール
- **BasedPyright**: 厳格な型チェック
- **Pytest**: テストフレームワークとカバレッジ測定
- **UV**: 依存関係管理と仮想環境
- **Pre-commit**: コミット前の品質チェック
- **GitHub Actions**: CI/CDパイプライン
- **Dependabot**: 自動依存関係更新

## Components and Interfaces

### 1. コード品質管理コンポーネント

#### Ruff設定 (pyproject.toml)
```toml
[tool.ruff]
target-version = "py39"
line-length = 88
select = [
    "E",    # pycodestyle errors
    "F",    # pyflakes
    "W",    # pycodestyle warnings
    "I",    # isort
    "N",    # pep8-naming
    "UP",   # pyupgrade
    "B",    # flake8-bugbear
    "A",    # flake8-builtins
    "C4",   # flake8-comprehensions
    "T20",  # flake8-print (デバッグprint禁止)
    "SIM",  # flake8-simplify
    "TCH",  # flake8-type-checking
]
ignore = []

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

[tool.pyright] (pyrightconfig.json を参照)
```toml
pythonVersion = "3.9"
reportMissingTypeStubs = true
typeCheckingMode = "strict"
```

### 2. テスト管理コンポーネント

#### Pytest設定 (pyproject.toml)
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "--strict-markers",
    "--strict-config",
    "--cov=src/setup_repo",
    "--cov-report=term-missing",
    "--cov-report=html",
    "--cov-report=xml",
    "--cov-fail-under=80",
]
markers = [
    "slow: marks tests as slow",
    "integration: marks tests as integration tests",
    "unit: marks tests as unit tests",
]
```

#### テストディレクトリ構造
```
tests/
├── __init__.py
├── conftest.py              # pytest設定とフィクスチャ
├── unit/                    # 単体テスト
│   ├── __init__.py
│   ├── test_config.py
│   ├── test_git_operations.py
│   ├── test_platform_detector.py
│   └── test_utils.py
├── integration/             # 統合テスト
│   ├── __init__.py
│   ├── test_setup_flow.py
│   └── test_sync_flow.py
└── fixtures/                # テストデータ
    ├── config_samples/
    └── mock_responses/
```

### 3. CI/CDパイプラインコンポーネント

#### GitHub Actions ワークフロー構造
```
.github/
├── workflows/
│   ├── ci.yml               # メインCI/CDパイプライン
│   ├── security.yml         # セキュリティスキャン
│   ├── release.yml          # リリース自動化
│   └── dependabot-auto-merge.yml  # Dependabot自動マージ
├── dependabot.yml           # Dependabot設定
└── ISSUE_TEMPLATE/          # イシューテンプレート
    ├── bug_report.md
    └── feature_request.md
```

### 4. Pre-commit統合コンポーネント

#### Pre-commit設定 (.pre-commit-config.yaml)
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
    - repo: local
        hooks:
            - id: basedpyright
                name: BasedPyright
                entry: uv run basedpyright
                language: system
  - repo: local
    hooks:
      - id: pytest-check
        name: pytest-check
        entry: uv run pytest tests/ -x
        language: system
        pass_filenames: false
        always_run: true
```

## Data Models

### 1. 品質メトリクス管理

```python
from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum

class QualityCheckStatus(Enum):
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"

@dataclass
class QualityMetrics:
    """品質メトリクスを管理するデータモデル"""
    ruff_issues: int
    pyright_errors: int
    test_coverage: float
    test_passed: int
    test_failed: int
    security_vulnerabilities: int

    def is_passing(self, min_coverage: float = 80.0) -> bool:
        """品質基準を満たしているかチェック"""
        return (
            self.ruff_issues == 0 and
            self.pyright_errors == 0 and
            self.test_coverage >= min_coverage and
            self.test_failed == 0 and
            self.security_vulnerabilities == 0
        )

@dataclass
class BuildResult:
    """ビルド結果を管理するデータモデル"""
    status: QualityCheckStatus
    metrics: QualityMetrics
    errors: List[str]
    warnings: List[str]
    timestamp: str
    commit_hash: str
```

### 2. 依存関係管理

```python
@dataclass
class DependencyUpdate:
    """依存関係更新情報を管理するデータモデル"""
    package_name: str
    current_version: str
    new_version: str
    update_type: str  # "major", "minor", "patch", "security"
    security_advisory: Optional[str]
    compatibility_risk: str  # "low", "medium", "high"

@dataclass
class SecurityVulnerability:
    """セキュリティ脆弱性情報を管理するデータモデル"""
    advisory_id: str
    severity: str  # "low", "medium", "high", "critical"
    package_name: str
    affected_versions: str
    patched_version: Optional[str]
    description: str
```

## Error Handling

### 1. 品質チェックエラーハンドリング

```python
class QualityCheckError(Exception):
    """品質チェック関連のエラー"""
    pass

class RuffError(QualityCheckError):
    """Ruffリンティングエラー"""
    pass

class TypeCheckError(QualityCheckError):
    """型チェックエラー (Pyright/BasedPyright)"""
    pass

class TestFailureError(QualityCheckError):
    """テスト失敗エラー"""
    pass

class CoverageError(QualityCheckError):
    """カバレッジ不足エラー"""
    pass
```

### 2. CI/CDエラーハンドリング

```python
class CIError(Exception):
    """CI/CD関連のエラー"""
    pass

class SecurityScanError(CIError):
    """セキュリティスキャンエラー"""
    pass

class ReleaseError(CIError):
    """リリースプロセスエラー"""
    pass
```

### 3. エラー報告とロギング

```python
import logging
from typing import Dict, Any

class QualityLogger:
    """品質チェック専用ロガー"""

    def __init__(self):
        self.logger = logging.getLogger("setup_repo.quality")

    def log_quality_check_start(self, check_type: str) -> None:
        """品質チェック開始をログ"""
        self.logger.info(f"品質チェック開始: {check_type}")

    def log_quality_check_result(self, check_type: str, result: Dict[str, Any]) -> None:
        """品質チェック結果をログ"""
        if result.get("success", False):
            self.logger.info(f"品質チェック成功: {check_type}")
        else:
            self.logger.error(f"品質チェック失敗: {check_type} - {result.get('errors', [])}")
```

## Testing Strategy

### 1. テスト階層

#### 単体テスト (Unit Tests)
- 各モジュールの個別機能テスト
- モック使用による外部依存関係の分離
- 高速実行（< 1秒/テスト）
- カバレッジ目標: 90%以上

#### 統合テスト (Integration Tests)
- モジュール間の相互作用テスト
- 実際のファイルシステム操作
- GitHub API呼び出し（テスト環境）
- 実行時間: 中程度（< 30秒/テスト）

#### エンドツーエンドテスト (E2E Tests)
- 完全なワークフローテスト
- 実際の環境での動作確認
- CI環境での自動実行
- 実行時間: 長時間（< 5分/テスト）

### 2. テスト実行戦略

#### 開発時テスト
```bash
# 高速単体テスト
uv run pytest tests/unit/ -v

# 特定モジュールテスト
uv run pytest tests/unit/test_config.py -v

# カバレッジ付きテスト
uv run pytest --cov=src/setup_repo --cov-report=html
```

#### CI/CDテスト
```bash
# 全テスト実行
uv run pytest tests/ --cov=src/setup_repo --cov-fail-under=80

# 並列テスト実行
uv run pytest tests/ -n auto

# JUnit形式レポート生成
uv run pytest tests/ --junit-xml=test-results.xml
```

### 3. テストデータ管理

#### フィクスチャ設計
```python
# tests/conftest.py
import pytest
from pathlib import Path
from unittest.mock import Mock

@pytest.fixture
def temp_config_dir(tmp_path):
    """一時的な設定ディレクトリ"""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    return config_dir

@pytest.fixture
def mock_github_api():
    """GitHub APIのモック"""
    mock = Mock()
    mock.get_user_repos.return_value = [
        {"name": "test-repo", "clone_url": "https://github.com/user/test-repo.git"}
    ]
    return mock

@pytest.fixture
def sample_config():
    """サンプル設定データ"""
    return {
        "github_token": "test_token",
        "github_username": "test_user",
        "clone_destination": "/tmp/repos"
    }
```

### 4. パフォーマンステスト

```python
import pytest
import time
from setup_repo.sync import sync_repositories

@pytest.mark.slow
def test_sync_performance(sample_config):
    """同期処理のパフォーマンステスト"""
    start_time = time.time()

    # 同期処理実行
    result = sync_repositories(sample_config, dry_run=True)

    execution_time = time.time() - start_time

    # パフォーマンス要件: 10リポジトリの同期が30秒以内
    assert execution_time < 30.0
    assert result.success
```

## Implementation Notes

### 1. 段階的実装アプローチ

#### フェーズ1: 基盤整備
- Ruff、BasedPyright/Pyright、Pytestの基本設定
- 基本的なテスト構造の作成
- Pre-commitフックの導入

#### フェーズ2: CI/CD構築
- GitHub Actionsワークフローの作成
- セキュリティスキャンの統合
- 自動テスト実行の設定

#### フェーズ3: 高度な自動化
- Dependabot設定
- 自動リリース管理
- 高度なセキュリティチェック

### 2. 既存コードとの統合

#### 既存設定の拡張
- `pyproject.toml`への新しいツール設定追加
- 既存のRuff設定の拡張
- MyPy設定の段階的厳格化

#### 後方互換性の維持
- 既存のCLIインターフェースの保持
- 設定ファイル形式の互換性維持
- 段階的な品質基準の導入

### 3. 品質基準の段階的導入

#### 初期段階 (緩和設定)
- Pyright / BasedPyright: 基本的な型チェックのみ
- カバレッジ: 60%以上
- Ruff: 基本的なエラーのみ

#### 中間段階 (標準設定)
- Pyright / BasedPyright: より厳格な型チェック
- カバレッジ: 80%以上
- Ruff: 包括的なチェック

#### 最終段階 (厳格設定)
- Pyright / BasedPyright: 完全な型安全性
- カバレッジ: 90%以上
- Ruff: 全ルール適用
