"""
品質ロガーのテスト
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from setup_repo.quality_logger import (
    CoverageError,
    LogLevel,
    MyPyError,
    QualityCheckError,
    QualityLogger,
    RuffError,
    SecurityScanError,
    TestFailureError,
    get_quality_logger,
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


class TestQualityLogger:
    """QualityLoggerクラスのテスト"""

    def test_logger_creation(self):
        """ロガーの作成をテスト"""
        logger = QualityLogger(
            name="test_logger",
            log_level=LogLevel.DEBUG,
            enable_console=True,
            enable_json_format=False,
        )

        assert logger.name == "test_logger"
        assert logger.log_level == LogLevel.DEBUG
        assert logger.enable_console is True
        assert logger.enable_json_format is False

    def test_logger_with_file_output(self):
        """ファイル出力付きロガーのテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"

            logger = QualityLogger(
                name="test_file_logger", log_file=log_file, enable_console=False
            )

            logger.info("テストメッセージ")

            assert log_file.exists()
            content = log_file.read_text(encoding="utf-8")
            assert "テストメッセージ" in content

    def test_json_format_logging(self):
        """JSON形式ログのテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.json"

            logger = QualityLogger(
                name="test_json_logger",
                log_file=log_file,
                enable_console=False,
                enable_json_format=True,
            )

            logger.info("JSONテストメッセージ")

            assert log_file.exists()
            content = log_file.read_text(encoding="utf-8")

            # JSON形式であることを確認
            log_entry = json.loads(content.strip())
            assert log_entry["message"] == "JSONテストメッセージ"
            assert log_entry["level"] == "INFO"

    def test_quality_check_logging(self):
        """品質チェックログのテスト"""
        logger = QualityLogger(enable_console=False)

        # 品質チェック開始ログ
        logger.log_quality_check_start("TestCheck", {"param": "value"})

        # 品質チェック成功ログ
        logger.log_quality_check_success("TestCheck", {"result": "success"})

        # 品質チェック失敗ログ
        error = QualityCheckError("テストエラー")
        logger.log_quality_check_failure("TestCheck", error)

    def test_metrics_summary_logging(self):
        """メトリクス概要ログのテスト"""
        logger = QualityLogger(enable_console=False)

        metrics = {"score": 85.5, "errors": 2, "passed": True}

        logger.log_metrics_summary(metrics)

    def test_ci_stage_logging(self):
        """CI/CDステージログのテスト"""
        logger = QualityLogger(enable_console=False)

        # ステージ開始ログ
        logger.log_ci_stage_start("TestStage", {"config": "test"})

        # ステージ成功ログ
        logger.log_ci_stage_success("TestStage", 10.5)

        # ステージ失敗ログ
        error = Exception("テストエラー")
        logger.log_ci_stage_failure("TestStage", error, 5.2)

    def test_error_with_context_logging(self):
        """コンテキスト付きエラーログのテスト"""
        logger = QualityLogger(enable_console=False)

        error = QualityCheckError(
            "コンテキストテストエラー", "TEST_ERROR", {"key": "value"}
        )
        context = {"stage": "test", "attempt": 1}

        logger.log_error_with_context(error, context, include_traceback=False)

    def test_error_report_creation(self):
        """エラーレポート作成のテスト"""
        logger = QualityLogger(enable_console=False)

        errors = [
            QualityCheckError("エラー1", "ERROR_1"),
            RuffError("エラー2", [{"file": "test.py"}]),
            MyPyError("エラー3", ["type error"]),
        ]

        context = {"test": "context"}
        report = logger.create_error_report(errors, context)

        assert report["total_errors"] == 3
        assert report["context"]["test"] == "context"
        assert len(report["errors"]) == 3
        assert report["errors"][0]["type"] == "QualityCheckError"
        assert report["errors"][1]["type"] == "RuffError"
        assert report["errors"][2]["type"] == "MyPyError"

    def test_error_report_saving(self):
        """エラーレポート保存のテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            logger = QualityLogger(enable_console=False)

            errors = [QualityCheckError("テストエラー")]
            output_file = Path(temp_dir) / "error_report.json"

            logger.save_error_report(errors, output_file)

            assert output_file.exists()

            with open(output_file, encoding="utf-8") as f:
                report = json.load(f)

            assert report["total_errors"] == 1
            assert report["errors"][0]["message"] == "テストエラー"


class TestQualityLoggerSingleton:
    """QualityLoggerシングルトンのテスト"""

    def test_get_quality_logger_singleton(self):
        """シングルトンロガーの取得をテスト"""
        logger1 = get_quality_logger()
        logger2 = get_quality_logger()

        # 同じインスタンスが返されることを確認
        assert logger1 is logger2

    @patch("setup_repo.quality_logger._default_logger", None)
    def test_get_quality_logger_with_params(self):
        """パラメータ付きロガー取得のテスト"""
        logger = get_quality_logger(
            name="test_singleton", log_level=LogLevel.DEBUG, enable_json_format=True
        )

        assert logger.name == "test_singleton"
        assert logger.log_level == LogLevel.DEBUG
        assert logger.enable_json_format is True
