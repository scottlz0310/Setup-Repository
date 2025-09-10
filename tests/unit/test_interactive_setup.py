"""インタラクティブセットアップ機能のテスト"""

import subprocess
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest

from src.setup_repo.interactive_setup import InteractiveSetup, SetupWizard


class TestInteractiveSetup:
    """InteractiveSetupクラスのテスト"""

    def test_init(self):
        """初期化のテスト"""
        # Act
        setup = InteractiveSetup()

        # Assert
        assert setup.platform_detector is not None
        assert setup.platform_info is not None
        assert setup.config == {}
        assert setup.errors == []

    @patch("builtins.input")
    @patch("builtins.open", new_callable=mock_open)
    def test_run_setup_success(self, mock_file, mock_input):
        """正常なセットアップ実行のテスト"""
        # Arrange
        mock_input.side_effect = [
            "test_token",  # GitHub token
            "test_user",  # GitHub username
            "./test_repos",  # Clone destination
            "y",  # Auto install
            "y",  # Setup VS Code
            "y",  # Save config
        ]

        setup = InteractiveSetup()

        # Act
        result = setup.run_setup()

        # Assert
        assert result["github_token"] == "test_token"
        assert result["github_username"] == "test_user"
        assert result["clone_destination"] == "./test_repos"
        assert result["auto_install_dependencies"] is True
        assert result["setup_vscode"] is True
        assert result["platform_specific_setup"] is True
        assert result["dry_run"] is False
        assert result["verbose"] is True

        # ファイル保存の確認
        mock_file.assert_called_once()
        handle = mock_file()
        handle.write.assert_called()

    @patch("builtins.input")
    def test_run_setup_empty_token(self, mock_input):
        """空のトークンでのエラーテスト"""
        # Arrange
        mock_input.side_effect = [""]  # Empty token

        setup = InteractiveSetup()

        # Act & Assert
        with pytest.raises(ValueError, match="GitHubトークンは必須です"):
            setup.run_setup()

    @patch("builtins.input")
    def test_run_setup_empty_username(self, mock_input):
        """空のユーザー名でのエラーテスト"""
        # Arrange
        mock_input.side_effect = [
            "test_token",  # GitHub token
            "",  # Empty username
        ]

        setup = InteractiveSetup()

        # Act & Assert
        with pytest.raises(ValueError, match="GitHubユーザー名は必須です"):
            setup.run_setup()

    @patch("builtins.input")
    def test_run_setup_default_destination(self, mock_input):
        """デフォルトのクローン先使用のテスト"""
        # Arrange
        mock_input.side_effect = [
            "test_token",  # GitHub token
            "test_user",  # GitHub username
            "",  # Empty destination (use default)
            "n",  # No auto install
            "n",  # No VS Code setup
            "n",  # Don't save config
        ]

        setup = InteractiveSetup()

        # Act
        result = setup.run_setup()

        # Assert
        assert result["clone_destination"] == "./repos"
        assert result["auto_install_dependencies"] is False
        assert result["setup_vscode"] is False

    @patch("builtins.input")
    def test_run_setup_no_save_config(self, mock_input):
        """設定保存しない場合のテスト"""
        # Arrange
        mock_input.side_effect = [
            "test_token",
            "test_user",
            "./test_repos",
            "y",
            "y",
            "n",  # Don't save config
        ]

        setup = InteractiveSetup()

        # Act
        with patch("builtins.open", mock_open()) as mock_file:
            result = setup.run_setup()

        # Assert
        assert result is not None
        mock_file.assert_not_called()  # ファイル保存されない


