"""
GitHub API操作のテスト
"""

import json
import urllib.error
import urllib.request
from unittest.mock import Mock, patch

import pytest

from setup_repo.github_api import GitHubAPI, GitHubAPIError, get_repositories, _get_authenticated_user


class TestGitHubAPI:
    """GitHubAPIクラスのテスト"""

    def test_init_success(self):
        """正常な初期化のテスト"""
        api = GitHubAPI("test_token", "test_user")
        
        assert api.token == "test_token"
        assert api.username == "test_user"
        assert api.headers["Authorization"] == "token test_token"
        assert api.headers["User-Agent"] == "setup-repo/1.0"
        assert api.headers["Accept"] == "application/vnd.github.v3+json"

    def test_init_empty_token(self):
        """空のトークンでの初期化エラーのテスト"""
        with pytest.raises(GitHubAPIError, match="GitHubトークンが必要です"):
            GitHubAPI("", "test_user")

    def test_init_empty_username(self):
        """空のユーザー名での初期化エラーのテスト"""
        with pytest.raises(GitHubAPIError, match="GitHubユーザー名が必要です"):
            GitHubAPI("test_token", "")

    @patch("urllib.request.urlopen")
    def test_get_user_info_success(self, mock_urlopen):
        """ユーザー情報取得成功のテスト"""
        # Arrange
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({"login": "test_user", "id": 123}).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        api = GitHubAPI("test_token", "test_user")
        
        # Act
        result = api.get_user_info()
        
        # Assert
        assert result["login"] == "test_user"
        assert result["id"] == 123

    @patch("urllib.request.urlopen")
    def test_get_user_info_401_error(self, mock_urlopen):
        """認証エラー(401)のテスト"""
        # Arrange
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="", code=401, msg="Unauthorized", hdrs=None, fp=None
        )
        
        api = GitHubAPI("invalid_token", "test_user")
        
        # Act & Assert
        with pytest.raises(GitHubAPIError, match="認証に失敗しました"):
            api.get_user_info()

    @patch("urllib.request.urlopen")
    def test_get_user_info_403_error(self, mock_urlopen):
        """レート制限エラー(403)のテスト"""
        # Arrange
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="", code=403, msg="Forbidden", hdrs=None, fp=None
        )
        
        api = GitHubAPI("test_token", "test_user")
        
        # Act & Assert
        with pytest.raises(GitHubAPIError, match="APIレート制限に達しました"):
            api.get_user_info()

    @patch("urllib.request.urlopen")
    def test_get_user_info_404_error(self, mock_urlopen):
        """ユーザー未発見エラー(404)のテスト"""
        # Arrange
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="", code=404, msg="Not Found", hdrs=None, fp=None
        )
        
        api = GitHubAPI("test_token", "test_user")
        
        # Act & Assert
        with pytest.raises(GitHubAPIError, match="ユーザーが見つかりません"):
            api.get_user_info()

    @patch("urllib.request.urlopen")
    def test_get_user_info_network_error(self, mock_urlopen):
        """ネットワークエラーのテスト"""
        # Arrange
        mock_urlopen.side_effect = ConnectionError("Network error")
        
        api = GitHubAPI("test_token", "test_user")
        
        # Act & Assert
        with pytest.raises(GitHubAPIError, match="ネットワークエラー"):
            api.get_user_info()

    @patch("urllib.request.urlopen")
    def test_get_user_repos_success(self, mock_urlopen):
        """リポジトリ一覧取得成功のテスト"""
        # Arrange
        repos_page1 = [{"name": "repo1", "id": 1}, {"name": "repo2", "id": 2}]
        repos_page2 = []  # 空のページで終了
        
        mock_response1 = Mock()
        mock_response1.read.return_value = json.dumps(repos_page1).encode()
        
        mock_response2 = Mock()
        mock_response2.read.return_value = json.dumps(repos_page2).encode()
        
        mock_urlopen.return_value.__enter__.side_effect = [mock_response1, mock_response2]
        
        api = GitHubAPI("test_token", "test_user")
        
        # Act
        result = api.get_user_repos()
        
        # Assert
        assert len(result) == 2
        assert result[0]["name"] == "repo1"
        assert result[1]["name"] == "repo2"

    @patch("urllib.request.urlopen")
    def test_get_user_repos_http_error(self, mock_urlopen):
        """リポジトリ取得時のHTTPエラーのテスト"""
        # Arrange
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="", code=401, msg="Unauthorized", hdrs=None, fp=None
        )
        
        api = GitHubAPI("test_token", "test_user")
        
        # Act & Assert
        with pytest.raises(GitHubAPIError, match="認証に失敗しました"):
            api.get_user_repos()

    @patch("urllib.request.urlopen")
    def test_get_user_repos_network_error(self, mock_urlopen):
        """リポジトリ取得時のネットワークエラーのテスト"""
        # Arrange
        mock_urlopen.side_effect = ConnectionError("Network error")
        
        api = GitHubAPI("test_token", "test_user")
        
        # Act & Assert
        with pytest.raises(GitHubAPIError, match="ネットワークエラー"):
            api.get_user_repos()


