# Setup Repository テスト戦略ドキュメント

## 概要

Setup-Repositoryプロジェクトのテスト戦略について詳細に説明します。リファクタリング後の新しいアーキテクチャに対応した包括的なテスト手法と、80%以上のカバレッジ目標を達成するための戦略を定義します。

## テスト戦略の目標

### 1. 品質目標

- **テストカバレッジ**: 80%以上（現在66.18%から向上）
- **テスト実行時間**: 5分以内
- **テスト成功率**: 99%以上
- **回帰テスト**: 100%の既存機能保護

### 2. 保守性目標

- **テストコードの可読性**: 明確で理解しやすいテスト
- **テストの独立性**: 各テストが他のテストに依存しない
- **テストの再現性**: 環境に依存しない安定したテスト

### 3. 効率性目標

- **並行実行**: テストの並行実行による高速化
- **選択的実行**: 変更箇所に関連するテストの優先実行
- **継続的実行**: CI/CDパイプラインでの自動実行

## テスト階層

### 1. Unit Tests (単体テスト)

**目的**: 個別のモジュール・関数・クラスの動作検証

**対象**: 全てのpublicメソッドとクリティカルなprivateメソッド

**カバレッジ目標**: 各モジュール80%以上

#### テスト対象モジュール

| モジュール | 現在カバレッジ | 目標カバレッジ | 優先度 |
|------------|----------------|----------------|--------|
| cli.py | 13.7% | 70% | 高 |
| interactive_setup.py | 16.4% | 60% | 高 |
| git_operations.py | 22.4% | 70% | 高 |
| python_env.py | 24.0% | 60% | 高 |
| uv_installer.py | 24.0% | 70% | 高 |
| safety_check.py | 27.9% | 70% | 高 |
| vscode_setup.py | 42.9% | 70% | 中 |
| ci_error_handler.py | 78.4% | 85% | 中 |
| github_api.py | 76.0% | 85% | 中 |
| setup.py | 76.0% | 85% | 中 |
| quality_metrics.py | 81.0% | 95% | 低 |
| gitignore_manager.py | 81.2% | 95% | 低 |
| platform_detector.py | 81.8% | 95% | 低 |

#### 単体テストの実装パターン

##### 1. 基本テストパターン

```python
import pytest
from unittest.mock import patch, MagicMock
from setup_repo.module_name import function_name

class TestFunctionName:
    """function_name関数のテスト"""
    
    def test_normal_case(self):
        """正常系テスト"""
        # Arrange
        input_data = "test_input"
        expected = "expected_output"
        
        # Act
        result = function_name(input_data)
        
        # Assert
        assert result == expected
    
    def test_error_case(self):
        """異常系テスト"""
        with pytest.raises(ValueError, match="Invalid input"):
            function_name(None)
    
    @pytest.mark.parametrize("input_val,expected", [
        ("input1", "output1"),
        ("input2", "output2"),
        ("input3", "output3"),
    ])
    def test_parametrized_cases(self, input_val, expected):
        """パラメータ化テスト"""
        result = function_name(input_val)
        assert result == expected
```

##### 2. モックを使用したテストパターン

```python
@patch('setup_repo.module_name.external_dependency')
def test_with_external_dependency(self, mock_dependency):
    """外部依存関係をモックしたテスト"""
    # Arrange
    mock_dependency.return_value = "mocked_result"
    
    # Act
    result = function_with_dependency()
    
    # Assert
    assert result == "expected_result"
    mock_dependency.assert_called_once_with("expected_args")
```

##### 3. ファイルシステムテストパターン

```python
import tempfile
from pathlib import Path

def test_file_operation():
    """ファイル操作のテスト"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Arrange
        test_file = Path(temp_dir) / "test.txt"
        
        # Act
        create_file(test_file, "test content")
        
        # Assert
        assert test_file.exists()
        assert test_file.read_text() == "test content"
```

### 2. Integration Tests (統合テスト)

**目的**: モジュール間の連携動作検証

**対象**: 主要なワークフローとモジュール間インターフェース

**カバレッジ目標**: 主要フロー100%

#### 統合テストの種類

##### 2.1 ワークフロー統合テスト

