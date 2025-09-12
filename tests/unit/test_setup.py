"""
初期セットアップ機能のテスト
"""

import json
from unittest.mock import Mock, patch

import pytest

from setup_repo.setup import (
    create_personal_config,
    run_interactive_setup,
    setup_dependencies,
    setup_repository_environment,
)


class TestSetupDependencies:
    """setup_dependencies関数のテスト"""

    @patch("setup_repo.setup.SetupWizard")
    def test_setup_dependencies_success(self, mock_wizard_class):
        """依存関係セットアップ成功のテスト"""
        # Arrange
        mock_wizard = Mock()
        mock_wizard.check_prerequisites.return_value = True
        mock_wizard_class.return_value = mock_wizard

        # Act
        result = setup_dependencies()

        # Assert
        assert result is True
        mock_wizard.check_prerequisites.assert_called_once()

    @patch("setup_repo.setup.SetupWizard")
    def test_setup_dependencies_failure(self, mock_wizard_class):
        """依存関係セットアップ失敗のテスト"""
        # Arrange
        mock_wizard = Mock()
        mock_wizard.check_prerequisites.return_value = False
        mock_wizard_class.return_value = mock_wizard

        # Act
        result = setup_dependencies()

        # Assert
        assert result is False
        mock_wizard.check_prerequisites.assert_called_once()


class TestCreatePersonalConfig:
    """create_personal_config関数のテスト"""

    @patch("setup_repo.setup.SetupWizard")
    @patch("pathlib.Path.exists")
    @patch("builtins.print")
    def test_create_personal_config_existing_file(self, mock_print, mock_exists, mock_wizard_class):
        """既存の設定ファイルがある場合のテスト"""
        # Arrange
        mock_exists.return_value = True

        # Act
        create_personal_config()

        # Assert
        mock_print.assert_called_with("✅ config.local.json は既に存在します")
        mock_wizard_class.assert_not_called()

    @patch("setup_repo.setup.SetupWizard")
    @patch("pathlib.Path.exists")
    def test_create_personal_config_new_file(self, mock_exists, mock_wizard_class):
        """新規設定ファイル作成のテスト"""
        # Arrange
        mock_exists.return_value = False
        mock_wizard = Mock()
        mock_wizard_class.return_value = mock_wizard

        # Act
        create_personal_config()

        # Assert
        mock_wizard.run.assert_called_once()


class TestRunInteractiveSetup:
    """run_interactive_setup関数のテスト"""

    @patch("setup_repo.setup.SetupWizard")
    def test_run_interactive_setup_success(self, mock_wizard_class):
        """インタラクティブセットアップ成功のテスト"""
        # Arrange
        mock_wizard = Mock()
        mock_wizard.run.return_value = True
        mock_wizard_class.return_value = mock_wizard

        # Act
        result = run_interactive_setup()

        # Assert
        assert result is True
        mock_wizard.run.assert_called_once()

    @patch("setup_repo.setup.SetupWizard")
    def test_run_interactive_setup_failure(self, mock_wizard_class):
        """インタラクティブセットアップ失敗のテスト"""
        # Arrange
        mock_wizard = Mock()
        mock_wizard.run.return_value = False
        mock_wizard_class.return_value = mock_wizard

        # Act
        result = run_interactive_setup()

        # Assert
        assert result is False
        mock_wizard.run.assert_called_once()


