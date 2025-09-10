# テスト実装例とベストプラクティス

## 🧪 テスト実装パターン

### 基盤モジュールテストの例

#### `test_config.py` 拡張例
```python
"""設定管理モジュールのテスト"""

import pytest
from unittest.mock import patch, mock_open
from pathlib import Path
from setup_repo.config import (
    load_config, 
    get_github_token, 
    get_github_user,
    auto_detect_config
)

class TestConfigManagement:
    """設定管理のテスト"""
    
    def test_load_config_with_local_file(self, temp_dir):
        """ローカル設定ファイル読み込みテスト"""
        config_file = temp_dir / "config.local.json"
        config_data = {
            "owner": "test_user",
            "github_token": "test_token"
        }
        config_file.write_text(json.dumps(config_data))
        
        with patch('setup_repo.config.Path.cwd', return_value=temp_dir):
            result = load_config()
            
        assert result["owner"] == "test_user"
        assert result["github_token"] == "test_token"
    
    @patch.dict('os.environ', {'GITHUB_TOKEN': 'env_token'})
    def test_get_github_token_from_env(self):
        """環境変数からのトークン取得テスト"""
        token = get_github_token()
        assert token == "env_token"
    
    @patch('subprocess.run')
    def test_get_github_token_from_gh_cli(self, mock_run):
        """gh CLIからのトークン取得テスト"""
        mock_run.return_value.stdout = "gh_cli_token"
        mock_run.return_value.returncode = 0
        
        with patch.dict('os.environ', {}, clear=True):
            token = get_github_token()
            
        assert token == "gh_cli_token"
        mock_run.assert_called_once()

    @pytest.mark.parametrize("env_vars,expected", [
        ({"GITHUB_USER": "env_user"}, "env_user"),
        ({"GITHUB_USERNAME": "username"}, "username"),
        ({}, None),
    ])
    def test_get_github_user_various_sources(self, env_vars, expected):
        """様々なソースからのユーザー名取得テスト"""
        with patch.dict('os.environ', env_vars, clear=True):
            result = get_github_user()
            
        assert result == expected
```

#### `test_utils.py` 新規作成例
```python
"""ユーティリティモジュールのテスト"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open
from setup_repo.utils import ProcessLock, TeeLogger

class TestProcessLock:
    """プロセスロックのテスト"""
    
    def test_lock_acquire_success(self, temp_dir):
        """ロック取得成功テスト"""
        lock_file = temp_dir / "test.lock"
        lock = ProcessLock(str(lock_file))
        
        result = lock.acquire()
        
        assert result is True
        assert lock.lock_fd is not None
        
        lock.release()
    
    def test_lock_acquire_failure_when_locked(self, temp_dir):
        """既にロックされている場合の取得失敗テスト"""
        lock_file = temp_dir / "test.lock"
        
        # 最初のロック
        lock1 = ProcessLock(str(lock_file))
        assert lock1.acquire() is True
        
        # 2番目のロック（失敗するはず）
        lock2 = ProcessLock(str(lock_file))
        assert lock2.acquire() is False
        
        lock1.release()
    
    def test_lock_release(self, temp_dir):
        """ロック解放テスト"""
        lock_file = temp_dir / "test.lock"
        lock = ProcessLock(str(lock_file))
        
        lock.acquire()
        lock.release()
        
        assert lock.lock_fd is None
        assert not lock_file.exists()

class TestTeeLogger:
    """TeeLoggerのテスト"""
    
    def test_tee_logger_without_file(self, capsys):
        """ファイル出力なしのTeeLoggerテスト"""
        logger = TeeLogger()
        
        print("test message")
        logger.close()
        
        captured = capsys.readouterr()
        assert "test message" in captured.out
    
    def test_tee_logger_with_file(self, temp_dir, capsys):
        """ファイル出力ありのTeeLoggerテスト"""
        log_file = temp_dir / "test.log"
        logger = TeeLogger(str(log_file))
        
        print("test message")
        logger.close()
        
        # コンソール出力確認
        captured = capsys.readouterr()
        assert "test message" in captured.out
        
        # ファイル出力確認
        assert log_file.exists()
        content = log_file.read_text()
        assert "test message" in content
```