class TestSetupWizard:
    """SetupWizardクラスのテスト"""

    def test_init(self):
        """初期化のテスト"""
        # Act
        wizard = SetupWizard()

        # Assert
        assert wizard.platform_detector is not None
        assert wizard.platform_info is not None
        assert wizard.config == {}
        assert wizard.errors == []

    @patch("builtins.print")
    def test_welcome_message(self, mock_print):
        """ウェルカムメッセージのテスト"""
        # Arrange
        wizard = SetupWizard()
        wizard.platform_info = Mock()
        wizard.platform_info.display_name = "Test Platform"

        # Act
        wizard.welcome_message()

        # Assert
        mock_print.assert_called()
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("セットアップリポジトリへようこそ" in call for call in print_calls)
        assert any("Test Platform" in call for call in print_calls)

    @patch("src.setup_repo.interactive_setup.validate_setup_prerequisites")
    @patch("builtins.print")
    def test_check_prerequisites_success(self, mock_print, mock_validate):
        """前提条件チェック成功のテスト"""
        # Arrange
        mock_validate.return_value = {
            "valid": True,
            "python": {"valid": True, "version": "3.9.0"},
            "git": {"available": True, "version": "git version 2.30.0"},
            "uv": {"available": True, "version": "uv 0.1.0"},
            "gh": {"available": True, "version": "gh version 2.0.0"},
            "warnings": [],
            "errors": [],
        }

        wizard = SetupWizard()

        # Act
        result = wizard.check_prerequisites()

        # Assert
        assert result is True
        mock_validate.assert_called_once()

    @patch("src.setup_repo.interactive_setup.validate_setup_prerequisites")
    @patch("builtins.print")
    def test_check_prerequisites_failure(self, mock_print, mock_validate):
        """前提条件チェック失敗のテスト"""
        # Arrange
        mock_validate.return_value = {
            "valid": False,
            "python": {"valid": False, "version": None},
            "git": {"available": False, "version": None},
            "uv": {"available": False, "version": None},
            "gh": {"available": False, "version": None},
            "warnings": ["Warning message"],
            "errors": ["Python not found", "Git not found"],
        }

        wizard = SetupWizard()

        # Act
        result = wizard.check_prerequisites()

        # Assert
        assert result is False
        mock_validate.assert_called_once()

    @patch("src.setup_repo.interactive_setup.get_available_package_managers")
    @patch("builtins.print")
    def test_setup_package_managers_success(self, mock_print, mock_get_managers):
        """パッケージマネージャーセットアップ成功のテスト"""
        # Arrange
        mock_get_managers.return_value = ["scoop", "winget"]

        wizard = SetupWizard()

        # Act
        result = wizard.setup_package_managers()

        # Assert
        assert result is True
        mock_get_managers.assert_called_once()

    @patch("src.setup_repo.interactive_setup.get_available_package_managers")
    @patch("builtins.input")
    @patch("builtins.print")
    def test_setup_package_managers_none_available(
        self, mock_print, mock_input, mock_get_managers
    ):
        """パッケージマネージャーが利用できない場合のテスト"""
        # Arrange
        mock_get_managers.return_value = []
        mock_input.return_value = "y"

        wizard = SetupWizard()

        # Act
        result = wizard.setup_package_managers()

        # Assert
        assert result is True
        mock_input.assert_called_once()

    @patch("src.setup_repo.interactive_setup.get_available_package_managers")
    @patch("builtins.input")
    @patch("builtins.print")
    def test_setup_package_managers_user_declines(
        self, mock_print, mock_input, mock_get_managers
    ):
        """ユーザーが続行を拒否した場合のテスト"""
        # Arrange
        mock_get_managers.return_value = []
        mock_input.return_value = "n"

        wizard = SetupWizard()

        # Act
        result = wizard.setup_package_managers()

        # Assert
        assert result is False

    def test_show_prerequisite_help_windows(self):
        """Windows用前提条件ヘルプのテスト"""
        # Arrange
        wizard = SetupWizard()
        wizard.platform_info = Mock()
        wizard.platform_info.name = "windows"

        # Act
        with patch("builtins.print") as mock_print:
            wizard._show_prerequisite_help()

        # Assert
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("Windows" in call for call in print_calls)
        assert any("winget" in call for call in print_calls)

    def test_show_prerequisite_help_linux(self):
        """Linux用前提条件ヘルプのテスト"""
        # Arrange
        wizard = SetupWizard()
        wizard.platform_info = Mock()
        wizard.platform_info.name = "linux"

        # Act
        with patch("builtins.print") as mock_print:
            wizard._show_prerequisite_help()

        # Assert
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("Linux" in call for call in print_calls)
        assert any("apt" in call for call in print_calls)

    def test_show_prerequisite_help_macos(self):
        """macOS用前提条件ヘルプのテスト"""
        # Arrange
        wizard = SetupWizard()
        wizard.platform_info = Mock()
        wizard.platform_info.name = "macos"

        # Act
        with patch("builtins.print") as mock_print:
            wizard._show_prerequisite_help()

        # Assert
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("macOS" in call for call in print_calls)
        assert any("brew" in call for call in print_calls)

    def test_show_prerequisite_help_wsl(self):
        """WSL用前提条件ヘルプのテスト"""
        # Arrange
        wizard = SetupWizard()
        wizard.platform_info = Mock()
        wizard.platform_info.name = "wsl"

        # Act
        with patch("builtins.print") as mock_print:
            wizard._show_prerequisite_help()

        # Assert
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("WSL" in call for call in print_calls)
        assert any("apt" in call for call in print_calls)

    @patch("subprocess.run")
    def test_check_tool_success(self, mock_run):
        """ツール存在チェック成功のテスト"""
        # Arrange
        mock_run.return_value = Mock()
        mock_run.return_value.stdout = "uv 0.1.0"

        wizard = SetupWizard()

        # Act
        with patch("builtins.print"):
            result = wizard._check_tool("uv")

        # Assert
        assert result is True
        mock_run.assert_called_once_with(
            ["uv", "--version"], capture_output=True, text=True, check=True
        )

    @patch("subprocess.run")
    def test_check_tool_failure(self, mock_run):
        """ツール存在チェック失敗のテスト"""
        # Arrange
        mock_run.side_effect = FileNotFoundError()

        wizard = SetupWizard()

        # Act
        result = wizard._check_tool("nonexistent")

        # Assert
        assert result is False

    @patch("subprocess.run")
    def test_check_tool_command_error(self, mock_run):
        """ツールコマンドエラーのテスト"""
        # Arrange
        mock_run.side_effect = subprocess.CalledProcessError(1, "cmd")

        wizard = SetupWizard()

        # Act
        result = wizard._check_tool("failing_tool")

        # Assert
        assert result is False

    @patch("src.setup_repo.interactive_setup.get_available_package_managers")
    @patch("src.setup_repo.interactive_setup.get_install_commands")
    @patch("subprocess.run")
    @patch("builtins.print")
    def test_install_uv_success(
        self, mock_print, mock_run, mock_get_commands, mock_get_managers
    ):
        """uvインストール成功のテスト"""
        # Arrange
        mock_get_managers.return_value = ["scoop"]
        mock_get_commands.return_value = {"scoop": ["scoop install uv"]}
        mock_run.return_value = Mock()

        wizard = SetupWizard()

        # Act
        result = wizard._install_uv()

        # Assert
        assert result is True
        mock_run.assert_called()

    @patch("src.setup_repo.interactive_setup.get_available_package_managers")
    @patch("src.setup_repo.interactive_setup.get_install_commands")
    @patch("subprocess.run")
    @patch("builtins.print")
    def test_install_uv_fallback_to_pip(
        self, mock_print, mock_run, mock_get_commands, mock_get_managers
    ):
        """uvインストールでpipフォールバックのテスト"""
        # Arrange
        mock_get_managers.return_value = ["scoop"]
        mock_get_commands.return_value = {"scoop": ["scoop install uv"]}

        # 最初の試行は失敗、pipは成功
        mock_run.side_effect = [
            subprocess.CalledProcessError(1, "cmd"),  # scoop失敗
            Mock(),  # pip成功
        ]

        wizard = SetupWizard()

        # Act
        result = wizard._install_uv()

        # Assert
        assert result is True
        assert mock_run.call_count == 2

    @patch("src.setup_repo.interactive_setup.get_available_package_managers")
    @patch("src.setup_repo.interactive_setup.get_install_commands")
    @patch("subprocess.run")
    @patch("builtins.print")
    def test_install_uv_all_fail(
        self, mock_print, mock_run, mock_get_commands, mock_get_managers
    ):
        """uvインストール全て失敗のテスト"""
        # Arrange
        mock_get_managers.return_value = ["scoop"]
        mock_get_commands.return_value = {"scoop": ["scoop install uv"]}
        mock_run.side_effect = subprocess.CalledProcessError(1, "cmd")

        wizard = SetupWizard()

        # Act
        result = wizard._install_uv()

        # Assert
        assert result is False

    @patch("src.setup_repo.interactive_setup.get_available_package_managers")
    @patch("src.setup_repo.interactive_setup.get_install_commands")
    @patch("subprocess.run")
    @patch("builtins.print")
    def test_install_gh_success(
        self, mock_print, mock_run, mock_get_commands, mock_get_managers
    ):
        """GitHub CLIインストール成功のテスト"""
        # Arrange
        mock_get_managers.return_value = ["scoop"]
        mock_get_commands.return_value = {
            "scoop": ["scoop install uv", "scoop install gh"]
        }
        mock_run.return_value = Mock()

        wizard = SetupWizard()

        # Act
        result = wizard._install_gh()

        # Assert
        assert result is True

    @patch("src.setup_repo.interactive_setup.get_available_package_managers")
    @patch("src.setup_repo.interactive_setup.get_install_commands")
    @patch("subprocess.run")
    @patch("builtins.print")
    def test_install_gh_failure(
        self, mock_print, mock_run, mock_get_commands, mock_get_managers
    ):
        """GitHub CLIインストール失敗のテスト"""
        # Arrange
        mock_get_managers.return_value = ["scoop"]
        mock_get_commands.return_value = {
            "scoop": ["scoop install uv", "scoop install gh"]
        }
        mock_run.side_effect = subprocess.CalledProcessError(1, "cmd")

        wizard = SetupWizard()

        # Act
        result = wizard._install_gh()

        # Assert
        assert result is False

    @patch("src.setup_repo.interactive_setup.validate_github_credentials")
    @patch("src.setup_repo.interactive_setup.validate_user_input")
    @patch("subprocess.run")
    @patch("builtins.print")
    def test_configure_github_existing_credentials(
        self, mock_print, mock_run, mock_validate_input, mock_validate_creds
    ):
        """既存のGitHub認証情報がある場合のテスト"""
        # Arrange
        mock_validate_creds.return_value = {
            "username": "existing_user",
            "token": "existing_token",
        }

        wizard = SetupWizard()

        # Act
        wizard.configure_github()

        # Assert
        assert wizard.config["owner"] == "existing_user"
        assert wizard.config["github_token"] == "existing_token"
        mock_validate_input.assert_not_called()

    @patch("src.setup_repo.interactive_setup.validate_github_credentials")
    @patch("src.setup_repo.interactive_setup.validate_user_input")
    @patch("subprocess.run")
    @patch("builtins.print")
    def test_configure_github_missing_username(
        self, mock_print, mock_run, mock_validate_input, mock_validate_creds
    ):
        """ユーザー名が不足している場合のテスト"""
        # Arrange
        mock_validate_creds.return_value = {
            "username": None,
            "token": "existing_token",
        }
        mock_validate_input.side_effect = [
            {"valid": True, "value": "new_user"},  # username input
        ]

        wizard = SetupWizard()

        # Act
        wizard.configure_github()

        # Assert
        assert wizard.config["owner"] == "new_user"
        mock_run.assert_called_with(
            ["git", "config", "--global", "user.name", "new_user"], check=True
        )

    @patch("src.setup_repo.interactive_setup.validate_github_credentials")
    @patch("src.setup_repo.interactive_setup.validate_user_input")
    @patch("subprocess.run")
    @patch("builtins.print")
    def test_configure_github_missing_token_with_gh_auth(
        self, mock_print, mock_run, mock_validate_input, mock_validate_creds
    ):
        """トークンが不足してGH認証を実行する場合のテスト"""
        # Arrange
        mock_validate_creds.side_effect = [
            {"username": "existing_user", "token": None},  # 初回チェック
            {"username": "existing_user", "token": "new_token"},  # 再チェック
        ]
        mock_validate_input.return_value = {
            "valid": True,
            "value": True,
        }  # GitHub CLI認証を選択

        wizard = SetupWizard()

        # Act
        wizard.configure_github()

        # Assert
        assert wizard.config["github_token"] == "new_token"
        mock_run.assert_called_with(["gh", "auth", "login"], check=True)

    @patch("src.setup_repo.interactive_setup.validate_user_input")
    @patch("src.setup_repo.interactive_setup.validate_directory_path")
    @patch("builtins.print")
    def test_configure_workspace_default(
        self, mock_print, mock_validate_path, mock_validate_input
    ):
        """デフォルトワークスペース使用のテスト"""
        # Arrange
        default_path = str(Path.home() / "workspace")
        mock_validate_input.return_value = {"valid": True, "value": ""}
        mock_validate_path.return_value = {
            "valid": True,
            "path": Path(default_path),
            "created": False,
        }

        wizard = SetupWizard()

        # Act
        wizard.configure_workspace()

        # Assert
        assert wizard.config["dest"] == default_path
        mock_validate_path.assert_called_once_with(default_path)

    @patch("src.setup_repo.interactive_setup.validate_user_input")
    @patch("src.setup_repo.interactive_setup.validate_directory_path")
    @patch("builtins.print")
    def test_configure_workspace_custom_path(
        self, mock_print, mock_validate_path, mock_validate_input
    ):
        """カスタムワークスペースパス使用のテスト"""
        # Arrange
        custom_path = "/custom/workspace"
        mock_validate_input.return_value = {"valid": True, "value": custom_path}
        mock_validate_path.return_value = {
            "valid": True,
            "path": Path(custom_path),
            "created": True,
        }

        wizard = SetupWizard()

        # Act
        wizard.configure_workspace()

        # Assert
        assert wizard.config["dest"] == custom_path
        mock_validate_path.assert_called_once_with(custom_path)

    @patch("src.setup_repo.interactive_setup.validate_user_input")
    @patch("src.setup_repo.interactive_setup.validate_directory_path")
    @patch("builtins.print")
    def test_configure_workspace_invalid_path(
        self, mock_print, mock_validate_path, mock_validate_input
    ):
        """無効なワークスペースパスの場合のテスト"""
        # Arrange
        invalid_path = "/invalid/path"
        default_path = str(Path.home() / "workspace")
        mock_validate_input.return_value = {"valid": True, "value": invalid_path}
        mock_validate_path.return_value = {
            "valid": False,
            "error": "Permission denied",
        }

        wizard = SetupWizard()

        # Act
        wizard.configure_workspace()

        # Assert
        assert wizard.config["dest"] == default_path

    @patch("builtins.open", new_callable=mock_open)
    @patch("builtins.print")
    def test_save_config_success(self, mock_print, mock_file):
        """設定保存成功のテスト"""
        # Arrange
        wizard = SetupWizard()
        wizard.config = {
            "owner": "test_user",
            "dest": "/test/workspace",
            "github_token": "test_token",
        }

        # Act
        result = wizard.save_config()

        # Assert
        assert result is True
        mock_file.assert_called_once_with(
            Path("config.local.json"), "w", encoding="utf-8"
        )

    @patch("builtins.open")
    @patch("builtins.print")
    def test_save_config_failure(self, mock_print, mock_file):
        """設定保存失敗のテスト"""
        # Arrange
        mock_file.side_effect = OSError("Permission denied")

        wizard = SetupWizard()
        wizard.config = {"owner": "test_user"}

        # Act
        result = wizard.save_config()

        # Assert
        assert result is False

    @patch("builtins.print")
    def test_show_next_steps(self, mock_print):
        """次のステップ表示のテスト"""
        # Arrange
        wizard = SetupWizard()
        wizard.config = {"github_token": "test_token"}

        # Act
        wizard.show_next_steps()

        # Assert
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("セットアップが完了しました" in call for call in print_calls)
        assert any("次のステップ" in call for call in print_calls)

    @patch("builtins.print")
    def test_show_next_steps_missing_token(self, mock_print):
        """トークン未設定時の次のステップ表示のテスト"""
        # Arrange
        wizard = SetupWizard()
        wizard.config = {"github_token": "YOUR_GITHUB_TOKEN"}

        # Act
        wizard.show_next_steps()

        # Assert
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("GitHubトークンが未設定です" in call for call in print_calls)

    @patch.object(SetupWizard, "show_next_steps")
    @patch.object(SetupWizard, "save_config")
    @patch.object(SetupWizard, "configure_workspace")
    @patch.object(SetupWizard, "configure_github")
    @patch.object(SetupWizard, "install_tools")
    @patch.object(SetupWizard, "setup_package_managers")
    @patch.object(SetupWizard, "check_prerequisites")
    @patch.object(SetupWizard, "welcome_message")
    def test_run_success(
        self,
        mock_welcome,
        mock_check_prereq,
        mock_setup_pkg,
        mock_install_tools,
        mock_config_github,
        mock_config_workspace,
        mock_save_config,
        mock_show_next,
    ):
        """セットアップウィザード実行成功のテスト"""
        # Arrange
        mock_check_prereq.return_value = True
        mock_setup_pkg.return_value = True
        mock_install_tools.return_value = True
        mock_save_config.return_value = True

        wizard = SetupWizard()

        # Act
        result = wizard.run()

        # Assert
        assert result is True
        mock_welcome.assert_called_once()
        mock_check_prereq.assert_called_once()
        mock_setup_pkg.assert_called_once()
        mock_install_tools.assert_called_once()
        mock_config_github.assert_called_once()
        mock_config_workspace.assert_called_once()
        mock_save_config.assert_called_once()
        mock_show_next.assert_called_once()

    @patch.object(SetupWizard, "check_prerequisites")
    @patch.object(SetupWizard, "welcome_message")
    @patch("builtins.print")
    def test_run_prerequisites_fail(self, mock_print, mock_welcome, mock_check_prereq):
        """前提条件チェック失敗時のテスト"""
        # Arrange
        mock_check_prereq.return_value = False

        wizard = SetupWizard()

        # Act
        result = wizard.run()

        # Assert
        assert result is False
        mock_welcome.assert_called_once()
        mock_check_prereq.assert_called_once()

    @patch.object(SetupWizard, "welcome_message")
    @patch("builtins.print")
    def test_run_keyboard_interrupt(self, mock_print, mock_welcome):
        """キーボード割り込み時のテスト"""
        # Arrange
        mock_welcome.side_effect = KeyboardInterrupt()

        wizard = SetupWizard()

        # Act
        result = wizard.run()

        # Assert
        assert result is False
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("セットアップが中断されました" in call for call in print_calls)

    @patch.object(SetupWizard, "welcome_message")
    @patch("builtins.print")
    def test_run_unexpected_error(self, mock_print, mock_welcome):
        """予期しないエラー時のテスト"""
        # Arrange
        mock_welcome.side_effect = Exception("Unexpected error")

        wizard = SetupWizard()

        # Act
        result = wizard.run()

        # Assert
        assert result is False
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("予期しないエラーが発生しました" in call for call in print_calls)


