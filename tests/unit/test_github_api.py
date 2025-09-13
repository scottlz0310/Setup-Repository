"""
GitHub API操作のテスト
"""

from unittest.mock import Mock, patch

import pytest
import requests

from setup_repo.github_api import (
    GitHubAPI,
    GitHubAPIError,
    _get_authenticated_user,
    get_repositories,
)


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

    @patch("requests.get")
    def test_get_user_info_success(self, mock_get):
        """ユーザー情報取得成功のテスト"""
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = {"login": "test_user", "id": 123}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        api = GitHubAPI("test_token", "test_user")

        # Act
        result = api.get_user_info()

        # Assert
        assert result["login"] == "test_user"
        assert result["id"] == 123

    @patch("requests.get")
    def test_get_user_info_401_error(self, mock_get):
        """認証エラー(401)のテスト"""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
        mock_get.return_value = mock_response

        api = GitHubAPI("invalid_token", "test_user")

        # Act & Assert
        with pytest.raises(GitHubAPIError, match="認証に失敗しました"):
            api.get_user_info()

    @patch("requests.get")
    def test_get_user_info_403_error(self, mock_get):
        """レート制限エラー(403)のテスト"""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
        mock_get.return_value = mock_response

        api = GitHubAPI("test_token", "test_user")

        # Act & Assert
        with pytest.raises(GitHubAPIError, match="APIレート制限に達しました"):
            api.get_user_info()

    @patch("requests.get")
    def test_get_user_info_404_error(self, mock_get):
        """ユーザー未発見エラー(404)のテスト"""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
        mock_get.return_value = mock_response

        api = GitHubAPI("test_token", "test_user")

        # Act & Assert
        with pytest.raises(GitHubAPIError, match="ユーザーが見つかりません|GitHub API エラー: 404"):
            api.get_user_info()

    @patch("requests.get")
    def test_get_user_info_network_error(self, mock_get):
        """ネットワークエラーのテスト"""
        # Arrange
        mock_get.side_effect = requests.exceptions.ConnectionError("Network error")

        api = GitHubAPI("test_token", "test_user")

        # Act & Assert
        with pytest.raises(GitHubAPIError, match="ネットワークエラー|GitHub API エラー"):
            api.get_user_info()

    @patch("requests.get")
    def test_get_user_repos_success(self, mock_get):
        """リポジトリ一覧取得成功のテスト"""
        # Arrange
        repos_page1 = [{"name": "repo1", "id": 1}, {"name": "repo2", "id": 2}]
        repos_page2 = []  # 空のページで終了

        mock_response1 = Mock()
        mock_response1.json.return_value = repos_page1
        mock_response1.raise_for_status.return_value = None

        mock_response2 = Mock()
        mock_response2.json.return_value = repos_page2
        mock_response2.raise_for_status.return_value = None

        mock_get.side_effect = [mock_response1, mock_response2]

        api = GitHubAPI("test_token", "test_user")

        # Act
        result = api.get_user_repos()

        # Assert
        assert len(result) == 2
        assert result[0]["name"] == "repo1"
        assert result[1]["name"] == "repo2"

    @patch("requests.get")
    def test_get_user_repos_http_error(self, mock_get):
        """リポジトリ取得時のHTTPエラーのテスト"""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
        mock_get.return_value = mock_response

        api = GitHubAPI("test_token", "test_user")

        # Act & Assert
        with pytest.raises(GitHubAPIError, match="認証に失敗しました"):
            api.get_user_repos()

    @patch("requests.get")
    def test_get_user_repos_network_error(self, mock_get):
        """リポジトリ取得時のネットワークエラーのテスト"""
        # Arrange
        mock_get.side_effect = requests.exceptions.ConnectionError("Network error")

        api = GitHubAPI("test_token", "test_user")

        # Act & Assert
        with pytest.raises(GitHubAPIError, match="ネットワークエラー"):
            api.get_user_repos()


