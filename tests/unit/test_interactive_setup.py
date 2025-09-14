"""対話型セットアップのテスト"""

from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest

from src.setup_repo.interactive_setup import InteractiveSetup, SetupWizard

from ..multiplatform.helpers import verify_current_platform


class TestInteractiveSetup:
    """InteractiveSetupのテストクラス"""

    @pytest.fixture
    def interactive_setup(self):
        """InteractiveSetupインスタンス"""
        return InteractiveSetup()

    @pytest.mark.unit
    def test_init(self, interactive_setup):
        """初期化テスト"""
        verify_current_platform()  # プラットフォーム検証

        assert interactive_setup.platform_detector is not None
        assert interactive_setup.platform_info is not None
        assert interactive_setup.config == {}
        assert interactive_setup.errors == []

    @pytest.mark.unit
    @patch("builtins.input")
    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump")
    def test_run_setup_basic(self, mock_json_dump, mock_file, mock_input, interactive_setup):
        """基本的なセットアップ実行テスト"""
        verify_current_platform()  # プラットフォーム検証

        # 入力をモック
        mock_input.side_effect = [
            "test_token",  # GitHub token
            "test_user",  # GitHub username
            "./test_repos",  # Clone destination
            "y",  # Auto install
            "y",  # Setup VS Code
            "y",  # Save config
        ]

        result = interactive_setup.run_setup()

        assert result["github_token"] == "test_token"
        assert result["github_username"] == "test_user"
        assert result["clone_destination"] == "./test_repos"
        assert result["auto_install_dependencies"] is True
        assert result["setup_vscode"] is True

    @pytest.mark.unit
    @patch("builtins.input")
    def test_run_setup_missing_token(self, mock_input, interactive_setup):
        """GitHubトークンが空の場合のエラーテスト"""
        verify_current_platform()  # プラットフォーム検証

        mock_input.side_effect = [""]  # Empty token

        with pytest.raises(ValueError, match="GitHubトークンは必須です"):
            interactive_setup.run_setup()

    @pytest.mark.unit
    @patch("builtins.input")
    def test_run_setup_missing_username(self, mock_input, interactive_setup):
        """GitHubユーザー名が空の場合のエラーテスト"""
        verify_current_platform()  # プラットフォーム検証

        mock_input.side_effect = ["test_token", ""]  # Empty username

        with pytest.raises(ValueError, match="GitHubユーザー名は必須です"):
            interactive_setup.run_setup()

    @pytest.mark.unit
    @patch("builtins.input")
    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump")
    def test_run_setup_default_values(self, mock_json_dump, mock_file, mock_input, interactive_setup):
        """デフォルト値の使用テスト"""
        verify_current_platform()  # プラットフォーム検証

        mock_input.side_effect = [
            "test_token",
            "test_user",
            "",  # Empty clone destination (should use default)
            "n",  # No auto install
            "n",  # No VS Code setup
            "n",  # Don't save config
        ]

        result = interactive_setup.run_setup()

        assert result["clone_destination"] == "./repos"
        assert result["auto_install_dependencies"] is False
        assert result["setup_vscode"] is False