### API層テストの例

#### `test_github_api.py` 新規作成例
```python
"""GitHub API操作のテスト"""

import pytest
from unittest.mock import Mock, patch
from setup_repo.github_api import GitHubAPI, GitHubAPIError, get_repositories

class TestGitHubAPI:
    """GitHub API操作のテスト"""
    
    @pytest.fixture
    def github_api(self):
        """GitHubAPIインスタンス"""
        return GitHubAPI(token="test_token", username="test_user")
    
    @patch('requests.get')
    def test_get_user_repos_success(self, mock_get, github_api):
        """リポジトリ一覧取得成功テスト"""
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "name": "repo1",
                "full_name": "test_user/repo1",
                "clone_url": "https://github.com/test_user/repo1.git",
                "ssh_url": "git@github.com:test_user/repo1.git",
                "private": False
            }
        ]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        repos = github_api.get_user_repos()
        
        assert len(repos) == 1
        assert repos[0]["name"] == "repo1"
        mock_get.assert_called_once()
    
    @patch('requests.get')
    def test_get_user_repos_api_error(self, mock_get, github_api):
        """API エラー時のテスト"""
        mock_get.side_effect = Exception("API Error")
        
        with pytest.raises(GitHubAPIError):
            github_api.get_user_repos()
    
    @patch('requests.get')
    def test_get_user_info_success(self, mock_get, github_api):
        """ユーザー情報取得成功テスト"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "login": "test_user",
            "name": "Test User",
            "email": "test@example.com"
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        user_info = github_api.get_user_info()
        
        assert user_info["login"] == "test_user"
        assert user_info["name"] == "Test User"

@patch('setup_repo.github_api.GitHubAPI')
def test_get_repositories_function(mock_github_api_class):
    """get_repositories関数のテスト"""
    mock_api = Mock()
    mock_api.get_user_repos.return_value = [{"name": "test_repo"}]
    mock_github_api_class.return_value = mock_api
    
    repos = get_repositories("test_user", "test_token")
    
    assert len(repos) == 1
    assert repos[0]["name"] == "test_repo"
    mock_github_api_class.assert_called_once_with(
        token="test_token", 
        username="test_user"
    )
```

### 統合テストの例

#### `test_sync_integration.py` 拡張例
```python
"""同期機能の統合テスト"""

import pytest
from unittest.mock import patch, Mock
from pathlib import Path
from setup_repo.sync import sync_repositories

@pytest.mark.integration
class TestSyncIntegration:
    """同期機能の統合テスト"""
    
    @patch('setup_repo.sync.get_repositories')
    @patch('setup_repo.sync.sync_repository_with_retries')
    @patch('setup_repo.sync.GitignoreManager')
    @patch('setup_repo.sync.apply_vscode_template')
    def test_full_sync_workflow(
        self, 
        mock_vscode, 
        mock_gitignore_manager, 
        mock_sync_repo, 
        mock_get_repos,
        temp_dir
    ):
        """完全な同期ワークフローテスト"""
        # モックセットアップ
        mock_get_repos.return_value = [
            {
                "name": "test-repo",
                "clone_url": "https://github.com/user/test-repo.git",
                "ssh_url": "git@github.com:user/test-repo.git"
            }
        ]
        mock_sync_repo.return_value = True
        
        mock_gitignore = Mock()
        mock_gitignore.setup_gitignore.return_value = True
        mock_gitignore_manager.return_value = mock_gitignore
        
        # 設定
        config = {
            "owner": "test_user",
            "dest": str(temp_dir),
            "github_token": "test_token",
            "dry_run": False
        }
        
        # 実行
        result = sync_repositories(config)
        
        # 検証
        assert result.success is True
        assert len(result.synced_repos) == 1
        assert "test-repo" in result.synced_repos
        
        mock_get_repos.assert_called_once()
        mock_sync_repo.assert_called_once()
        mock_gitignore.setup_gitignore.assert_called_once()
        mock_vscode.assert_called_once()
```

