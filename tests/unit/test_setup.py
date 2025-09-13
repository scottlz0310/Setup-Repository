"""セットアップ機能のテスト"""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from ..multiplatform.helpers import verify_current_platform, skip_if_not_platform

from src.setup_repo.setup import (
    setup_dependencies,
    create_personal_config,
    run_interactive_setup,
    setup_repository_environment
)


class TestSetupDependencies:
    """setup_dependencies関数のテスト"""

    @pytest.mark.unit
    @patch('src.setup_repo.setup.SetupWizard')
    def test_setup_dependencies_success(self, mock_wizard_class):
        """依存関係セットアップ成功テスト"""
        platform_info = verify_current_platform()
        
        mock_wizard = Mock()
        mock_wizard.check_prerequisites.return_value = True
        mock_wizard_class.return_value = mock_wizard
        
        result = setup_dependencies()
        
        assert result is True
        mock_wizard.check_prerequisites.assert_called_once()

    @pytest.mark.unit
    @patch('src.setup_repo.setup.SetupWizard')
    def test_setup_dependencies_failure(self, mock_wizard_class):
        """依存関係セットアップ失敗テスト"""
        platform_info = verify_current_platform()
        
        mock_wizard = Mock()
        mock_wizard.check_prerequisites.return_value = False
        mock_wizard_class.return_value = mock_wizard
        
        result = setup_dependencies()
        
        assert result is False


class TestCreatePersonalConfig:
    """create_personal_config関数のテスト"""

    @pytest.mark.unit
    @patch('pathlib.Path.exists')
    def test_create_personal_config_already_exists(self, mock_exists, capsys):
        """設定ファイルが既に存在する場合"""
        platform_info = verify_current_platform()
        
        mock_exists.return_value = True
        
        create_personal_config()
        
        captured = capsys.readouterr()
        assert "config.local.json は既に存在します" in captured.out

    @pytest.mark.unit
    @patch('pathlib.Path.exists')
    @patch('src.setup_repo.setup.SetupWizard')
    def test_create_personal_config_new_file(self, mock_wizard_class, mock_exists):
        """新規設定ファイル作成の場合"""
        platform_info = verify_current_platform()
        
        mock_exists.return_value = False
        mock_wizard = Mock()
        mock_wizard.run.return_value = True
        mock_wizard_class.return_value = mock_wizard
        
        create_personal_config()
        
        mock_wizard.run.assert_called_once()


class TestRunInteractiveSetup:
    """run_interactive_setup関数のテスト"""

    @pytest.mark.unit
    @patch('src.setup_repo.setup.SetupWizard')
    def test_run_interactive_setup_success(self, mock_wizard_class):
        """インタラクティブセットアップ成功テスト"""
        platform_info = verify_current_platform()
        
        mock_wizard = Mock()
        mock_wizard.run.return_value = True
        mock_wizard_class.return_value = mock_wizard
        
        result = run_interactive_setup()
        
        assert result is True
        mock_wizard.run.assert_called_once()

    @pytest.mark.unit
    @patch('src.setup_repo.setup.SetupWizard')
    def test_run_interactive_setup_failure(self, mock_wizard_class):
        """インタラクティブセットアップ失敗テスト"""
        platform_info = verify_current_platform()
        
        mock_wizard = Mock()
        mock_wizard.run.return_value = False
        mock_wizard_class.return_value = mock_wizard
        
        result = run_interactive_setup()
        
        assert result is False


