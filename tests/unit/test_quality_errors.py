"""
品質エラーモジュールのテスト
"""

import json
import tempfile
from pathlib import Path

from setup_repo.quality_errors import (
    CIError,
    CoverageError,
    ErrorReporter,
    MyPyError,
    QualityCheckError,
    ReleaseError,
    RuffError,
    SecurityScanError,
    TestFailureError,
)


class TestQualityCheckErrors:
    """品質チェックエラークラスのテスト"""

    def test_quality_check_error_creation(self):
        """QualityCheckErrorの作成をテスト"""
        error = QualityCheckError("テストエラー", "TEST_ERROR", {"detail": "詳細情報"})

        assert str(error) == "テストエラー"
        assert error.error_code == "TEST_ERROR"
        assert error.details["detail"] == "詳細情報"
        assert error.timestamp is not None

    def test_ruff_error_creation(self):
        """RuffErrorの作成をテスト"""
        issues = [{"filename": "test.py", "message": "テストエラー"}]
        error = RuffError("Ruffエラー", issues)

        assert str(error) == "Ruffエラー"
        assert error.error_code == "RUFF_ERROR"
        assert error.details["issues"] == issues

    def test_mypy_error_creation(self):
        """MyPyErrorの作成をテスト"""
        errors = ["test.py:1: error: テストエラー"]
        error = MyPyError("MyPyエラー", errors)

        assert str(error) == "MyPyエラー"
        assert error.error_code == "MYPY_ERROR"
        assert error.details["errors"] == errors

    def test_test_failure_error_creation(self):
        """TestFailureErrorの作成をテスト"""
        failed_tests = ["test_example.py::test_fail"]
        error = TestFailureError("テスト失敗", failed_tests, 75.0)

        assert str(error) == "テスト失敗"
        assert error.error_code == "TEST_FAILURE"
        assert error.details["failed_tests"] == failed_tests
        assert error.details["coverage"] == 75.0

    def test_coverage_error_creation(self):
        """CoverageErrorの作成をテスト"""
        error = CoverageError("カバレッジ不足", 70.0, 80.0)

        assert str(error) == "カバレッジ不足"
        assert error.error_code == "COVERAGE_ERROR"
        assert error.details["current_coverage"] == 70.0
        assert error.details["required_coverage"] == 80.0

    def test_security_scan_error_creation(self):
        """SecurityScanErrorの作成をテスト"""
        vulnerabilities = [{"severity": "high", "package": "test"}]
        error = SecurityScanError("セキュリティエラー", vulnerabilities)

        assert str(error) == "セキュリティエラー"
        assert error.error_code == "SECURITY_ERROR"
        assert error.details["vulnerabilities"] == vulnerabilities


class TestCIErrors:
    """CI/CDエラークラスのテスト"""

    def test_ci_error_creation(self):
        """CIErrorの作成をテスト"""
        error = CIError("CIエラー", "CI_ERROR", {"stage": "build"})

        assert str(error) == "CIエラー"
        assert error.error_code == "CI_ERROR"
        assert error.details["stage"] == "build"
        assert error.timestamp is not None

    def test_release_error_creation(self):
        """ReleaseErrorの作成をテスト"""
        error = ReleaseError("リリースエラー", "deploy")

        assert str(error) == "リリースエラー"
        assert error.error_code == "RELEASE_ERROR"
        assert error.details["release_stage"] == "deploy"


class TestErrorReporter:
    """ErrorReporterクラスのテスト"""

    def test_error_reporter_creation(self):
        """ErrorReporterの作成をテスト"""
        reporter = ErrorReporter()
        assert reporter.report_dir == Path("error-reports")

        custom_dir = Path("custom-reports")
        reporter_custom = ErrorReporter(custom_dir)
        assert reporter_custom.report_dir == custom_dir

    def test_get_report_path(self):
        """レポートパス取得のテスト"""
        reporter = ErrorReporter()
        path = reporter.get_report_path("test_report.json")

        assert path == Path("error-reports") / "test_report.json"

    def test_create_error_report(self):
        """エラーレポート作成のテスト"""
        reporter = ErrorReporter()

        errors = [
            QualityCheckError("エラー1", "ERROR_1"),
            RuffError("エラー2", [{"file": "test.py"}]),
            MyPyError("エラー3", ["type error"]),
        ]

        context = {"test": "context"}
        report = reporter.create_error_report(errors, context)

        assert report["total_errors"] == 3
        assert report["context"]["test"] == "context"
        assert len(report["errors"]) == 3
        assert report["errors"][0]["type"] == "QualityCheckError"
        assert report["errors"][1]["type"] == "RuffError"
        assert report["errors"][2]["type"] == "MyPyError"

    def test_save_report(self):
        """レポート保存のテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            reporter = ErrorReporter(Path(temp_dir))

            error_data = {
                "timestamp": "2024-01-01T00:00:00",
                "total_errors": 1,
                "errors": [{"type": "TestError", "message": "テストエラー"}],
            }

            saved_path = reporter.save_report(error_data, "test")

            assert saved_path.exists()
            assert saved_path.parent == Path(temp_dir)
            assert "test_error_report_" in saved_path.name

            with open(saved_path, encoding="utf-8") as f:
                loaded_data = json.load(f)

            assert loaded_data == error_data

    def test_format_error_message(self):
        """エラーメッセージフォーマットのテスト"""
        reporter = ErrorReporter()

        # QualityCheckErrorの場合
        quality_error = QualityCheckError("品質エラー", "QUALITY_001", {"detail": "詳細"})
        formatted = reporter.format_error_message(quality_error)
        assert "[QUALITY_001]" in formatted
        assert "品質エラー" in formatted
        assert "詳細" in formatted

        # 通常のExceptionの場合
        normal_error = Exception("通常エラー")
        formatted_normal = reporter.format_error_message(normal_error)
        assert formatted_normal == "通常エラー"

    def test_log_exception(self):
        """例外ログフォーマットのテスト"""
        reporter = ErrorReporter()

        error = QualityCheckError("テストエラー", "TEST_001", {"key": "value"})
        formatted = reporter.log_exception(error, include_traceback=False)

        assert "QualityCheckError" in formatted
        assert "テストエラー" in formatted
        assert "TEST_001" in formatted
        assert "key" in formatted

        # トレースバック付きのテスト
        formatted_with_trace = reporter.log_exception(error, include_traceback=True)
        assert "スタックトレース" in formatted_with_trace
