"""品質メトリクス収集機能のテスト"""

import json
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

from setup_repo.quality_metrics import (
    BuildResult,
    QualityCheckStatus,
    QualityLogger,
    QualityMetrics,
    QualityMetricsCollector,
)


class TestQualityMetrics:
    """QualityMetricsクラスのテスト"""

    def test_quality_metrics_initialization(self):
        """QualityMetricsの初期化テスト"""
        metrics = QualityMetrics()

        assert metrics.ruff_issues == 0
        assert metrics.mypy_errors == 0
        assert metrics.test_coverage == 0.0
        assert metrics.test_passed == 0
        assert metrics.test_failed == 0
        assert metrics.security_vulnerabilities == 0
        assert metrics.timestamp != ""
        assert metrics.commit_hash != ""

    def test_quality_metrics_with_values(self):
        """値を指定したQualityMetricsのテスト"""
        metrics = QualityMetrics(
            ruff_issues=5,
            mypy_errors=3,
            test_coverage=85.5,
            test_passed=20,
            test_failed=2,
            security_vulnerabilities=1,
            timestamp="2024-01-01T00:00:00",
            commit_hash="abc12345",
        )

        assert metrics.ruff_issues == 5
        assert metrics.mypy_errors == 3
        assert metrics.test_coverage == 85.5
        assert metrics.test_passed == 20
        assert metrics.test_failed == 2
        assert metrics.security_vulnerabilities == 1
        assert metrics.timestamp == "2024-01-01T00:00:00"
        assert metrics.commit_hash == "abc12345"

    def test_is_passing_success(self):
        """品質基準を満たす場合のテスト"""
        metrics = QualityMetrics(
            ruff_issues=0,
            mypy_errors=0,
            test_coverage=85.0,
            test_passed=20,
            test_failed=0,
            security_vulnerabilities=0,
        )

        assert metrics.is_passing(80.0) is True

    def test_is_passing_failure_coverage(self):
        """カバレッジ不足で品質基準を満たさない場合のテスト"""
        metrics = QualityMetrics(
            ruff_issues=0,
            mypy_errors=0,
            test_coverage=75.0,  # 80%未満
            test_passed=20,
            test_failed=0,
            security_vulnerabilities=0,
        )

        assert metrics.is_passing(80.0) is False

    def test_is_passing_failure_ruff_issues(self):
        """Ruffエラーで品質基準を満たさない場合のテスト"""
        metrics = QualityMetrics(
            ruff_issues=1,  # エラーあり
            mypy_errors=0,
            test_coverage=85.0,
            test_passed=20,
            test_failed=0,
            security_vulnerabilities=0,
        )

        assert metrics.is_passing(80.0) is False

    def test_get_quality_score_perfect(self):
        """完璧な品質スコアのテスト"""
        metrics = QualityMetrics(
            ruff_issues=0,
            mypy_errors=0,
            test_coverage=100.0,
            test_passed=20,
            test_failed=0,
            security_vulnerabilities=0,
        )

        assert metrics.get_quality_score() == 100.0

    def test_get_quality_score_with_issues(self):
        """問題がある場合の品質スコアのテスト"""
        metrics = QualityMetrics(
            ruff_issues=5,  # -10点
            mypy_errors=2,  # -6点
            test_coverage=70.0,  # -5点 (80-70)*0.5
            test_passed=18,
            test_failed=1,  # -5点
            security_vulnerabilities=1,  # -10点
        )

        # 100 - 10 - 6 - 5 - 5 - 10 = 64
        expected_score = 64.0
        assert metrics.get_quality_score() == expected_score


