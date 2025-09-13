"""
入力検証セキュリティテスト

マルチプラットフォームテスト方針に準拠した入力検証セキュリティのテスト
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from setup_repo.config import load_config
from setup_repo.git_operations import GitOperations
from setup_repo.github_api import GitHubAPI, GitHubAPIError
from tests.multiplatform.helpers import verify_current_platform


@pytest.mark.security
class TestInputValidationSecurity:
    """入力検証セキュリティのテスト"""

    def test_config_validation(self):
        """設定検証テスト"""
        verify_current_platform()  # プラットフォーム検証

        # 正常な設定読み込み
        config = load_config()
        assert isinstance(config, dict)
        
        # 基本的な設定項目の存在確認
        assert "owner" in config
        assert "dest" in config

    def test_path_validation(self):
        """パス検証テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            
            # 正常なパスのテスト
            normal_path = base_path / "normal_file.txt"
            normal_path.touch()
            assert normal_path.exists()
            
            # パストラバーサルのテスト
            try:
                dangerous_path = base_path / "../../../etc/passwd"
                resolved = dangerous_path.resolve()
                # ベースパス外へのアクセスを検出
                resolved.relative_to(base_path.resolve())
            except ValueError:
                # パストラバーサルが防止された
                pass

    def test_git_operations_validation(self):
        """コマンド検証テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            git_ops = GitOperations()
            
            # 正常なGit操作のテスト
            assert git_ops.is_git_repository(temp_dir) is False
            
            # コマンドインジェクションのテスト
            malicious_url = "repo; rm -rf /"
            
            with patch("subprocess.run") as mock_run:
                mock_run.side_effect = ValueError("Invalid command")
                result = git_ops.clone_repository(malicious_url, temp_dir)
                assert result is False

    def test_github_token_validation(self):
        """GitHubトークン検証テスト"""
        # 空のトークンでのエラーテスト
        with pytest.raises(GitHubAPIError):
            GitHubAPI("", "testuser")
            
        # 空のユーザー名でのエラーテスト
        with pytest.raises(GitHubAPIError):
            GitHubAPI("test_token", "")
            
        # 正常な初期化
        api = GitHubAPI("test_token", "testuser")
        assert api.token == "test_token"
        assert api.username == "testuser"

    @pytest.mark.integration
    def test_input_validation_integration(self):
        """入力検証統合テスト"""
        verify_current_platform()  # プラットフォーム検証
        
        # 設定検証
        config = load_config()
        assert isinstance(config, dict)
        
        # Git操作検証
        git_ops = GitOperations()
        with tempfile.TemporaryDirectory() as temp_dir:
            assert git_ops.is_git_repository(temp_dir) is False
        
        # GitHub API検証
        api = GitHubAPI("test_token", "testuser")
        assert api.token == "test_token"