class TestSetupWizardInstallTools:
    """SetupWizardのinstall_toolsメソッドのテスト"""

    @patch.object(SetupWizard, "_install_gh")
    @patch.object(SetupWizard, "_install_uv")
    @patch.object(SetupWizard, "_check_tool")
    @patch("builtins.print")
    def test_install_tools_all_present(
        self, mock_print, mock_check_tool, mock_install_uv, mock_install_gh
    ):
        """全ツールが既にインストール済みの場合のテスト"""
        # Arrange
        mock_check_tool.side_effect = [True, True]  # uv, gh both present

        wizard = SetupWizard()

        # Act
        result = wizard.install_tools()

        # Assert
        assert result is True
        mock_install_uv.assert_not_called()
        mock_install_gh.assert_not_called()

    @patch.object(SetupWizard, "_install_gh")
    @patch.object(SetupWizard, "_install_uv")
    @patch.object(SetupWizard, "_check_tool")
    @patch("builtins.input")
    @patch("builtins.print")
    def test_install_tools_uv_missing_gh_optional_yes(
        self, mock_print, mock_input, mock_check_tool, mock_install_uv, mock_install_gh
    ):
        """uvが不足、ghをインストールする場合のテスト"""
        # Arrange
        mock_check_tool.side_effect = [False, False]  # uv, gh both missing
        mock_install_uv.return_value = True
        mock_install_gh.return_value = True
        mock_input.return_value = "y"  # Install gh

        wizard = SetupWizard()

        # Act
        result = wizard.install_tools()

        # Assert
        assert result is True
        mock_install_uv.assert_called_once()
        mock_install_gh.assert_called_once()

    @patch.object(SetupWizard, "_install_gh")
    @patch.object(SetupWizard, "_install_uv")
    @patch.object(SetupWizard, "_check_tool")
    @patch("builtins.input")
    @patch("builtins.print")
    def test_install_tools_uv_missing_gh_optional_no(
        self, mock_print, mock_input, mock_check_tool, mock_install_uv, mock_install_gh
    ):
        """uvが不足、ghをインストールしない場合のテスト"""
        # Arrange
        mock_check_tool.side_effect = [False, False]  # uv, gh both missing
        mock_install_uv.return_value = True
        mock_input.return_value = "n"  # Don't install gh

        wizard = SetupWizard()

        # Act
        result = wizard.install_tools()

        # Assert
        assert result is True
        mock_install_uv.assert_called_once()
        mock_install_gh.assert_not_called()

    @patch.object(SetupWizard, "_install_uv")
    @patch.object(SetupWizard, "_check_tool")
    @patch("builtins.print")
    def test_install_tools_uv_install_fails(
        self, mock_print, mock_check_tool, mock_install_uv
    ):
        """uvインストール失敗の場合のテスト"""
        # Arrange
        mock_check_tool.side_effect = [False, True]  # uv missing, gh present
        mock_install_uv.return_value = False

        wizard = SetupWizard()

        # Act
        result = wizard.install_tools()

        # Assert
        assert result is False
        mock_install_uv.assert_called_once()