class TestSetupRepositoryEnvironment:
    """setup_repository_environment関数のテスト"""

    @pytest.fixture
    def mock_config(self):
        """モック設定データ"""
        return {
            "github_token": "test_token",
            "github_username": "test_user",
            "clone_destination": "/test/path"
        }

    @pytest.mark.unit
    @patch('src.setup_repo.setup.load_config')
    @patch('src.setup_repo.setup.PlatformDetector')
    @patch('src.setup_repo.setup.GitHubAPI')
    def test_setup_repository_environment_success(self, mock_github_api_class, 
                                                 mock_platform_detector_class, 
                                                 mock_load_config, mock_config):
        """リポジトリ環境セットアップ成功テスト"""
        platform_info = verify_current_platform()
        
        # モック設定
        mock_load_config.return_value = mock_config
        
        mock_platform_detector = Mock()
        mock_platform = Mock()
        mock_platform_detector.detect_platform.return_value = mock_platform
        mock_platform_detector_class.return_value = mock_platform_detector
        
        mock_github_api = Mock()
        mock_user_info = {"login": "test_user", "id": 12345}
        mock_github_api.get_user_info.return_value = mock_user_info
        mock_github_api_class.return_value = mock_github_api
        
        result = setup_repository_environment()
        
        assert result["success"] is True
        assert result["config"] == mock_config
        assert result["platform"] == mock_platform
        assert result["github_user_info"] == mock_user_info
        assert result["dry_run"] is False

    @pytest.mark.unit
    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.exists')
    @patch('src.setup_repo.setup.PlatformDetector')
    @patch('src.setup_repo.setup.GitHubAPI')
    def test_setup_repository_environment_custom_config(self, mock_github_api_class,
                                                        mock_platform_detector_class,
                                                        mock_exists, mock_file, mock_config):
        """カスタム設定ファイルでのセットアップテスト"""
        platform_info = verify_current_platform()
        
        # カスタム設定ファイルの存在をモック
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = json.dumps(mock_config)
        
        # その他のモック設定
        mock_platform_detector = Mock()
        mock_platform_detector.detect_platform.return_value = Mock()
        mock_platform_detector_class.return_value = mock_platform_detector
        
        mock_github_api = Mock()
        mock_github_api.get_user_info.return_value = {"login": "test_user"}
        mock_github_api_class.return_value = mock_github_api
        
        result = setup_repository_environment(config_path="custom_config.json")
        
        assert result["success"] is True
        assert result["config"] == mock_config

    @pytest.mark.unit
    def test_setup_repository_environment_config_file_not_found(self):
        """設定ファイルが見つからない場合"""
        platform_info = verify_current_platform()
        
        with pytest.raises(FileNotFoundError, match="設定ファイルが見つかりません"):
            setup_repository_environment(config_path="nonexistent.json")

    @pytest.mark.unit
    @patch('src.setup_repo.setup.load_config')
    def test_setup_repository_environment_missing_required_field(self, mock_load_config):
        """必須フィールドが不足している場合"""
        platform_info = verify_current_platform()
        
        # github_tokenが不足している設定
        incomplete_config = {
            "github_username": "test_user"
        }
        mock_load_config.return_value = incomplete_config
        
        with pytest.raises(ValueError, match="必須フィールドが不足しています: github_token"):
            setup_repository_environment()

    @pytest.mark.unit
    @patch('src.setup_repo.setup.load_config')
    @patch('src.setup_repo.setup.PlatformDetector')
    @patch('src.setup_repo.setup.GitHubAPI')
    @patch('pathlib.Path.mkdir')
    def test_setup_repository_environment_dry_run(self, mock_mkdir, mock_github_api_class,
                                                 mock_platform_detector_class, 
                                                 mock_load_config, mock_config):
        """ドライランモードでのセットアップテスト"""
        platform_info = verify_current_platform()
        
        # モック設定
        mock_load_config.return_value = mock_config
        
        mock_platform_detector = Mock()
        mock_platform_detector.detect_platform.return_value = Mock()
        mock_platform_detector_class.return_value = mock_platform_detector
        
        mock_github_api = Mock()
        mock_github_api.get_user_info.return_value = {"login": "test_user"}
        mock_github_api_class.return_value = mock_github_api
        
        result = setup_repository_environment(dry_run=True)
        
        assert result["success"] is True
        assert result["dry_run"] is True
        # ドライランモードではディレクトリ作成が実行されない
        mock_mkdir.assert_not_called()

    @pytest.mark.unit
    @patch('src.setup_repo.setup.load_config')
    @patch('src.setup_repo.setup.PlatformDetector')
    @patch('src.setup_repo.setup.GitHubAPI')
    @patch('pathlib.Path.mkdir')
    def test_setup_repository_environment_create_directory(self, mock_mkdir, 
                                                          mock_github_api_class,
                                                          mock_platform_detector_class,
                                                          mock_load_config, mock_config):
        """ディレクトリ作成を含むセットアップテスト"""
        platform_info = verify_current_platform()
        
        # モック設定
        mock_load_config.return_value = mock_config
        
        mock_platform_detector = Mock()
        mock_platform_detector.detect_platform.return_value = Mock()
        mock_platform_detector_class.return_value = mock_platform_detector
        
        mock_github_api = Mock()
        mock_github_api.get_user_info.return_value = {"login": "test_user"}
        mock_github_api_class.return_value = mock_github_api
        
        result = setup_repository_environment()
        
        assert result["success"] is True
        # ディレクトリ作成が実行されることを確認
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @pytest.mark.unit
    @patch('src.setup_repo.setup.load_config')
    @patch('src.setup_repo.setup.PlatformDetector')
    def test_setup_repository_environment_platform_error(self, mock_platform_detector_class,
                                                         mock_load_config, mock_config):
        """プラットフォーム検出エラーの場合"""
        platform_info = verify_current_platform()
        
        mock_load_config.return_value = mock_config
        
        mock_platform_detector = Mock()
        mock_platform_detector.detect_platform.side_effect = Exception("Platform detection failed")
        mock_platform_detector_class.return_value = mock_platform_detector
        
        with pytest.raises(Exception, match="Platform detection failed"):
            setup_repository_environment()

    @pytest.mark.unit
    @patch('src.setup_repo.setup.load_config')
    @patch('src.setup_repo.setup.PlatformDetector')
    @patch('src.setup_repo.setup.GitHubAPI')
    def test_setup_repository_environment_github_error(self, mock_github_api_class,
                                                       mock_platform_detector_class,
                                                       mock_load_config, mock_config):
        """GitHub API エラーの場合"""
        platform_info = verify_current_platform()
        
        mock_load_config.return_value = mock_config
        
        mock_platform_detector = Mock()
        mock_platform_detector.detect_platform.return_value = Mock()
        mock_platform_detector_class.return_value = mock_platform_detector
        
        mock_github_api = Mock()
        mock_github_api.get_user_info.side_effect = Exception("GitHub API error")
        mock_github_api_class.return_value = mock_github_api
        
        with pytest.raises(Exception, match="GitHub API error"):
            setup_repository_environment()

    @pytest.mark.unit
    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.exists')
    def test_setup_repository_environment_invalid_json(self, mock_exists, mock_file):
        """無効なJSON設定ファイルの場合"""
        platform_info = verify_current_platform()
        
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = "invalid json"
        
        with pytest.raises(json.JSONDecodeError):
            setup_repository_environment(config_path="invalid.json")


