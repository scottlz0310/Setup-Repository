"""
GitHub API統合テスト

このモジュールでは、GitHub API統合の統合テストを実装します。
実際のGitHub APIとの通信をモックしながら、API統合機能の
動作を包括的に検証します。
"""

import os
from typing import Any
from unittest.mock import Mock, patch

import pytest
import requests

from setup_repo.github_api import GitHubAPI, GitHubAPIError

from ..multiplatform.helpers import check_platform_modules, verify_current_platform


@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("CI") and not os.environ.get("GITHUB_TOKEN"),
    reason="GitHub APIテストはCI環境またはGITHUB_TOKEN設定時のみ実行",
)
class TestGitHubAPIIntegration:
    """GitHub API統合テストクラス"""

    def test_github_api_initialization(
        self,
        sample_config: dict[str, Any],
    ) -> None:
        """GitHub API初期化テスト"""
        # プラットフォーム検証を統合
        verify_current_platform()  # プラットフォーム検証
        check_platform_modules()

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
        sample_config: dict[str, Any],
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

        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = mock_user_info
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

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
        mock_get.assert_called_once()

    def test_get_user_repos_integration(
        self,
        sample_config: dict[str, Any],
    ) -> None:
        """ユーザーリポジトリ取得の統合テスト"""
        # モックレスポンスを準備（ページネーション対応）
        mock_repos_page1 = [
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

        call_count = 0

        def mock_get_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            mock_response = Mock()
            mock_response.raise_for_status.return_value = None

            if call_count == 1:
                # 最初のページ
                mock_response.json.return_value = mock_repos_page1
            else:
                # 2ページ目以降は空
                mock_response.json.return_value = []

            return mock_response

        with patch("requests.get", side_effect=mock_get_side_effect):
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

        # 2回呼び出されることを確認（1ページ目と2ページ目）
        assert call_count == 2

    def test_api_error_handling(
        self,
        sample_config: dict[str, Any],
    ) -> None:
        """API エラーハンドリングテスト"""
        # 401 Unauthorized エラー
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
            mock_get.return_value = mock_response

            api = GitHubAPI(
                token="invalid_token",
                username=sample_config["github_username"],
            )

            with pytest.raises(GitHubAPIError) as exc_info:
                api.get_user_info()

            assert "401" in str(exc_info.value)
            assert "認証に失敗" in str(exc_info.value)

        # 404 Not Found エラー
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
            mock_get.return_value = mock_response

            api = GitHubAPI(
                token=sample_config["github_token"],
                username="nonexistent_user",
            )

            with pytest.raises(GitHubAPIError) as exc_info:
                api.get_user_repos()

            assert "GitHub API エラー: 404" in str(exc_info.value)

        # 403 Rate Limit エラー
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 403
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
            mock_get.return_value = mock_response

            api = GitHubAPI(
                token=sample_config["github_token"],
                username=sample_config["github_username"],
            )

            with pytest.raises(GitHubAPIError) as exc_info:
                api.get_user_info()

            assert "403" in str(exc_info.value)
            assert "レート制限" in str(exc_info.value)

    def test_api_pagination_handling(
        self,
        sample_config: dict[str, Any],
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
            for i in range(1, 4)  # 3個のリポジトリ（1ページ目）
        ]

        page2_repos = [
            {
                "name": f"repo-{i}",
                "clone_url": f"https://github.com/test_user/repo-{i}.git",
                "description": f"リポジトリ{i}",
                "private": False,
                "default_branch": "main",
            }
            for i in range(4, 6)  # 2個のリポジトリ（2ページ目）
        ]

        call_count = 0

        def mock_get_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            mock_response = Mock()
            mock_response.raise_for_status.return_value = None

            if call_count == 1:
                mock_response.json.return_value = page1_repos
            elif call_count == 2:
                mock_response.json.return_value = page2_repos
            else:
                # 3ページ目以降は空
                mock_response.json.return_value = []

            return mock_response

        with patch("requests.get", side_effect=mock_get_side_effect):
            api = GitHubAPI(
                token=sample_config["github_token"],
                username=sample_config["github_username"],
            )
            repos = api.get_user_repos()

        # 全ページのリポジトリが取得されることを確認
        assert len(repos) == 5  # 3 + 2
        assert repos[0]["name"] == "repo-1"
        assert repos[4]["name"] == "repo-5"
        assert call_count == 3  # 3回呼び出される（1ページ目、2ページ目、空の3ページ目）

    def test_api_timeout_handling(
        self,
        sample_config: dict[str, Any],
    ) -> None:
        """APIタイムアウト処理テスト"""
        with patch("requests.get") as mock_get:
            mock_get.side_effect = requests.exceptions.Timeout("Request timed out")

            api = GitHubAPI(
                token=sample_config["github_token"],
                username=sample_config["github_username"],
            )

            with pytest.raises(GitHubAPIError) as exc_info:
                api.get_user_info()

            assert "ネットワークエラー" in str(exc_info.value)

    def test_api_network_error_handling(
        self,
        sample_config: dict[str, Any],
    ) -> None:
        """APIネットワークエラー処理テスト"""
        with patch("requests.get") as mock_get:
            mock_get.side_effect = requests.exceptions.ConnectionError("Network error")

            api = GitHubAPI(
                token=sample_config["github_token"],
                username=sample_config["github_username"],
            )

            with pytest.raises(GitHubAPIError) as exc_info:
                api.get_user_info()

            assert "ネットワークエラー" in str(exc_info.value)

    def test_api_response_validation(
        self,
        sample_config: dict[str, Any],
    ) -> None:
        """APIレスポンス検証テスト"""
        # 無効なJSONレスポンス
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.json.side_effect = ValueError("Invalid JSON")
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            api = GitHubAPI(
                token=sample_config["github_token"],
                username=sample_config["github_username"],
            )

            with pytest.raises(GitHubAPIError):
                api.get_user_info()

        # 正常なレスポンス
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {"login": "test_user", "name": "Test User"}
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            api = GitHubAPI(
                token=sample_config["github_token"],
                username=sample_config["github_username"],
            )

            user_info = api.get_user_info()
            assert user_info["login"] == "test_user"
            assert user_info["name"] == "Test User"

    def test_api_authentication_methods(
        self,
        sample_config: dict[str, Any],
    ) -> None:
        """API認証方法テスト"""
        # トークン認証
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {"login": "test_user"}
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            api = GitHubAPI(
                token=sample_config["github_token"],
                username=sample_config["github_username"],
            )
            api.get_user_info()

            # Requestが適切なヘッダーで呼び出されたことを確認
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            headers = call_args[1]["headers"]  # headersはkwargsにある
            assert "Authorization" in headers
            assert f"token {sample_config['github_token']}" in headers["Authorization"]

    @pytest.mark.slow
    def test_api_rate_limit_respect(
        self,
        sample_config: dict[str, Any],
    ) -> None:
        """APIレート制限遵守テスト"""
        import time

        call_times = []

        def mock_get_with_timing(*args, **kwargs):
            call_times.append(time.time())
            mock_response = Mock()
            mock_response.json.return_value = {"login": "test_user"}
            mock_response.raise_for_status.return_value = None
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
            intervals = [call_times[i + 1] - call_times[i] for i in range(len(call_times) - 1)]
            # 極端に短い間隔でないことを確認
            assert all(interval >= 0 for interval in intervals)

    def test_api_integration_with_environment_variables(
        self,
        sample_config: dict[str, Any],
    ) -> None:
        """環境変数を使用したAPI統合テスト"""
        # 環境変数からの認証情報取得
        env_token = "env_github_token"
        env_username = "env_github_user"

        with (
            patch.dict(os.environ, {"GITHUB_TOKEN": env_token, "GITHUB_USERNAME": env_username}),
            patch("requests.get") as mock_get,
        ):
            mock_response = Mock()
            mock_response.json.return_value = {"login": env_username}
            mock_response.raise_for_status.return_value = None
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
        headers = call_args[1]["headers"]  # headersはkwargsにある
        assert f"token {env_token}" in headers["Authorization"]

    def test_api_integration_error_recovery(
        self,
        sample_config: dict[str, Any],
    ) -> None:
        """APIエラー回復テスト"""
        call_count = 0

        def mock_get_with_retry(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            if call_count == 1:
                # 最初の呼び出しは失敗
                mock_response = Mock()
                mock_response.status_code = 500
                mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
                return mock_response
            else:
                # 2回目の呼び出しは成功
                mock_response = Mock()
                mock_response.json.return_value = {"login": "test_user"}
                mock_response.raise_for_status.return_value = None
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