class TestSetupRepositoryEnvironment:
    """setup_repository_environment関数のテスト"""

    @patch("setup_repo.setup.GitHubAPI")
    @patch("setup_repo.setup.PlatformDetector")
    @patch("setup_repo.setup.load_config")
    def test_setup_repository_environment_success(
        self, mock_load_config, mock_platform_detector_class, mock_github_api_class
    ):
        """リポジトリ環境セットアップ成功のテスト"""
        # Arrange
        config = {
            "github_token": "test_token",
            "github_username": "test_user",
            "clone_destination": "/test/repos",
        }
        mock_load_config.return_value = config

        mock_platform_detector = Mock()
        mock_platform_detector.detect_platform.return_value = "linux"
        mock_platform_detector_class.return_value = mock_platform_detector

        mock_github_api = Mock()
        mock_github_api.get_user_info.return_value = {"login": "test_user", "id": 123}
        mock_github_api_class.return_value = mock_github_api

        with patch("pathlib.Path.mkdir") as mock_mkdir:
            # Act
            result = setup_repository_environment()

            # Assert
            assert result["success"] is True
            assert result["config"] == config
            assert result["platform"] == "linux"
            assert result["github_user_info"]["login"] == "test_user"
            assert result["dry_run"] is False
            mock_mkdir.assert_called_once()

    @patch("setup_repo.setup.load_config")
    def test_setup_repository_environment_missing_token(self, mock_load_config):
        """GitHubトークンが不足している場合のテスト"""
        # Arrange
        config = {
            "github_username": "test_user"
            # github_tokenが不足
        }
        mock_load_config.return_value = config

        # Act & Assert
        with pytest.raises(ValueError, match="必須フィールドが不足しています: github_token"):
            setup_repository_environment()

    @patch("setup_repo.setup.load_config")
    def test_setup_repository_environment_missing_username(self, mock_load_config):
        """GitHubユーザー名が不足している場合のテスト"""
        # Arrange
        config = {
            "github_token": "test_token"
            # github_usernameが不足
        }
        mock_load_config.return_value = config

        # Act & Assert
        with pytest.raises(ValueError, match="必須フィールドが不足しています: github_username"):
            setup_repository_environment()

    @patch("setup_repo.setup.GitHubAPI")
    @patch("setup_repo.setup.PlatformDetector")
    @patch("setup_repo.setup.load_config")
    def test_setup_repository_environment_dry_run(
        self, mock_load_config, mock_platform_detector_class, mock_github_api_class
    ):
        """ドライランモードのテスト"""
        # Arrange
        config = {
            "github_token": "test_token",
            "github_username": "test_user",
            "clone_destination": "/test/repos",
        }
        mock_load_config.return_value = config

        mock_platform_detector = Mock()
        mock_platform_detector.detect_platform.return_value = "linux"
        mock_platform_detector_class.return_value = mock_platform_detector

        mock_github_api = Mock()
        mock_github_api.get_user_info.return_value = {"login": "test_user", "id": 123}
        mock_github_api_class.return_value = mock_github_api

        with patch("pathlib.Path.mkdir") as mock_mkdir:
            # Act
            result = setup_repository_environment(dry_run=True)

            # Assert
            assert result["success"] is True
            assert result["dry_run"] is True
            mock_mkdir.assert_not_called()  # ドライランではディレクトリ作成しない

    @patch("builtins.open")
    def test_setup_repository_environment_custom_config_path(self, mock_open):
        """カスタム設定パスのテスト"""
        # Arrange
        config = {"github_token": "test_token", "github_username": "test_user"}
        mock_file = Mock()
        mock_file.read.return_value = json.dumps(config)
        mock_open.return_value.__enter__.return_value = mock_file

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("setup_repo.setup.PlatformDetector") as mock_platform_detector_class,
            patch("setup_repo.setup.GitHubAPI") as mock_github_api_class,
        ):
            mock_platform_detector = Mock()
            mock_platform_detector.detect_platform.return_value = "linux"
            mock_platform_detector_class.return_value = mock_platform_detector

            mock_github_api = Mock()
            mock_github_api.get_user_info.return_value = {
                "login": "test_user",
                "id": 123,
            }
            mock_github_api_class.return_value = mock_github_api

            # Act
            result = setup_repository_environment(config_path="/custom/config.json")

            # Assert
            assert result["success"] is True
            assert result["config"] == config

    def test_setup_repository_environment_config_file_not_found(self):
        """設定ファイルが見つからない場合のテスト"""
        # Act & Assert
        with pytest.raises(FileNotFoundError, match="設定ファイルが見つかりません"):
            setup_repository_environment(config_path="/nonexistent/config.json")

    @patch("setup_repo.setup.GitHubAPI")
    @patch("setup_repo.setup.PlatformDetector")
    @patch("setup_repo.setup.load_config")
    def test_setup_repository_environment_platform_error(
        self, mock_load_config, mock_platform_detector_class, mock_github_api_class
    ):
        """プラットフォーム検出エラーのテスト"""
        # Arrange
        config = {"github_token": "test_token", "github_username": "test_user"}
        mock_load_config.return_value = config

        mock_platform_detector = Mock()
        mock_platform_detector.detect_platform.side_effect = Exception("Platform detection failed")
        mock_platform_detector_class.return_value = mock_platform_detector

        # Act & Assert
        with pytest.raises(Exception, match="Platform detection failed"):
            setup_repository_environment()

    @patch("setup_repo.setup.GitHubAPI")
    @patch("setup_repo.setup.PlatformDetector")
    @patch("setup_repo.setup.load_config")
    def test_setup_repository_environment_github_api_error(
        self, mock_load_config, mock_platform_detector_class, mock_github_api_class
    ):
        """GitHub API エラーのテスト"""
        # Arrange
        config = {"github_token": "invalid_token", "github_username": "test_user"}
        mock_load_config.return_value = config

        mock_platform_detector = Mock()
        mock_platform_detector.detect_platform.return_value = "linux"
        mock_platform_detector_class.return_value = mock_platform_detector

        mock_github_api = Mock()
        mock_github_api.get_user_info.side_effect = Exception("API Error")
        mock_github_api_class.return_value = mock_github_api

        # Act & Assert
        with pytest.raises(Exception, match="API Error"):
            setup_repository_environment()

    @patch("setup_repo.setup.GitHubAPI")
    @patch("setup_repo.setup.PlatformDetector")
    @patch("setup_repo.setup.load_config")
    def test_setup_repository_environment_no_clone_destination(
        self, mock_load_config, mock_platform_detector_class, mock_github_api_class
    ):
        """クローン先ディレクトリが設定されていない場合のテスト"""
        # Arrange
        config = {
            "github_token": "test_token",
            "github_username": "test_user",
            # clone_destinationなし
        }
        mock_load_config.return_value = config

        mock_platform_detector = Mock()
        mock_platform_detector.detect_platform.return_value = "linux"
        mock_platform_detector_class.return_value = mock_platform_detector

        mock_github_api = Mock()
        mock_github_api.get_user_info.return_value = {"login": "test_user", "id": 123}
        mock_github_api_class.return_value = mock_github_api

        with patch("pathlib.Path.mkdir") as mock_mkdir:
            # Act
            result = setup_repository_environment()

            # Assert
            assert result["success"] is True
            # clone_destinationがないのでディレクトリ作成しない
            mock_mkdir.assert_not_called()


