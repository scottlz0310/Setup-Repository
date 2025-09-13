"""
設定管理機能のテスト

マルチプラットフォームテスト方針に準拠した設定管理機能のテスト
"""

import os
from unittest.mock import patch

import pytest

from setup_repo.config import (
    auto_detect_config,
    get_github_token,
    get_github_user,
    load_config,
)
from tests.multiplatform.helpers import (
    get_platform_specific_config,
    verify_current_platform,
)


class TestConfig:
    """設定管理機能のテスト"""

    def test_auto_detect_config(self):
        """設定自動検出テスト"""
        verify_current_platform()  # プラットフォーム検証

        config = auto_detect_config()

        # 基本的な設定項目が存在することを確認
        assert "owner" in config
        assert "dest" in config
        assert "github_token" in config
        assert "use_https" in config
        assert "max_retries" in config
        assert isinstance(config["max_retries"], int)
        assert config["max_retries"] >= 0

    def test_load_config_default(self):
        """デフォルト設定読み込みテスト"""
        config = load_config()

        # デフォルト設定が正しく読み込まれることを確認
        assert isinstance(config, dict)
        assert "owner" in config
        assert "dest" in config

    def test_get_github_token_from_env(self):
        """環境変数からのGitHubトークン取得テスト"""
        with patch.dict(os.environ, {"GITHUB_TOKEN": "test_token"}):
            token = get_github_token()
            assert token == "test_token"

    def test_get_github_token_no_env(self):
        """環境変数がない場合のGitHubトークン取得テスト"""
        with patch.dict(os.environ, {}, clear=True), patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()
            token = get_github_token()
            assert token is None

    def test_get_github_user_from_env(self):
        """環境変数からのGitHubユーザー取得テスト"""
        with patch.dict(os.environ, {"GITHUB_USER": "testuser"}):
            user = get_github_user()
            assert user == "testuser"

    def test_get_github_user_from_git_config(self):
        """Git設定からのユーザー取得テスト"""
        with patch.dict(os.environ, {}, clear=True), patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = "testuser\n"
            mock_run.return_value.returncode = 0
            user = get_github_user()
            assert user == "testuser"

    def test_get_github_user_no_config(self):
        """設定がない場合のユーザー取得テスト"""
        with patch.dict(os.environ, {}, clear=True), patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()
            user = get_github_user()
            assert user is None

    @pytest.mark.integration
    def test_config_platform_integration(self):
        """プラットフォーム統合テスト"""
        platform_info = verify_current_platform()
        get_platform_specific_config()  # プラットフォーム設定取得

        config = load_config()

        # プラットフォーム固有の設定が適用されることを確認
        assert isinstance(config, dict)
        assert "dest" in config

        # プラットフォーム情報が正しく取得できることを確認
        assert platform_info.name in ["windows", "linux", "wsl", "macos"]

    def test_config_environment_override(self):
        """環境変数による設定上書きテスト"""
        with patch.dict(
            os.environ,
            {"GITHUB_TOKEN": "env_token", "GITHUB_USERNAME": "env_user", "CLONE_DESTINATION": "/custom/path"},
        ):
            config = load_config()

            assert config["github_token"] == "env_token"
            assert config.get("github_username") == "env_user"
            assert config.get("clone_destination") == "/custom/path"
