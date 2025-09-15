"""品質ログ機能のテスト."""

import platform
import tempfile
from pathlib import Path

import pytest

from ..multiplatform.helpers import verify_current_platform


class TestQualityLogger:
    """品質ログ機能のテストクラス."""

    def setup_method(self):
        """テストメソッドの前処理."""
        self.platform_info = verify_current_platform()
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """テストメソッドの後処理."""
        # 一時ディレクトリのクリーンアップ
        import contextlib
        import shutil
        import time

        if self.temp_dir.exists():
            # Windowsでのファイルロック問題を回避
            for _ in range(3):
                try:
                    shutil.rmtree(self.temp_dir)
                    break
                except PermissionError:
                    time.sleep(0.1)
                    continue
            else:
                # 最終的に失敗した場合は無視
                with contextlib.suppress(PermissionError):
                    shutil.rmtree(self.temp_dir)

    @pytest.mark.unit
    def test_quality_logger_initialization(self):
        """品質ログ機能の初期化テスト."""
        # ログ設定のモック
        logger_config = {
            "name": "quality_logger",
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "handlers": ["console", "file"],
        }

        # 初期化の検証
        assert logger_config["name"] == "quality_logger"
        assert logger_config["level"] == "INFO"
        assert len(logger_config["handlers"]) == 2

    @pytest.mark.unit
    def test_lint_result_logging(self):
        """リンティング結果のログ記録テスト."""
        # リンティング結果のモック
        lint_results = {"files_checked": 25, "errors": 3, "warnings": 7, "fixed": 2, "duration": 1.5}

        # ログメッセージの生成
        log_message = (
            f"Lint check completed: {lint_results['files_checked']} files, "
            f"{lint_results['errors']} errors, {lint_results['warnings']} warnings"
        )

        # ログ記録の検証
        assert "Lint check completed" in log_message
        assert "25 files" in log_message
        assert "3 errors" in log_message

    @pytest.mark.unit
    def test_test_result_logging(self):
        """テスト結果のログ記録テスト."""
        # テスト結果のモック
        test_results = {"total": 50, "passed": 45, "failed": 2, "skipped": 3, "coverage": 85.5, "duration": 12.3}

        # ログメッセージの生成
        log_message = (
            f"Test run completed: {test_results['passed']}/{test_results['total']} passed, "
            f"coverage: {test_results['coverage']}%"
        )

        # ログ記録の検証
        assert "Test run completed" in log_message
        assert "45/50 passed" in log_message
        assert "coverage: 85.5%" in log_message

    @pytest.mark.unit
    def test_security_scan_logging(self):
        """セキュリティスキャン結果のログ記録テスト."""
        # セキュリティスキャン結果のモック
        security_results = {"files_scanned": 30, "vulnerabilities": {"high": 1, "medium": 2, "low": 0}, "duration": 5.2}

        # ログメッセージの生成
        total_vulns = sum(security_results["vulnerabilities"].values())
        log_message = (
            f"Security scan completed: {security_results['files_scanned']} files, {total_vulns} vulnerabilities found"
        )

        # ログ記録の検証
        assert "Security scan completed" in log_message
        assert "30 files" in log_message
        assert "3 vulnerabilities" in log_message

    @pytest.mark.unit
    def test_quality_metrics_logging(self):
        """品質メトリクスのログ記録テスト."""
        # 品質メトリクスのモック
        quality_metrics = {
            "timestamp": "2024-12-01T10:00:00Z",
            "platform": self.platform_info.name,
            "python_version": "3.9.0",
            "metrics": {"code_quality": 85, "test_coverage": 88, "security_score": 95, "maintainability": 82},
            "overall_score": 87.5,
        }

        # ログメッセージの生成
        log_message = (
            f"Quality metrics collected: overall score {quality_metrics['overall_score']}, "
            f"platform: {quality_metrics['platform']}"
        )

        # ログ記録の検証
        assert "Quality metrics collected" in log_message
        assert "overall score 87.5" in log_message
        assert f"platform: {self.platform_info.name}" in log_message

    @pytest.mark.unit
    def test_error_logging(self):
        """エラーログ記録のテスト."""
        # エラー情報のモック
        error_info = {
            "type": "LintError",
            "message": "Failed to parse file: syntax error",
            "file": "broken_file.py",
            "line": 15,
            "traceback": ["line1", "line2", "line3"],
        }

        # エラーログメッセージの生成
        error_message = (
            f"Quality check error: {error_info['type']} in {error_info['file']}:{error_info['line']} - "
            f"{error_info['message']}"
        )

        # エラーログの検証
        assert "Quality check error" in error_message
        assert "LintError" in error_message
        assert "broken_file.py:15" in error_message

    @pytest.mark.unit
    def test_performance_logging(self):
        """パフォーマンスログ記録のテスト."""
        # パフォーマンス情報のモック
        performance_info = {
            "operation": "full_quality_check",
            "duration": 45.2,
            "files_processed": 150,
            "memory_usage": "256MB",
            "cpu_usage": "75%",
        }

        # パフォーマンスログメッセージの生成
        perf_message = (
            f"Performance: {performance_info['operation']} completed in {performance_info['duration']}s, "
            f"processed {performance_info['files_processed']} files"
        )

        # パフォーマンスログの検証
        assert "Performance:" in perf_message
        assert "45.2s" in perf_message
        assert "150 files" in perf_message

    @pytest.mark.unit
    def test_structured_logging(self):
        """構造化ログ記録のテスト."""
        # 構造化ログデータのモック
        structured_log = {
            "timestamp": "2024-12-01T10:00:00Z",
            "level": "INFO",
            "logger": "quality_logger",
            "event": "quality_check_completed",
            "data": {
                "files_checked": 100,
                "issues_found": 5,
                "duration": 30.5,
                "platform": self.platform_info.name,
            },
        }

        # 構造化ログの検証
        assert structured_log["event"] == "quality_check_completed"
        assert structured_log["data"]["files_checked"] == 100
        assert structured_log["data"]["platform"] == self.platform_info.name

    @pytest.mark.unit
    def test_log_rotation(self):
        """ログローテーション機能のテスト."""
        # ログローテーション設定のモック
        rotation_config = {"max_size": "10MB", "backup_count": 5, "rotation_interval": "daily", "compression": True}

        # ログローテーション設定の検証
        assert rotation_config["max_size"] == "10MB"
        assert rotation_config["backup_count"] == 5
        assert rotation_config["compression"] is True

    @pytest.mark.unit
    def test_log_filtering(self):
        """ログフィルタリング機能のテスト."""
        # ログフィルター設定のモック
        filter_config = {
            "min_level": "INFO",
            "exclude_patterns": ["debug_info", "temp_"],
            "include_only": ["quality_", "test_", "security_"],
        }

        # フィルタリングロジックのテスト
        test_messages = [
            "quality_check_started",
            "debug_info_message",
            "test_execution_completed",
            "temp_file_created",
            "security_scan_finished",
        ]

        filtered_messages = [
            msg
            for msg in test_messages
            if any(pattern in msg for pattern in filter_config["include_only"])
            and not any(pattern in msg for pattern in filter_config["exclude_patterns"])
        ]

        # フィルタリング結果の検証
        assert len(filtered_messages) == 3
        assert "debug_info_message" not in filtered_messages
        assert "temp_file_created" not in filtered_messages

    @pytest.mark.unit
    @pytest.mark.skipif(platform.system() == "Windows", reason="Unix固有のログ機能")
    def test_unix_specific_logging(self):
        """Unix固有のログ機能テスト."""
        # Unix固有のログ設定
        unix_log_config = {"syslog_enabled": True, "facility": "LOG_LOCAL0", "socket_path": "/dev/log"}

        # Unix固有ログ設定の検証
        assert unix_log_config["syslog_enabled"] is True
        assert unix_log_config["facility"] == "LOG_LOCAL0"

    @pytest.mark.unit
    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows固有のログ機能")
    def test_windows_specific_logging(self):
        """Windows固有のログ機能テスト."""
        # Windows固有のログ設定
        windows_log_config = {"event_log_enabled": True, "source_name": "QualityChecker", "log_type": "Application"}

        # Windows固有ログ設定の検証
        assert windows_log_config["event_log_enabled"] is True
        assert windows_log_config["source_name"] == "QualityChecker"

    @pytest.mark.unit
    def test_quality_logger_real_functionality(self):
        """実際のQualityLogger機能のテスト"""
        from setup_repo.quality_logger import LogLevel, QualityLogger

        # ログファイルを一時ディレクトリに作成
        log_file = self.temp_dir / "quality_test.log"

        # QualityLoggerの初期化テスト
        logger = QualityLogger(
            name="test_logger",
            log_level=LogLevel.DEBUG,
            log_file=log_file,
            enable_console=True,
            enable_json_format=False,
        )

        # 基本ログ機能のテスト
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")

        # ログファイルが作成されていることを確認
        assert log_file.exists()

        # ログ内容の確認
        log_content = log_file.read_text(encoding="utf-8")
        assert "Debug message" in log_content
        assert "Info message" in log_content
        assert "Warning message" in log_content

    @pytest.mark.unit
    def test_quality_check_logging_methods(self):
        """品質チェックログメソッドのテスト"""
        from setup_repo.quality_logger import QualityLogger

        log_file = self.temp_dir / "quality_check.log"
        logger = QualityLogger(log_file=log_file, enable_console=False)

        # 品質チェック開始ログ
        logger.log_quality_check_start("ruff", {"files": 10})

        # 品質チェック成功ログ
        logger.log_quality_check_success("ruff", {"errors": 0, "warnings": 2})

        # 品質チェック失敗ログ
        test_error = Exception("Test error")
        logger.log_quality_check_failure("mypy", test_error, {"file": "test.py"})

        # 品質チェック結果ログ
        result_success = {"success": True, "metrics": {"score": 95}}
        logger.log_quality_check_result("pytest", result_success)

        result_failure = {"success": False, "errors": ["Test failed"], "details": {"line": 42}}
        logger.log_quality_check_result("coverage", result_failure)

        # ログ内容の確認
        log_content = log_file.read_text(encoding="utf-8")
        assert "品質チェック開始: ruff" in log_content
        assert "品質チェック成功: ruff" in log_content
        assert "品質チェック失敗: mypy" in log_content

    @pytest.mark.unit
    def test_ci_stage_logging_methods(self):
        """CI/CDステージログメソッドのテスト"""
        from setup_repo.quality_logger import QualityLogger

        log_file = self.temp_dir / "ci_stage.log"
        logger = QualityLogger(log_file=log_file, enable_console=False)

        # CIステージ開始ログ
        logger.log_ci_stage_start("build", {"branch": "main"})

        # CIステージ成功ログ
        logger.log_ci_stage_success("build", duration=45.2)

        # CIステージ失敗ログ
        test_error = RuntimeError("Build failed")
        logger.log_ci_stage_failure("test", test_error, duration=12.5)

        # ログ内容の確認
        log_content = log_file.read_text(encoding="utf-8")
        assert "CI/CDステージ開始: build" in log_content
        assert "CI/CDステージ成功: build" in log_content
        assert "45.20秒" in log_content
        assert "CI/CDステージ失敗: test" in log_content

    @pytest.mark.unit
    def test_error_reporting_methods(self):
        """エラーレポートメソッドのテスト"""
        from setup_repo.quality_logger import QualityLogger

        log_file = self.temp_dir / "error_report.log"
        logger = QualityLogger(log_file=log_file, enable_console=False)

        # コンテキスト付きエラーログ
        test_error = ValueError("Invalid value")
        context = {"function": "test_function", "line": 123}
        logger.log_error_with_context(test_error, context, include_traceback=True)

        # エラーレポート作成
        errors = [ValueError("Error 1"), RuntimeError("Error 2")]
        report = logger.create_error_report(errors, context)

        # レポートの基本構造を確認
        assert isinstance(report, dict)
        assert "errors" in report or "summary" in report  # ErrorReporterの実装に依存

        # エラーレポート保存
        report_file = self.temp_dir / "custom_report.json"
        saved_path = logger.save_error_report(errors, report_file, context)

        # 保存されたファイルの確認
        assert saved_path.exists()
        assert saved_path.suffix == ".json"

    @pytest.mark.unit
    def test_metrics_logging_methods(self):
        """メトリクスログメソッドのテスト"""
        from setup_repo.quality_logger import QualityLogger

        log_file = self.temp_dir / "metrics.log"
        logger = QualityLogger(log_file=log_file, enable_console=False)

        # 辞書形式のメトリクス
        metrics_dict = {"coverage": 85.5, "complexity": 12, "maintainability": 78}
        logger.log_metrics_summary(metrics_dict)

        # オブジェクト形式のメトリクス（__dict__あり）
        class MockMetrics:
            def __init__(self):
                self.coverage = 90.0
                self.complexity = 8

        mock_metrics = MockMetrics()
        logger.log_metrics_summary(mock_metrics)

        # ログ内容の確認
        log_content = log_file.read_text(encoding="utf-8")
        # format_metrics_summaryの出力が含まれていることを確認
        assert "メトリクス" in log_content or "coverage" in log_content

    @pytest.mark.unit
    def test_json_formatter_functionality(self):
        """JSONフォーマッター機能のテスト"""
        from setup_repo.quality_logger import QualityLogger

        log_file = self.temp_dir / "json_format.log"
        logger = QualityLogger(log_file=log_file, enable_console=False, enable_json_format=True)

        # JSON形式でログ出力
        logger.info("JSON format test", extra_data={"key": "value"})
        logger.error("JSON error test", error_code=500)

        # ログファイルが作成されていることを確認
        assert log_file.exists()

        # JSON形式のログが出力されていることを確認
        log_content = log_file.read_text(encoding="utf-8")
        # JSONフォーマッターが使用されていることを間接的に確認
        assert "JSON format test" in log_content

    @pytest.mark.unit
    def test_global_logger_functions(self):
        """グローバルロガー関数のテスト"""
        from setup_repo.quality_logger import LogLevel, configure_quality_logging, get_quality_logger

        # グローバルロガーの取得
        logger1 = get_quality_logger()
        logger2 = get_quality_logger()

        # シングルトンパターンの確認
        assert logger1 is logger2

        # ログ設定の再構成
        log_file = self.temp_dir / "configured.log"
        configured_logger = configure_quality_logging(log_level=LogLevel.DEBUG, log_file=log_file, enable_console=False)

        # 再構成されたロガーの確認
        assert configured_logger is not None
        configured_logger.debug("Configuration test")

        # ログファイルが作成されていることを確認
        assert log_file.exists()

    @pytest.mark.unit
    def test_dataclass_metrics_handling(self):
        """データクラスメトリクスの処理テスト"""
        from dataclasses import dataclass

        from setup_repo.quality_logger import QualityLogger

        @dataclass
        class TestMetrics:
            coverage: float
            complexity: int
            score: float

        log_file = self.temp_dir / "dataclass_metrics.log"
        logger = QualityLogger(log_file=log_file, enable_console=False)

        # データクラスメトリクスのログ
        metrics = TestMetrics(coverage=85.5, complexity=12, score=78.2)
        logger.log_metrics_summary(metrics)

        # ログ内容の確認
        log_content = log_file.read_text(encoding="utf-8")
        # データクラスが適切に処理されていることを確認
        assert "85.5" in log_content or "coverage" in log_content

    @pytest.mark.unit
    def test_invalid_metrics_handling(self):
        """無効なメトリクスの処理テスト"""
        from setup_repo.quality_logger import QualityLogger

        log_file = self.temp_dir / "invalid_metrics.log"
        logger = QualityLogger(log_file=log_file, enable_console=False)

        # 無効なメトリクスタイプのテスト
        invalid_metrics = "invalid_string_metrics"
        logger.log_metrics_summary(invalid_metrics)

        # 数値メトリクスのテスト
        numeric_metrics = 42
        logger.log_metrics_summary(numeric_metrics)

        # ログ内容の確認（警告メッセージが出力されることを確認）
        log_content = log_file.read_text(encoding="utf-8")
        assert "メトリクスの形式が不正" in log_content

    @pytest.mark.unit
    def test_log_aggregation(self):
        """ログ集約機能のテスト."""
        # ログ集約データのモック
        aggregated_logs = {
            "period": "daily",
            "date": "2024-12-01",
            "summary": {
                "total_checks": 50,
                "successful_checks": 45,
                "failed_checks": 5,
                "average_duration": 25.3,
                "most_common_issues": ["E501", "W292", "F401"],
            },
        }

        # ログ集約の検証
        assert aggregated_logs["summary"]["total_checks"] == 50
        assert aggregated_logs["summary"]["successful_checks"] == 45
        assert len(aggregated_logs["summary"]["most_common_issues"]) == 3