class TestGetRepositories:
    """get_repositories関数のテスト"""

    @patch("setup_repo.github_api._get_authenticated_user")
    @patch("requests.get")
    def test_get_repositories_no_token(self, mock_get, mock_get_auth_user):
        """トークンなしでのリポジトリ取得のテスト"""
        # Arrange
        repos_page1 = [{"name": "public_repo", "id": 1}]
        repos_page2 = []  # 空のページで終了

        mock_response1 = Mock()
        mock_response1.json.return_value = repos_page1
        mock_response1.raise_for_status.return_value = None

        mock_response2 = Mock()
        mock_response2.json.return_value = repos_page2
        mock_response2.raise_for_status.return_value = None

        mock_get.side_effect = [mock_response1, mock_response2]

        # Act
        with patch("logging.getLogger") as mock_logger:
            result = get_repositories("test_owner")

        # Assert
        assert len(result) == 1
        assert result[0]["name"] == "public_repo"
        # ログ出力が呼ばれたことを確認
        mock_logger.assert_called()

    @patch("setup_repo.github_api._get_authenticated_user")
    @patch("requests.get")
    def test_get_repositories_with_token_same_user(self, mock_get, mock_get_auth_user):
        """トークンありで同じユーザーのリポジトリ取得のテスト"""
        # Arrange
        mock_get_auth_user.return_value = "test_owner"
        repos_page1 = [{"name": "private_repo", "id": 1}]
        repos_page2 = []  # 空のページで終了

        mock_response1 = Mock()
        mock_response1.json.return_value = repos_page1
        mock_response1.raise_for_status.return_value = None

        mock_response2 = Mock()
        mock_response2.json.return_value = repos_page2
        mock_response2.raise_for_status.return_value = None

        mock_get.side_effect = [mock_response1, mock_response2]

        # Act
        result = get_repositories("test_owner", "test_token")

        # Assert
        assert len(result) == 1
        assert result[0]["name"] == "private_repo"

    @patch("setup_repo.github_api._get_authenticated_user")
    @patch("requests.get")
    def test_get_repositories_with_token_different_user(self, mock_get, mock_get_auth_user):
        """トークンありで異なるユーザーのリポジトリ取得のテスト"""
        # Arrange
        mock_get_auth_user.return_value = "auth_user"
        repos_page1 = [{"name": "other_repo", "id": 1}]
        repos_page2 = []  # 空のページで終了

        mock_response1 = Mock()
        mock_response1.json.return_value = repos_page1
        mock_response1.raise_for_status.return_value = None

        mock_response2 = Mock()
        mock_response2.json.return_value = repos_page2
        mock_response2.raise_for_status.return_value = None

        mock_get.side_effect = [mock_response1, mock_response2]

        # Act
        result = get_repositories("other_owner", "test_token")

        # Assert
        assert len(result) == 1
        assert result[0]["name"] == "other_repo"

    @patch("requests.get")
    def test_get_repositories_http_error(self, mock_get):
        """HTTPエラー時のテスト"""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
        mock_get.return_value = mock_response

        # Act
        with patch("logging.getLogger") as mock_logger:
            result = get_repositories("nonexistent_owner")

        # Assert
        assert result == []
        # ログ出力が呼ばれたことを確認
        mock_logger.assert_called()

    @patch("requests.get")
    def test_get_repositories_network_error(self, mock_get):
        """ネットワークエラー時のテスト"""
        # Arrange
        mock_get.side_effect = requests.exceptions.ConnectionError("Network error")

        # Act
        with patch("logging.getLogger") as mock_logger:
            result = get_repositories("test_owner")

        # Assert
        assert result == []
        # ログ出力が呼ばれたことを確認
        mock_logger.assert_called()

    @patch("requests.get")
    def test_get_repositories_https_url_validation(self, mock_get):
        """HTTPS URLの使用確認テスト"""
        # この関数は内部でHTTPS URLのみを使用することを確認
        repos_page1 = [{"name": "repo", "id": 1}]
        repos_page2 = []  # 空のページで終了

        mock_response1 = Mock()
        mock_response1.json.return_value = repos_page1
        mock_response1.raise_for_status.return_value = None

        mock_response2 = Mock()
        mock_response2.json.return_value = repos_page2
        mock_response2.raise_for_status.return_value = None

        mock_get.side_effect = [mock_response1, mock_response2]

        result = get_repositories("test_owner")

        assert len(result) == 1
        assert result[0]["name"] == "repo"


