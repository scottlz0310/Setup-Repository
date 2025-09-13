"""ログ設定機能のテスト"""

import os
import platform
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from ..multiplatform.helpers import verify_current_platform, skip_if_not_platform

from src.setup_repo.logging_config import (
    LoggingConfig,
    setup_project_logging,
    setup_ci_logging,
    setup_development_logging,
    setup_testing_logging,
    create_platform_specific_error_message,
    get_platform_debug_info
)
from src.setup_repo.quality_logger import LogLevel


class TestLoggingConfig:
    """LoggingConfigのテストクラス"""

    @pytest.mark.unit
    def test_get_log_level_from_env_default(self):
        """デフォルトログレベルの取得"""
        platform_info = verify_current_platform()
        
        with patch.dict(os.environ, {}, clear=True):
            level = LoggingConfig.get_log_level_from_env()
            assert level == LogLevel.INFO

    @pytest.mark.unit
    def test_get_log_level_from_env_debug(self):
        """DEBUG環境変数からのログレベル取得"""
        platform_info = verify_current_platform()
        
        with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}):
            level = LoggingConfig.get_log_level_from_env()
            assert level == LogLevel.DEBUG

    @pytest.mark.unit
    def test_get_log_level_from_env_invalid(self):
        """無効な環境変数からのログレベル取得"""
        platform_info = verify_current_platform()
        
        with patch.dict(os.environ, {"LOG_LEVEL": "INVALID"}):
            level = LoggingConfig.get_log_level_from_env()
            assert level == LogLevel.INFO  # デフォルトにフォールバック

    @pytest.mark.unit
    def test_is_debug_mode_false(self):
        """デバッグモード判定（False）"""
        platform_info = verify_current_platform()
        
        with patch.dict(os.environ, {}, clear=True):
            assert LoggingConfig.is_debug_mode() is False

    @pytest.mark.unit
    def test_is_debug_mode_true_debug_env(self):
        """デバッグモード判定（DEBUG環境変数）"""
        platform_info = verify_current_platform()
        
        with patch.dict(os.environ, {"DEBUG": "true"}):
            assert LoggingConfig.is_debug_mode() is True

    @pytest.mark.unit
    def test_is_debug_mode_true_log_level(self):
        """デバッグモード判定（LOG_LEVEL環境変数）"""
        platform_info = verify_current_platform()
        
        with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}):
            assert LoggingConfig.is_debug_mode() is True

    @pytest.mark.unit
    def test_is_debug_mode_true_ci_debug(self):
        """デバッグモード判定（CI_DEBUG環境変数）"""
        platform_info = verify_current_platform()
        
        with patch.dict(os.environ, {"CI_DEBUG": "1"}):
            assert LoggingConfig.is_debug_mode() is True

    @pytest.mark.unit
    def test_is_ci_environment_false(self):
        """CI環境判定（False）"""
        platform_info = verify_current_platform()
        
        with patch.dict(os.environ, {}, clear=True):
            assert LoggingConfig.is_ci_environment() is False

    @pytest.mark.unit
    def test_is_ci_environment_true_ci(self):
        """CI環境判定（CI環境変数）"""
        platform_info = verify_current_platform()
        
        with patch.dict(os.environ, {"CI": "true"}):
            assert LoggingConfig.is_ci_environment() is True

    @pytest.mark.unit
    def test_is_ci_environment_true_github_actions(self):
        """CI環境判定（GitHub Actions）"""
        platform_info = verify_current_platform()
        
        with patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}):
            assert LoggingConfig.is_ci_environment() is True

    @pytest.mark.unit
    def test_should_use_json_format_false(self):
        """JSON形式判定（False）"""
        platform_info = verify_current_platform()
        
        with patch.dict(os.environ, {}, clear=True):
            assert LoggingConfig.should_use_json_format() is False

    @pytest.mark.unit
    def test_should_use_json_format_true(self):
        """JSON形式判定（True）"""
        platform_info = verify_current_platform()
        
        with patch.dict(os.environ, {"JSON_LOGS": "true"}):
            assert LoggingConfig.should_use_json_format() is True

    @pytest.mark.unit
    def test_get_log_file_path_default(self):
        """デフォルトログファイルパス取得"""
        platform_info = verify_current_platform()
        
        with patch.dict(os.environ, {}, clear=True):
            path = LoggingConfig.get_log_file_path()
            assert path == Path("logs/quality.log")

    @pytest.mark.unit
    def test_get_log_file_path_custom_name(self):
        """カスタム名でのログファイルパス取得"""
        platform_info = verify_current_platform()
        
        with patch.dict(os.environ, {}, clear=True):
            path = LoggingConfig.get_log_file_path("custom")
            assert path == Path("logs/custom.log")

    @pytest.mark.unit
    def test_get_log_file_path_custom_dir(self):
        """カスタムディレクトリでのログファイルパス取得"""
        platform_info = verify_current_platform()
        
        with patch.dict(os.environ, {"LOG_DIR": "/custom/logs"}):
            path = LoggingConfig.get_log_file_path()
            assert path == Path("/custom/logs/quality.log")

    @pytest.mark.unit
    def test_get_log_file_path_ci_environment(self):
        """CI環境でのログファイルパス取得（None）"""
        platform_info = verify_current_platform()
        
        with patch.dict(os.environ, {"CI": "true"}):
            path = LoggingConfig.get_log_file_path()
            assert path is None

    @pytest.mark.unit
    def test_get_log_file_path_ci_with_explicit_file(self):
        """CI環境で明示的にファイル指定した場合"""
        platform_info = verify_current_platform()
        
        with patch.dict(os.environ, {"CI": "true", "CI_LOG_FILE": "true"}):
            path = LoggingConfig.get_log_file_path()
            assert path == Path("logs/quality.log")

    @pytest.mark.unit
    def test_get_log_file_path_error_handling(self):
        """ログファイルパス取得時のエラーハンドリング"""
        platform_info = verify_current_platform()
        
        with patch('pathlib.Path.__truediv__', side_effect=OSError("Path error")):
            with patch('pathlib.Path.cwd', return_value=Path("/current")):
                path = LoggingConfig.get_log_file_path()
                assert path == Path("/current/logs/quality.log")

    @pytest.mark.unit
    @patch('src.setup_repo.logging_config.configure_quality_logging')
    def test_configure_for_environment_default(self, mock_configure):
        """デフォルト環境での設定"""
        platform_info = verify_current_platform()
        
        mock_logger = Mock()
        mock_configure.return_value = mock_logger
        
        with patch.dict(os.environ, {}, clear=True):
            logger = LoggingConfig.configure_for_environment()
            
            mock_configure.assert_called_once()
            args, kwargs = mock_configure.call_args
            assert kwargs['log_level'] == LogLevel.INFO
            assert kwargs['enable_console'] is True
            assert kwargs['enable_json_format'] is False

    @pytest.mark.unit
    @patch('src.setup_repo.logging_config.configure_quality_logging')
    def test_configure_for_environment_debug(self, mock_configure):
        """デバッグ環境での設定"""
        platform_info = verify_current_platform()
        
        mock_logger = Mock()
        mock_configure.return_value = mock_logger
        
        with patch.dict(os.environ, {"DEBUG": "true"}):
            logger = LoggingConfig.configure_for_environment()
            
            args, kwargs = mock_configure.call_args
            assert kwargs['log_level'] == LogLevel.DEBUG

    @pytest.mark.unit
    @patch('src.setup_repo.logging_config.PlatformDetector')
    def test_get_debug_context(self, mock_detector_class):
        """デバッグコンテキスト取得"""
        platform_info = verify_current_platform()
        
        # PlatformDetectorのモック設定
        mock_detector = Mock()
        mock_platform_info = Mock()
        mock_platform_info.name = "windows"
        mock_platform_info.display_name = "Windows"
        mock_platform_info.shell = "powershell"
        mock_platform_info.python_cmd = "python"
        mock_platform_info.package_managers = ["scoop"]
        
        mock_detector.get_platform_info.return_value = mock_platform_info
        mock_detector.diagnose_issues.return_value = {"issues": []}
        mock_detector.get_ci_info.return_value = {"ci": "github"}
        mock_detector_class.return_value = mock_detector
        
        with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG", "CI": "true"}):
            context = LoggingConfig.get_debug_context()
            
            assert context["log_level"] == "DEBUG"
            assert context["debug_mode"] == "True"
            assert context["ci_environment"] == "True"
            assert "platform_info" in context
            assert "system_info" in context

    @pytest.mark.unit
    @patch('src.setup_repo.logging_config.configure_quality_logging')
    def test_setup_project_logging(self, mock_configure):
        """プロジェクトロギング設定"""
        platform_info = verify_current_platform()
        
        mock_logger = Mock()
        mock_configure.return_value = mock_logger
        
        logger = setup_project_logging()
        
        assert logger == mock_logger
        mock_configure.assert_called_once()

    @pytest.mark.unit
    @patch('src.setup_repo.logging_config.configure_quality_logging')
    def test_setup_ci_logging(self, mock_configure):
        """CIロギング設定"""
        platform_info = verify_current_platform()
        
        mock_logger = Mock()
        mock_configure.return_value = mock_logger
        
        logger = setup_ci_logging()
        
        args, kwargs = mock_configure.call_args
        assert kwargs['log_file'] is None
        assert kwargs['enable_console'] is True
        assert kwargs['enable_json_format'] is True

    @pytest.mark.unit
    @patch('src.setup_repo.logging_config.configure_quality_logging')
    def test_setup_development_logging(self, mock_configure):
        """開発環境ロギング設定"""
        platform_info = verify_current_platform()
        
        mock_logger = Mock()
        mock_configure.return_value = mock_logger
        
        logger = setup_development_logging()
        
        args, kwargs = mock_configure.call_args
        assert kwargs['log_level'] == LogLevel.DEBUG
        assert kwargs['log_file'] == Path("logs/development.log")
        assert kwargs['enable_json_format'] is False

    @pytest.mark.unit
    @patch('src.setup_repo.logging_config.configure_quality_logging')
    def test_setup_testing_logging(self, mock_configure):
        """テスト環境ロギング設定"""
        platform_info = verify_current_platform()
        
        mock_logger = Mock()
        mock_configure.return_value = mock_logger
        
        logger = setup_testing_logging()
        
        args, kwargs = mock_configure.call_args
        assert kwargs['log_level'] == LogLevel.WARNING
        assert kwargs['log_file'] is None
        assert kwargs['enable_console'] is False

    @pytest.mark.unit
    @patch('src.setup_repo.logging_config.detect_platform')
    @patch('src.setup_repo.logging_config.check_module_availability')
    def test_create_platform_specific_error_message_windows_fcntl(self, mock_check_module, mock_detect):
        """Windows環境でのfcntlエラーメッセージ"""
        platform_info = verify_current_platform()
        
        mock_platform_info = Mock()
        mock_platform_info.display_name = "Windows"
        mock_platform_info.package_managers = ["scoop"]
        mock_detect.return_value = mock_platform_info
        mock_check_module.return_value = {"available": True}
        
        error = Exception("fcntl module not available")
        message = create_platform_specific_error_message(error, "windows")
        
        assert "Windows環境では fcntl モジュールは利用できません" in message
        assert "msvcrt モジュールを使用してください" in message

    @pytest.mark.unit
    @patch('src.setup_repo.logging_config.detect_platform')
    def test_create_platform_specific_error_message_macos_command_not_found(self, mock_detect):
        """macOS環境でのコマンド未発見エラーメッセージ"""
        platform_info = verify_current_platform()
        
        mock_platform_info = Mock()
        mock_platform_info.display_name = "macOS"
        mock_platform_info.package_managers = ["brew"]
        mock_detect.return_value = mock_platform_info
        
        error = Exception("command not found: uv")
        context = {"missing_tool": "uv"}
        message = create_platform_specific_error_message(error, "macos", context)
        
        assert "Homebrew を使用してツールをインストール" in message
        assert "brew install uv" in message

    @pytest.mark.unit
    @patch('src.setup_repo.logging_config.detect_platform')
    def test_create_platform_specific_error_message_linux_permission(self, mock_detect):
        """Linux環境での権限エラーメッセージ"""
        platform_info = verify_current_platform()
        
        mock_platform_info = Mock()
        mock_platform_info.display_name = "Linux"
        mock_platform_info.package_managers = ["apt"]
        mock_detect.return_value = mock_platform_info
        
        error = Exception("permission denied")
        message = create_platform_specific_error_message(error, "linux")
        
        assert "sudo 権限が必要な場合があります" in message

    @pytest.mark.unit
    @patch('src.setup_repo.logging_config.detect_platform')
    def test_create_platform_specific_error_message_wsl_path(self, mock_detect):
        """WSL環境でのパスエラーメッセージ"""
        platform_info = verify_current_platform()
        
        mock_platform_info = Mock()
        mock_platform_info.display_name = "WSL"
        mock_platform_info.package_managers = ["apt"]
        mock_detect.return_value = mock_platform_info
        
        error = Exception("windows path error")
        message = create_platform_specific_error_message(error, "wsl")
        
        assert "Windows と Linux の両方のパスが混在" in message
        assert "wslpath コマンドでパス変換を確認" in message

    @pytest.mark.unit
    @patch('src.setup_repo.logging_config.detect_platform')
    def test_create_platform_specific_error_message_ci_environment(self, mock_detect):
        """CI環境でのエラーメッセージ"""
        platform_info = verify_current_platform()
        
        mock_platform_info = Mock()
        mock_platform_info.display_name = "Linux"
        mock_platform_info.package_managers = ["apt"]
        mock_detect.return_value = mock_platform_info
        
        with patch.dict(os.environ, {"CI": "true", "GITHUB_ACTIONS": "true"}):
            error = Exception("test error")
            message = create_platform_specific_error_message(error, "linux")
            
            assert "CI環境" in message
            assert "GitHub Actions環境でのトラブルシューティング" in message

    @pytest.mark.unit
    @patch('src.setup_repo.logging_config.detect_platform')
    @patch('src.setup_repo.logging_config.get_available_package_managers')
    def test_get_platform_debug_info(self, mock_get_managers, mock_detect):
        """プラットフォームデバッグ情報取得"""
        platform_info = verify_current_platform()
        
        mock_platform_info = Mock()
        mock_platform_info.name = "windows"
        mock_platform_info.display_name = "Windows"
        mock_platform_info.shell = "powershell"
        mock_platform_info.python_cmd = "python"
        mock_platform_info.package_managers = ["scoop", "winget"]
        
        mock_detect.return_value = mock_platform_info
        mock_get_managers.return_value = ["scoop"]
        
        debug_info = get_platform_debug_info()
        
        assert debug_info["platform"]["name"] == "windows"
        assert debug_info["platform"]["display_name"] == "Windows"
        assert debug_info["platform"]["available_package_managers"] == ["scoop"]
        assert "system" in debug_info
        assert "environment" in debug_info

    @pytest.mark.unit
    def test_log_level_mapping_completeness(self):
        """ログレベルマッピングの完全性テスト"""
        platform_info = verify_current_platform()
        
        # すべてのLogLevelが含まれていることを確認
        expected_levels = {
            "DEBUG": LogLevel.DEBUG,
            "INFO": LogLevel.INFO,
            "WARNING": LogLevel.WARNING,
            "ERROR": LogLevel.ERROR,
            "CRITICAL": LogLevel.CRITICAL,
        }
        
        assert LoggingConfig.LOG_LEVEL_MAPPING == expected_levels

    @pytest.mark.unit
    @patch('platform.system')
    def test_get_log_file_path_platform_specific_fallback(self, mock_system):
        """プラットフォーム固有のフォールバック処理"""
        platform_info = verify_current_platform()
        
        # Windowsの場合
        mock_system.return_value = "Windows"
        
        with patch('pathlib.Path.__truediv__', side_effect=OSError("Path error")):
            with patch('pathlib.Path.cwd', side_effect=Exception("CWD error")):
                path = LoggingConfig.get_log_file_path()
                # WindowsPathが使用されることを確認
                assert "quality.log" in str(path)

    @pytest.mark.unit
    def test_environment_variable_combinations(self):
        """環境変数の組み合わせテスト"""
        platform_info = verify_current_platform()
        
        # 複数の環境変数が設定された場合の優先順位
        with patch.dict(os.environ, {
            "DEBUG": "false",
            "LOG_LEVEL": "DEBUG",
            "CI_DEBUG": "true"
        }):
            assert LoggingConfig.is_debug_mode() is True  # いずれかがTrueなら全体がTrue

        with patch.dict(os.environ, {
            "CI": "false",
            "GITHUB_ACTIONS": "true",
            "CONTINUOUS_INTEGRATION": "false"
        }):
            assert LoggingConfig.is_ci_environment() is True  # いずれかがTrueなら全体がTrue