```python
class TestSetupWorkflow:
    """セットアップワークフローの統合テスト"""
    
    @patch('setup_repo.github_api.get_repositories')
    @patch('setup_repo.git_operations.clone_repository')
    def test_full_setup_workflow(self, mock_clone, mock_get_repos):
        """完全なセットアップワークフローテスト"""
        # Arrange
        mock_get_repos.return_value = [{"name": "test-repo", "clone_url": "https://github.com/user/test-repo.git"}]
        mock_clone.return_value = True
        
        config = {
            "github_token": "test_token",
            "target_directory": "/tmp/test"
        }
        
        # Act
        result = run_setup(config)
        
        # Assert
        assert result.success is True
        mock_get_repos.assert_called_once()
        mock_clone.assert_called_once()
```

##### 2.2 エラーハンドリング統合テスト

```python
class TestErrorHandlingIntegration:
    """エラーハンドリングの統合テスト"""
    
    @patch('setup_repo.github_api.get_repositories')
    def test_github_api_error_handling(self, mock_get_repos):
        """GitHub APIエラー時の統合処理テスト"""
        # Arrange
        mock_get_repos.side_effect = GitHubAPIError("API rate limit exceeded")
        
        # Act & Assert
        with pytest.raises(SetupError, match="GitHub API error"):
            run_setup({"github_token": "invalid_token"})
```

##### 2.3 クロスプラットフォーム統合テスト

```python
class TestCrossPlatformIntegration:
    """クロスプラットフォーム統合テスト"""
    
    @pytest.mark.parametrize("platform", ["windows", "linux", "macos"])
    @patch('setup_repo.platform_detector.detect_platform')
    def test_platform_specific_setup(self, mock_detect, platform):
        """プラットフォーム固有セットアップの統合テスト"""
        # Arrange
        mock_detect.return_value = platform
        
        # Act
        result = setup_platform_specific_tools()
        
        # Assert
        assert result.platform == platform
        assert result.tools_installed is True
```

### 3. Performance Tests (パフォーマンステスト)

**目的**: システムのパフォーマンス特性の検証

**対象**: 大量データ処理、メモリ使用量、実行時間

#### パフォーマンステストの種類

##### 3.1 大量リポジトリ処理テスト

```python
import time
import psutil
import pytest

class TestLargeRepositoryPerformance:
    """大量リポジトリ処理のパフォーマンステスト"""
    
    @pytest.mark.performance
    def test_sync_100_repositories(self):
        """100個のリポジトリ同期パフォーマンステスト"""
        # Arrange
        repositories = [f"repo_{i}" for i in range(100)]
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss
        
        # Act
        result = sync_repositories(repositories)
        
        # Assert
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss
        
        execution_time = end_time - start_time
        memory_usage = end_memory - start_memory
        
        assert execution_time < 300  # 5分以内
        assert memory_usage < 100 * 1024 * 1024  # 100MB以内
        assert result.success_count == 100
```

##### 3.2 メモリリークテスト

```python
class TestMemoryLeaks:
    """メモリリークテスト"""
    
    @pytest.mark.performance
    def test_repeated_operations_memory_usage(self):
        """繰り返し操作でのメモリ使用量テスト"""
        initial_memory = psutil.Process().memory_info().rss
        
        # 1000回の操作を実行
        for i in range(1000):
            result = perform_operation()
            assert result is not None
        
        final_memory = psutil.Process().memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # メモリ増加が10MB以内であることを確認
        assert memory_increase < 10 * 1024 * 1024
```

### 4. End-to-End Tests (E2Eテスト)

**目的**: ユーザーの実際の使用シナリオの検証

**対象**: CLIコマンドの完全な実行フロー

#### E2Eテストの実装

```python
import subprocess
import tempfile
from pathlib import Path

class TestEndToEndScenarios:
    """エンドツーエンドシナリオテスト"""
    
    def test_complete_setup_scenario(self):
        """完全なセットアップシナリオのE2Eテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Arrange
            config_file = Path(temp_dir) / "config.json"
            config_file.write_text(json.dumps({
                "github_token": "test_token",
                "target_directory": temp_dir
            }))
            
            # Act
            result = subprocess.run([
                "python", "main.py", "setup",
                "--config", str(config_file)
            ], capture_output=True, text=True)
            
            # Assert
            assert result.returncode == 0
            assert "Setup completed successfully" in result.stdout
```

## テストデータ管理

### 1. テストフィクスチャ

#### 共通フィクスチャ