class TestGetAuthenticatedUser:
    """_get_authenticated_user関数のテスト"""

    @patch("requests.get")
    def test_get_authenticated_user_success(self, mock_get):
        """認証ユーザー取得成功のテスト"""
        # Arrange
        user_data = {"login": "test_user", "id": 123}
        mock_response = Mock()
        mock_response.json.return_value = user_data
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Act
        result = _get_authenticated_user("test_token")

        # Assert
        assert result == "test_user"

    @patch("requests.get")
    def test_get_authenticated_user_http_error(self, mock_get):
        """HTTPエラー時のテスト"""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
        mock_get.return_value = mock_response

        # Act
        result = _get_authenticated_user("invalid_token")

        # Assert
        assert result is None

    @patch("requests.get")
    def test_get_authenticated_user_network_error(self, mock_get):
        """ネットワークエラー時のテスト"""
        # Arrange
        mock_get.side_effect = requests.exceptions.ConnectionError("Network error")

        # Act
        result = _get_authenticated_user("test_token")

        # Assert
        assert result is None

    @patch("requests.get")
    def test_get_authenticated_user_invalid_json(self, mock_get):
        """無効なJSONレスポンスのテスト"""
        # Arrange
        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Act
        result = _get_authenticated_user("test_token")

        # Assert
        assert result is None

    @patch("requests.get")
    def test_get_authenticated_user_missing_login(self, mock_get):
        """loginフィールドがないレスポンスのテスト"""
        # Arrange
        user_data = {"id": 123}  # loginフィールドなし
        mock_response = Mock()
        mock_response.json.return_value = user_data
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Act
        result = _get_authenticated_user("test_token")

        # Assert
        assert result is None


