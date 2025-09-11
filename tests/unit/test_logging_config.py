"""
ロギング設定のテスト
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from setup_repo.logging_config import (
    LoggingConfig,
    setup_ci_logging,
    setup_development_logging,
    setup_project_logging,
    setup_testing_logging,
)
from setup_repo.quality_logger import LogLevel, QualityLogger


class TestLoggingConfig:
    """ロギング設定クラスのテスト"""

    def test_get_log_level_from_env_default(self):
        """デフォルトログレベルの取得をテスト"""
        with patch.dict(os.environ, {}, clear=True):
            level = LoggingConfig.get_log_level_from_env()
            assert level == LogLevel.INFO

    @patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"})
    def test_get_log_level_from_env_debug(self):
        """DEBUG環境変数からのログレベル取得をテスト"""
        level = LoggingConfig.get_log_level_from_env()
        assert level == LogLevel.DEBUG

    @patch.dict(os.environ, {"LOG_LEVEL": "ERROR"})
    def test_get_log_level_from_env_error(self):
        """ERROR環境変数からのログレベル取得をテスト"""
        level = LoggingConfig.get_log_level_from_env()
        assert level == LogLevel.ERROR

    @patch.dict(os.environ, {"LOG_LEVEL": "invalid"})
    def test_get_log_level_from_env_invalid(self):
        """無効なログレベルの場合のデフォルト値をテスト"""
        level = LoggingConfig.get_log_level_from_env()
        assert level == LogLevel.INFO

    def test_is_debug_mode_false(self):
        """デバッグモードでない場合をテスト"""
        with patch.dict(os.environ, {}, clear=True):
            assert LoggingConfig.is_debug_mode() is False

    @patch.dict(os.environ, {"DEBUG": "true"})
    def test_is_debug_mode_debug_true(self):
        """DEBUG=trueの場合をテスト"""
        assert LoggingConfig.is_debug_mode() is True

    @patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"})
    def test_is_debug_mode_log_level_debug(self):
        """LOG_LEVEL=DEBUGの場合をテスト"""
        assert LoggingConfig.is_debug_mode() is True

    @patch.dict(os.environ, {"CI_DEBUG": "1"})
    def test_is_debug_mode_ci_debug(self):
        """CI_DEBUG=1の場合をテスト"""
        assert LoggingConfig.is_debug_mode() is True

    def test_is_ci_environment_false(self):
        """CI環境でない場合をテスト"""
        with patch.dict(os.environ, {}, clear=True):
            assert LoggingConfig.is_ci_environment() is False

    @patch.dict(os.environ, {"CI": "true"})
    def test_is_ci_environment_ci_true(self):
        """CI=trueの場合をテスト"""
        assert LoggingConfig.is_ci_environment() is True

    @patch.dict(os.environ, {"GITHUB_ACTIONS": "true"})
    def test_is_ci_environment_github_actions(self):
        """GITHUB_ACTIONS=trueの場合をテスト"""
        assert LoggingConfig.is_ci_environment() is True

    @patch.dict(os.environ, {"CONTINUOUS_INTEGRATION": "1"})
    def test_is_ci_environment_continuous_integration(self):
        """CONTINUOUS_INTEGRATION=1の場合をテスト"""
        assert LoggingConfig.is_ci_environment() is True

    def test_should_use_json_format_false(self):
        """JSON形式を使用しない場合をテスト"""
        with patch.dict(os.environ, {}, clear=True):
            assert LoggingConfig.should_use_json_format() is False

    @patch.dict(os.environ, {"CI_JSON_LOGS": "true"})
    def test_should_use_json_format_ci_json_logs(self):
        """CI_JSON_LOGS=trueの場合をテスト"""
        assert LoggingConfig.should_use_json_format() is True

    @patch.dict(os.environ, {"JSON_LOGS": "1"})
    def test_should_use_json_format_json_logs(self):
        """JSON_LOGS=1の場合をテスト"""
        assert LoggingConfig.should_use_json_format() is True

    def test_get_log_file_path_default(self):
        """デフォルトログファイルパスの取得をテスト"""
        with patch.dict(os.environ, {}, clear=True):
            path = LoggingConfig.get_log_file_path()
            assert path == Path("logs/quality.log")

    def test_get_log_file_path_custom_dir_unix(self, platform_mocker):
        """Unix系システムでのカスタムログディレクトリの場合をテスト"""
        with (
            patch.dict(os.environ, {"LOG_DIR": "/custom/logs"}),
            platform_mocker("linux"),
        ):
            path = LoggingConfig.get_log_file_path("custom")
            assert path == Path("/custom/logs/custom.log")

    def test_get_log_file_path_custom_dir_windows(self, platform_mocker):
        """Windowsでのカスタムログディレクトリの場合をテスト"""
        with (
            patch.dict(os.environ, {"LOG_DIR": "C:\\custom\\logs"}),
            platform_mocker("windows"),
        ):
            path = LoggingConfig.get_log_file_path("custom")
            # Pathオブジェクトは現在のプラットフォームに基づいて正規化するため、
            # パスの構成要素を確認する
            assert path.parts[-1] == "custom.log"
            assert "custom" in str(path) and "logs" in str(path)

    def test_get_log_file_path_custom_dir_relative(self):
        """相対パスでのカスタムログディレクトリの場合をテスト"""
        with patch.dict(os.environ, {"LOG_DIR": "custom_logs"}):
            path = LoggingConfig.get_log_file_path("custom")
            assert path == Path("custom_logs/custom.log")

    @patch.dict(os.environ, {"CI": "true"})
    def test_get_log_file_path_ci_environment(self):
        """CI環境でのログファイルパス取得をテスト"""
        path = LoggingConfig.get_log_file_path()
        assert path is None

    @patch.dict(os.environ, {"CI": "true", "CI_LOG_FILE": "true"})
    def test_get_log_file_path_ci_with_log_file(self):
        """CI環境でCI_LOG_FILE=trueの場合をテスト"""
        path = LoggingConfig.get_log_file_path()
        assert path == Path("logs/quality.log")

    def test_configure_for_environment_default(self):
        """デフォルト環境設定をテスト"""
        with patch.dict(os.environ, {}, clear=True):
            logger = LoggingConfig.configure_for_environment()

            assert isinstance(logger, QualityLogger)
            assert logger.log_level == LogLevel.INFO
            assert logger.enable_console is True
            assert logger.enable_json_format is False

    @patch.dict(
        os.environ, {"LOG_LEVEL": "DEBUG", "CI_JSON_LOGS": "true", "CI": "true"}
    )
    def test_configure_for_environment_ci_debug(self):
        """CI環境でのデバッグ設定をテスト"""
        logger = LoggingConfig.configure_for_environment()

        assert isinstance(logger, QualityLogger)
        assert logger.log_level == LogLevel.DEBUG
        assert logger.enable_console is True
        assert logger.enable_json_format is True
        assert logger.log_file is None  # CI環境ではファイルログなし

    @patch.dict(os.environ, {"DEBUG": "true"})
    def test_configure_for_environment_debug_mode(self):
        """デバッグモードでの設定をテスト"""
        logger = LoggingConfig.configure_for_environment()

        assert logger.log_level == LogLevel.DEBUG

    def test_get_debug_context(self):
        """デバッグコンテキストの取得をテスト"""
        with patch.dict(
            os.environ,
            {
                "LOG_LEVEL": "DEBUG",
                "DEBUG": "true",
                "CI": "false",
                "GITHUB_ACTIONS": "false",
            },
        ):
            context = LoggingConfig.get_debug_context()

            assert context["log_level"] == "DEBUG"
            assert context["debug_mode"] == "True"
            assert context["ci_environment"] == "False"
            assert context["json_format"] == "False"
            assert "environment_variables" in context
            assert "LOG_LEVEL" in context["environment_variables"]

    def test_get_log_file_path_cross_platform_compatibility(self, platform_mocker):
        """クロスプラットフォーム互換性のテスト"""
        test_cases = [
            # (platform, log_dir, expected_components)
            ("windows", "C:\\logs", ["logs", "test.log"]),
            ("linux", "/var/log", ["var", "log", "test.log"]),
            ("macos", "/var/log", ["var", "log", "test.log"]),
        ]

        for platform_name, log_dir, expected_components in test_cases:
            with (
                patch.dict(os.environ, {"LOG_DIR": log_dir}),
                platform_mocker(platform_name),
            ):
                path = LoggingConfig.get_log_file_path("test")
                # Pathオブジェクトの構成要素を確認
                assert path.name == "test.log"
                # パスに期待される要素が含まれていることを確認
                path_str = str(path)
                for component in expected_components[:-1]:  # ファイル名以外の要素
                    assert component in path_str

    def test_get_log_file_path_environment_variables_mock(self):
        """環境変数のモックが適切に設定されることをテスト"""
        # CI環境でない場合のテスト
        with (
            patch.dict(os.environ, {}, clear=True),
            patch.dict(os.environ, {"LOG_DIR": "test_logs"}),
        ):
            path = LoggingConfig.get_log_file_path()
            assert path == Path("test_logs/quality.log")

        # CI環境の場合のテスト
        with patch.dict(os.environ, {"CI": "true"}, clear=True):
            path = LoggingConfig.get_log_file_path()
            assert path is None

        # CI環境でCI_LOG_FILE=trueの場合のテスト
        with patch.dict(os.environ, {"CI": "true", "CI_LOG_FILE": "true"}, clear=True):
            path = LoggingConfig.get_log_file_path()
            assert path == Path("logs/quality.log")


class TestLoggingSetupFunctions:
    """ロギングセットアップ関数のテスト"""

    def test_setup_project_logging(self):
        """プロジェクトロギングセットアップをテスト"""
        with patch.dict(os.environ, {}, clear=True):
            logger = setup_project_logging()
            assert isinstance(logger, QualityLogger)

    @pytest.mark.parametrize(
        "platform_name", ["linux", "macos", "wsl"]
    )  # Windowsは除外
    def test_setup_project_logging_cross_platform(
        self, platform_name: str, platform_mocker
    ):
        """Unix系プラットフォームでのプロジェクトロギングセットアップをテスト"""
        with (
            patch.dict(os.environ, {}, clear=True),
            platform_mocker(platform_name),
        ):
            logger = setup_project_logging()
            assert isinstance(logger, QualityLogger)
            # プラットフォームに関係なく基本的な設定が正しいことを確認
            assert logger.enable_console is True

    def test_setup_ci_logging(self):
        """CI環境ロギングセットアップをテスト"""
        logger = setup_ci_logging()

        assert isinstance(logger, QualityLogger)
        assert logger.log_file is None
        assert logger.enable_console is True
        assert logger.enable_json_format is True

    @patch.dict(os.environ, {"DEBUG": "true"})
    def test_setup_ci_logging_debug_mode(self):
        """デバッグモードでのCI環境ロギングセットアップをテスト"""
        logger = setup_ci_logging()

        assert logger.log_level == LogLevel.DEBUG

    def test_setup_development_logging(self):
        """開発環境ロギングセットアップをテスト"""
        logger = setup_development_logging()

        assert isinstance(logger, QualityLogger)
        assert logger.log_level == LogLevel.DEBUG
        assert logger.log_file == Path("logs/development.log")
        assert logger.enable_console is True
        assert logger.enable_json_format is False

    def test_setup_testing_logging(self):
        """テスト環境ロギングセットアップをテスト"""
        logger = setup_testing_logging()

        assert isinstance(logger, QualityLogger)
        assert logger.log_level == LogLevel.WARNING
        assert logger.log_file is None
        assert logger.enable_console is False
        assert logger.enable_json_format is False

    def test_ci_environment_detection_cross_platform(self, platform_mocker):
        """CI環境検出のクロスプラットフォームテスト"""
        ci_env_vars = [
            {"CI": "true"},
            {"GITHUB_ACTIONS": "true"},
            {"CONTINUOUS_INTEGRATION": "1"},
        ]

        for env_vars in ci_env_vars:
            with patch.dict(os.environ, env_vars, clear=True):
                # 各プラットフォームでCI環境が正しく検出されることを確認
                for platform_name in ["windows", "linux", "macos"]:
                    with platform_mocker(platform_name):
                        assert LoggingConfig.is_ci_environment() is True
                        logger = setup_ci_logging()
                        assert isinstance(logger, QualityLogger)
                        assert logger.log_file is None
                        assert logger.enable_console is True
                        assert logger.enable_json_format is True

    def test_path_handling_with_environment_variables(self, platform_mocker):
        """環境変数を使用したパス処理のテスト"""
        # Unix系のパス
        with (
            patch.dict(os.environ, {"LOG_DIR": "/tmp/logs"}, clear=True),
            platform_mocker("linux"),
        ):
            logger = LoggingConfig.configure_for_environment()
            # CI環境でない場合、ログファイルが設定されることを確認
            if not LoggingConfig.is_ci_environment():
                expected_path = Path("/tmp/logs/quality.log")
                assert logger.log_file == expected_path

        # Windowsのパス
        with (
            patch.dict(os.environ, {"LOG_DIR": "C:\\temp\\logs"}, clear=True),
            platform_mocker("windows"),
        ):
            logger = LoggingConfig.configure_for_environment()
            if not LoggingConfig.is_ci_environment():
                # パスの構成要素を確認
                assert logger.log_file.name == "quality.log"
                assert "temp" in str(logger.log_file) and "logs" in str(logger.log_file)