class TestSetupWizardPackageManagerHelp:
    """SetupWizardのパッケージマネージャーヘルプメソッドのテスト"""

    def test_show_package_manager_help_windows(self):
        """Windows用パッケージマネージャーヘルプのテスト"""
        # Arrange
        wizard = SetupWizard()
        wizard.platform_info = Mock()
        wizard.platform_info.name = "windows"

        # Act
        with patch("builtins.print") as mock_print:
            wizard._show_package_manager_help()

        # Assert
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("Windows" in call for call in print_calls)
        assert any("Scoop" in call for call in print_calls)

    def test_show_package_manager_help_linux(self):
        """Linux用パッケージマネージャーヘルプのテスト"""
        # Arrange
        wizard = SetupWizard()
        wizard.platform_info = Mock()
        wizard.platform_info.name = "linux"

        # Act
        with patch("builtins.print") as mock_print:
            wizard._show_package_manager_help()

        # Assert
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("Linux" in call for call in print_calls)
        assert any("Snap" in call for call in print_calls)

    def test_show_package_manager_help_wsl(self):
        """WSL用パッケージマネージャーヘルプのテスト"""
        # Arrange
        wizard = SetupWizard()
        wizard.platform_info = Mock()
        wizard.platform_info.name = "wsl"

        # Act
        with patch("builtins.print") as mock_print:
            wizard._show_package_manager_help()

        # Assert
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("Linux" in call for call in print_calls)
        assert any("Snap" in call for call in print_calls)

    def test_show_package_manager_help_macos(self):
        """macOS用パッケージマネージャーヘルプのテスト"""
        # Arrange
        wizard = SetupWizard()
        wizard.platform_info = Mock()
        wizard.platform_info.name = "macos"

        # Act
        with patch("builtins.print") as mock_print:
            wizard._show_package_manager_help()

        # Assert
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("macOS" in call for call in print_calls)
        assert any("Homebrew" in call for call in print_calls)