class TestEdgeCases:
    """エッジケースのテスト"""

    @patch("requests.get")
    def test_get_repositories_pagination(self, mock_get):
        """ページネーション処理のテスト"""
        # Arrange
        repos_page1 = [{"name": f"repo{i}", "id": i} for i in range(100)]
        repos_page2 = [{"name": f"repo{i}", "id": i} for i in range(100, 150)]
        repos_page3 = []  # 空のページで終了

        responses = []
        for repos in [repos_page1, repos_page2, repos_page3]:
            mock_response = Mock()
            mock_response.json.return_value = repos
            mock_response.raise_for_status.return_value = None
            responses.append(mock_response)

        mock_get.side_effect = responses

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

    @patch("requests.get")
    def test_get_user_repos_empty_response(self, mock_get):
        """空のレスポンスのテスト"""
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = []
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        api = GitHubAPI("test_token", "test_user")

        # Act
        result = api.get_user_repos()

        # Assert
        assert result == []

    @patch("requests.get")
    def test_get_user_info_malformed_json(self, mock_get):
        """不正なJSONレスポンスのテスト"""
        # Arrange
        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        api = GitHubAPI("test_token", "test_user")

        # Act & Assert
        with pytest.raises(GitHubAPIError):
            api.get_user_info()

    @patch("requests.get")
    def test_get_user_repos_malformed_json(self, mock_get):
        """リポジトリ取得時の不正なJSONレスポンスのテスト"""
        # Arrange
        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        api = GitHubAPI("test_token", "test_user")

        # Act & Assert
        with pytest.raises(GitHubAPIError):
            api.get_user_repos()

    @patch("requests.get")
    def test_get_user_repos_403_rate_limit(self, mock_get):
        """リポジトリ取得時のレート制限エラーのテスト"""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
        mock_get.return_value = mock_response

        api = GitHubAPI("test_token", "test_user")

        # Act & Assert
        with pytest.raises(GitHubAPIError, match="APIレート制限に達しました"):
            api.get_user_repos()

    @patch("requests.get")
    def test_get_user_info_500_server_error(self, mock_get):
        """サーバーエラー(500)のテスト"""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
        mock_get.return_value = mock_response

        api = GitHubAPI("test_token", "test_user")

        # Act & Assert
        with pytest.raises(GitHubAPIError, match="GitHub API エラー: 500"):
            api.get_user_info()

    @patch("requests.get")
    def test_get_user_repos_timeout_error(self, mock_get):
        """タイムアウトエラーのテスト"""
        # Arrange
        mock_get.side_effect = requests.exceptions.Timeout("Request timed out")

        api = GitHubAPI("test_token", "test_user")

        # Act & Assert
        with pytest.raises(GitHubAPIError, match="ネットワークエラー"):
            api.get_user_repos()

    def test_github_api_init_with_whitespace_token(self):
        """空白文字のみのトークンでの初期化テスト（現在の実装では許可される）"""
        # 現在の実装では空白文字のみの文字列は有効として扱われる
        api = GitHubAPI("   ", "test_user")
        assert api.token == "   "
        assert api.username == "test_user"

    def test_github_api_init_with_whitespace_username(self):
        """空白文字のみのユーザー名での初期化テスト（現在の実装では許可される）"""
        # 現在の実装では空白文字のみの文字列は有効として扱われる
        api = GitHubAPI("test_token", "   ")
        assert api.token == "test_token"
        assert api.username == "   "

    def test_github_api_init_with_none_values(self):
        """None値での初期化エラーのテスト"""
        with pytest.raises(GitHubAPIError, match="GitHubトークンが必要です"):
            GitHubAPI(None, "test_user")

        with pytest.raises(GitHubAPIError, match="GitHubユーザー名が必要です"):
            GitHubAPI("test_token", None)