class TestEdgeCases:
    """エッジケースのテスト"""

    @patch("builtins.open")
    def test_setup_repository_environment_invalid_json(self, mock_open):
        """無効なJSONファイルのテスト"""
        # Arrange
        mock_file = Mock()
        mock_file.read.return_value = "invalid json"
        mock_open.return_value.__enter__.return_value = mock_file

        with (
            patch("pathlib.Path.exists", return_value=True),
            pytest.raises(json.JSONDecodeError),
        ):
            # Act & Assert
            setup_repository_environment(config_path="/invalid/config.json")

    @patch("setup_repo.setup.GitHubAPI")
    @patch("setup_repo.setup.PlatformDetector")
    @patch("setup_repo.setup.load_config")
    def test_setup_repository_environment_empty_config_values(
        self, mock_load_config, mock_platform_detector_class, mock_github_api_class
    ):
        """空の設定値のテスト"""
        # Arrange
        config = {
            "github_token": "",  # 空文字
            "github_username": "test_user",
        }
        mock_load_config.return_value = config

        # Act & Assert
        with pytest.raises(ValueError, match="必須フィールドが不足しています: github_token"):
            setup_repository_environment()

    @patch("setup_repo.setup.GitHubAPI")
    @patch("setup_repo.setup.PlatformDetector")
    @patch("setup_repo.setup.load_config")
    def test_setup_repository_environment_none_config_values(
        self, mock_load_config, mock_platform_detector_class, mock_github_api_class
    ):
        """None値の設定のテスト"""
        # Arrange
        config = {
            "github_token": None,  # None値
            "github_username": "test_user",
        }
        mock_load_config.return_value = config

        # Act & Assert
        with pytest.raises(ValueError, match="必須フィールドが不足しています: github_token"):
            setup_repository_environment()

    @patch("setup_repo.setup.GitHubAPI")
    @patch("setup_repo.setup.PlatformDetector")
    @patch("setup_repo.setup.load_config")
    def test_setup_repository_environment_mkdir_error(
        self, mock_load_config, mock_platform_detector_class, mock_github_api_class
    ):
        """ディレクトリ作成エラーのテスト"""
        # Arrange
        config = {
            "github_token": "test_token",
            "github_username": "test_user",
            "clone_destination": "/test/repos",
        }
        mock_load_config.return_value = config

        mock_platform_detector = Mock()
        mock_platform_detector.detect_platform.return_value = "linux"
        mock_platform_detector_class.return_value = mock_platform_detector

        mock_github_api = Mock()
        mock_github_api.get_user_info.return_value = {"login": "test_user", "id": 123}
        mock_github_api_class.return_value = mock_github_api

        with (
            patch("pathlib.Path.mkdir", side_effect=OSError("Permission denied")),
            pytest.raises(OSError, match="Permission denied"),
        ):
            # Act & Assert
            setup_repository_environment()


