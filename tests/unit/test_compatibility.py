"""
後方互換性機能のテスト
"""

import sys
import warnings
from unittest.mock import MagicMock, patch

from setup_repo.compatibility import (
    CIErrorHandlerCompatibility,
    InteractiveSetupCompatibility,
    LoggingConfigCompatibility,
    QualityLoggerCompatibility,
    QualityMetricsCompatibility,
    _deprecated_import,
    check_deprecated_imports,
    create_compatibility_aliases,
    show_migration_guide,
)


class TestDeprecatedImport:
    """非推奨インポート機能のテスト"""

    def test_deprecated_import_warning(self):
        """非推奨インポート警告のテスト"""
        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_function = MagicMock()
            mock_module.test_function = mock_function
            mock_import.return_value = mock_module

            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")

                result = _deprecated_import("old_module", "new_module", "test_function")

                # 警告が発行されたことを確認
                assert len(w) == 1
                assert issubclass(w[0].category, DeprecationWarning)
                assert "old_module.test_function is deprecated" in str(w[0].message)
                assert "new_module.test_function instead" in str(w[0].message)

                # 正しい関数が返されたことを確認
                assert result == mock_function
                mock_import.assert_called_once_with("setup_repo.new_module")


class TestQualityLoggerCompatibility:
    """Quality Logger互換性クラスのテスト"""

    def setup_method(self):
        """テスト前の準備"""
        self.compat = QualityLoggerCompatibility()

    @patch("setup_repo.compatibility._deprecated_import")
    def test_error_function_routing(self, mock_deprecated_import):
        """エラー処理関数のルーティングテスト"""
        mock_deprecated_import.return_value = MagicMock()

        # エラー処理関数をテスト
        error_functions = [
            "QualityError",
            "QualityWarning",
            "handle_quality_error",
            "format_error_message",
            "log_exception",
            "create_error_report",
        ]

        for func_name in error_functions:
            self.compat.__getattr__(func_name)
            mock_deprecated_import.assert_called_with(
                "quality_logger", "quality_errors", func_name
            )

    @patch("setup_repo.compatibility._deprecated_import")
    def test_formatter_function_routing(self, mock_deprecated_import):
        """フォーマッター関数のルーティングテスト"""
        mock_deprecated_import.return_value = MagicMock()

        # フォーマッター関数をテスト
        formatter_functions = [
            "ColoredFormatter",
            "JSONFormatter",
            "format_log_message",
            "add_color_codes",
            "strip_color_codes",
        ]

        for func_name in formatter_functions:
            self.compat.__getattr__(func_name)
            mock_deprecated_import.assert_called_with(
                "quality_logger", "quality_formatters", func_name
            )

    @patch("setup_repo.compatibility._deprecated_import")
    def test_default_function_routing(self, mock_deprecated_import):
        """デフォルト関数のルーティングテスト"""
        mock_deprecated_import.return_value = MagicMock()

        # 基本ログ機能をテスト
        self.compat.__getattr__("setup_quality_logging")
        mock_deprecated_import.assert_called_with(
            "quality_logger", "quality_logger", "setup_quality_logging"
        )


class TestCIErrorHandlerCompatibility:
    """CI Error Handler互換性クラスのテスト"""

    def setup_method(self):
        """テスト前の準備"""
        self.compat = CIErrorHandlerCompatibility()

    @patch("setup_repo.compatibility._deprecated_import")
    def test_environment_function_routing(self, mock_deprecated_import):
        """CI環境検出関数のルーティングテスト"""
        mock_deprecated_import.return_value = MagicMock()

        # CI環境検出関数をテスト
        environment_functions = [
            "detect_ci_environment",
            "get_system_info",
            "collect_environment_vars",
            "get_ci_metadata",
            "is_ci_environment",
        ]

        for func_name in environment_functions:
            self.compat.__getattr__(func_name)
            mock_deprecated_import.assert_called_with(
                "ci_error_handler", "ci_environment", func_name
            )

    @patch("setup_repo.compatibility._deprecated_import")
    def test_error_handler_function_routing(self, mock_deprecated_import):
        """エラーハンドリング関数のルーティングテスト"""
        mock_deprecated_import.return_value = MagicMock()

        # エラーハンドリング関数をテスト
        self.compat.__getattr__("handle_ci_error")
        mock_deprecated_import.assert_called_with(
            "ci_error_handler", "ci_error_handler", "handle_ci_error"
        )


