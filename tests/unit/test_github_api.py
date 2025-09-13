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
    create_repository,
    get_repository_info,
    get_user_repositories,
    update_repository_settings,
)
from tests.multiplatform.helpers import verify_current_platform


class TestGitHubAPI:
    """GitHub API機能のテスト"""

    def test_github_api_init(self):
        """GitHubAPIクラスの初期化テスト"""
        verify_current_platform()  # プラットフォーム検証

        api = GitHubAPI("test_token")
        assert api.token == "test_token"
        assert api.base_url == "https://api.github.com"
        assert "User-Agent" in api.headers

    def test_github_api_init_with_custom_base_url(self):
        """カスタムベースURLでの初期化テスト"""
        api = GitHubAPI("test_token", base_url="https://api.github.enterprise.com")
        assert api.base_url == "https://api.github.enterprise.com"

    def test_get_user_repositories_success(self):
        """ユーザーリポジトリ取得成功テスト"""
        mock_response_data = [
            {
                "name": "repo1",
                "full_name": "user/repo1",
                "private": False,
                "clone_url": "https://github.com/user/repo1.git",
            },
            {
                "name": "repo2",
                "full_name": "user/repo2",
                "private": True,
                "clone_url": "https://github.com/user/repo2.git",
            },
        ]

        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            mock_get.return_value = mock_response

            repositories = get_user_repositories("test_token")

            assert len(repositories) == 2
            assert repositories[0]["name"] == "repo1"
            assert repositories[1]["private"] is True

    def test_get_user_repositories_authentication_error(self):
        """認証エラーでのリポジトリ取得テスト"""
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.json.return_value = {"message": "Bad credentials"}
            mock_get.return_value = mock_response

            with pytest.raises(GitHubAPIError, match="認証に失敗"):
                get_user_repositories("invalid_token")

    def test_get_user_repositories_rate_limit(self):
        """レート制限エラーのテスト"""
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 403
            mock_response.json.return_value = {"message": "API rate limit exceeded"}
            mock_response.headers = {"X-RateLimit-Reset": "1640995200"}
            mock_get.return_value = mock_response

            with pytest.raises(GitHubAPIError, match="レート制限"):
                get_user_repositories("test_token")

    def test_create_repository_success(self):
        """リポジトリ作成成功テスト"""
        mock_response_data = {
            "name": "new-repo",
            "full_name": "user/new-repo",
            "clone_url": "https://github.com/user/new-repo.git",
            "html_url": "https://github.com/user/new-repo",
        }

        with patch("requests.post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 201
            mock_response.json.return_value = mock_response_data
            mock_post.return_value = mock_response

            result = create_repository("test_token", "new-repo", description="Test repository", private=False)

            assert result["name"] == "new-repo"
            assert result["clone_url"] == "https://github.com/user/new-repo.git"

    def test_create_repository_already_exists(self):
        """既存リポジトリ作成エラーテスト"""
        with patch("requests.post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 422
            mock_response.json.return_value = {
                "message": "Repository creation failed.",
                "errors": [{"message": "name already exists on this account"}],
            }
            mock_post.return_value = mock_response

            with pytest.raises(GitHubAPIError, match="既に存在"):
                create_repository("test_token", "existing-repo")

    def test_get_repository_info_success(self):
        """リポジトリ情報取得成功テスト"""
        mock_response_data = {
            "name": "test-repo",
            "full_name": "user/test-repo",
            "description": "Test repository",
            "private": False,
            "default_branch": "main",
            "language": "Python",
            "stargazers_count": 10,
            "forks_count": 5,
        }

        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            mock_get.return_value = mock_response

            info = get_repository_info("test_token", "user", "test-repo")

            assert info["name"] == "test-repo"
            assert info["language"] == "Python"
            assert info["stargazers_count"] == 10

    def test_get_repository_info_not_found(self):
        """存在しないリポジトリ情報取得テスト"""
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.json.return_value = {"message": "Not Found"}
            mock_get.return_value = mock_response

            with pytest.raises(GitHubAPIError, match="リポジトリが見つかりません"):
                get_repository_info("test_token", "user", "nonexistent-repo")

    def test_update_repository_settings_success(self):
        """リポジトリ設定更新成功テスト"""
        mock_response_data = {"name": "updated-repo", "description": "Updated description", "private": True}

        with patch("requests.patch") as mock_patch:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            mock_patch.return_value = mock_response

            result = update_repository_settings(
                "test_token", "user", "test-repo", description="Updated description", private=True
            )

            assert result["description"] == "Updated description"
            assert result["private"] is True

    def test_github_api_class_make_request(self):
        """GitHubAPIクラスのリクエスト実行テスト"""
        api = GitHubAPI("test_token")

        with patch("requests.request") as mock_request:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"test": "data"}
            mock_request.return_value = mock_response

            result = api._make_request("GET", "/user")

            assert result["test"] == "data"
            mock_request.assert_called_once()

    def test_github_api_class_handle_error_response(self):
        """GitHubAPIクラスのエラーレスポンス処理テスト"""
        api = GitHubAPI("test_token")

        with patch("requests.request") as mock_request:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.json.return_value = {"message": "Internal Server Error"}
            mock_request.return_value = mock_response

            with pytest.raises(GitHubAPIError, match="サーバーエラー"):
                api._make_request("GET", "/user")

    def test_github_api_pagination(self):
        """GitHub APIのページネーション処理テスト"""
        api = GitHubAPI("test_token")

        # 1ページ目のレスポンス
        page1_data = [{"name": f"repo{i}"} for i in range(30)]
        # 2ページ目のレスポンス
        page2_data = [{"name": f"repo{i}"} for i in range(30, 50)]

        with patch("requests.get") as mock_get:
            # 1ページ目
            mock_response1 = Mock()
            mock_response1.status_code = 200
            mock_response1.json.return_value = page1_data
            mock_response1.headers = {"Link": '<https://api.github.com/user/repos?page=2>; rel="next"'}

            # 2ページ目
            mock_response2 = Mock()
            mock_response2.status_code = 200
            mock_response2.json.return_value = page2_data
            mock_response2.headers = {}

            mock_get.side_effect = [mock_response1, mock_response2]

            all_repos = api.get_all_repositories()

            assert len(all_repos) == 50
            assert all_repos[0]["name"] == "repo0"
            assert all_repos[49]["name"] == "repo49"

    @pytest.mark.integration
    def test_github_api_full_workflow(self):
        """GitHub APIの完全ワークフローテスト"""
        verify_current_platform()  # プラットフォーム検証

        with (
            patch("requests.get") as mock_get,
            patch("requests.post") as mock_post,
            patch("requests.patch") as mock_patch,
        ):
            # ユーザー情報取得のモック
            mock_get.return_value = Mock(status_code=200, json=lambda: {"login": "testuser", "name": "Test User"})

            # リポジトリ作成のモック
            mock_post.return_value = Mock(
                status_code=201, json=lambda: {"name": "test-repo", "full_name": "testuser/test-repo"}
            )

            # 設定更新のモック
            mock_patch.return_value = Mock(
                status_code=200, json=lambda: {"name": "test-repo", "description": "Updated"}
            )

            api = GitHubAPI("test_token")

            # ワークフロー実行
            user_info = api.get_user_info()
            repo = api.create_repository("test-repo")
            updated_repo = api.update_repository("testuser", "test-repo", description="Updated")

            assert user_info["login"] == "testuser"
            assert repo["name"] == "test-repo"
            assert updated_repo["description"] == "Updated"

    @pytest.mark.network
    def test_github_api_network_timeout(self):
        """ネットワークタイムアウトのテスト"""
        api = GitHubAPI("test_token")

        with patch("requests.get") as mock_get:
            mock_get.side_effect = requests.Timeout("Request timeout")

            with pytest.raises(GitHubAPIError, match="タイムアウト"):
                api.get_user_info()

    def test_github_api_connection_error(self):
        """接続エラーのテスト"""
        api = GitHubAPI("test_token")

        with patch("requests.get") as mock_get:
            mock_get.side_effect = requests.ConnectionError("Connection failed")

            with pytest.raises(GitHubAPIError, match="接続エラー"):
                api.get_user_info()

    @pytest.mark.slow
    def test_github_api_performance(self):
        """GitHub API操作のパフォーマンステスト"""
        import time

        api = GitHubAPI("test_token")

        start_time = time.time()

        with patch("requests.get") as mock_get:
            mock_get.return_value = Mock(status_code=200, json=lambda: {"test": "data"})

            # 複数のAPI呼び出しを実行
            for _ in range(10):
                api._make_request("GET", "/user")

        elapsed = time.time() - start_time
        assert elapsed < 2.0, f"GitHub API操作が遅すぎます: {elapsed}秒"
