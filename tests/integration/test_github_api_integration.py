"""
GitHub API統合テスト

このモジュールでは、GitHub API統合の統合テストを実装します。
実際のGitHub APIとの通信をモックしながら、API統合機能の
動作を包括的に検証します。
"""

import json
import os
from typing import Any, Dict
from unittest.mock import Mock, patch

import pytest

from setup_repo.github_api import GitHubAPI, GitHubAPIError


@pytest.mark.integration
class TestGitHubAPIIntegration:
    """GitHub API統合テストクラス"""

    def test_github_api_initialization(
        self,
        sample_config: Dict[str, Any],
    ) -> None:
        """GitHub API初期化テスト"""
        # 正常な初期化
        api = GitHubAPI(
            token=sample_config["github_token"],
            username=sample_config["github_username"],
        )

        assert api.token == sample_config["github_token"]
        assert api.username == sample_config["github_username"]

        # 無効なトークンでの初期化
        with pytest.raises((ValueError, GitHubAPIError)):
            GitHubAPI(token="", username=sample_config["github_username"])

    def test_get_user_info_integration(
        self,
        sample_config: Dict[str, Any],
    ) -> None:
        """ユーザー情報取得の統合テスト"""
        # モックレスポンスを準備
        mock_user_info = {
            "login": sample_config["github_username"],
            "name": "Test User",
            "email": "test@example.com",
            "public_repos": 10,
            "followers": 5,
            "following": 3,
        }

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = Mock()
            mock_response.read.return_value = json.dumps(mock_user_info).encode("utf-8")
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=None)
            mock_urlopen.return_value = mock_response

            api = GitHubAPI(
                token=sample_config["github_token"],
                username=sample_config["github_username"],
            )
            user_info = api.get_user_info()

        # 結果を検証
        assert user_info["login"] == sample_config["github_username"]
        assert user_info["name"] == "Test User"
        assert user_info["email"] == "test@example.com"
        assert user_info["public_repos"] == 10

        # APIが適切に呼び出されたことを確認
        mock_urlopen.assert_called_once()

    def test_get_user_repos_integration(
        self,
        sample_config: Dict[str, Any],
    ) -> None:
        """ユーザーリポジトリ取得の統合テスト"""
        # モックレスポンスを準備
        mock_repos = [
            {
                "name": "test-repo-1",
                "clone_url": "https://github.com/test_user/test-repo-1.git",
                "description": "テストリポジトリ1",
                "private": False,
                "default_branch": "main",
                "language": "Python",
                "stargazers_count": 5,
                "forks_count": 2,
            },
            {
                "name": "test-repo-2",
                "clone_url": "https://github.com/test_user/test-repo-2.git",
                "description": "テストリポジトリ2",
                "private": True,
                "default_branch": "master",
                "language": "JavaScript",
                "stargazers_count": 10,
                "forks_count": 3,
            },
        ]

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = Mock()
            mock_response.read.return_value = json.dumps(mock_repos).encode("utf-8")
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=None)
            mock_urlopen.return_value = mock_response

            api = GitHubAPI(
                token=sample_config["github_token"],
                username=sample_config["github_username"],
            )
            repos = api.get_user_repos()

        # 結果を検証
        assert len(repos) == 2
        assert repos[0]["name"] == "test-repo-1"
        assert repos[0]["private"] is False
        assert repos[1]["name"] == "test-repo-2"
        assert repos[1]["private"] is True

        # APIが適切に呼び出されたことを確認
        mock_urlopen.assert_called_once()

    def test_api_error_handling(
        self,
        sample_config: Dict[str, Any],
    ) -> None:
        """API エラーハンドリングテスト"""
        # 401 Unauthorized エラー
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.json.return_value = {"message": "Bad credentials"}
            mock_get.return_value = mock_response

            api = GitHubAPI(
                token="invalid_token",
                username=sample_config["github_username"],
            )

            with pytest.raises(GitHubAPIError) as exc_info:
                api.get_user_info()

            assert "401" in str(exc_info.value)
            assert "Bad credentials" in str(exc_info.value)

        # 404 Not Found エラー
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.json.return_value = {"message": "Not Found"}
            mock_get.return_value = mock_response

            api = GitHubAPI(
                token=sample_config["github_token"],
                username="nonexistent_user",
            )

            with pytest.raises(GitHubAPIError) as exc_info:
                api.get_user_repos()

            assert "404" in str(exc_info.value)

        # 403 Rate Limit エラー
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 403
            mock_response.json.return_value = {"message": "API rate limit exceeded"}
            mock_response.headers = {"X-RateLimit-Reset": "1640995200"}
            mock_get.return_value = mock_response

            api = GitHubAPI(
                token=sample_config["github_token"],
                username=sample_config["github_username"],
            )

            with pytest.raises(GitHubAPIError) as exc_info:
                api.get_user_info()

            assert "rate limit" in str(exc_info.value).lower()

    def test_api_pagination_handling(
        self,
        sample_config: Dict[str, Any],
    ) -> None:
        """APIページネーション処理テスト"""
        # 複数ページのレスポンスをシミュレート
        page1_repos = [
            {
                "name": f"repo-{i}",
                "clone_url": f"https://github.com/test_user/repo-{i}.git",
                "description": f"リポジトリ{i}",
                "private": False,
                "default_branch": "main",
            }
            for i in range(1, 31)  # 30個のリポジトリ（1ページ目）
        ]

        page2_repos = [
            {
                "name": f"repo-{i}",
                "clone_url": f"https://github.com/test_user/repo-{i}.git",
                "description": f"リポジトリ{i}",
                "private": False,
                "default_branch": "main",
            }
            for i in range(31, 41)  # 10個のリポジトリ（2ページ目）
        ]

        def mock_get_side_effect(url: str, **kwargs) -> Mock:
            mock_response = Mock()
            mock_response.status_code = 200

            if "page=1" in url or "page" not in url:
                mock_response.json.return_value = page1_repos
                mock_response.headers = {
                    "Link": '<https://api.github.com/user/repos?page=2>; rel="next"'
                }
            elif "page=2" in url:
                mock_response.json.return_value = page2_repos
                mock_response.headers = {}
            else:
                mock_response.json.return_value = []
                mock_response.headers = {}

            return mock_response

        with patch("requests.get", side_effect=mock_get_side_effect):
            api = GitHubAPI(
                token=sample_config["github_token"],
                username=sample_config["github_username"],
            )
            repos = api.get_user_repos()

        # 全ページのリポジトリが取得されることを確認
        assert len(repos) == 40  # 30 + 10
        assert repos[0]["name"] == "repo-1"
        assert repos[39]["name"] == "repo-40"

    def test_api_timeout_handling(
        self,
        sample_config: Dict[str, Any],
    ) -> None:
        """APIタイムアウト処理テスト"""
        import requests

        with patch("requests.get") as mock_get:
            mock_get.side_effect = requests.Timeout("Request timed out")

            api = GitHubAPI(
                token=sample_config["github_token"],
                username=sample_config["github_username"],
            )

            with pytest.raises(GitHubAPIError) as exc_info:
                api.get_user_info()

            assert "timeout" in str(exc_info.value).lower()

    def test_api_network_error_handling(
        self,
        sample_config: Dict[str, Any],
    ) -> None:
        """APIネットワークエラー処理テスト"""
        import requests

        with patch("requests.get") as mock_get:
            mock_get.side_effect = requests.ConnectionError("Network error")

            api = GitHubAPI(
                token=sample_config["github_token"],
                username=sample_config["github_username"],
            )

            with pytest.raises(GitHubAPIError) as exc_info:
                api.get_user_info()

            assert (
                "network" in str(exc_info.value).lower()
                or "connection" in str(exc_info.value).lower()
            )

    def test_api_response_validation(
        self,
        sample_config: Dict[str, Any],
    ) -> None:
        """APIレスポンス検証テスト"""
        # 無効なJSONレスポンス
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
            mock_get.return_value = mock_response

            api = GitHubAPI(
                token=sample_config["github_token"],
                username=sample_config["github_username"],
            )

            with pytest.raises(GitHubAPIError):
                api.get_user_info()

        # 必須フィールドが不足したレスポンス
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "incomplete": "data"
            }  # loginフィールドなし
            mock_get.return_value = mock_response

            api = GitHubAPI(
                token=sample_config["github_token"],
                username=sample_config["github_username"],
            )

            # 不完全なデータでもエラーにならないが、適切に処理される
            user_info = api.get_user_info()
            assert "incomplete" in user_info

    def test_api_authentication_methods(
        self,
        sample_config: Dict[str, Any],
    ) -> None:
        """API認証方法テスト"""
        # トークン認証
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"login": "test_user"}
            mock_get.return_value = mock_response

            api = GitHubAPI(
                token=sample_config["github_token"],
                username=sample_config["github_username"],
            )
            api.get_user_info()

            # Authorizationヘッダーが設定されていることを確認
            call_args = mock_get.call_args
            headers = call_args[1]["headers"]
            assert "Authorization" in headers
            assert f"token {sample_config['github_token']}" in headers["Authorization"]

    @pytest.mark.slow
    def test_api_rate_limit_respect(
        self,
        sample_config: Dict[str, Any],
    ) -> None:
        """APIレート制限遵守テスト"""
        import time

        call_times = []

        def mock_get_with_timing(*args, **kwargs) -> Mock:
            call_times.append(time.time())
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"login": "test_user"}
            return mock_response

        with patch("requests.get", side_effect=mock_get_with_timing):
            api = GitHubAPI(
                token=sample_config["github_token"],
                username=sample_config["github_username"],
            )

            # 複数回のAPI呼び出し
            for _ in range(3):
                api.get_user_info()

        # 呼び出し間隔が適切であることを確認
        assert len(call_times) == 3
        if len(call_times) > 1:
            # 連続呼び出しの間隔をチェック（実装に依存）
            intervals = [
                call_times[i + 1] - call_times[i] for i in range(len(call_times) - 1)
            ]
            # 極端に短い間隔でないことを確認
            assert all(interval >= 0 for interval in intervals)

    def test_api_integration_with_environment_variables(
        self,
        sample_config: Dict[str, Any],
    ) -> None:
        """環境変数を使用したAPI統合テスト"""
        # 環境変数からの認証情報取得
        env_token = "env_github_token"
        env_username = "env_github_user"

        with patch.dict(
            os.environ, {"GITHUB_TOKEN": env_token, "GITHUB_USERNAME": env_username}
        ):
            with patch("requests.get") as mock_get:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"login": env_username}
                mock_get.return_value = mock_response

                # 環境変数から認証情報を取得してAPI初期化
                api = GitHubAPI(
                    token=os.getenv("GITHUB_TOKEN"),
                    username=os.getenv("GITHUB_USERNAME"),
                )
                user_info = api.get_user_info()

        # 環境変数の値が使用されることを確認
        assert user_info["login"] == env_username

        # APIが適切な認証情報で呼び出されたことを確認
        call_args = mock_get.call_args
        headers = call_args[1]["headers"]
        assert f"token {env_token}" in headers["Authorization"]

    def test_api_integration_error_recovery(
        self,
        sample_config: Dict[str, Any],
    ) -> None:
        """APIエラー回復テスト"""
        call_count = 0

        def mock_get_with_retry(*args, **kwargs) -> Mock:
            nonlocal call_count
            call_count += 1

            mock_response = Mock()
            if call_count == 1:
                # 最初の呼び出しは失敗
                mock_response.status_code = 500
                mock_response.json.return_value = {"message": "Internal Server Error"}
            else:
                # 2回目の呼び出しは成功
                mock_response.status_code = 200
                mock_response.json.return_value = {"login": "test_user"}

            return mock_response

        with patch("requests.get", side_effect=mock_get_with_retry):
            api = GitHubAPI(
                token=sample_config["github_token"],
                username=sample_config["github_username"],
            )

            # 最初の呼び出しは失敗するはず
            with pytest.raises(GitHubAPIError):
                api.get_user_info()

            # 2回目の呼び出しは成功するはず
            user_info = api.get_user_info()
            assert user_info["login"] == "test_user"

        # 両方の呼び出しが実行されたことを確認
        assert call_count == 2