class TestLoggingConfigCompatibility:
    """Logging Config互換性クラスのテスト"""

    def setup_method(self):
        """テスト前の準備"""
        self.compat = LoggingConfigCompatibility()

    @patch("setup_repo.compatibility._deprecated_import")
    def test_handler_function_routing(self, mock_deprecated_import):
        """ハンドラー関数のルーティングテスト"""
        mock_deprecated_import.return_value = MagicMock()

        # ハンドラー関数をテスト
        handler_functions = [
            "TeeHandler",
            "RotatingFileHandler",
            "ColoredConsoleHandler",
            "create_file_handler",
            "create_console_handler",
        ]

        for func_name in handler_functions:
            self.compat.__getattr__(func_name)
            mock_deprecated_import.assert_called_with(
                "logging_config", "logging_handlers", func_name
            )

    @patch("setup_repo.compatibility._deprecated_import")
    def test_config_function_routing(self, mock_deprecated_import):
        """設定関数のルーティングテスト"""
        mock_deprecated_import.return_value = MagicMock()

        # 基本設定関数をテスト
        self.compat.__getattr__("setup_logging")
        mock_deprecated_import.assert_called_with(
            "logging_config", "logging_config", "setup_logging"
        )


class TestQualityMetricsCompatibility:
    """Quality Metrics互換性クラスのテスト"""

    def setup_method(self):
        """テスト前の準備"""
        self.compat = QualityMetricsCompatibility()

    @patch("setup_repo.compatibility._deprecated_import")
    def test_collector_function_routing(self, mock_deprecated_import):
        """データ収集関数のルーティングテスト"""
        mock_deprecated_import.return_value = MagicMock()

        # データ収集関数をテスト
        collector_functions = [
            "collect_ruff_metrics",
            "collect_mypy_metrics",
            "collect_pytest_metrics",
            "collect_coverage_metrics",
            "parse_tool_output",
        ]

        for func_name in collector_functions:
            self.compat.__getattr__(func_name)
            mock_deprecated_import.assert_called_with(
                "quality_metrics", "quality_collectors", func_name
            )

    @patch("setup_repo.compatibility._deprecated_import")
    def test_metrics_function_routing(self, mock_deprecated_import):
        """メトリクス計算関数のルーティングテスト"""
        mock_deprecated_import.return_value = MagicMock()

        # メトリクス計算関数をテスト
        self.compat.__getattr__("calculate_quality_score")
        mock_deprecated_import.assert_called_with(
            "quality_metrics", "quality_metrics", "calculate_quality_score"
        )


class TestInteractiveSetupCompatibility:
    """Interactive Setup互換性クラスのテスト"""

    def setup_method(self):
        """テスト前の準備"""
        self.compat = InteractiveSetupCompatibility()

    @patch("setup_repo.compatibility._deprecated_import")
    def test_validator_function_routing(self, mock_deprecated_import):
        """検証関数のルーティングテスト"""
        mock_deprecated_import.return_value = MagicMock()

        # 検証関数をテスト
        validator_functions = [
            "validate_github_credentials",
            "validate_directory_path",
            "validate_setup_prerequisites",
            "check_system_requirements",
        ]

        for func_name in validator_functions:
            self.compat.__getattr__(func_name)
            mock_deprecated_import.assert_called_with(
                "interactive_setup", "setup_validators", func_name
            )

    @patch("setup_repo.compatibility._deprecated_import")
    def test_setup_function_routing(self, mock_deprecated_import):
        """セットアップ関数のルーティングテスト"""
        mock_deprecated_import.return_value = MagicMock()

        # メインウィザード関数をテスト
        self.compat.__getattr__("run_interactive_setup")
        mock_deprecated_import.assert_called_with(
            "interactive_setup", "interactive_setup", "run_interactive_setup"
        )


