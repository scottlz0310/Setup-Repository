"""
品質コレクターモジュールのテスト
"""

import json
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from setup_repo.quality_collectors import (
    QualityToolCollector,
    collect_coverage_metrics,
    collect_mypy_metrics,
    collect_pytest_metrics,
    collect_ruff_metrics,
    parse_tool_output,
)


class TestQualityToolCollector:
    """QualityToolCollectorクラスのテスト"""

    def test_collector_creation(self):
        """コレクターの作成をテスト"""
        collector = QualityToolCollector()
        
        assert collector.project_root == Path.cwd()
        assert collector.logger is not None

    def test_collector_with_custom_params(self):
        """カスタムパラメータでのコレクター作成をテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            logger = MagicMock()
            
            collector = QualityToolCollector(project_root, logger)
            
            assert collector.project_root == project_root
            assert collector.logger is logger


class TestCollectRuffMetrics:
    """collect_ruff_metricsのテスト"""

    @patch('subprocess.run')
    def test_collect_ruff_metrics_success(self, mock_run):
        """Ruffメトリクス収集成功のテスト"""
        # Ruffが成功した場合のモック
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "[]"  # 問題なし
        
        result = collect_ruff_metrics()
        
        assert result["success"] is True
        assert result["issue_count"] == 0
        assert result["issues"] == []
        assert result["errors"] == []

    @patch('subprocess.run')
    def test_collect_ruff_metrics_with_issues(self, mock_run):
        """Ruffメトリクス収集（問題あり）のテスト"""
        issues = [
            {"filename": "test.py", "message": "Line too long"},
            {"filename": "test2.py", "message": "Unused import"}
        ]
        
        mock_run.return_value.returncode = 1
        mock_run.return_value.stdout = json.dumps(issues)
        
        result = collect_ruff_metrics()
        
        assert result["success"] is False
        assert result["issue_count"] == 2
        assert result["issues"] == issues
        assert len(result["errors"]) == 1

    @patch('subprocess.run')
    def test_collect_ruff_metrics_subprocess_error(self, mock_run):
        """Ruffメトリクス収集（サブプロセスエラー）のテスト"""
        mock_run.side_effect = subprocess.CalledProcessError(1, "ruff")
        
        result = collect_ruff_metrics()
        
        assert result["success"] is False
        assert result["issue_count"] == 0
        assert len(result["errors"]) == 1

    @patch('subprocess.run')
    def test_collect_ruff_metrics_json_error(self, mock_run):
        """Ruffメトリクス収集（JSON解析エラー）のテスト"""
        mock_run.return_value.returncode = 1
        mock_run.return_value.stdout = "invalid json"
        
        result = collect_ruff_metrics()
        
        assert result["success"] is False
        assert result["issue_count"] == 0
        assert len(result["errors"]) == 1


class TestCollectMypyMetrics:
    """collect_mypy_metricsのテスト"""

    @patch('subprocess.run')
    def test_collect_mypy_metrics_success(self, mock_run):
        """MyPyメトリクス収集成功のテスト"""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "Success: no issues found"
        
        result = collect_mypy_metrics()
        
        assert result["success"] is True
        assert result["error_count"] == 0
        assert result["error_details"] == []
        assert result["errors"] == []

    @patch('subprocess.run')
    def test_collect_mypy_metrics_with_errors(self, mock_run):
        """MyPyメトリクス収集（エラーあり）のテスト"""
        stdout = """
        test.py:10: error: Incompatible types
        test.py:15: error: Missing return statement
        test2.py:5: error: Undefined variable
        """
        
        mock_run.return_value.returncode = 1
        mock_run.return_value.stdout = stdout
        
        result = collect_mypy_metrics()
        
        assert result["success"] is False
        assert result["error_count"] == 3
        assert len(result["error_details"]) == 3
        assert len(result["errors"]) == 1

    @patch('subprocess.run')
    def test_collect_mypy_metrics_subprocess_error(self, mock_run):
        """MyPyメトリクス収集（サブプロセスエラー）のテスト"""
        mock_run.side_effect = FileNotFoundError()
        
        result = collect_mypy_metrics()
        
        assert result["success"] is False
        assert result["error_count"] == 0
        assert len(result["errors"]) == 1


class TestCollectPytestMetrics:
    """collect_pytest_metricsのテスト"""

    @patch('subprocess.run')
    def test_collect_pytest_metrics_success(self, mock_run):
        """Pytestメトリクス収集成功のテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            
            # カバレッジファイルを作成
            coverage_data = {
                "totals": {"percent_covered": 85.5}
            }
            coverage_file = project_root / "coverage.json"
            with open(coverage_file, "w") as f:
                json.dump(coverage_data, f)
            
            # テストレポートファイルを作成
            test_data = {
                "summary": {"passed": 10, "failed": 0},
                "tests": []
            }
            test_report_file = project_root / "test-report.json"
            with open(test_report_file, "w") as f:
                json.dump(test_data, f)
            
            mock_run.return_value.returncode = 0
            
            result = collect_pytest_metrics(project_root)
            
            assert result["success"] is True
            assert result["coverage_percent"] == 85.5
            assert result["tests_passed"] == 10
            assert result["tests_failed"] == 0
            assert result["errors"] == []

    @patch('subprocess.run')
    def test_collect_pytest_metrics_with_failures(self, mock_run):
        """Pytestメトリクス収集（失敗あり）のテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            
            # テストレポートファイルを作成（失敗あり）
            test_data = {
                "summary": {"passed": 8, "failed": 2},
                "tests": [
                    {"outcome": "failed", "nodeid": "test_example.py::test_fail1"},
                    {"outcome": "failed", "nodeid": "test_example.py::test_fail2"}
                ]
            }
            test_report_file = project_root / "test-report.json"
            with open(test_report_file, "w") as f:
                json.dump(test_data, f)
            
            mock_run.return_value.returncode = 1
            
            result = collect_pytest_metrics(project_root)
            
            assert result["success"] is False
            assert result["tests_passed"] == 8
            assert result["tests_failed"] == 2
            assert len(result["failed_tests"]) == 2
            assert len(result["errors"]) == 1

    @patch('subprocess.run')
    @patch('os.cpu_count')
    def test_collect_pytest_metrics_parallel(self, mock_cpu_count, mock_run):
        """Pytestメトリクス収集（並列実行）のテスト"""
        mock_cpu_count.return_value = 8
        mock_run.return_value.returncode = 0
        
        collect_pytest_metrics(parallel_workers="auto")
        
        # 並列実行のオプションが含まれていることを確認
        call_args = mock_run.call_args[0][0]
        assert "-n" in call_args
        assert "6" in call_args  # 8 * 0.75 = 6

    @patch('subprocess.run')
    def test_collect_pytest_metrics_subprocess_error(self, mock_run):
        """Pytestメトリクス収集（サブプロセスエラー）のテスト"""
        mock_run.side_effect = subprocess.CalledProcessError(1, "pytest")
        
        result = collect_pytest_metrics()
        
        assert result["success"] is False
        assert result["coverage_percent"] == 0.0
        assert result["tests_passed"] == 0
        assert result["tests_failed"] == 0
        assert len(result["errors"]) == 1


class TestCollectCoverageMetrics:
    """collect_coverage_metricsのテスト"""

    def test_collect_coverage_metrics_success(self):
        """カバレッジメトリクス収集成功のテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            
            coverage_data = {
                "totals": {"percent_covered": 92.3},
                "files": {"test.py": {"summary": {"percent_covered": 95.0}}}
            }
            coverage_file = project_root / "coverage.json"
            with open(coverage_file, "w") as f:
                json.dump(coverage_data, f)
            
            result = collect_coverage_metrics(project_root)
            
            assert result["success"] is True
            assert result["coverage_percent"] == 92.3
            assert "coverage_data" in result
            assert result["errors"] == []

    def test_collect_coverage_metrics_file_not_found(self):
        """カバレッジメトリクス収集（ファイルなし）のテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            
            result = collect_coverage_metrics(project_root)
            
            assert result["success"] is False
            assert result["coverage_percent"] == 0.0
            assert len(result["errors"]) == 1

    def test_collect_coverage_metrics_json_error(self):
        """カバレッジメトリクス収集（JSON解析エラー）のテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            
            coverage_file = project_root / "coverage.json"
            with open(coverage_file, "w") as f:
                f.write("invalid json")
            
            result = collect_coverage_metrics(project_root)
            
            assert result["success"] is False
            assert result["coverage_percent"] == 0.0
            assert len(result["errors"]) == 1