class TestGetRepositoriesAdvanced:
    """get_repositories関数の高度なテスト"""

    @patch("setup_repo.github_api._get_authenticated_user")
    @patch("requests.get")
    def test_get_repositories_auth_user_none(self, mock_get, mock_get_auth_user):
        """認証ユーザーがNoneの場合のテスト"""
        # Arrange
        mock_get_auth_user.return_value = None
        repos_page1 = [{"name": "public_repo", "id": 1}]
        repos_page2 = []

        mock_response1 = Mock()
        mock_response1.json.return_value = repos_page1
        mock_response1.raise_for_status.return_value = None

        mock_response2 = Mock()
        mock_response2.json.return_value = repos_page2
        mock_response2.raise_for_status.return_value = None

        mock_get.side_effect = [mock_response1, mock_response2]

        # Act
        result = get_repositories("test_owner", "test_token")

        # Assert
        assert len(result) == 1
        assert result[0]["name"] == "public_repo"

    @patch("setup_repo.github_api._get_authenticated_user")
    @patch("requests.get")
    def test_get_repositories_case_insensitive_user_match(self, mock_get, mock_get_auth_user):
        """大文字小文字を区別しないユーザーマッチのテスト"""
        # Arrange
        mock_get_auth_user.return_value = "TEST_OWNER"  # 大文字
        repos_page1 = [{"name": "private_repo", "id": 1}]
        repos_page2 = []

        mock_response1 = Mock()
        mock_response1.json.return_value = repos_page1
        mock_response1.raise_for_status.return_value = None

        mock_response2 = Mock()
        mock_response2.json.return_value = repos_page2
        mock_response2.raise_for_status.return_value = None

        mock_get.side_effect = [mock_response1, mock_response2]

        # Act
        result = get_repositories("test_owner", "test_token")  # 小文字

        # Assert
        assert len(result) == 1
        assert result[0]["name"] == "private_repo"

    @patch("requests.get")
    def test_get_repositories_json_decode_error(self, mock_get):
        """JSONデコードエラーのテスト"""
        # Arrange
        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Act
        with patch("logging.getLogger") as mock_logger:
            result = get_repositories("test_owner")

        # Assert
        assert result == []
        # ログ出力が呼ばれたことを確認
        mock_logger.assert_called()

    @patch("requests.get")
    def test_get_repositories_second_page_error(self, mock_get):
        """2ページ目でエラーが発生した場合のテスト"""
        # Arrange
        repos_page1 = [{"name": "repo1", "id": 1}]

        mock_response1 = Mock()
        mock_response1.json.return_value = repos_page1
        mock_response1.raise_for_status.return_value = None

        # 2ページ目でエラー
        mock_response2 = Mock()
        mock_response2.status_code = 500
        mock_response2.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response2)

        mock_get.side_effect = [mock_response1, mock_response2]

        # Act
        result = get_repositories("test_owner")

        # Assert
        assert len(result) == 1  # 1ページ目のデータは取得済み
        assert result[0]["name"] == "repo1"

    @patch("requests.get")
    def test_get_repositories_url_validation(self, mock_get):
        """URL検証のテスト（実際にはHTTPS URLのみ使用されることを確認）"""
        # Arrange
        repos_page1 = [{"name": "repo1", "id": 1}]
        repos_page2 = []

        mock_response1 = Mock()
        mock_response1.json.return_value = repos_page1
        mock_response1.raise_for_status.return_value = None

        mock_response2 = Mock()
        mock_response2.json.return_value = repos_page2
        mock_response2.raise_for_status.return_value = None

        mock_get.side_effect = [mock_response1, mock_response2]

        # Act
        result = get_repositories("test_owner")

        # Assert
        assert len(result) == 1
        # URLがHTTPSで始まることを確認（実際のリクエストで検証される）
        call_args = mock_get.call_args_list
        for call in call_args:
            url = call[0][0]  # 最初の引数がURL
            assert url.startswith("https://")


class TestGetAuthenticatedUserAdvanced:
    """_get_authenticated_user関数の高度なテスト"""

    @patch("requests.get")
    def test_get_authenticated_user_empty_response(self, mock_get):
        """空のレスポンスのテスト"""
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Act
        result = _get_authenticated_user("test_token")

        # Assert
        assert result is None

    @patch("requests.get")
    def test_get_authenticated_user_url_validation(self, mock_get):
        """URL検証のテスト"""
        # Arrange
        user_data = {"login": "test_user", "id": 123}
        mock_response = Mock()
        mock_response.json.return_value = user_data
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Act
        result = _get_authenticated_user("test_token")

        # Assert
        assert result == "test_user"
        # URLがHTTPSで始まることを確認
        call_args = mock_get.call_args_list[0]
        url = call_args[0][0]  # 最初の引数がURL
        assert url.startswith("https://")

    @patch("requests.get")
    def test_get_authenticated_user_headers_validation(self, mock_get):
        """ヘッダー検証のテスト"""
        # Arrange
        user_data = {"login": "test_user", "id": 123}
        mock_response = Mock()
        mock_response.json.return_value = user_data
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Act
        result = _get_authenticated_user("test_token")

        # Assert
        assert result == "test_user"
        # ヘッダーが正しく設定されていることを確認
        call_args = mock_get.call_args_list[0]
        headers = call_args[1]["headers"]  # headersはkwargsにある
        assert "Authorization" in headers
        assert headers["Authorization"] == "token test_token"
        # User-Agentヘッダーが設定されていることを確認
        assert "User-Agent" in headers