class TestCompatibilityAliases:
    """互換性エイリアス機能のテスト"""

    def test_create_compatibility_aliases(self):
        """互換性エイリアス作成テスト"""
        # sys.modulesの初期状態を保存
        original_modules = sys.modules.copy()

        try:
            # 互換性エイリアスを作成
            create_compatibility_aliases()

            # 互換性モジュールがsys.modulesに追加されたことを確認
            expected_modules = [
                "setup_repo.quality_logger_legacy",
                "setup_repo.ci_error_handler_legacy",
                "setup_repo.logging_config_legacy",
                "setup_repo.quality_metrics_legacy",
                "setup_repo.interactive_setup_legacy",
            ]

            for module_name in expected_modules:
                assert module_name in sys.modules
                assert hasattr(sys.modules[module_name], "__getattr__")

        finally:
            # sys.modulesを元の状態に戻す
            for module_name in list(sys.modules.keys()):
                if module_name not in original_modules:
                    del sys.modules[module_name]


class TestMigrationGuide:
    """移行ガイド機能のテスト"""

    @patch("builtins.print")
    def test_show_migration_guide(self, mock_print):
        """移行ガイド表示テスト"""
        show_migration_guide()

        # print関数が呼び出されたことを確認
        mock_print.assert_called_once()

        # 出力内容に重要な情報が含まれていることを確認
        output = mock_print.call_args[0][0]
        assert "Setup Repository リファクタリング移行ガイド" in output
        assert "Quality Logger分割" in output
        assert "CI Error Handler分割" in output
        assert "Logging Config分割" in output
        assert "Quality Metrics分割" in output
        assert "Interactive Setup分割" in output
        assert "docs/migration-guide.md" in output


class TestDeprecatedImportCheck:
    """非推奨インポートチェック機能のテスト"""

    def test_check_deprecated_imports_with_deprecated_module(self):
        """非推奨モジュール使用時のチェックテスト"""
        # 非推奨モジュールをsys.modulesに追加
        original_modules = sys.modules.copy()

        try:
            # テスト用の非推奨モジュールを追加
            sys.modules["quality_logger_legacy"] = MagicMock()

            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")

                check_deprecated_imports()

                # 警告が発行されたことを確認
                assert len(w) == 1
                assert issubclass(w[0].category, DeprecationWarning)
                assert (
                    "非推奨モジュール quality_logger_legacy が使用されています"
                    in str(w[0].message)
                )

        finally:
            # sys.modulesを元の状態に戻す
            for module_name in list(sys.modules.keys()):
                if module_name not in original_modules:
                    del sys.modules[module_name]

    def test_check_deprecated_imports_without_deprecated_module(self):
        """非推奨モジュール未使用時のチェックテスト"""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            check_deprecated_imports()

            # 警告が発行されないことを確認
            deprecated_warnings = [
                warning for warning in w if "非推奨モジュール" in str(warning.message)
            ]
            assert len(deprecated_warnings) == 0


class TestCompatibilityIntegration:
    """互換性機能統合テスト"""

    def setup_method(self):
        """テスト前の準備"""
        self.original_modules = sys.modules.copy()

    def teardown_method(self):
        """テスト後のクリーンアップ"""
        # sys.modulesを元の状態に戻す
        for module_name in list(sys.modules.keys()):
            if module_name not in self.original_modules:
                del sys.modules[module_name]

    def test_full_compatibility_workflow(self):
        """完全な互換性ワークフローテスト"""
        # 互換性エイリアスを作成
        create_compatibility_aliases()

        # 各互換性モジュールが正しく動作することを確認
        compatibility_modules = [
            "setup_repo.quality_logger_legacy",
            "setup_repo.ci_error_handler_legacy",
            "setup_repo.logging_config_legacy",
            "setup_repo.quality_metrics_legacy",
            "setup_repo.interactive_setup_legacy",
        ]

        for module_name in compatibility_modules:
            assert module_name in sys.modules
            module = sys.modules[module_name]
            assert hasattr(module, "__getattr__")

            # __getattr__メソッドが呼び出し可能であることを確認
            assert callable(module.__getattr__)

    @patch("setup_repo.compatibility._deprecated_import")
    def test_legacy_import_simulation(self, mock_deprecated_import):
        """レガシーインポートシミュレーションテスト"""
        mock_deprecated_import.return_value = MagicMock()

        # 互換性エイリアスを作成
        create_compatibility_aliases()

        # レガシーモジュールから関数をインポートしようとする
        legacy_module = sys.modules["setup_repo.quality_logger_legacy"]

        # エラー処理関数のインポートをシミュレート
        legacy_module.__getattr__("QualityError")
        mock_deprecated_import.assert_called_with(
            "quality_logger", "quality_errors", "QualityError"
        )