class TestSetupIntegration:
    """セットアップ機能の統合テスト"""

    @pytest.mark.unit
    @patch('src.setup_repo.setup.SetupWizard')
    def test_full_setup_workflow(self, mock_wizard_class):
        """完全なセットアップワークフローテスト"""
        platform_info = verify_current_platform()
        
        mock_wizard = Mock()
        mock_wizard.check_prerequisites.return_value = True
        mock_wizard.run.return_value = True
        mock_wizard_class.return_value = mock_wizard
        
        # 依存関係チェック
        deps_result = setup_dependencies()
        assert deps_result is True
        
        # インタラクティブセットアップ
        setup_result = run_interactive_setup()
        assert setup_result is True

    @pytest.mark.unit
    def test_error_handling_robustness(self):
        """エラーハンドリングの堅牢性テスト"""
        platform_info = verify_current_platform()
        
        # 存在しない設定ファイルでのエラー
        with pytest.raises(FileNotFoundError):
            setup_repository_environment(config_path="nonexistent.json")
        
        # 不正な設定でのエラー
        with pytest.raises(ValueError):
            # load_configをモックして不正な設定を返す
            with patch('src.setup_repo.setup.load_config', return_value={}):
                setup_repository_environment()

    @pytest.mark.unit
    @patch('pathlib.Path.exists')
    def test_config_file_handling(self, mock_exists):
        """設定ファイル処理のテスト"""
        platform_info = verify_current_platform()
        
        # 既存ファイルの場合
        mock_exists.return_value = True
        create_personal_config()  # 例外が発生しないことを確認
        
        # 新規ファイルの場合
        mock_exists.return_value = False
        with patch('src.setup_repo.setup.SetupWizard') as mock_wizard_class:
            mock_wizard = Mock()
            mock_wizard.run.return_value = True
            mock_wizard_class.return_value = mock_wizard
            
            create_personal_config()
            mock_wizard.run.assert_called_once()