class TestSetupWizard:
    """SetupWizardのテストクラス"""

    @pytest.fixture
    def setup_wizard(self):
        """SetupWizardインスタンス"""
        return SetupWizard()

    @pytest.mark.unit
    def test_init(self, setup_wizard):
        """初期化テスト"""
        verify_current_platform()  # プラットフォーム検証

        assert setup_wizard.platform_detector is not None
        assert setup_wizard.platform_info is not None
        assert setup_wizard.config == {}
        assert setup_wizard.errors == []

    @pytest.mark.unit
    def test_welcome_message(self, setup_wizard, capsys):
        """ウェルカムメッセージテスト"""
        verify_current_platform()  # プラットフォーム検証

        setup_wizard.welcome_message()

        captured = capsys.readouterr()
        assert "セットアップリポジトリへようこそ" in captured.out
        assert "検出されたプラットフォーム" in captured.out

    @pytest.mark.unit
    @patch("src.setup_repo.interactive_setup.validate_setup_prerequisites")
    def test_check_prerequisites_success(self, mock_validate, setup_wizard, capsys):
        """前提条件チェック成功テスト"""
        verify_current_platform()  # プラットフォーム検証

        mock_validate.return_value = {
            "valid": True,
            "python": {"valid": True, "version": "3.9.0"},
            "git": {"available": True, "version": "git version 2.30.0"},
            "uv": {"available": True, "version": "uv 0.1.0"},
            "gh": {"available": True, "version": "gh version 2.0.0"},
            "warnings": [],
            "errors": [],
        }

        result = setup_wizard.check_prerequisites()

        assert result is True
        captured = capsys.readouterr()
        assert "Python 3.9.0" in captured.out

    @pytest.mark.unit
    @patch("src.setup_repo.interactive_setup.validate_setup_prerequisites")
    def test_check_prerequisites_failure(self, mock_validate, setup_wizard, capsys):
        """前提条件チェック失敗テスト"""
        verify_current_platform()  # プラットフォーム検証

        mock_validate.return_value = {
            "valid": False,
            "python": {"valid": False, "version": None},
            "git": {"available": False, "version": None},
            "uv": {"available": False, "version": None},
            "gh": {"available": False, "version": None},
            "warnings": ["Warning message"],
            "errors": ["Python not found"],
        }

        result = setup_wizard.check_prerequisites()

        assert result is False
        captured = capsys.readouterr()
        assert "前提条件が満たされていません" in captured.out

    @pytest.mark.unit
    @patch("src.setup_repo.interactive_setup.get_available_package_managers")
    def test_setup_package_managers_success(self, mock_get_managers, setup_wizard, capsys):
        """パッケージマネージャーセットアップ成功テスト"""
        verify_current_platform()  # プラットフォーム検証

        mock_get_managers.return_value = ["scoop", "winget"]

        result = setup_wizard.setup_package_managers()

        assert result is True
        captured = capsys.readouterr()
        assert "利用可能なパッケージマネージャー" in captured.out

    @pytest.mark.unit
    @patch("src.setup_repo.interactive_setup.get_available_package_managers")
    @patch("builtins.input")
    def test_setup_package_managers_none_available(self, mock_input, mock_get_managers, setup_wizard):
        """利用可能なパッケージマネージャーがない場合"""
        verify_current_platform()  # プラットフォーム検証

        mock_get_managers.return_value = []
        mock_input.return_value = "y"

        result = setup_wizard.setup_package_managers()

        assert result is True

    @pytest.mark.unit
    @patch("subprocess.run")
    def test_check_tool_success(self, mock_run, setup_wizard, capsys):
        """ツール存在チェック成功テスト"""
        verify_current_platform()  # プラットフォーム検証

        mock_run.return_value = Mock(stdout="uv 0.1.0", returncode=0)

        result = setup_wizard._check_tool("uv")

        assert result is True
        captured = capsys.readouterr()
        assert "uv: uv 0.1.0" in captured.out

    @pytest.mark.unit
    @patch("subprocess.run")
    def test_check_tool_failure(self, mock_run, setup_wizard):
        """ツール存在チェック失敗テスト"""
        verify_current_platform()  # プラットフォーム検証

        mock_run.side_effect = FileNotFoundError()

        result = setup_wizard._check_tool("nonexistent")

        assert result is False

    @pytest.mark.unit
    @patch.object(SetupWizard, "_check_tool")
    @patch.object(SetupWizard, "_install_uv")
    def test_install_tools_uv_missing(self, mock_install_uv, mock_check_tool, setup_wizard):
        """uvが不足している場合のツールインストール"""
        verify_current_platform()  # プラットフォーム検証

        mock_check_tool.side_effect = [False, True]  # uv missing, gh available
        mock_install_uv.return_value = True

        result = setup_wizard.install_tools()

        assert result is True
        mock_install_uv.assert_called_once()

    @pytest.mark.unit
    @patch("src.setup_repo.interactive_setup.get_available_package_managers")
    @patch("src.setup_repo.interactive_setup.get_install_commands")
    @patch("subprocess.run")
    def test_install_uv_success(self, mock_run, mock_get_commands, mock_get_managers, setup_wizard):
        """uvインストール成功テスト"""
        verify_current_platform()  # プラットフォーム検証

        mock_get_managers.return_value = ["scoop"]
        mock_get_commands.return_value = {"scoop": ["scoop install uv"]}
        mock_run.return_value = Mock(returncode=0)

        result = setup_wizard._install_uv()

        assert result is True

    @pytest.mark.unit
    @patch("src.setup_repo.interactive_setup.get_available_package_managers")
    @patch("src.setup_repo.interactive_setup.get_install_commands")
    @patch("subprocess.run")
    def test_install_uv_fallback_pip(self, mock_run, mock_get_commands, mock_get_managers, setup_wizard):
        """uvインストールのpipフォールバック"""
        verify_current_platform()  # プラットフォーム検証

        mock_get_managers.return_value = []
        mock_get_commands.return_value = {}
        mock_run.return_value = Mock(returncode=0)

        result = setup_wizard._install_uv()

        assert result is True
        # pipでのインストールが呼ばれることを確認
        mock_run.assert_called_with(["pip", "install", "uv"], check=True)

    @pytest.mark.unit
    @patch("src.setup_repo.interactive_setup.validate_github_credentials")
    @patch("builtins.input")
    def test_configure_github_existing_credentials(self, mock_input, mock_validate, setup_wizard):
        """既存のGitHub認証情報がある場合"""
        verify_current_platform()  # プラットフォーム検証

        mock_validate.return_value = {"username": "test_user", "token": "test_token"}

        setup_wizard.configure_github()

        assert setup_wizard.config["owner"] == "test_user"
        assert setup_wizard.config["github_token"] == "test_token"

    @pytest.mark.unit
    @patch("src.setup_repo.interactive_setup.validate_github_credentials")
    @patch("src.setup_repo.interactive_setup.validate_user_input")
    @patch("subprocess.run")
    def test_configure_github_missing_username(self, mock_run, mock_validate_input, mock_validate, setup_wizard):
        """GitHubユーザー名が不足している場合"""
        verify_current_platform()  # プラットフォーム検証

        mock_validate.return_value = {"username": None, "token": "test_token"}
        mock_validate_input.return_value = {"valid": True, "value": "new_user"}

        setup_wizard.configure_github()

        assert setup_wizard.config["owner"] == "new_user"
        mock_run.assert_called_once()

    @pytest.mark.unit
    @patch("src.setup_repo.interactive_setup.validate_user_input")
    @patch("src.setup_repo.interactive_setup.validate_directory_path")
    def test_configure_workspace_default(self, mock_validate_path, mock_validate_input, setup_wizard):
        """デフォルトワークスペース設定"""
        verify_current_platform()  # プラットフォーム検証

        default_workspace = str(Path.home() / "workspace")
        mock_validate_input.return_value = {"valid": True, "value": ""}
        mock_validate_path.return_value = {"valid": True, "path": Path(default_workspace)}

        setup_wizard.configure_workspace()

        assert setup_wizard.config["dest"] == default_workspace

    @pytest.mark.unit
    @patch("src.setup_repo.interactive_setup.validate_user_input")
    @patch("src.setup_repo.interactive_setup.validate_directory_path")
    def test_configure_workspace_custom(self, mock_validate_path, mock_validate_input, setup_wizard):
        """カスタムワークスペース設定"""
        verify_current_platform()  # プラットフォーム検証

        custom_path = "/custom/workspace"
        mock_validate_input.return_value = {"valid": True, "value": custom_path}
        mock_validate_path.return_value = {"valid": True, "path": Path(custom_path), "created": True}

        setup_wizard.configure_workspace()

        # プラットフォーム固有のパス形式を考慮
        expected_path = str(Path(custom_path))
        assert setup_wizard.config["dest"] == expected_path

    @pytest.mark.unit
    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump")
    def test_save_config_success(self, mock_json_dump, mock_file, setup_wizard, capsys):
        """設定保存成功テスト"""
        verify_current_platform()  # プラットフォーム検証

        setup_wizard.config = {"owner": "test_user", "dest": "/test/path"}

        result = setup_wizard.save_config()

        assert result is True
        mock_json_dump.assert_called_once()
        captured = capsys.readouterr()
        assert "設定ファイルを作成しました" in captured.out

    @pytest.mark.unit
    @patch("builtins.open", side_effect=OSError("Permission denied"))
    def test_save_config_failure(self, mock_file, setup_wizard, capsys):
        """設定保存失敗テスト"""
        verify_current_platform()  # プラットフォーム検証

        result = setup_wizard.save_config()

        assert result is False
        captured = capsys.readouterr()
        assert "設定ファイルの保存に失敗" in captured.out

    @pytest.mark.unit
    def test_show_next_steps(self, setup_wizard, capsys):
        """次のステップ表示テスト"""
        verify_current_platform()  # プラットフォーム検証

        setup_wizard.show_next_steps()

        captured = capsys.readouterr()
        assert "セットアップが完了しました" in captured.out
        assert "次のステップ" in captured.out

    @pytest.mark.unit
    def test_show_next_steps_token_warning(self, setup_wizard, capsys):
        """トークン未設定警告の表示テスト"""
        verify_current_platform()  # プラットフォーム検証

        setup_wizard.config["github_token"] = "YOUR_GITHUB_TOKEN"
        setup_wizard.show_next_steps()

        captured = capsys.readouterr()
        assert "GitHubトークンが未設定です" in captured.out

    @pytest.mark.unit
    @patch.object(SetupWizard, "welcome_message")
    @patch.object(SetupWizard, "check_prerequisites")
    @patch.object(SetupWizard, "setup_package_managers")
    @patch.object(SetupWizard, "install_tools")
    @patch.object(SetupWizard, "configure_github")
    @patch.object(SetupWizard, "configure_workspace")
    @patch.object(SetupWizard, "save_config")
    @patch.object(SetupWizard, "show_next_steps")
    def test_run_success(
        self,
        mock_show_next,
        mock_save,
        mock_configure_workspace,
        mock_configure_github,
        mock_install,
        mock_setup_managers,
        mock_check_prereq,
        mock_welcome,
        setup_wizard,
    ):
        """セットアップウィザード実行成功テスト"""
        verify_current_platform()  # プラットフォーム検証

        # すべてのステップを成功に設定
        mock_check_prereq.return_value = True
        mock_setup_managers.return_value = True
        mock_install.return_value = True
        mock_save.return_value = True

        result = setup_wizard.run()

        assert result is True
        mock_welcome.assert_called_once()
        mock_show_next.assert_called_once()

    @pytest.mark.unit
    @patch.object(SetupWizard, "welcome_message")
    @patch.object(SetupWizard, "check_prerequisites")
    def test_run_prerequisites_failure(self, mock_check_prereq, mock_welcome, setup_wizard):
        """前提条件チェック失敗時のセットアップウィザード"""
        verify_current_platform()  # プラットフォーム検証

        mock_check_prereq.return_value = False

        result = setup_wizard.run()

        assert result is False

    @pytest.mark.unit
    @patch.object(SetupWizard, "welcome_message")
    @patch.object(SetupWizard, "check_prerequisites", side_effect=KeyboardInterrupt())
    def test_run_keyboard_interrupt(self, mock_check_prereq, mock_welcome, setup_wizard, capsys):
        """キーボード割り込み時のセットアップウィザード"""
        verify_current_platform()  # プラットフォーム検証

        result = setup_wizard.run()

        assert result is False
        captured = capsys.readouterr()
        assert "セットアップが中断されました" in captured.out

    @pytest.mark.unit
    @patch.object(SetupWizard, "welcome_message")
    @patch.object(SetupWizard, "check_prerequisites", side_effect=Exception("Test error"))
    def test_run_unexpected_error(self, mock_check_prereq, mock_welcome, setup_wizard, capsys):
        """予期しないエラー時のセットアップウィザード"""
        verify_current_platform()  # プラットフォーム検証

        result = setup_wizard.run()

        assert result is False
        captured = capsys.readouterr()
        assert "予期しないエラーが発生しました" in captured.out
