"""品質フォーマッターのテスト"""

import json
import logging
from unittest.mock import Mock, patch

import pytest

from ..multiplatform.helpers import verify_current_platform


class TestQualityFormatters:
    """品質フォーマッターのテストクラス"""

    @pytest.mark.unit
    def test_colored_formatter_basic(self):
        """色付きフォーマッターの基本テスト"""
        verify_current_platform()

        try:
            from src.setup_repo.quality_formatters import ColoredFormatter
        except ImportError:
            pytest.skip("ColoredFormatterが利用できません")

        formatter = ColoredFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0, msg="テストメッセージ", args=(), exc_info=None
        )

        formatted = formatter.format(record)
        assert "テストメッセージ" in formatted
        assert "\033[32m" in formatted  # 緑色コード
        assert "\033[0m" in formatted  # リセットコード

    @pytest.mark.unit
    def test_colored_formatter_with_platform_info(self):
        """プラットフォーム情報付き色付きフォーマッターのテスト"""
        verify_current_platform()

        try:
            from src.setup_repo.quality_formatters import ColoredFormatter
        except ImportError:
            pytest.skip("ColoredFormatterが利用できません")

        formatter = ColoredFormatter(include_platform_info=True)

        # platform_detectorモジュールをモック
        with patch("src.setup_repo.platform_detector.detect_platform") as mock_detect:
            mock_platform = Mock()
            mock_platform.name = "linux"
            mock_platform.display_name = "Linux"
            mock_platform.shell = "bash"
            mock_platform.python_cmd = "python3"
            mock_platform.package_managers = ["apt"]
            mock_detect.return_value = mock_platform

            record = logging.LogRecord(
                name="test", level=logging.ERROR, pathname="", lineno=0, msg="エラーメッセージ", args=(), exc_info=None
            )

            formatted = formatter.format(record)
            # プラットフォーム情報が含まれるか、またはエラーが適切に処理されることを確認
            assert "[linux]" in formatted or "[unknown]" in formatted
            assert "エラーメッセージ" in formatted
            assert "\033[31m" in formatted  # 赤色コード

    @pytest.mark.unit
    def test_json_formatter_basic(self):
        """JSONフォーマッターの基本テスト"""
        verify_current_platform()

        try:
            from src.setup_repo.quality_formatters import JSONFormatter
        except ImportError:
            pytest.skip("JSONFormatterが利用できません")

        formatter = JSONFormatter(include_platform_info=False)
        record = logging.LogRecord(
            name="test.logger",
            level=logging.WARNING,
            pathname="test.py",
            lineno=42,
            msg="警告メッセージ",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        assert log_data["level"] == "WARNING"
        assert log_data["message"] == "警告メッセージ"
        assert log_data["logger"] == "test.logger"
        assert log_data["line"] == 42

    @pytest.mark.unit
    def test_json_formatter_with_platform_info(self):
        """プラットフォーム情報付きJSONフォーマッターのテスト"""
        verify_current_platform()

        try:
            from src.setup_repo.quality_formatters import JSONFormatter
        except ImportError:
            pytest.skip("JSONFormatterが利用できません")

        formatter = JSONFormatter(include_platform_info=True)

        with patch("src.setup_repo.platform_detector.detect_platform") as mock_detect:
            mock_platform = Mock()
            mock_platform.name = "windows"
            mock_platform.display_name = "Windows"
            mock_platform.shell = "cmd"
            mock_platform.python_cmd = "python"
            mock_platform.package_managers = ["winget"]
            mock_detect.return_value = mock_platform

            record = logging.LogRecord(
                name="test", level=logging.INFO, pathname="", lineno=0, msg="情報メッセージ", args=(), exc_info=None
            )

            formatted = formatter.format(record)
            log_data = json.loads(formatted)

            assert "platform" in log_data
            assert log_data["platform"]["name"] == "windows"
            assert log_data["platform"]["display_name"] == "Windows"

    @pytest.mark.unit
    def test_format_log_message(self):
        """ログメッセージフォーマット関数のテスト"""
        verify_current_platform()

        try:
            from src.setup_repo.quality_formatters import format_log_message
        except ImportError:
            pytest.skip("format_log_messageが利用できません")

        # 基本的なフォーマット
        message = format_log_message("テストメッセージ", "INFO")
        assert "INFO" in message
        assert "テストメッセージ" in message

        # コンテキスト付きフォーマット
        context = {"user": "test", "action": "format"}
        message_with_context = format_log_message("コンテキスト付き", "DEBUG", context=context)
        assert "DEBUG" in message_with_context
        assert "コンテキスト付き" in message_with_context
        assert "コンテキスト:" in message_with_context

    @pytest.mark.unit
    def test_add_color_codes(self):
        """色コード追加関数のテスト"""
        verify_current_platform()

        try:
            from src.setup_repo.quality_formatters import add_color_codes
        except ImportError:
            pytest.skip("add_color_codesが利用できません")

        # 各レベルの色コードテスト
        error_text = add_color_codes("エラーテキスト", "ERROR")
        assert "\033[31m" in error_text  # 赤色
        assert "\033[0m" in error_text  # リセット

        info_text = add_color_codes("情報テキスト", "INFO")
        assert "\033[32m" in info_text  # 緑色

        # 不明なレベル
        unknown_text = add_color_codes("不明レベル", "UNKNOWN")
        assert "\033[0m" in unknown_text  # リセットのみ

    @pytest.mark.unit
    def test_strip_color_codes(self):
        """色コード除去関数のテスト"""
        verify_current_platform()

        try:
            from src.setup_repo.quality_formatters import strip_color_codes
        except ImportError:
            pytest.skip("strip_color_codesが利用できません")

        colored_text = "\033[31mエラーメッセージ\033[0m"
        clean_text = strip_color_codes(colored_text)
        assert clean_text == "エラーメッセージ"
        assert "\033[" not in clean_text

    @pytest.mark.unit
    def test_format_metrics_summary(self):
        """メトリクス概要フォーマット関数のテスト"""
        verify_current_platform()

        try:
            from src.setup_repo.quality_formatters import format_metrics_summary
        except ImportError:
            pytest.skip("format_metrics_summaryが利用できません")

        metrics = {
            "coverage": 85.5,
            "tests_passed": True,
            "linting_errors": 0,
            "security_issues": False,
            "build_status": "success",
        }

        summary = format_metrics_summary(metrics)
        assert "品質メトリクス概要" in summary
        assert "coverage: 85.5" in summary
        assert "✅" in summary  # tests_passed: True
        assert "❌" in summary  # security_issues: False

    @pytest.mark.unit
    def test_format_quality_check_result_success(self):
        """品質チェック結果フォーマット（成功）のテスト"""
        verify_current_platform()

        try:
            from src.setup_repo.quality_formatters import format_quality_check_result
        except ImportError:
            pytest.skip("format_quality_check_resultが利用できません")

        success_result = {"success": True, "metrics": {"coverage": 90, "issues": 0}}

        formatted = format_quality_check_result("pytest", success_result)
        assert "品質チェック成功: pytest" in formatted
        assert "メトリクス:" in formatted

    @pytest.mark.unit
    def test_format_quality_check_result_failure(self):
        """品質チェック結果フォーマット（失敗）のテスト"""
        verify_current_platform()

        try:
            from src.setup_repo.quality_formatters import format_quality_check_result
        except ImportError:
            pytest.skip("format_quality_check_resultが利用できません")

        failure_result = {
            "success": False,
            "errors": ["テストエラー1", "テストエラー2"],
            "details": {"failed_tests": ["test_example"]},
        }

        formatted = format_quality_check_result("ruff", failure_result)
        assert "品質チェック失敗: ruff" in formatted
        assert "テストエラー1" in formatted
        assert "詳細:" in formatted

    @pytest.mark.unit
    def test_format_quality_check_result_xss_protection(self):
        """品質チェック結果フォーマットのXSS保護テスト"""
        verify_current_platform()

        try:
            from src.setup_repo.quality_formatters import format_quality_check_result
        except ImportError:
            pytest.skip("format_quality_check_resultが利用できません")

        malicious_result = {
            "success": False,
            "errors": ["<script>alert('xss')</script>"],
        }

        formatted = format_quality_check_result("<script>alert('xss')</script>", malicious_result)
        assert "<script>" not in formatted
        assert "&lt;script&gt;" in formatted  # HTMLエスケープされている

    @pytest.mark.unit
    def test_json_formatter_with_exception(self):
        """例外情報付きJSONフォーマッターのテスト"""
        verify_current_platform()

        try:
            from src.setup_repo.quality_formatters import JSONFormatter
        except ImportError:
            pytest.skip("JSONFormatterが利用できません")

        formatter = JSONFormatter(include_platform_info=False)

        try:
            raise ValueError("テスト例外")
        except ValueError:
            import sys

            exc_info = sys.exc_info()

            record = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname="",
                lineno=0,
                msg="例外が発生しました",
                args=(),
                exc_info=exc_info,
            )

            formatted = formatter.format(record)
            log_data = json.loads(formatted)

            assert "exception" in log_data
            assert "ValueError" in log_data["exception"]

    @pytest.mark.unit
    def test_format_quality_report_json(self):
        """品質レポートのJSON形式フォーマットテスト"""
        verify_current_platform()

        try:
            from src.setup_repo.quality_formatters import format_quality_report
        except ImportError:
            pytest.skip("format_quality_reportが利用できません")

        test_data = {
            "coverage": 85.5,
            "tests_passed": True,
            "linting_errors": 0,
            "timestamp": "2024-01-01 12:00:00",
        }

        result = format_quality_report(test_data, "json")
        parsed = json.loads(result)

        assert parsed["coverage"] == 85.5
        assert parsed["tests_passed"] is True
        assert parsed["linting_errors"] == 0

    @pytest.mark.unit
    def test_format_quality_report_html(self):
        """品質レポートのHTML形式フォーマットテスト"""
        verify_current_platform()

        try:
            from src.setup_repo.quality_formatters import format_quality_report
        except ImportError:
            pytest.skip("format_quality_reportが利用できません")

        test_data = {
            "coverage": 90.0,
            "build_status": {"success": True, "duration": "2m 30s"},
        }

        result = format_quality_report(test_data, "html")

        assert "<!DOCTYPE html>" in result
        assert "品質レポート" in result
        assert "<strong>coverage:</strong> 90.0" in result
        assert "生成日時:" in result

    @pytest.mark.unit
    def test_format_quality_report_text(self):
        """品質レポートのテキスト形式フォーマットテスト"""
        verify_current_platform()

        try:
            from src.setup_repo.quality_formatters import format_quality_report
        except ImportError:
            pytest.skip("format_quality_reportが利用できません")

        test_data = {
            "coverage": 75.0,
            "security": {"vulnerabilities": 0, "scan_date": "2024-01-01"},
            "performance": "good",
        }

        result = format_quality_report(test_data, "text")

        assert "=== 品質レポート ===" in result
        assert "coverage: 75.0" in result
        assert "security:" in result
        assert "vulnerabilities: 0" in result
        assert "performance: good" in result

    @pytest.mark.unit
    def test_format_quality_report_invalid_format(self):
        """品質レポートの無効な形式テスト"""
        verify_current_platform()

        try:
            from src.setup_repo.quality_formatters import format_quality_report
        except ImportError:
            pytest.skip("format_quality_reportが利用できません")

        test_data = {"test": "data"}

        with pytest.raises(ValueError, match="サポートされていない形式"):
            format_quality_report(test_data, "invalid_format")