class TestBuildResult:
    """BuildResultクラスのテスト"""

    def test_build_result_to_dict(self):
        """BuildResultの辞書変換テスト"""
        metrics = QualityMetrics(ruff_issues=1, test_coverage=85.0)
        result = BuildResult(
            status=QualityCheckStatus.FAILED,
            metrics=metrics,
            errors=["エラー1", "エラー2"],
            warnings=["警告1"],
            duration_seconds=30.5,
        )

        result_dict = result.to_dict()

        assert result_dict["status"] == "failed"
        assert result_dict["errors"] == ["エラー1", "エラー2"]
        assert result_dict["warnings"] == ["警告1"]
        assert result_dict["duration_seconds"] == 30.5
        assert "metrics" in result_dict


class TestQualityLogger:
    """QualityLoggerクラスのテスト"""

    def test_quality_logger_initialization(self):
        """QualityLoggerの初期化テスト"""
        logger = QualityLogger()
        assert logger.logger.name == "setup_repo.quality"

    def test_log_quality_check_start(self, caplog):
        """品質チェック開始ログのテスト"""
        logger = QualityLogger()
        logger.log_quality_check_start("Ruff")

        assert "品質チェック開始: Ruff" in caplog.text

    def test_log_quality_check_result_success(self, caplog):
        """成功時の品質チェック結果ログのテスト"""
        logger = QualityLogger()
        result = {"success": True}
        logger.log_quality_check_result("Ruff", result)

        assert "品質チェック成功: Ruff" in caplog.text

    def test_log_quality_check_result_failure(self, caplog):
        """失敗時の品質チェック結果ログのテスト"""
        logger = QualityLogger()
        result = {"success": False, "errors": ["エラー1", "エラー2"]}
        logger.log_quality_check_result("Ruff", result)

        assert "品質チェック失敗: Ruff" in caplog.text

    def test_log_metrics_summary(self, caplog):
        """メトリクス概要ログのテスト"""
        logger = QualityLogger()
        metrics = QualityMetrics(ruff_issues=2, mypy_errors=1, test_coverage=85.0, security_vulnerabilities=0)

        logger.log_metrics_summary(metrics)

        assert "品質メトリクス概要" in caplog.text
        assert "test_coverage: 85.0" in caplog.text
        assert "ruff_issues: 2" in caplog.text
        assert "mypy_errors: 1" in caplog.text