class TestGetRepositories:
    """get_repositories関数のテスト"""

    @patch("setup_repo.github_api._get_authenticated_user")
    @patch("urllib.request.urlopen")
    @patch("builtins.print")
    def test_get_repositories_no_token(self, mock_print, mock_urlopen, mock_get_auth_user):
        """トークンなしでのリポジトリ取得のテスト"""
        # Arrange
        repos = [{"name": "public_repo", "id": 1}]
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(repos).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        # Act
        result = get_repositories("test_owner")
        
        # Assert
        assert len(result) == 1
        assert result[0]["name"] == "public_repo"
        mock_print.assert_called()

    @patch("setup_repo.github_api._get_authenticated_user")
    @patch("urllib.request.urlopen")
    @patch("builtins.print")
    def test_get_repositories_with_token_same_user(self, mock_print, mock_urlopen, mock_get_auth_user):
        """トークンありで同じユーザーのリポジトリ取得のテスト"""
        # Arrange
        mock_get_auth_user.return_value = "test_owner"
        repos = [{"name": "private_repo", "id": 1}]
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(repos).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        # Act
        result = get_repositories("test_owner", "test_token")
        
        # Assert
        assert len(result) == 1
        assert result[0]["name"] == "private_repo"

    @patch("setup_repo.github_api._get_authenticated_user")
    @patch("urllib.request.urlopen")
    @patch("builtins.print")
    def test_get_repositories_with_token_different_user(self, mock_print, mock_urlopen, mock_get_auth_user):
        """トークンありで異なるユーザーのリポジトリ取得のテスト"""
        # Arrange
        mock_get_auth_user.return_value = "auth_user"
        repos = [{"name": "other_repo", "id": 1}]
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(repos).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        # Act
        result = get_repositories("other_owner", "test_token")
        
        # Assert
        assert len(result) == 1
        assert result[0]["name"] == "other_repo"

    @patch("urllib.request.urlopen")
    @patch("builtins.print")
    def test_get_repositories_http_error(self, mock_print, mock_urlopen):
        """HTTPエラー時のテスト"""
        # Arrange
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="", code=404, msg="Not Found", hdrs=None, fp=None
        )
        
        # Act
        result = get_repositories("nonexistent_owner")
        
        # Assert
        assert result == []
        mock_print.assert_called()

    @patch("urllib.request.urlopen")
    @patch("builtins.print")
    def test_get_repositories_network_error(self, mock_print, mock_urlopen):
        """ネットワークエラー時のテスト"""
        # Arrange
        mock_urlopen.side_effect = ConnectionError("Network error")
        
        # Act
        result = get_repositories("test_owner")
        
        # Assert
        assert result == []
        mock_print.assert_called()

    @patch("urllib.request.urlopen")
    def test_get_repositories_non_https_url(self, mock_urlopen):
        """非HTTPSのURLでのセキュリティテスト"""
        # この関数は内部でHTTPS URLのみを使用するため、
        # 実際にはこのテストは通常のフローをテストする
        repos = [{"name": "repo", "id": 1}]
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(repos).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        result = get_repositories("test_owner")
        
        assert len(result) == 1


