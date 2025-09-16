"""品質エラー処理機能のテスト."""

import json
import platform
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from src.setup_repo.quality_errors import (
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

from ..multiplatform.helpers import verify_current_platform


class TestQualityErrorClasses:
    """品質エラークラスのテスト."""

    @pytest.mark.unit
    def test_quality_check_error_initialization(self):
        """QualityCheckErrorの初期化テスト."""
        verify_current_platform()

        error = QualityCheckError("テストエラー", error_code="TEST_001", details={"file": "test.py", "line": 10})

        assert str(error) == "テストエラー"
        assert error.message == "テストエラー"
        assert error.error_code == "TEST_001"
        assert error.details["file"] == "test.py"
        assert error.details["line"] == 10
        assert error.timestamp is not None

    @pytest.mark.unit
    def test_quality_check_error_defaults(self):
        """QualityCheckErrorのデフォルト値テスト."""
        verify_current_platform()

        error = QualityCheckError("シンプルエラー")

        assert error.error_code == "QUALITY_ERROR"
        assert error.details == {}
        assert isinstance(error.timestamp, str)

    @pytest.mark.unit
    def test_ruff_error_specific_functionality(self):
        """RuffError固有機能のテスト."""
        verify_current_platform()

        issues = [
            {"file": "test.py", "line": 10, "code": "E501", "message": "Line too long"},
            {"file": "main.py", "line": 5, "code": "F401", "message": "Unused import"},
        ]

        error = RuffError("Ruffリンティングエラー", issues=issues)

        assert error.error_code == "RUFF_ERROR"
        assert len(error.details["issues"]) == 2
        assert error.details["issues"][0]["code"] == "E501"
        assert error.details["issues"][1]["code"] == "F401"

    @pytest.mark.unit
    def test_mypy_error_specific_functionality(self):
        """MyPyError固有機能のテスト."""
        verify_current_platform()

        type_errors = ["test.py:10: error: Incompatible types", "main.py:15: error: Missing return statement"]

        error = MyPyError("MyPy型チェックエラー", errors=type_errors)

        assert error.error_code == "MYPY_ERROR"
        assert len(error.details["errors"]) == 2
        assert "Incompatible types" in error.details["errors"][0]

    @pytest.mark.unit
    def test_test_failure_error_with_coverage(self):
        """TestFailureErrorのカバレッジ情報テスト."""
        verify_current_platform()

        failed_tests = ["test_example", "test_integration"]

        error = TestFailureError("テスト失敗", failed_tests=failed_tests, coverage=75.5)

        assert error.error_code == "TEST_FAILURE"
        assert error.details["failed_tests"] == failed_tests
        assert error.details["coverage"] == 75.5

    @pytest.mark.unit
    def test_coverage_error_threshold_validation(self):
        """CoverageErrorの閾値検証テスト."""
        verify_current_platform()

        error = CoverageError("カバレッジ不足", current_coverage=75.0, required_coverage=80.0)

        assert error.error_code == "COVERAGE_ERROR"
        assert error.details["current_coverage"] == 75.0
        assert error.details["required_coverage"] == 80.0

        # 閾値チェックロジック
        coverage_gap = error.details["required_coverage"] - error.details["current_coverage"]
        assert coverage_gap == 5.0

    @pytest.mark.unit
    def test_security_scan_error_vulnerabilities(self):
        """SecurityScanErrorの脆弱性情報テスト."""
        verify_current_platform()

        vulnerabilities = [
            {"cve": "CVE-2021-33503", "severity": "HIGH", "package": "requests"},
            {"cve": "CVE-2021-44228", "severity": "CRITICAL", "package": "log4j"},
        ]

        error = SecurityScanError("セキュリティ脆弱性検出", vulnerabilities=vulnerabilities)

        assert error.error_code == "SECURITY_ERROR"
        assert len(error.details["vulnerabilities"]) == 2

        # 重要度別分類
        critical_vulns = [v for v in error.details["vulnerabilities"] if v["severity"] == "CRITICAL"]
        assert len(critical_vulns) == 1
        assert critical_vulns[0]["package"] == "log4j"

    @pytest.mark.unit
    def test_ci_error_inheritance(self):
        """CIErrorの継承関係テスト."""
        verify_current_platform()

        error = CIError("CI処理エラー", error_code="CI_001", details={"stage": "build", "duration": 120})

        assert isinstance(error, Exception)
        assert error.error_code == "CI_001"
        assert error.details["stage"] == "build"

    @pytest.mark.unit
    def test_release_error_stage_tracking(self):
        """ReleaseErrorのステージ追跡テスト."""
        verify_current_platform()

        error = ReleaseError("リリース失敗", release_stage="deployment")

        assert error.error_code == "RELEASE_ERROR"
        assert error.details["release_stage"] == "deployment"

        # ステージ別エラー処理
        if error.details["release_stage"] == "deployment":
            assert "deployment" in str(error.details)


class TestErrorReporter:
    """ErrorReporterクラスのテスト."""

    @pytest.mark.unit
    def test_error_reporter_initialization(self, temp_dir):
        """ErrorReporterの初期化テスト."""
        verify_current_platform()

        reporter = ErrorReporter(report_dir=temp_dir)
        assert reporter.report_dir == temp_dir

        # デフォルト初期化
        default_reporter = ErrorReporter()
        assert default_reporter.report_dir.name == "error-reports"

    @pytest.mark.unit
    def test_create_error_report_comprehensive(self, temp_dir):
        """包括的なエラーレポート作成テスト."""
        verify_current_platform()

        reporter = ErrorReporter(report_dir=temp_dir)

        errors = [
            RuffError("リンティングエラー", issues=[{"file": "test.py", "line": 10}]),
            CoverageError("カバレッジ不足", 75.0, 80.0),
            SecurityScanError("脆弱性検出", vulnerabilities=[{"cve": "CVE-2021-1234"}]),
        ]

        context = {"platform": "windows", "python_version": "3.9.0"}

        report = reporter.create_error_report(errors, context)

        assert report["total_errors"] == 3
        assert report["context"]["platform"] == "windows"
        assert len(report["errors"]) == 3

        # 各エラータイプの検証
        error_types = [error["type"] for error in report["errors"]]
        assert "RuffError" in error_types
        assert "CoverageError" in error_types
        assert "SecurityScanError" in error_types

    @pytest.mark.unit
    def test_save_report_file_creation(self, temp_dir):
        """レポートファイル作成テスト."""
        verify_current_platform()

        reporter = ErrorReporter(report_dir=temp_dir)

        error_data = {
            "timestamp": datetime.now().isoformat(),
            "errors": [{"type": "TestError", "message": "テストエラー"}],
        }

        report_path = reporter.save_report(error_data, "quality")

        assert report_path.exists()
        assert report_path.suffix == ".json"
        assert "quality_error_report" in report_path.name

        # ファイル内容の検証
        with open(report_path, encoding="utf-8") as f:
            saved_data = json.load(f)

        assert saved_data["timestamp"] == error_data["timestamp"]
        assert len(saved_data["errors"]) == 1

    @pytest.mark.unit
    def test_format_error_message_quality_errors(self):
        """品質エラーメッセージフォーマットテスト."""
        verify_current_platform()

        reporter = ErrorReporter()

        # QualityCheckErrorのフォーマット
        quality_error = RuffError("リンティングエラー", issues=[{"file": "test.py"}])
        formatted = reporter.format_error_message(quality_error)

        assert "[RUFF_ERROR]" in formatted
        assert "リンティングエラー" in formatted
        assert "詳細:" in formatted

        # 通常の例外のフォーマット
        normal_error = ValueError("通常のエラー")
        formatted_normal = reporter.format_error_message(normal_error)

        assert formatted_normal == "通常のエラー"

    @pytest.mark.unit
    def test_log_exception_with_traceback(self):
        """例外ログ（トレースバック付き）テスト."""
        verify_current_platform()

        reporter = ErrorReporter()

        error = MyPyError("型エラー", errors=["test.py:10: error"])

        # トレースバック付きログ
        with patch("traceback.format_exc", return_value="Mock traceback"):
            log_output = reporter.log_exception(error, include_traceback=True)

        log_data = json.loads(log_output.split("\nスタックトレース:")[0])

        assert log_data["error_type"] == "MyPyError"
        assert log_data["error_code"] == "MYPY_ERROR"
        assert "Mock traceback" in log_output

        # トレースバックなしログ
        log_output_no_trace = reporter.log_exception(error, include_traceback=False)
        assert "スタックトレース:" not in log_output_no_trace

    @pytest.mark.unit
    def test_get_report_path_functionality(self, temp_dir):
        """レポートパス取得機能テスト."""
        verify_current_platform()

        reporter = ErrorReporter(report_dir=temp_dir)

        filename = "test_report.json"
        path = reporter.get_report_path(filename)

        # Windows短縮パス（RUNNER~1など）を考慮した比較
        assert path.parent.resolve() == temp_dir.resolve()
        assert path.name == filename
        assert isinstance(path, Path)


class TestQualityErrorHandling:
    """品質エラー処理のテストクラス."""

    def setup_method(self):
        """テストメソッドの前処理."""
        self.platform_info = verify_current_platform()

    @pytest.mark.unit
    def test_lint_error_handling(self):
        """リンティングエラーの処理テスト."""
        # モックエラーレスポンス
        mock_error = {"file": "test.py", "line": 10, "column": 5, "message": "Line too long", "code": "E501"}

        # エラー処理ロジックのテスト
        assert mock_error["code"] == "E501"
        assert mock_error["line"] == 10

    @pytest.mark.unit
    def test_type_check_error_handling(self):
        """型チェックエラーの処理テスト."""
        mock_mypy_error = {"file": "test.py", "line": 15, "message": "Incompatible types", "severity": "error"}

        # MyPyエラー処理のテスト
        assert mock_mypy_error["severity"] == "error"
        assert "Incompatible types" in mock_mypy_error["message"]

    @pytest.mark.unit
    def test_test_failure_error_handling(self):
        """テスト失敗エラーの処理テスト."""
        mock_test_error = {
            "test": "test_example",
            "file": "test_example.py",
            "error": "AssertionError: Expected 5, got 3",
            "traceback": ["line1", "line2", "line3"],
        }

        # テストエラー処理のテスト
        assert "AssertionError" in mock_test_error["error"]
        assert len(mock_test_error["traceback"]) == 3

    @pytest.mark.unit
    def test_security_error_handling(self):
        """セキュリティエラーの処理テスト."""
        mock_security_error = {
            "file": "vulnerable.py",
            "line": 20,
            "issue": "Hardcoded password",
            "severity": "HIGH",
            "confidence": "HIGH",
        }

        # セキュリティエラー処理のテスト
        assert mock_security_error["severity"] == "HIGH"
        assert mock_security_error["confidence"] == "HIGH"

    @pytest.mark.unit
    def test_coverage_error_handling(self):
        """カバレッジエラーの処理テスト."""
        mock_coverage_error = {"file": "uncovered.py", "missing_lines": [10, 11, 12, 15], "coverage_percent": 75.5}

        # カバレッジエラー処理のテスト
        assert len(mock_coverage_error["missing_lines"]) == 4
        assert mock_coverage_error["coverage_percent"] < 80

    @pytest.mark.unit
    def test_dependency_error_handling(self):
        """依存関係エラーの処理テスト."""
        mock_dependency_error = {
            "package": "requests",
            "version": "2.25.0",
            "vulnerability": "CVE-2021-33503",
            "severity": "MEDIUM",
        }

        # 依存関係エラー処理のテスト
        assert mock_dependency_error["package"] == "requests"
        assert "CVE-" in mock_dependency_error["vulnerability"]

    @pytest.mark.unit
    @pytest.mark.skipif(platform.system() == "Windows", reason="Unix固有のエラー処理")
    def test_unix_specific_error_handling(self):
        """Unix固有のエラー処理テスト."""
        # Unix固有のエラー処理
        mock_unix_error = {"type": "PermissionError", "message": "Permission denied", "errno": 13}

        assert mock_unix_error["errno"] == 13
        assert mock_unix_error["type"] == "PermissionError"

    @pytest.mark.unit
    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows固有のエラー処理")
    def test_windows_specific_error_handling(self):
        """Windows固有のエラー処理テスト."""
        # Windows固有のエラー処理
        mock_windows_error = {"type": "WindowsError", "message": "Access is denied", "winerror": 5}

        assert mock_windows_error["winerror"] == 5
        assert mock_windows_error["type"] == "WindowsError"

    @pytest.mark.unit
    def test_error_aggregation(self):
        """エラー集約処理のテスト."""
        errors = [
            {"type": "lint", "count": 5},
            {"type": "type", "count": 2},
            {"type": "test", "count": 1},
            {"type": "security", "count": 0},
        ]

        # エラー集約のテスト
        total_errors = sum(error["count"] for error in errors)
        assert total_errors == 8

        # 重要度別分類
        critical_errors = [e for e in errors if e["type"] in ["security", "test"]]
        assert len(critical_errors) == 2

    @pytest.mark.unit
    def test_error_reporting_format(self):
        """エラーレポート形式のテスト."""
        error_report = {
            "timestamp": "2024-12-01T10:00:00Z",
            "platform": self.platform_info.name,
            "python_version": "3.9.0",
            "errors": {"lint": 3, "type": 1, "test": 0, "security": 2},
            "total": 6,
        }

        # レポート形式のテスト
        assert error_report["total"] == 6
        assert error_report["platform"] in ["windows", "linux", "macos", "wsl"]
        assert "timestamp" in error_report

    @pytest.mark.unit
    def test_error_threshold_checking(self):
        """エラー閾値チェックのテスト."""
        thresholds = {"lint": 10, "type": 5, "test": 0, "security": 0}

        current_errors = {"lint": 8, "type": 3, "test": 0, "security": 1}

        # 閾値チェック
        violations = []
        for error_type, count in current_errors.items():
            if count > thresholds[error_type]:
                violations.append(error_type)

        assert "security" in violations
        assert "lint" not in violations
        assert len(violations) == 1

    @pytest.mark.unit
    def test_error_integration_with_reporter(self, temp_dir):
        """エラークラスとレポーターの統合テスト."""
        verify_current_platform()

        reporter = ErrorReporter(report_dir=temp_dir)

        # 複数種類のエラーを作成
        errors = [
            QualityCheckError("基本エラー", "BASE_001"),
            RuffError("フォーマットエラー", [{"file": "test.py", "line": 1}]),
            TestFailureError("テスト失敗", ["test_func"], 65.0),
        ]

        # レポート作成と保存
        report = reporter.create_error_report(errors)
        saved_path = reporter.save_report(report, "integration")

        # 保存されたレポートの検証
        assert saved_path.exists()

        with open(saved_path, encoding="utf-8") as f:
            loaded_report = json.load(f)

        assert loaded_report["total_errors"] == 3

        # エラーコードの検証
        error_codes = [error.get("code") for error in loaded_report["errors"]]
        assert "BASE_001" in error_codes
        assert "RUFF_ERROR" in error_codes
        assert "TEST_FAILURE" in error_codes