```python
# tests/conftest.py
import pytest
import tempfile
from pathlib import Path

@pytest.fixture
def temp_directory():
    """一時ディレクトリフィクスチャ"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)

@pytest.fixture
def sample_config():
    """サンプル設定フィクスチャ"""
    return {
        "github_token": "test_token",
        "target_directory": "/tmp/test",
        "repositories": ["test-repo1", "test-repo2"]
    }

@pytest.fixture
def mock_github_api():
    """GitHub APIモックフィクスチャ"""
    with patch('setup_repo.github_api.GitHubAPI') as mock:
        mock.return_value.get_repositories.return_value = [
            {"name": "test-repo", "clone_url": "https://github.com/user/test-repo.git"}
        ]
        yield mock
```

#### モジュール固有フィクスチャ

```python
# tests/unit/test_git_operations.py
@pytest.fixture
def git_repository(temp_directory):
    """Gitリポジトリフィクスチャ"""
    repo_dir = temp_directory / "test-repo"
    repo_dir.mkdir()
    
    # 初期化
    subprocess.run(["git", "init"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_dir, check=True)
    
    # 初期コミット
    (repo_dir / "README.md").write_text("# Test Repository")
    subprocess.run(["git", "add", "README.md"], cwd=repo_dir, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_dir, check=True)
    
    return repo_dir
```

### 2. テストデータファイル

```
tests/
├── fixtures/
│   ├── config_samples/
│   │   ├── valid_config.json
│   │   ├── invalid_config.json
│   │   └── minimal_config.json
│   ├── mock_responses/
│   │   ├── github_api_responses.json
│   │   ├── git_status_outputs.txt
│   │   └── quality_tool_outputs.json
│   └── test_repositories/
│       ├── python_project/
│       ├── javascript_project/
│       └── mixed_project/
```

## モック戦略

### 1. 外部依存関係のモック

#### GitHub API

```python
@pytest.fixture
def mock_github_api():
    """GitHub APIのモック"""
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "repositories": [
                {"name": "repo1", "clone_url": "https://github.com/user/repo1.git"},
                {"name": "repo2", "clone_url": "https://github.com/user/repo2.git"}
            ]
        }
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        yield mock_get
```

#### ファイルシステム操作

```python
@pytest.fixture
def mock_file_operations():
    """ファイルシステム操作のモック"""
    with patch('pathlib.Path.exists') as mock_exists, \
         patch('pathlib.Path.mkdir') as mock_mkdir, \
         patch('pathlib.Path.write_text') as mock_write:
        
        mock_exists.return_value = True
        yield {
            'exists': mock_exists,
            'mkdir': mock_mkdir,
            'write_text': mock_write
        }
```

#### 外部コマンド実行

```python
@pytest.fixture
def mock_subprocess():
    """サブプロセス実行のモック"""
    with patch('subprocess.run') as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Command executed successfully"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        yield mock_run
```

### 2. 内部依存関係のモック

#### 設定管理

```python
@pytest.fixture
def mock_config():
    """設定管理のモック"""
    with patch('setup_repo.config.load_config') as mock_load:
        mock_load.return_value = {
            "github_token": "test_token",
            "target_directory": "/tmp/test"
        }
        yield mock_load
```

## テスト実行戦略

### 1. 並行実行

```bash
# pytest-xdistを使用した並行実行
uv run pytest -n auto

# 特定の数のワーカーで実行
uv run pytest -n 4
```

### 2. 選択的実行

```bash
# マーカーによる選択実行
uv run pytest -m "not performance"  # パフォーマンステスト以外
uv run pytest -m "unit"             # 単体テストのみ
uv run pytest -m "integration"      # 統合テストのみ

# ファイルパターンによる選択実行
uv run pytest tests/unit/           # 単体テストディレクトリ
uv run pytest -k "test_setup"       # setup関連テスト
```

### 3. カバレッジ測定

```bash
# カバレッジ付きテスト実行
uv run pytest --cov=src/setup_repo --cov-report=html --cov-report=term

# カバレッジ閾値チェック
uv run pytest --cov=src/setup_repo --cov-fail-under=80

# 詳細カバレッジレポート
uv run pytest --cov=src/setup_repo --cov-report=html --cov-report=term-missing
```

## CI/CD統合

### 1. GitHub Actions設定