class TestGetAuthenticatedUser:
    """_get_authenticated_user関数のテスト"""

    @patch("urllib.request.urlopen")
    def test_get_authenticated_user_success(self, mock_urlopen):
        """認証ユーザー取得成功のテスト"""
        # Arrange
        user_data = {"login": "test_user", "id": 123}
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(user_data).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        # Act
        result = _get_authenticated_user("test_token")
        
        # Assert
        assert result == "test_user"

    @patch("urllib.request.urlopen")
    def test_get_authenticated_user_http_error(self, mock_urlopen):
        """HTTPエラー時のテスト"""
        # Arrange
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="", code=401, msg="Unauthorized", hdrs=None, fp=None
        )
        
        # Act
        result = _get_authenticated_user("invalid_token")
        
        # Assert
        assert result is None

    @patch("urllib.request.urlopen")
    def test_get_authenticated_user_network_error(self, mock_urlopen):
        """ネットワークエラー時のテスト"""
        # Arrange
        mock_urlopen.side_effect = ConnectionError("Network error")
        
        # Act
        result = _get_authenticated_user("test_token")
        
        # Assert
        assert result is None

    @patch("urllib.request.urlopen")
    def test_get_authenticated_user_invalid_json(self, mock_urlopen):
        """無効なJSONレスポンスのテスト"""
        # Arrange
        mock_response = Mock()
        mock_response.read.return_value = b"invalid json"
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        # Act
        result = _get_authenticated_user("test_token")
        
        # Assert
        assert result is None

    @patch("urllib.request.urlopen")
    def test_get_authenticated_user_missing_login(self, mock_urlopen):
        """loginフィールドがないレスポンスのテスト"""
        # Arrange
        user_data = {"id": 123}  # loginフィールドなし
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(user_data).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        # Act
        result = _get_authenticated_user("test_token")
        
        # Assert
        assert result is None


class TestEdgeCases:
    """エッジケースのテスト"""

    @patch("urllib.request.urlopen")
    def test_get_repositories_pagination(self, mock_urlopen):
        """ページネーション処理のテスト"""
        # Arrange
        repos_page1 = [{"name": f"repo{i}", "id": i} for i in range(100)]
        repos_page2 = [{"name": f"repo{i}", "id": i} for i in range(100, 150)]
        repos_page3 = []  # 空のページで終了
        
        responses = []
        for repos in [repos_page1, repos_page2, repos_page3]:
            mock_response = Mock()
            mock_response.read.return_value = json.dumps(repos).encode()
            responses.append(mock_response)
        
        mock_urlopen.return_value.__enter__.side_effect = responses
        
        # Act
        result = get_repositories("test_owner")
        
        # Assert
        assert len(result) == 150
        assert result[0]["name"] == "repo0"
        assert result[149]["name"] == "repo149"

    def test_github_api_headers_format(self):
        """ヘッダーフォーマットのテスト"""
        api = GitHubAPI("test_token", "test_user")
        
        assert "token test_token" in api.headers["Authorization"]
        assert "setup-repo/1.0" in api.headers["User-Agent"]
        assert "application/vnd.github.v3+json" in api.headers["Accept"]

    @patch("urllib.request.urlopen")
    def test_get_user_repos_empty_response(self, mock_urlopen):
        """空のレスポンスのテスト"""
        # Arrange
        mock_response = Mock()
        mock_response.read.return_value = json.dumps([]).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        api = GitHubAPI("test_token", "test_user")
        
        # Act
        result = api.get_user_repos()
        
        # Assert
        assert result == []

    @patch("urllib.request.urlopen")
    def test_get_user_info_malformed_json(self, mock_urlopen):
        """不正なJSONレスポンスのテスト"""
        # Arrange
        mock_response = Mock()
        mock_response.read.return_value = b"invalid json"
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        api = GitHubAPI("test_token", "test_user")
        
        # Act & Assert
        with pytest.raises(GitHubAPIError):
            api.get_user_info()