class TestParseToolOutput:
    """parse_tool_outputのテスト"""

    def test_parse_tool_output_json(self):
        """JSON形式のツール出力解析のテスト"""
        json_output = '{"issues": [{"file": "test.py", "message": "error"}]}'
        
        result = parse_tool_output("ruff", json_output, "json")
        
        assert "issues" in result
        assert len(result["issues"]) == 1

    def test_parse_tool_output_json_error(self):
        """JSON形式のツール出力解析（エラー）のテスト"""
        invalid_json = "invalid json"
        
        result = parse_tool_output("ruff", invalid_json, "json")
        
        assert "error" in result

    def test_parse_tool_output_ruff_text(self):
        """Ruffテキスト出力解析のテスト"""
        ruff_output = """
        test.py:10:5: E501 line too long
        test.py:15:1: F401 unused import
        """
        
        result = parse_tool_output("ruff", ruff_output, "text")
        
        assert "issues" in result
        assert result["issue_count"] == 2

    def test_parse_tool_output_mypy_text(self):
        """MyPyテキスト出力解析のテスト"""
        mypy_output = """
        test.py:10: error: Incompatible types
        test.py:15: error: Missing return statement
        """
        
        result = parse_tool_output("mypy", mypy_output, "text")
        
        assert "errors" in result
        assert result["error_count"] == 2

    def test_parse_tool_output_generic(self):
        """汎用ツール出力解析のテスト"""
        generic_output = """
        Line 1
        Line 2
        Line 3
        """
        
        result = parse_tool_output("generic", generic_output, "text")
        
        assert "output_lines" in result
        assert result["line_count"] == 3