"""
GitHub API機能の修正されたテスト

外部依存（HTTP）のみモック、内部ロジックは実際に実行
"""

from unittest.mock import Mock, patch

import pytest
import requests

from setup_repo.github_api import GitHubAPI, GitHubAPIError, get_repositories


class TestGitHubAPI:
    """GitHub API機能のテスト"""

    def test_github_api_init(self):
        """GitHubAPIクラスの初期化テスト"""
        api = GitHubAPI("test_token", "testuser")
        assert api.token == "test_token"
        assert api.username == "testuser"
        assert "Authorization" in api.headers
        assert api.headers["Authorization"] == "token test_token"

    def test_github_api_init_error(self):
        """無効なパラメータでの初期化エラーテスト"""
        with pytest.raises(GitHubAPIError, match="GitHubトークンが必要です"):
            GitHubAPI("", "testuser")

        with pytest.raises(GitHubAPIError, match="GitHubユーザー名が必要です"):
            GitHubAPI("test_token", "")

    @patch("requests.get")
    def test_get_user_info_success(self, mock_get):
        """ユーザー情報取得成功テスト"""
        # モックレスポンスの設定
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"login": "testuser", "name": "Test User", "email": "test@example.com"}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        api = GitHubAPI("test_token", "testuser")
        user_info = api.get_user_info()

        assert user_info["login"] == "testuser"
        assert user_info["name"] == "Test User"
        mock_get.assert_called_once()

    @patch("requests.get")
    def test_get_user_info_authentication_error(self, mock_get):
        """認証エラーでのユーザー情報取得テスト"""
        # 認証エラーのモック設定
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("401 Unauthorized")
        mock_get.return_value = mock_response

        api = GitHubAPI("invalid_token", "testuser")

        with pytest.raises(GitHubAPIError, match="認証に失敗"):
            api.get_user_info()

    @patch("requests.get")
    def test_get_user_repos_success(self, mock_get):
        """ユーザーリポジトリ取得成功テスト"""
        # モックレスポンスの設定
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "name": "repo1",
                "full_name": "testuser/repo1",
                "private": False,
                "clone_url": "https://github.com/testuser/repo1.git",
                "ssh_url": "git@github.com:testuser/repo1.git",
                "description": "Test repository",
                "default_branch": "main",
            }
        ]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        api = GitHubAPI("test_token", "testuser")
        repos = api.get_user_repos()

        assert len(repos) == 1
        assert repos[0]["name"] == "repo1"
        assert repos[0]["full_name"] == "testuser/repo1"
        mock_get.assert_called_once()

    @patch("requests.get")
    def test_get_repositories_function(self, mock_get):
        """リポジトリ取得関数のテスト"""
        # モックレスポンスの設定
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "name": "repo1",
                "full_name": "testuser/repo1",
                "clone_url": "https://github.com/testuser/repo1.git",
                "ssh_url": "git@github.com:testuser/repo1.git",
                "description": "Test repository",
                "default_branch": "main",
            }
        ]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        repos = get_repositories("testuser", "test_token")

        assert len(repos) == 1
        assert repos[0]["name"] == "repo1"
        mock_get.assert_called_once()

    @patch("requests.get")
    def test_get_repositories_no_token(self, mock_get):
        """トークンなしでのリポジトリ取得テスト"""
        # モックレスポンスの設定
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "name": "public-repo",
                "full_name": "testuser/public-repo",
                "clone_url": "https://github.com/testuser/public-repo.git",
                "ssh_url": "git@github.com:testuser/public-repo.git",
                "description": "Public repository",
                "default_branch": "main",
            }
        ]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        repos = get_repositories("testuser", None)

        assert len(repos) == 1
        assert repos[0]["name"] == "public-repo"
        mock_get.assert_called_once()

    @patch("requests.get")
    def test_network_error_handling(self, mock_get):
        """ネットワークエラーハンドリングテスト"""
        # ネットワークエラーのモック設定
        mock_get.side_effect = requests.exceptions.ConnectionError("Network error")

        api = GitHubAPI("test_token", "testuser")

        with pytest.raises(GitHubAPIError, match="ネットワークエラー"):
            api.get_user_info()

    def test_headers_construction(self):
        """ヘッダー構築ロジックのテスト（外部依存なし）"""
        api = GitHubAPI("test_token", "testuser")

        # 内部属性のテスト
        assert api.username == "testuser"
        assert api.token == "test_token"

        # ヘッダー構築のテスト
        expected_headers = {
            "Authorization": "token test_token",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "setup-repo/1.0",
        }
        for key, value in expected_headers.items():
            assert api.headers.get(key) == value

    def test_empty_response_handling(self):
        """空レスポンスの処理テスト"""
        with patch("requests.get") as mock_get:
            # 空配列のレスポンス
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = []
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            api = GitHubAPI("test_token", "testuser")
            repos = api.get_user_repos()

            assert repos == []
            assert len(repos) == 0
