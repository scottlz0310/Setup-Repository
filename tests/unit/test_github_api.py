"""
GitHub API機能のテスト

マルチプラットフォームテスト方針に準拠したGitHub API機能のテスト
"""

from unittest.mock import Mock, patch

import pytest
import requests

from setup_repo.github_api import GitHubAPI, GitHubAPIError, get_repositories
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

    def test_get_user_info_rate_limit_error(self):
        """APIレート制限エラーテスト（403エラー）"""
        api = GitHubAPI("test_token", "testuser")

        with patch("setup_repo.github_api.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 403
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
            mock_get.return_value = mock_response

            with pytest.raises(GitHubAPIError, match="APIレート制限に達しました"):
                api.get_user_info()

    def test_get_user_info_not_found_error(self):
        """ユーザー未発見エラーテスト（404エラー）"""
        api = GitHubAPI("test_token", "testuser")

        with patch("setup_repo.github_api.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
            mock_get.return_value = mock_response

            with pytest.raises(GitHubAPIError, match="ユーザーが見つかりません"):
                api.get_user_info()

    def test_get_user_info_value_error(self):
        """JSONレスポンス解析エラーテスト"""
        api = GitHubAPI("test_token", "testuser")

        with patch("setup_repo.github_api.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.side_effect = ValueError("Invalid JSON")
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            with pytest.raises(GitHubAPIError, match="レスポンスの解析に失敗しました"):
                api.get_user_info()

    def test_get_user_info_network_error(self):
        """ネットワークエラーテスト"""
        api = GitHubAPI("test_token", "testuser")

        with patch("setup_repo.github_api.requests.get") as mock_get:
            mock_get.side_effect = requests.exceptions.ConnectionError("Network error")

            with pytest.raises(GitHubAPIError, match="ネットワークエラー"):
                api.get_user_info()

    def test_get_user_repos_authentication_error(self):
        """リポジトリ取得時の認証エラーテスト"""
        api = GitHubAPI("invalid_token", "testuser")

        with patch("setup_repo.github_api.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
            mock_get.return_value = mock_response

            with pytest.raises(GitHubAPIError, match="認証に失敗しました"):
                api.get_user_repos()

    def test_get_user_repos_rate_limit_error(self):
        """リポジトリ取得時のレート制限エラーテスト"""
        api = GitHubAPI("test_token", "testuser")

        with patch("setup_repo.github_api.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 403
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
            mock_get.return_value = mock_response

            with pytest.raises(GitHubAPIError, match="APIレート制限に達しました"):
                api.get_user_repos()

    def test_get_user_repos_value_error(self):
        """リポジトリ取得時のJSON解析エラーテスト"""
        api = GitHubAPI("test_token", "testuser")

        with patch("setup_repo.github_api.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.side_effect = ValueError("Invalid JSON")
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            with pytest.raises(GitHubAPIError, match="レスポンスの解析に失敗しました"):
                api.get_user_repos()

    def test_get_user_repos_network_error(self):
        """リポジトリ取得時のネットワークエラーテスト"""
        api = GitHubAPI("test_token", "testuser")

        with patch("setup_repo.github_api.requests.get") as mock_get:
            mock_get.side_effect = requests.exceptions.ConnectionError("Network error")

            with pytest.raises(GitHubAPIError, match="ネットワークエラー"):
                api.get_user_repos()

    def test_get_repositories_other_user_with_auth(self):
        """認証ユーザーで他のユーザーのリポジトリ取得テスト"""
        with patch("setup_repo.github_api.requests.get") as mock_get:
            # 認証ユーザー取得のレスポンス
            mock_auth_response = Mock()
            mock_auth_response.status_code = 200
            mock_auth_response.json.return_value = {"login": "authenticated_user"}
            mock_auth_response.raise_for_status.return_value = None

            # 他のユーザーのリポジトリ取得のレスポンス
            mock_repos_response = Mock()
            mock_repos_response.status_code = 200
            mock_repos_response.json.return_value = [{"name": "other_repo", "full_name": "other_user/other_repo"}]
            mock_repos_response.raise_for_status.return_value = None

            # 空のレスポンス（ページネーション終了）
            mock_empty_response = Mock()
            mock_empty_response.status_code = 200
            mock_empty_response.json.return_value = []
            mock_empty_response.raise_for_status.return_value = None

            mock_get.side_effect = [mock_auth_response, mock_repos_response, mock_empty_response]

            repos = get_repositories("other_user", "test_token")
            assert len(repos) == 1
            assert repos[0]["name"] == "other_repo"

    def test_get_repositories_network_error(self):
        """リポジトリ取得関数でのネットワークエラーテスト"""
        with patch("setup_repo.github_api.requests.get") as mock_get:
            mock_get.side_effect = requests.exceptions.ConnectionError("Network error")

            repos = get_repositories("testuser", "test_token")
            assert repos == []  # エラー時は空のリストを返す

    def test_get_authenticated_user_invalid_response(self):
        """認証ユーザー取得で無効なレスポンステスト"""
        with patch("setup_repo.github_api.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = "invalid_data"  # 辞書型でない
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            from setup_repo.github_api import _get_authenticated_user

            result = _get_authenticated_user("test_token")
            assert result is None

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