class TestSetupRepositoryEnvironmentAdvanced:
    """setup_repository_environment関数の高度なテスト"""

    @patch("setup_repo.setup.GitHubAPI")
    @patch("setup_repo.setup.PlatformDetector")
    @patch("setup_repo.setup.load_config")
    def test_setup_repository_environment_partial_config(
        self, mock_load_config, mock_platform_detector_class, mock_github_api_class
    ):
        """部分的な設定でのテスト"""
        # Arrange
        config = {
            "github_token": "test_token",
            "github_username": "test_user",
            # clone_destinationなし、その他のオプション設定もなし
        }
        mock_load_config.return_value = config

        mock_platform_detector = Mock()
        mock_platform_detector.detect_platform.return_value = "windows"
        mock_platform_detector_class.return_value = mock_platform_detector

        mock_github_api = Mock()
        mock_github_api.get_user_info.return_value = {
            "login": "test_user",
            "id": 123,
            "name": "Test User",
        }
        mock_github_api_class.return_value = mock_github_api

        # Act
        result = setup_repository_environment()

        # Assert
        assert result["success"] is True
        assert result["config"] == config
        assert result["platform"] == "windows"
        assert result["github_user_info"]["name"] == "Test User"

    @patch("setup_repo.setup.GitHubAPI")
    @patch("setup_repo.setup.PlatformDetector")
    @patch("setup_repo.setup.load_config")
    def test_setup_repository_environment_github_api_initialization_error(
        self, mock_load_config, mock_platform_detector_class, mock_github_api_class
    ):
        """GitHub API初期化エラーのテスト"""
        # Arrange
        config = {"github_token": "test_token", "github_username": "test_user"}
        mock_load_config.return_value = config

        mock_platform_detector = Mock()
        mock_platform_detector.detect_platform.return_value = "linux"
        mock_platform_detector_class.return_value = mock_platform_detector

        # GitHub API初期化時にエラー
        mock_github_api_class.side_effect = Exception("GitHub API initialization failed")

        # Act & Assert
        with pytest.raises(Exception, match="GitHub API initialization failed"):
            setup_repository_environment()

    @patch("setup_repo.setup.GitHubAPI")
    @patch("setup_repo.setup.PlatformDetector")
    @patch("setup_repo.setup.load_config")
    def test_setup_repository_environment_result_structure(
        self, mock_load_config, mock_platform_detector_class, mock_github_api_class
    ):
        """結果構造の詳細テスト"""
        # Arrange
        config = {
            "github_token": "test_token",
            "github_username": "test_user",
            "clone_destination": "/test/repos",
        }
        mock_load_config.return_value = config

        mock_platform_detector = Mock()
        mock_platform_detector.detect_platform.return_value = "macos"
        mock_platform_detector_class.return_value = mock_platform_detector

        mock_github_api = Mock()
        user_info = {
            "login": "test_user",
            "id": 123,
            "name": "Test User",
            "email": "test@example.com",
            "public_repos": 10,
        }
        mock_github_api.get_user_info.return_value = user_info
        mock_github_api_class.return_value = mock_github_api

        with patch("pathlib.Path.mkdir"):
            # Act
            result = setup_repository_environment()

            # Assert
            assert "config" in result
            assert "platform" in result
            assert "github_user_info" in result
            assert "dry_run" in result
            assert "success" in result

            assert result["config"] == config
            assert result["platform"] == "macos"
            assert result["github_user_info"] == user_info
            assert result["dry_run"] is False
            assert result["success"] is True

    @patch("builtins.open")
    def test_setup_repository_environment_custom_config_json_error(self, mock_open):
        """カスタム設定ファイルのJSON解析エラーのテスト"""
        # Arrange
        mock_file = Mock()
        mock_file.read.side_effect = json.JSONDecodeError("Invalid JSON", "test", 0)
        mock_open.return_value.__enter__.return_value = mock_file

        with (
            patch("pathlib.Path.exists", return_value=True),
            pytest.raises(json.JSONDecodeError),
        ):
            # Act & Assert
            setup_repository_environment(config_path="/invalid/config.json")

    @patch("builtins.open")
    def test_setup_repository_environment_custom_config_file_read_error(self, mock_open):
        """カスタム設定ファイル読み込みエラーのテスト"""
        # Arrange
        mock_open.side_effect = OSError("Permission denied")

        with (
            patch("pathlib.Path.exists", return_value=True),
            pytest.raises(IOError, match="Permission denied"),
        ):
            # Act & Assert
            setup_repository_environment(config_path="/restricted/config.json")

    @patch("setup_repo.setup.GitHubAPI")
    @patch("setup_repo.setup.PlatformDetector")
    @patch("setup_repo.setup.load_config")
    def test_setup_repository_environment_all_required_fields_validation(
        self, mock_load_config, mock_platform_detector_class, mock_github_api_class
    ):
        """全必須フィールドの検証テスト"""
        # github_tokenとgithub_usernameの両方が不足
        config = {}
        mock_load_config.return_value = config

        # Act & Assert
        with pytest.raises(ValueError, match="必須フィールドが不足しています: github_token"):
            setup_repository_environment()

    @patch("setup_repo.setup.GitHubAPI")
    @patch("setup_repo.setup.PlatformDetector")
    @patch("setup_repo.setup.load_config")
    def test_setup_repository_environment_error_handling_with_result(
        self, mock_load_config, mock_platform_detector_class, mock_github_api_class
    ):
        """エラー時の結果構造テスト"""
        # Arrange
        config = {"github_token": "test_token", "github_username": "test_user"}
        mock_load_config.return_value = config

        mock_platform_detector = Mock()
        mock_platform_detector.detect_platform.return_value = "linux"
        mock_platform_detector_class.return_value = mock_platform_detector

        # GitHub APIでエラー発生
        mock_github_api = Mock()
        mock_github_api.get_user_info.side_effect = Exception("API Error")
        mock_github_api_class.return_value = mock_github_api

        # Act & Assert
        try:
            setup_repository_environment()
            raise AssertionError("例外が発生するはずです")
        except Exception as e:
            assert str(e) == "API Error"

    @patch("setup_repo.setup.GitHubAPI")
    @patch("setup_repo.setup.PlatformDetector")
    @patch("setup_repo.setup.load_config")
    def test_setup_repository_environment_clone_destination_creation_success(
        self, mock_load_config, mock_platform_detector_class, mock_github_api_class
    ):
        """クローン先ディレクトリ作成成功のテスト"""
        # Arrange
        config = {
            "github_token": "test_token",
            "github_username": "test_user",
            "clone_destination": "/test/new/repos",
        }
        mock_load_config.return_value = config

        mock_platform_detector = Mock()
        mock_platform_detector.detect_platform.return_value = "linux"
        mock_platform_detector_class.return_value = mock_platform_detector

        mock_github_api = Mock()
        mock_github_api.get_user_info.return_value = {"login": "test_user", "id": 123}
        mock_github_api_class.return_value = mock_github_api

        with patch("pathlib.Path.mkdir") as mock_mkdir:
            # Act
            result = setup_repository_environment()

            # Assert
            assert result["success"] is True
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)