```yaml
# .github/workflows/test.yml
name: Test Suite

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python-version: [3.9, 3.10, 3.11, 3.12]
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Install uv
      uses: astral-sh/setup-uv@v1
      with:
        version: "latest"
    
    - name: Set up Python
      run: uv python install ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: uv sync --dev
    
    - name: Run unit tests
      run: uv run pytest tests/unit/ --cov=src/setup_repo --cov-report=xml
    
    - name: Run integration tests
      run: uv run pytest tests/integration/
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

### 2. 品質ゲート

```yaml
# .github/workflows/quality-gate.yml
name: Quality Gate

on:
  pull_request:
    branches: [ main ]

jobs:
  quality-check:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Install uv
      uses: astral-sh/setup-uv@v1
    
    - name: Install dependencies
      run: uv sync --dev
    
    - name: Run linting
      run: uv run ruff check .
    
    - name: Run type checking
      run: uv run mypy src/
    
    - name: Run tests with coverage
      run: uv run pytest --cov=src/setup_repo --cov-fail-under=80
    
    - name: Run security checks
      run: uv run bandit -r src/
```

## テストメトリクス

### 1. カバレッジメトリクス

- **行カバレッジ**: 実行された行の割合
- **分岐カバレッジ**: 実行された分岐の割合
- **関数カバレッジ**: 呼び出された関数の割合

### 2. 品質メトリクス

- **テスト成功率**: 成功したテストの割合
- **テスト実行時間**: 各テストの実行時間
- **テストの安定性**: 同じ条件での成功率

### 3. 保守性メトリクス

- **テストコードの複雑度**: テストコードの理解しやすさ
- **テストの独立性**: 他のテストへの依存度
- **テストデータの管理**: テストデータの整理状況

## テスト環境管理

### 1. 開発環境

```bash
# 開発環境でのテスト実行
uv sync --dev
uv run pytest --cov=src/setup_repo --cov-report=html

# ウォッチモードでのテスト実行
uv run pytest-watch
```

### 2. CI環境

```bash
# CI環境での最適化されたテスト実行
uv run pytest --cov=src/setup_repo --cov-report=xml --tb=short -q
```

### 3. 本番環境テスト

```bash
# 本番環境での煙テスト
uv run pytest tests/smoke/ --tb=short
```

## トラブルシューティング

### 1. よくある問題

#### テストの不安定性

**問題**: テストが時々失敗する

**解決策**:

- 外部依存関係の適切なモック
- テスト間の状態共有の排除
- 時間依存処理の固定化

#### カバレッジの不足

**問題**: カバレッジが目標に達しない

**解決策**:

- 未テストコードパスの特定
- エッジケースのテスト追加
- 例外処理のテスト強化

#### テスト実行時間の増加

**問題**: テスト実行に時間がかかりすぎる

**解決策**:

- 並行実行の活用
- 重いテストの最適化
- 選択的テスト実行

### 2. デバッグ手法

#### テスト失敗の調査

```bash
# 詳細な失敗情報を表示
uv run pytest --tb=long -v

# 特定のテストのみ実行
uv run pytest tests/unit/test_specific.py::TestClass::test_method -v

# デバッガーでテスト実行
uv run pytest --pdb
```

#### カバレッジ不足の調査

```bash
# 未カバー行の表示
uv run pytest --cov=src/setup_repo --cov-report=term-missing

# HTMLレポートでの詳細確認
uv run pytest --cov=src/setup_repo --cov-report=html
open htmlcov/index.html
```

## 継続的改善

### 1. テスト品質の監視

- 定期的なテストレビュー
- カバレッジトレンドの監視
- テスト実行時間の追跡

### 2. テスト戦略の更新

- 新機能に対するテスト戦略の策定
- 既存テストの改善
- テストツールの評価・導入

### 3. チーム教育

- テスト作成のベストプラクティス共有
- 新しいテスト手法の導入
- テストレビューの実施

## まとめ

この包括的なテスト戦略により、Setup-Repositoryプロジェクトは以下を実現します：

1. **高品質の保証**: 80%以上のカバレッジによる品質保証
2. **継続的な品質向上**: CI/CDパイプラインでの自動テスト
3. **効率的な開発**: 適切なテスト分類による効率的な実行
4. **保守性の確保**: 明確で理解しやすいテストコード
5. **回帰防止**: 包括的なテストによる既存機能の保護

この戦略に従うことで、リファクタリング後のアーキテクチャを安全に保ち、継続的な改善を実現できます。
