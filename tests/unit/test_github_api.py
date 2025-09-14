"""
GitHub API機能のテスト

マルチプラットフォームテスト方針に準拠したGitHub API機能のテスト
"""

from unittest.mock import Mock, patch

import pytest
import requests

from setup_repo.github_api import (
    GitHubAPI,
    GitHubAPIError,
    get_repositories,
)
from tests.multiplatform.helpers import verify_current_platform


class TestGitHubAPI:
    """GitHub API機能のテスト"""

    def test_github_api_init(self):
        """GitHubAPIクラスの初期化テスト"""
        verify_current_platform()  # プラットフォーム検証

        api = GitHubAPI("test_token", "testuser")
        assert api.token == "test_token"
        assert api.username == "testuser"
        assert "User-Agent" in api.headers

    def test_github_api_init_error(self):
        """無効なパラメータでの初期化エラーテスト"""
        with pytest.raises(GitHubAPIError, match="GitHubトークンが必要です"):
            GitHubAPI("", "testuser")

        with pytest.raises(GitHubAPIError, match="GitHubユーザー名が必要です"):
            GitHubAPI("test_token", "")

    def test_get_user_info_success(self):
        """ユーザー情報取得成功テスト"""
        api = GitHubAPI("test_token", "testuser")

        mock_response_data = {"login": "testuser", "name": "Test User", "email": "test@example.com"}

        with patch("setup_repo.github_api.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            user_info = api.get_user_info()

            assert user_info["login"] == "testuser"
            assert user_info["name"] == "Test User"

    def test_get_user_info_authentication_error(self):
        """認証エラーでのユーザー情報取得テスト"""
        api = GitHubAPI("invalid_token", "testuser")

        with patch("setup_repo.github_api.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
            mock_get.return_value = mock_response

            with pytest.raises(GitHubAPIError, match="認証に失敗"):
                api.get_user_info()

    def test_get_user_repos_success(self):
        """ユーザーリポジトリ取得成功テスト"""
        api = GitHubAPI("test_token", "testuser")

        mock_response_data = [
            {
                "name": "repo1",
                "full_name": "testuser/repo1",
                "private": False,
                "clone_url": "https://github.com/testuser/repo1.git",
            }
        ]

        with patch("setup_repo.github_api.requests.get") as mock_get:
            # 最初のリクエストでデータを返し、2回目のリクエストで空のリストを返す
            mock_response_first = Mock()
            mock_response_first.status_code = 200
            mock_response_first.json.return_value = mock_response_data
            mock_response_first.raise_for_status = Mock(return_value=None)
            
            mock_response_second = Mock()
            mock_response_second.status_code = 200
            mock_response_second.json.return_value = []  # 空のリストでループを終了
            mock_response_second.raise_for_status = Mock(return_value=None)
            
            mock_get.side_effect = [mock_response_first, mock_response_second]

            repos = api.get_user_repos()

            assert len(repos) == 1
            assert repos[0]["name"] == "repo1"
            assert mock_get.call_count == 2  # 2回呼ばれることを確認

    def test_get_repositories_function(self):
        """リポジトリ取得関数のテスト"""
        mock_response_data = [
            {
                "name": "repo1",
                "full_name": "testuser/repo1",
                "clone_url": "https://github.com/testuser/repo1.git",
            }
        ]

        with patch("setup_repo.github_api.requests.get") as mock_get:
            # 認証ユーザー取得のレスポンス
            mock_auth_response = Mock()
            mock_auth_response.status_code = 200
            mock_auth_response.json.return_value = {"login": "testuser"}
            mock_auth_response.raise_for_status.return_value = None
            
            # リポジトリ一覧取得のレスポンス
            mock_repos_response = Mock()
            mock_repos_response.status_code = 200
            mock_repos_response.json.return_value = mock_response_data
            mock_repos_response.raise_for_status.return_value = None
            
            # 空のレスポンス（ページネーション終了）
            mock_empty_response = Mock()
            mock_empty_response.status_code = 200
            mock_empty_response.json.return_value = []
            mock_empty_response.raise_for_status.return_value = None
            
            mock_get.side_effect = [mock_auth_response, mock_repos_response, mock_empty_response]

            repos = get_repositories("testuser", "test_token")

            assert len(repos) == 1
            assert repos[0]["name"] == "repo1"

    def test_get_repositories_no_token(self):
        """トークンなしでのリポジトリ取得テスト"""
        mock_response_data = [
            {
                "name": "public-repo",
                "full_name": "testuser/public-repo",
                "clone_url": "https://github.com/testuser/public-repo.git",
            }
        ]

        with patch("setup_repo.github_api.requests.get") as mock_get:
            # 最初のページでデータを返し、2回目で空のリストを返す
            mock_response_first = Mock()
            mock_response_first.status_code = 200
            mock_response_first.json.return_value = mock_response_data
            mock_response_first.raise_for_status.return_value = None
            
            mock_response_second = Mock()
            mock_response_second.status_code = 200
            mock_response_second.json.return_value = []
            mock_response_second.raise_for_status.return_value = None
            
            mock_get.side_effect = [mock_response_first, mock_response_second]

            repos = get_repositories("testuser", None)

            assert len(repos) == 1
            assert repos[0]["name"] == "public-repo"

    @pytest.mark.integration
    def test_github_api_integration(self):
        """GitHub API統合テスト"""
        verify_current_platform()  # プラットフォーム検証

        api = GitHubAPI("test_token", "testuser")

        with patch("setup_repo.github_api.requests.get") as mock_get:
            # ユーザー情報取得のモック
            mock_user_response = Mock()
            mock_user_response.status_code = 200
            mock_user_response.json.return_value = {"login": "testuser", "name": "Test User"}
            mock_user_response.raise_for_status.return_value = None
            
            # リポジトリ取得のモック（最初のページ）
            mock_repos_response = Mock()
            mock_repos_response.status_code = 200
            mock_repos_response.json.return_value = [{"name": "repo1", "full_name": "testuser/repo1"}]
            mock_repos_response.raise_for_status.return_value = None
            
            # 空のレスポンス（ページネーション終了）
            mock_empty_response = Mock()
            mock_empty_response.status_code = 200
            mock_empty_response.json.return_value = []
            mock_empty_response.raise_for_status.return_value = None
            
            mock_get.side_effect = [mock_user_response, mock_repos_response, mock_empty_response]

            user_info = api.get_user_info()
            assert user_info["login"] == "testuser"

            repos = api.get_user_repos()
            assert len(repos) == 1
            assert repos[0]["name"] == "repo1"