## 🎯 カバレッジ最適化テクニック

### 1. エッジケースの網羅
```python
@pytest.mark.parametrize("input_value,expected_exception", [
    ("", ValueError),
    (None, TypeError),
    ("invalid_path", FileNotFoundError),
])
def test_edge_cases(input_value, expected_exception):
    """エッジケースのテスト"""
    with pytest.raises(expected_exception):
        function_under_test(input_value)
```

### 2. 条件分岐の完全カバー
```python
def test_all_platform_branches():
    """全プラットフォーム分岐のテスト"""
    with patch('platform.system', return_value='Windows'):
        assert detect_platform() == "windows"
        
    with patch('platform.system', return_value='Darwin'):
        assert detect_platform() == "macos"
        
    with patch('platform.system', return_value='Linux'):
        assert detect_platform() == "linux"
```

### 3. 例外処理のテスト
```python
def test_exception_handling():
    """例外処理のテスト"""
    with patch('builtins.open', side_effect=IOError("File not found")):
        result = load_config_safely()
        assert result == {}  # デフォルト値が返される
```

## 📊 カバレッジ監視の自動化

### カバレッジ監視スクリプト
```python
# scripts/coverage-monitor.py
import json
import sys
from pathlib import Path

def check_coverage_requirements():
    """カバレッジ要件チェック"""
    coverage_file = Path("coverage.json")
    if not coverage_file.exists():
        print("❌ カバレッジファイルが見つかりません")
        return False
    
    with open(coverage_file) as f:
        data = json.load(f)
    
    total_coverage = data["totals"]["percent_covered"]
    
    # 全体カバレッジチェック
    if total_coverage < 80:
        print(f"❌ 総合カバレッジ不足: {total_coverage:.1f}% < 80%")
        return False
    
    # モジュール別カバレッジチェック
    failed_modules = []
    for filename, file_data in data["files"].items():
        if "src/setup_repo" in filename:
            module_coverage = file_data["summary"]["percent_covered"]
            if module_coverage < 60:
                failed_modules.append(f"{filename}: {module_coverage:.1f}%")
    
    if failed_modules:
        print("❌ カバレッジ不足モジュール:")
        for module in failed_modules:
            print(f"   {module}")
        return False
    
    print(f"✅ カバレッジ要件を満たしています: {total_coverage:.1f}%")
    return True

if __name__ == "__main__":
    success = check_coverage_requirements()
    sys.exit(0 if success else 1)
```

### Makefileタスク追加
```makefile
# カバレッジ監視
coverage-monitor:
	@echo "📊 カバレッジ監視実行中..."
	uv run pytest --cov=src/setup_repo --cov-report=json
	uv run python scripts/coverage-monitor.py

# カバレッジトレンド
coverage-trend:
	@echo "📈 カバレッジトレンド分析中..."
	uv run python scripts/coverage-trend-analysis.py
```

## ✅ テスト品質チェックリスト

### 各テストファイルで確認すべき項目
- [ ] 全ての public 関数・メソッドをテスト
- [ ] 正常系・異常系の両方をカバー
- [ ] エッジケース（空文字、None、境界値）をテスト
- [ ] モックを適切に使用
- [ ] テストの独立性を保持
- [ ] 意味のあるアサーション
- [ ] 適切なテスト名（何をテストするか明確）

### パフォーマンス考慮事項
- [ ] テスト実行時間が5分以内
- [ ] 重いI/O操作はモック化
- [ ] 並列実行可能な設計
- [ ] 適切なフィクスチャの使用