class TestQualityMetricsCollector:
    """QualityMetricsCollectorクラスのテスト"""

    def test_collector_initialization(self):
        """QualityMetricsCollectorの初期化テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            collector = QualityMetricsCollector(project_root)

            assert collector.project_root == project_root
            assert collector.logger is not None

    @patch("subprocess.run")
    def test_collect_ruff_metrics_success(self, mock_run):
        """Ruffメトリクス収集成功のテスト"""
        # subprocess.runのモック設定
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "[]"  # エラーなし

        collector = QualityMetricsCollector()
        result = collector.collect_ruff_metrics()

        assert result["success"] is True
        assert result["issue_count"] == 0
        assert result["errors"] == []

    @patch("subprocess.run")
    def test_collect_ruff_metrics_with_issues(self, mock_run):
        """Ruffメトリクス収集でエラーがある場合のテスト"""
        # subprocess.runのモック設定
        mock_run.return_value.returncode = 1
        mock_run.return_value.stdout = '[{"code": "E501", "message": "line too long"}]'

        collector = QualityMetricsCollector()
        result = collector.collect_ruff_metrics()

        assert result["success"] is False
        assert result["issue_count"] == 1
        assert result["errors"]

    @patch("subprocess.run")
    def test_collect_mypy_metrics_success(self, mock_run):
        """MyPyメトリクス収集成功のテスト"""
        # subprocess.runのモック設定
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""  # エラーなし

        collector = QualityMetricsCollector()
        result = collector.collect_mypy_metrics()

        assert result["success"] is True
        assert result["error_count"] == 0
        assert result["errors"] == []

    @patch("subprocess.run")
    def test_collect_mypy_metrics_with_errors(self, mock_run):
        """MyPyメトリクス収集でエラーがある場合のテスト"""
        # subprocess.runのモック設定
        mock_run.return_value.returncode = 1
        mock_run.return_value.stdout = "file.py:10: error: Missing type annotation\nfile.py:20: error: Invalid type"

        collector = QualityMetricsCollector()
        result = collector.collect_mypy_metrics()

        assert result["success"] is False
        assert result["error_count"] == 2
        assert result["errors"]

    @patch("subprocess.run")
    def test_collect_test_metrics_success(self, mock_run):
        """テストメトリクス収集成功のテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)

            # カバレッジファイルのモック
            coverage_file = project_root / "coverage.json"
            coverage_data = {"totals": {"percent_covered": 85.5}}
            with open(coverage_file, "w") as f:
                json.dump(coverage_data, f)

            # テストレポートファイルのモック
            test_report_file = project_root / "test-report.json"
            test_data = {"summary": {"passed": 20, "failed": 0}}
            with open(test_report_file, "w") as f:
                json.dump(test_data, f)

            # subprocess.runのモック設定
            mock_run.return_value.returncode = 0

            collector = QualityMetricsCollector(project_root)
            result = collector.collect_test_metrics()

            assert result["success"] is True
            assert result["coverage_percent"] == 85.5
            assert result["tests_passed"] == 20
            assert result["tests_failed"] == 0

    @patch("subprocess.run")
    def test_collect_security_metrics_success(self, mock_run):
        """セキュリティメトリクス収集成功のテスト"""

        # subprocess.runのモック設定（BanditとSafety両方とも問題なし）
        def mock_subprocess_side_effect(*args, **kwargs):
            mock_result = type("MockResult", (), {})()
            mock_result.returncode = 0

            command = args[0]
            if "bandit" in command:
                mock_result.stdout = '{"results": []}'
            elif "safety" in command:
                mock_result.stdout = "[]"
            else:
                mock_result.stdout = ""

            return mock_result

        mock_run.side_effect = mock_subprocess_side_effect

        collector = QualityMetricsCollector()
        result = collector.collect_security_metrics()

        assert result["success"] is True
        assert result["vulnerability_count"] == 0
        assert result["errors"] == []

    def test_save_metrics_report(self):
        """メトリクスレポート保存のテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            collector = QualityMetricsCollector(project_root)

            metrics = QualityMetrics(
                ruff_issues=1,
                test_coverage=85.0,
                timestamp="2024-01-01T00:00:00",
                commit_hash="abc12345",
            )

            report_file = collector.save_metrics_report(metrics)

            assert report_file.exists()

            # レポート内容を確認
            with open(report_file, encoding="utf-8") as f:
                report_data = json.load(f)

            assert report_data["timestamp"] == "2024-01-01T00:00:00"
            assert report_data["commit_hash"] == "abc12345"
            assert report_data["metrics"]["ruff_issues"] == 1
            assert report_data["metrics"]["test_coverage"] == 85.0
            assert "quality_score" in report_data
            assert "passing" in report_data

    def test_save_metrics_report_custom_path(self):
        """カスタムパスでのメトリクスレポート保存のテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            collector = QualityMetricsCollector(project_root)
            custom_path = project_root / "custom" / "report.json"

            metrics = QualityMetrics(test_coverage=90.0)
            report_file = collector.save_metrics_report(metrics, custom_path)

            assert report_file == custom_path
            assert report_file.exists()
            assert report_file.parent.exists()  # ディレクトリが作成されている

    @patch("subprocess.run")
    @patch("os.getenv")
    def test_collect_security_metrics_with_vulnerabilities(self, mock_getenv, mock_run):
        """セキュリティ脆弱性が見つかった場合のテスト"""
        # CI環境ではない場合をシミュレート
        mock_getenv.side_effect = lambda key, default="": "false" if key == "CI" else default

        def mock_subprocess_side_effect(*args, **kwargs):
            mock_result = type("MockResult", (), {})()

            command = args[0] if args else []
            command_str = " ".join(command) if isinstance(command, list) else str(command)

            if "--version" in command_str:
                # ツールのバージョンチェックは成功させる
                mock_result.returncode = 0
                mock_result.stdout = "tool version 1.0.0"
            elif "bandit" in command_str and "-r" in command_str:
                # Banditスキャンで脆弱性を発見
                mock_result.returncode = 1
                mock_result.stdout = '{"results": [{"issue_severity": "HIGH", "issue_text": "Test vulnerability"}]}'
            elif "safety" in command_str and "check" in command_str:
                # Safetyチェックで脆弱性を発見
                mock_result.returncode = 1
                mock_result.stdout = '[{"vulnerability": "Test safety issue"}]'
            else:
                mock_result.returncode = 0
                mock_result.stdout = ""

            return mock_result

        mock_run.side_effect = mock_subprocess_side_effect

        collector = QualityMetricsCollector()
        result = collector.collect_security_metrics()

        # ローカル環境では脆弱性が見つかった場合は失敗となる
        assert result["success"] is False
        assert "vulnerability_count" in result
        assert result["vulnerability_count"] >= 1
        assert "vulnerabilities" in result
        assert len(result["vulnerabilities"]) >= 1

    @patch("subprocess.run")
    def test_collect_security_metrics_json_decode_error(self, mock_run):
        """JSONデコードエラーが発生した場合のテスト"""

        def mock_subprocess_side_effect(*args, **kwargs):
            mock_result = type("MockResult", (), {})()
            mock_result.returncode = 0
            mock_result.stdout = "invalid json"
            return mock_result

        mock_run.side_effect = mock_subprocess_side_effect

        collector = QualityMetricsCollector()
        result = collector.collect_security_metrics()

        assert result["success"] is True
        assert result["vulnerability_count"] == 0

    @patch("subprocess.run")
    def test_collect_security_metrics_file_not_found_error(self, mock_run):
        """ファイルが見つからない場合のテスト"""

        # ツールが利用できない場合のシミュレーション
        def mock_subprocess_side_effect(*args, **kwargs):
            command = args[0] if args else []
            command_str = " ".join(command) if isinstance(command, list) else str(command)

            if "--version" in command_str:
                # バージョンチェックでツールが見つからない
                raise FileNotFoundError("Command not found")
            else:
                # 実際のスキャンでもエラー
                raise FileNotFoundError("Command not found")

        mock_run.side_effect = mock_subprocess_side_effect

        collector = QualityMetricsCollector()
        result = collector.collect_security_metrics()

        # ツールが利用できない場合は成功となる（脆弱性は見つからない）
        assert result["success"] is True
        assert result["vulnerability_count"] == 0
        assert "vulnerabilities" in result
        assert "no_tools_available" in result
        assert result["no_tools_available"] is True

    @patch("subprocess.run")
    def test_collect_all_metrics_integration(self, mock_run):
        """すべてのメトリクス収集の統合テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)

            # カバレッジファイルのモック
            coverage_file = project_root / "coverage.json"
            coverage_data = {"totals": {"percent_covered": 88.5}}
            with open(coverage_file, "w") as f:
                json.dump(coverage_data, f)

            # テストレポートファイルのモック
            test_report_file = project_root / "test-report.json"
            test_data = {"summary": {"passed": 25, "failed": 1}}
            with open(test_report_file, "w") as f:
                json.dump(test_data, f)

            # subprocess.runのモック設定
            def mock_subprocess_side_effect(*args, **kwargs):
                mock_result = type("MockResult", (), {})()
                command = args[0]

                if "ruff" in command:
                    mock_result.returncode = 1
                    mock_result.stdout = '[{"code": "E501"}]'
                elif "mypy" in command:
                    mock_result.returncode = 1
                    mock_result.stdout = "file.py:10: error: Missing type"
                elif "pytest" in command:
                    mock_result.returncode = 0
                elif "bandit" in command:
                    mock_result.returncode = 0
                    mock_result.stdout = '{"results": []}'
                elif "safety" in command:
                    mock_result.returncode = 0
                    mock_result.stdout = "[]"
                else:
                    mock_result.returncode = 0
                    mock_result.stdout = ""

                return mock_result

            mock_run.side_effect = mock_subprocess_side_effect

            collector = QualityMetricsCollector(project_root)
            metrics = collector.collect_all_metrics()

            assert metrics.ruff_issues == 1
            assert metrics.mypy_errors == 1
            assert metrics.test_coverage == 88.5
            assert metrics.test_passed == 25
            assert metrics.test_failed == 1
            assert metrics.security_vulnerabilities == 0

    def test_quality_metrics_edge_cases(self):
        """QualityMetricsのエッジケーステスト"""
        # 極端な値でのテスト
        metrics = QualityMetrics(
            ruff_issues=1000,  # 大量のエラー
            mypy_errors=500,
            test_coverage=0.0,  # 最低カバレッジ
            test_passed=0,
            test_failed=100,
            security_vulnerabilities=50,
        )

        # 品質スコアが0以下にならないことを確認
        score = metrics.get_quality_score()
        assert score == 0.0

        # 品質基準を満たさないことを確認
        assert metrics.is_passing() is False

    def test_quality_metrics_items_method(self):
        """QualityMetricsのitemsメソッドテスト"""
        metrics = QualityMetrics(ruff_issues=5, test_coverage=75.0)
        items = dict(metrics.items())

        assert "ruff_issues" in items
        assert items["ruff_issues"] == 5
        assert "test_coverage" in items
        assert items["test_coverage"] == 75.0

    def test_quality_metrics_to_dict_method(self):
        """QualityMetricsのto_dictメソッドテスト"""
        metrics = QualityMetrics(mypy_errors=3, test_passed=20)
        result_dict = metrics.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["mypy_errors"] == 3
        assert result_dict["test_passed"] == 20

    @patch("subprocess.run")
    def test_get_current_commit_hash_error(self, mock_run):
        """コミットハッシュ取得エラーのテスト"""
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        metrics = QualityMetrics()
        assert metrics.commit_hash == "unknown"

    @patch("subprocess.run")
    def test_get_current_commit_hash_file_not_found(self, mock_run):
        """Gitコマンドが見つからない場合のテスト"""
        mock_run.side_effect = FileNotFoundError()

        metrics = QualityMetrics()
        assert metrics.commit_hash == "unknown"

    def test_quality_metrics_custom_min_coverage(self):
        """カスタム最小カバレッジでのテスト"""
        metrics = QualityMetrics(
            ruff_issues=0,
            mypy_errors=0,
            test_coverage=70.0,
            test_failed=0,
            security_vulnerabilities=0,
        )

        # デフォルト80%では失敗
        assert metrics.is_passing(80.0) is False

        # 60%では成功
        assert metrics.is_passing(60.0) is True

    @patch("subprocess.run")
    def test_collect_test_metrics_with_parallel_workers(self, mock_run):
        """並列ワーカー指定でのテストメトリクス収集テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)

            # カバレッジファイルのモック
            coverage_file = project_root / "coverage.json"
            coverage_data = {"totals": {"percent_covered": 92.0}}
            with open(coverage_file, "w") as f:
                json.dump(coverage_data, f)

            # テストレポートファイルのモック
            test_report_file = project_root / "test-report.json"
            test_data = {"summary": {"passed": 30, "failed": 0}}
            with open(test_report_file, "w") as f:
                json.dump(test_data, f)

            mock_run.return_value.returncode = 0

            collector = QualityMetricsCollector(project_root)
            result = collector.collect_test_metrics(parallel_workers=4)

            assert result["success"] is True
            assert result["coverage_percent"] == 92.0
            assert result["tests_passed"] == 30
            assert result["tests_failed"] == 0
