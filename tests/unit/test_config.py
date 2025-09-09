"""
config.pyモジュールの包括的な単体テスト

設定管理機能のテスト：
- GitHub認証情報の自動検出
- 設定ファイルの読み込み
- 自動検出フォールバック機能
"""

import json
import os
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from src.setup_repo.config import (
    auto_detect_config,
    get_github_token,
    get_github_user,
    load_config,
)


@pytest.mark.unit
class TestGetGithubToken:
    """get_github_token関数のテスト"""

    def test_get_token_from_environment_variable(self) -> None:
        """環境変数からGitHubトークンを取得するテスト"""
        with patch.dict(os.environ, {"GITHUB_TOKEN": "env_token_123"}):
            token = get_github_token()
            assert token == "env_token_123"

    def test_get_token_from_gh_cli(self) -> None:
        """gh CLIからGitHubトークンを取得するテスト"""
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value.stdout = "gh_cli_token_456\n"
            mock_run.return_value.returncode = 0

            token = get_github_token()
            assert token == "gh_cli_token_456"

            # gh CLIが正しく呼び出されることを確認
            mock_run.assert_called_once_with(
                ["gh", "auth", "token"],
                capture_output=True,
                text=True,
                check=True,
            )

    def test_get_token_environment_variable_priority(self) -> None:
        """環境変数がgh CLIより優先されることをテスト"""
        with (
            patch.dict(os.environ, {"GITHUB_TOKEN": "env_priority_token"}),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value.stdout = "gh_cli_token"

            token = get_github_token()
            assert token == "env_priority_token"

            # gh CLIが呼び出されないことを確認
            mock_run.assert_not_called()

    def test_get_token_gh_cli_failure(self) -> None:
        """gh CLIが失敗した場合のテスト"""
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.side_effect = subprocess.CalledProcessError(1, "gh")

            token = get_github_token()
            assert token is None

    def test_get_token_gh_cli_not_found(self) -> None:
        """gh CLIが見つからない場合のテスト"""
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.side_effect = FileNotFoundError()

            token = get_github_token()
            assert token is None

    def test_get_token_no_sources_available(self) -> None:
        """トークンソースが利用できない場合のテスト"""
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.side_effect = FileNotFoundError()

            token = get_github_token()
            assert token is None


@pytest.mark.unit
class TestGetGithubUser:
    """get_github_user関数のテスト"""

    def test_get_user_from_environment_variable(self) -> None:
        """環境変数からGitHubユーザー名を取得するテスト"""
        with patch.dict(os.environ, {"GITHUB_USER": "env_user"}):
            user = get_github_user()
            assert user == "env_user"

    def test_get_user_from_git_config(self) -> None:
        """git configからユーザー名を取得するテスト"""
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value.stdout = "git_config_user\n"
            mock_run.return_value.returncode = 0

            user = get_github_user()
            assert user == "git_config_user"

            # git configが正しく呼び出されることを確認
            mock_run.assert_called_once_with(
                ["git", "config", "--global", "user.name"],
                capture_output=True,
                text=True,
                check=True,
            )

    def test_get_user_environment_variable_priority(self) -> None:
        """環境変数がgit configより優先されることをテスト"""
        with (
            patch.dict(os.environ, {"GITHUB_USER": "env_priority_user"}),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value.stdout = "git_config_user"

            user = get_github_user()
            assert user == "env_priority_user"

            # git configが呼び出されないことを確認
            mock_run.assert_not_called()

    def test_get_user_git_config_failure(self) -> None:
        """git configが失敗した場合のテスト"""
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.side_effect = subprocess.CalledProcessError(1, "git")

            user = get_github_user()
            assert user is None

    def test_get_user_git_not_found(self) -> None:
        """gitが見つからない場合のテスト"""
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.side_effect = FileNotFoundError()

            user = get_github_user()
            assert user is None


@pytest.mark.unit
class TestAutoDetectConfig:
    """auto_detect_config関数のテスト"""

    def test_auto_detect_config_with_all_values(self) -> None:
        """すべての値が検出される場合のテスト"""
        with (
            patch("src.setup_repo.config.get_github_user") as mock_user,
            patch("src.setup_repo.config.get_github_token") as mock_token,
        ):
            mock_user.return_value = "detected_user"
            mock_token.return_value = "detected_token"

            config = auto_detect_config()

            assert config["owner"] == "detected_user"
            assert config["github_token"] == "detected_token"
            assert config["dest"] == str(Path.home() / "workspace")
            assert config["use_https"] is False
            assert config["max_retries"] == 2
            assert config["skip_uv_install"] is False
            assert config["auto_stash"] is False
            assert config["sync_only"] is False
            assert config["log_file"] == str(
                Path.home() / "logs" / "repo-sync.log"
            )

    def test_auto_detect_config_with_missing_values(self) -> None:
        """一部の値が検出されない場合のテスト"""
        with (
            patch("src.setup_repo.config.get_github_user") as mock_user,
            patch("src.setup_repo.config.get_github_token") as mock_token,
        ):
            mock_user.return_value = None
            mock_token.return_value = None

            config = auto_detect_config()

            assert config["owner"] == ""
            assert config["github_token"] is None
            # その他のデフォルト値は変わらない
            assert config["dest"] == str(Path.home() / "workspace")
            assert config["use_https"] is False

    def test_auto_detect_config_default_paths(self) -> None:
        """デフォルトパスが正しく設定されることをテスト"""
        with (
            patch("src.setup_repo.config.get_github_user") as mock_user,
            patch("src.setup_repo.config.get_github_token") as mock_token,
        ):
            mock_user.return_value = "test_user"
            mock_token.return_value = "test_token"

            config = auto_detect_config()

            # パスがPath.home()を基準に設定されることを確認
            expected_dest = str(Path.home() / "workspace")
            expected_log = str(Path.home() / "logs" / "repo-sync.log")

            assert config["dest"] == expected_dest
            assert config["log_file"] == expected_log


@pytest.mark.unit
class TestLoadConfig:
    """load_config関数のテスト"""

    def test_load_config_with_local_config_file(self, temp_dir: Path) -> None:
        """config.local.jsonが存在する場合のテスト"""
        # テスト用設定ファイルを作成
        local_config = {
            "owner": "file_user",
            "github_token": "file_token",
            "dest": "/custom/path",
        }

        config_file = temp_dir / "config.local.json"
        with open(config_file, "w") as f:
            json.dump(local_config, f)

        # カレントディレクトリを変更してテスト
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)

            with patch("src.setup_repo.config.auto_detect_config") as mock_auto:
                mock_auto.return_value = {
                    "owner": "auto_user",
                    "github_token": "auto_token",
                    "dest": "/auto/path",
                    "use_https": False,
                }

                config = load_config()

                # ファイル設定が自動検出設定を上書きすることを確認
                assert config["owner"] == "file_user"
                assert config["github_token"] == "file_token"
                assert config["dest"] == "/custom/path"
                # ファイルにない設定は自動検出値が使われる
                assert config["use_https"] is False

        finally:
            os.chdir(original_cwd)

    def test_load_config_with_global_config_file(self, temp_dir: Path) -> None:
        """config.jsonが存在する場合のテスト"""
        # テスト用設定ファイルを作成
        global_config = {"owner": "global_user", "github_token": "global_token"}

        config_file = temp_dir / "config.json"
        with open(config_file, "w") as f:
            json.dump(global_config, f)

        # カレントディレクトリを変更してテスト
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)

            with patch("src.setup_repo.config.auto_detect_config") as mock_auto:
                mock_auto.return_value = {
                    "owner": "auto_user",
                    "github_token": "auto_token",
                    "dest": "/auto/path",
                }

                config = load_config()

                # ファイル設定が自動検出設定を上書きすることを確認
                assert config["owner"] == "global_user"
                assert config["github_token"] == "global_token"
                assert config["dest"] == "/auto/path"  # ファイルにない設定

        finally:
            os.chdir(original_cwd)

    def test_load_config_local_priority_over_global(self, temp_dir: Path) -> None:
        """config.local.jsonがconfig.jsonより優先されることをテスト"""
        # 両方の設定ファイルを作成
        local_config = {"owner": "local_user"}
        global_config = {"owner": "global_user"}

        local_file = temp_dir / "config.local.json"
        global_file = temp_dir / "config.json"

        with open(local_file, "w") as f:
            json.dump(local_config, f)
        with open(global_file, "w") as f:
            json.dump(global_config, f)

        # カレントディレクトリを変更してテスト
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)

            with patch("src.setup_repo.config.auto_detect_config") as mock_auto:
                mock_auto.return_value = {"owner": "auto_user"}

                config = load_config()

                # local設定が優先されることを確認
                assert config["owner"] == "local_user"

        finally:
            os.chdir(original_cwd)

    def test_load_config_no_config_files(self, temp_dir: Path) -> None:
        """設定ファイルが存在しない場合のテスト"""
        # カレントディレクトリを変更してテスト
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)

            with patch("src.setup_repo.config.auto_detect_config") as mock_auto:
                expected_config = {
                    "owner": "auto_user",
                    "github_token": "auto_token",
                    "dest": "/auto/path",
                }
                mock_auto.return_value = expected_config

                config = load_config()

                # 自動検出設定がそのまま返されることを確認
                assert config == expected_config

        finally:
            os.chdir(original_cwd)

    def test_load_config_invalid_json_file(self, temp_dir: Path) -> None:
        """無効なJSONファイルが存在する場合のテスト"""
        # 無効なJSONファイルを作成
        config_file = temp_dir / "config.local.json"
        with open(config_file, "w") as f:
            f.write("invalid json content")

        # カレントディレクトリを変更してテスト
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)

            with patch("src.setup_repo.config.auto_detect_config") as mock_auto:
                expected_config = {"owner": "auto_user"}
                mock_auto.return_value = expected_config

                # JSONDecodeErrorが発生することを確認
                with pytest.raises(json.JSONDecodeError):
                    load_config()

        finally:
            os.chdir(original_cwd)


@pytest.mark.unit
class TestConfigIntegration:
    """設定管理の統合テスト"""

    def test_full_config_loading_workflow(self, temp_dir: Path) -> None:
        """完全な設定読み込みワークフローのテスト"""
        # 環境変数とファイル設定を組み合わせたテスト
        with patch.dict(
            os.environ, {"GITHUB_TOKEN": "env_token", "GITHUB_USER": "env_user"}
        ):
            # 設定ファイルを作成
            file_config = {"dest": "/custom/destination", "use_https": True}

            config_file = temp_dir / "config.local.json"
            with open(config_file, "w") as f:
                json.dump(file_config, f)

            # カレントディレクトリを変更してテスト
            original_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)

                config = load_config()

                # 環境変数からの値
                assert config["github_token"] == "env_token"
                assert config["owner"] == "env_user"

                # ファイルからの値
                assert config["dest"] == "/custom/destination"
                assert config["use_https"] is True

                # デフォルト値
                assert config["max_retries"] == 2
                assert config["skip_uv_install"] is False

            finally:
                os.chdir(original_cwd)