class TestSetupFunctionsEdgeCases:
    """セットアップ関数のエッジケースのテスト"""

    @patch("setup_repo.setup.SetupWizard")
    def test_setup_dependencies_wizard_exception(self, mock_wizard_class):
        """SetupWizardで例外が発生した場合のテスト"""
        # Arrange
        mock_wizard = Mock()
        mock_wizard.check_prerequisites.side_effect = Exception("Wizard error")
        mock_wizard_class.return_value = mock_wizard

        # Act & Assert
        with pytest.raises(Exception, match="Wizard error"):
            setup_dependencies()

    @patch("setup_repo.setup.SetupWizard")
    @patch("pathlib.Path.exists")
    @patch("builtins.print")
    def test_create_personal_config_wizard_exception(self, mock_print, mock_exists, mock_wizard_class):
        """create_personal_configでSetupWizardが例外を発生させた場合のテスト"""
        # Arrange
        mock_exists.return_value = False
        mock_wizard = Mock()
        mock_wizard.run.side_effect = Exception("Wizard run error")
        mock_wizard_class.return_value = mock_wizard

        # Act & Assert
        with pytest.raises(Exception, match="Wizard run error"):
            create_personal_config()

    @patch("setup_repo.setup.SetupWizard")
    def test_run_interactive_setup_wizard_exception(self, mock_wizard_class):
        """run_interactive_setupでSetupWizardが例外を発生させた場合のテスト"""
        # Arrange
        mock_wizard = Mock()
        mock_wizard.run.side_effect = Exception("Interactive setup error")
        mock_wizard_class.return_value = mock_wizard

        # Act & Assert
        with pytest.raises(Exception, match="Interactive setup error"):
            run_interactive_setup()

    @patch("setup_repo.setup.SetupWizard")
    @patch("pathlib.Path.exists")
    def test_create_personal_config_path_operations(self, mock_exists, mock_wizard_class):
        """create_personal_configのパス操作テスト"""
        # Arrange
        mock_exists.return_value = False
        mock_wizard = Mock()
        mock_wizard.run.return_value = True
        mock_wizard_class.return_value = mock_wizard

        # Act
        create_personal_config()

        # Assert
        mock_exists.assert_called_once()
        mock_wizard.run.assert_called_once()

    @patch("setup_repo.setup.GitHubAPI")
    @patch("setup_repo.setup.PlatformDetector")
    @patch("builtins.open")
    def test_setup_repository_environment_custom_config_empty_file(
        self, mock_open, mock_platform_detector_class, mock_github_api_class
    ):
        """空の設定ファイルのテスト"""
        # Arrange
        mock_file = Mock()
        mock_file.read.return_value = "{}"  # 空のJSON
        mock_open.return_value.__enter__.return_value = mock_file

        with (
            patch("pathlib.Path.exists", return_value=True),
            pytest.raises(ValueError, match="必須フィールドが不足しています"),
        ):
            # Act & Assert
            setup_repository_environment(config_path="/empty/config.json")

    @patch("setup_repo.setup.GitHubAPI")
    @patch("setup_repo.setup.PlatformDetector")
    @patch("setup_repo.setup.load_config")
    def test_setup_repository_environment_boolean_dry_run_validation(
        self, mock_load_config, mock_platform_detector_class, mock_github_api_class
    ):
        """dry_runパラメータのブール値検証テスト"""
        # Arrange
        config = {"github_token": "test_token", "github_username": "test_user"}
        mock_load_config.return_value = config

        mock_platform_detector = Mock()
        mock_platform_detector.detect_platform.return_value = "linux"
        mock_platform_detector_class.return_value = mock_platform_detector

        mock_github_api = Mock()
        mock_github_api.get_user_info.return_value = {"login": "test_user", "id": 123}
        mock_github_api_class.return_value = mock_github_api

        # Act - dry_run=Trueの場合
        result_dry = setup_repository_environment(dry_run=True)

        # Act - dry_run=Falseの場合
        with patch("pathlib.Path.mkdir"):
            result_normal = setup_repository_environment(dry_run=False)

        # Assert
        assert result_dry["dry_run"] is True
        assert result_normal["dry_run"] is False
