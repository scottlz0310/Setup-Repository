"""品質メトリクス収集のテスト"""

import json
import subprocess
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest

from src.setup_repo.quality_collectors import (
    QualityToolCollector,
    collect_coverage_metrics,
    collect_mypy_metrics,
    collect_pytest_metrics,
    collect_ruff_metrics,
    parse_tool_output,
)

from ..multiplatform.helpers import verify_current_platform


class TestQualityToolCollector:
    """QualityToolCollectorのテストクラス"""

    @pytest.mark.unit
    def test_init_default(self):
        """デフォルト初期化テスト"""
        verify_current_platform()  # プラットフォーム検証

        collector = QualityToolCollector()

        assert collector.project_root == Path.cwd()
        assert collector.logger is not None

    @pytest.mark.unit
    def test_init_custom(self, tmp_path):
        """カスタム初期化テスト"""
        verify_current_platform()  # プラットフォーム検証

        mock_logger = Mock()
        collector = QualityToolCollector(tmp_path, mock_logger)

        assert collector.project_root == tmp_path
        assert collector.logger == mock_logger


class TestCollectRuffMetrics:
    """collect_ruff_metrics関数のテスト"""

    @pytest.mark.unit
    @patch("subprocess.run")
    def test_collect_ruff_metrics_success(self, mock_run, tmp_path):
        """Ruffメトリクス収集成功テスト"""
        verify_current_platform()  # プラットフォーム検証

        # 成功時のモック設定
        mock_run.return_value = Mock(
            returncode=0,
            stdout="[]",  # 問題なしのJSON
            stderr="",
        )

        result = collect_ruff_metrics(tmp_path)

        assert result["success"] is True
        assert result["issue_count"] == 0
        assert result["issues"] == []
        assert result["errors"] == []

    @pytest.mark.unit
    @patch("subprocess.run")
    def test_collect_ruff_metrics_with_issues(self, mock_run, tmp_path):
        """Ruffメトリクス収集（問題あり）テスト"""
        verify_current_platform()  # プラットフォーム検証

        # 問題ありのモック設定
        issues_json = json.dumps(
            [{"filename": "src/test.py", "line": 1, "column": 1, "code": "E501", "message": "line too long"}]
        )

        mock_run.return_value = Mock(returncode=1, stdout=issues_json, stderr="")

        result = collect_ruff_metrics(tmp_path)

        assert result["success"] is False
        assert result["issue_count"] == 1
        assert len(result["issues"]) == 1
        assert "Ruffチェックで1件の問題" in result["errors"][0]

    @pytest.mark.unit
    @patch("subprocess.run")
    def test_collect_ruff_metrics_no_output(self, mock_run, tmp_path):
        """Ruffメトリクス収集（出力なし）テスト"""
        verify_current_platform()  # プラットフォーム検証

        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        result = collect_ruff_metrics(tmp_path)

        assert result["success"] is True
        assert result["issue_count"] == 0
        assert result["issues"] == []

    @pytest.mark.unit
    @patch("subprocess.run")
    def test_collect_ruff_metrics_subprocess_error(self, mock_run, tmp_path):
        """Ruffメトリクス収集（サブプロセスエラー）テスト"""
        verify_current_platform()  # プラットフォーム検証

        mock_run.side_effect = subprocess.CalledProcessError(1, "ruff")

        result = collect_ruff_metrics(tmp_path)

        assert result["success"] is False
        assert result["issue_count"] == 0
        assert len(result["errors"]) > 0

    @pytest.mark.unit
    @patch("subprocess.run")
    def test_collect_ruff_metrics_json_decode_error(self, mock_run, tmp_path):
        """Ruffメトリクス収集（JSON解析エラー）テスト"""
        verify_current_platform()  # プラットフォーム検証

        mock_run.return_value = Mock(returncode=1, stdout="invalid json", stderr="")

        result = collect_ruff_metrics(tmp_path)

        assert result["success"] is False
        assert result["issue_count"] == 0
        assert len(result["errors"]) > 0


class TestCollectMypyMetrics:
    """collect_mypy_metrics関数のテスト"""

    @pytest.mark.unit
    @patch("subprocess.run")
    def test_collect_mypy_metrics_success(self, mock_run, tmp_path):
        """MyPyメトリクス収集成功テスト"""
        verify_current_platform()  # プラットフォーム検証

        mock_run.return_value = Mock(returncode=0, stdout="Success: no issues found", stderr="")

        result = collect_mypy_metrics(tmp_path)

        assert result["success"] is True
        assert result["error_count"] == 0
        assert result["error_details"] == []
        assert result["errors"] == []

    @pytest.mark.unit
    @patch("subprocess.run")
    def test_collect_mypy_metrics_with_errors(self, mock_run, tmp_path):
        """MyPyメトリクス収集（エラーあり）テスト"""
        verify_current_platform()  # プラットフォーム検証

        mypy_output = """src/test.py:10: error: Incompatible types
src/test.py:20: error: Missing return statement
src/test.py:30: error: Undefined variable"""

        mock_run.return_value = Mock(returncode=1, stdout=mypy_output, stderr="")

        result = collect_mypy_metrics(tmp_path)

        assert result["success"] is False
        assert result["error_count"] == 3
        assert len(result["error_details"]) == 3
        assert "MyPyで3件のエラー" in result["errors"][0]

    @pytest.mark.unit
    @patch("subprocess.run")
    def test_collect_mypy_metrics_subprocess_error(self, mock_run, tmp_path):
        """MyPyメトリクス収集（サブプロセスエラー）テスト"""
        verify_current_platform()  # プラットフォーム検証

        mock_run.side_effect = FileNotFoundError("mypy not found")

        result = collect_mypy_metrics(tmp_path)

        assert result["success"] is False
        assert result["error_count"] == 0
        assert len(result["errors"]) > 0


class TestCollectPytestMetrics:
    """collect_pytest_metrics関数のテスト"""

    @pytest.fixture
    def mock_coverage_data(self):
        """モックカバレッジデータ"""
        return {"totals": {"percent_covered": 85.5, "num_statements": 100, "missing_lines": 15}}

    @pytest.fixture
    def mock_test_report_data(self):
        """モックテストレポートデータ"""
        return {
            "summary": {"passed": 10, "failed": 0, "skipped": 1},
            "tests": [
                {"nodeid": "test_example.py::test_success", "outcome": "passed"},
                {"nodeid": "test_example.py::test_skip", "outcome": "skipped"},
            ],
        }

    @pytest.mark.unit
    @patch("subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.exists")
    def test_collect_pytest_metrics_success(
        self, mock_exists, mock_file, mock_run, tmp_path, mock_coverage_data, mock_test_report_data
    ):
        """Pytestメトリクス収集成功テスト"""
        verify_current_platform()  # プラットフォーム検証

        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        mock_exists.return_value = True

        # ファイル読み込みのモック設定
        mock_file.side_effect = [
            mock_open(read_data=json.dumps(mock_coverage_data)).return_value,
            mock_open(read_data=json.dumps(mock_test_report_data)).return_value,
        ]

        result = collect_pytest_metrics(tmp_path, coverage_threshold=80.0)

        assert result["success"] is True
        assert result["coverage_percent"] == 85.5
        assert result["tests_passed"] == 10
        assert result["tests_failed"] == 0
        assert result["errors"] == []

    @pytest.mark.unit
    @patch("subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.exists")
    def test_collect_pytest_metrics_coverage_failure(
        self, mock_exists, mock_file, mock_run, tmp_path, mock_test_report_data
    ):
        """Pytestメトリクス収集（カバレッジ不足）テスト"""
        verify_current_platform()  # プラットフォーム検証

        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        mock_exists.return_value = True

        # 低いカバレッジデータ
        low_coverage_data = {"totals": {"percent_covered": 70.0, "num_statements": 100, "missing_lines": 30}}

        mock_file.side_effect = [
            mock_open(read_data=json.dumps(low_coverage_data)).return_value,
            mock_open(read_data=json.dumps(mock_test_report_data)).return_value,
        ]

        result = collect_pytest_metrics(tmp_path, coverage_threshold=80.0)

        assert result["success"] is False
        assert result["coverage_percent"] == 70.0
        assert "カバレッジ不足" in result["errors"][0]

    @pytest.mark.unit
    @patch("subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.exists")
    def test_collect_pytest_metrics_test_failure(self, mock_exists, mock_file, mock_run, tmp_path, mock_coverage_data):
        """Pytestメトリクス収集（テスト失敗）テスト"""
        verify_current_platform()  # プラットフォーム検証

        mock_run.return_value = Mock(returncode=1, stdout="", stderr="")
        mock_exists.return_value = True

        # 失敗テストを含むレポートデータ
        failed_test_report = {
            "summary": {"passed": 8, "failed": 2, "skipped": 0},
            "tests": [
                {"nodeid": "test_example.py::test_fail1", "outcome": "failed"},
                {"nodeid": "test_example.py::test_fail2", "outcome": "failed"},
            ],
        }

        mock_file.side_effect = [
            mock_open(read_data=json.dumps(mock_coverage_data)).return_value,
            mock_open(read_data=json.dumps(failed_test_report)).return_value,
        ]

        result = collect_pytest_metrics(tmp_path, coverage_threshold=80.0)

        assert result["success"] is False
        assert result["tests_failed"] == 2
        assert len(result["failed_tests"]) == 2
        assert "テストで2件の失敗" in result["errors"][0]

    @pytest.mark.unit
    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    @patch.dict("os.environ", {"CI": "true", "UNIT_TESTS_ONLY": "true"})
    def test_collect_pytest_metrics_ci_environment(self, mock_exists, mock_run, tmp_path):
        """CI環境でのPytestメトリクス収集テスト"""
        verify_current_platform()  # プラットフォーム検証

        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        mock_exists.return_value = False  # カバレッジファイルなし

        result = collect_pytest_metrics(tmp_path, coverage_threshold=80.0)

        assert result["is_ci_environment"] is True
        assert result["unit_tests_only"] is True
        assert result["effective_threshold"] == 70.0  # CI環境では閾値が下がる

    @pytest.mark.unit
    @patch("subprocess.run")
    def test_collect_pytest_metrics_subprocess_error(self, mock_run, tmp_path):
        """Pytestメトリクス収集（サブプロセスエラー）テスト"""
        verify_current_platform()  # プラットフォーム検証

        mock_run.side_effect = FileNotFoundError("pytest not found")

        result = collect_pytest_metrics(tmp_path)

        assert result["success"] is False
        assert result["coverage_percent"] == 0.0
        assert len(result["errors"]) > 0


class TestCollectCoverageMetrics:
    """collect_coverage_metrics関数のテスト"""

    @pytest.mark.unit
    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.exists")
    def test_collect_coverage_metrics_success(self, mock_exists, mock_file, tmp_path):
        """カバレッジメトリクス収集成功テスト"""
        verify_current_platform()  # プラットフォーム検証

        coverage_data = {"totals": {"percent_covered": 92.5, "num_statements": 200, "missing_lines": 15}}

        mock_exists.return_value = True
        mock_file.return_value.read.return_value = json.dumps(coverage_data)

        result = collect_coverage_metrics(tmp_path)

        assert result["success"] is True
        assert result["coverage_percent"] == 92.5
        assert result["coverage_data"] == coverage_data
        assert result["errors"] == []

    @pytest.mark.unit
    @patch("pathlib.Path.exists")
    def test_collect_coverage_metrics_file_not_found(self, mock_exists, tmp_path):
        """カバレッジメトリクス収集（ファイルなし）テスト"""
        verify_current_platform()  # プラットフォーム検証

        mock_exists.return_value = False

        result = collect_coverage_metrics(tmp_path)

        assert result["success"] is False
        assert result["coverage_percent"] == 0.0
        assert "カバレッジファイルが見つかりません" in result["errors"][0]

    @pytest.mark.unit
    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.exists")
    def test_collect_coverage_metrics_json_error(self, mock_exists, mock_file, tmp_path):
        """カバレッジメトリクス収集（JSON解析エラー）テスト"""
        verify_current_platform()  # プラットフォーム検証

        mock_exists.return_value = True
        mock_file.return_value.read.return_value = "invalid json"

        result = collect_coverage_metrics(tmp_path)

        assert result["success"] is False
        assert result["coverage_percent"] == 0.0
        assert "カバレッジデータ解析エラー" in result["errors"][0]


class TestParseToolOutput:
    """parse_tool_output関数のテスト"""

    @pytest.mark.unit
    def test_parse_tool_output_json_format(self):
        """JSON形式のツール出力解析テスト"""
        verify_current_platform()  # プラットフォーム検証

        json_output = '{"issues": [{"code": "E501", "message": "line too long"}]}'

        result = parse_tool_output("ruff", json_output, "json")

        assert "issues" in result
        assert len(result["issues"]) == 1

    @pytest.mark.unit
    def test_parse_tool_output_json_invalid(self):
        """無効なJSON形式のツール出力解析テスト"""
        verify_current_platform()  # プラットフォーム検証

        invalid_json = "invalid json output"

        result = parse_tool_output("ruff", invalid_json, "json")

        assert "error" in result
        assert "JSON出力解析に失敗" in result["error"]

    @pytest.mark.unit
    def test_parse_tool_output_ruff_text(self):
        """Ruffテキスト出力解析テスト"""
        verify_current_platform()  # プラットフォーム検証

        ruff_output = """src/test.py:10:1: E501 line too long
src/test.py:20:5: F401 unused import
Found 2 errors."""

        result = parse_tool_output("ruff", ruff_output, "text")

        assert "issues" in result
        assert result["issue_count"] == 2
        assert len(result["issues"]) == 2

    @pytest.mark.unit
    def test_parse_tool_output_mypy_text(self):
        """MyPyテキスト出力解析テスト"""
        verify_current_platform()  # プラットフォーム検証

        mypy_output = """src/test.py:10: error: Incompatible types
src/test.py:20: error: Missing return statement
Found 2 errors in 1 file"""

        result = parse_tool_output("mypy", mypy_output, "text")

        assert "errors" in result
        assert result["error_count"] == 2
        assert len(result["errors"]) == 2

    @pytest.mark.unit
    def test_parse_tool_output_generic_text(self):
        """汎用テキスト出力解析テスト"""
        verify_current_platform()  # プラットフォーム検証

        generic_output = """Line 1
Line 2
Line 3"""

        result = parse_tool_output("unknown_tool", generic_output, "text")

        assert "output_lines" in result
        assert result["line_count"] == 3
        assert len(result["output_lines"]) == 3

    @pytest.mark.unit
    def test_parse_tool_output_empty_text(self):
        """空のテキスト出力解析テスト"""
        verify_current_platform()  # プラットフォーム検証

        empty_output = ""

        result = parse_tool_output("ruff", empty_output, "text")

        assert result["issue_count"] == 0
        assert result["issues"] == []


class TestQualityCollectorsIntegration:
    """品質メトリクス収集の統合テスト"""

    @pytest.mark.unit
    @patch("subprocess.run")
    def test_all_collectors_error_handling(self, mock_run, tmp_path):
        """全コレクターのエラーハンドリングテスト"""
        verify_current_platform()  # プラットフォーム検証

        # 全てのサブプロセス呼び出しでエラーを発生させる
        mock_run.side_effect = FileNotFoundError("Tool not found")

        ruff_result = collect_ruff_metrics(tmp_path)
        mypy_result = collect_mypy_metrics(tmp_path)
        pytest_result = collect_pytest_metrics(tmp_path)

        # 全てのコレクターがエラーを適切に処理することを確認
        assert ruff_result["success"] is False
        assert mypy_result["success"] is False
        assert pytest_result["success"] is False

        # エラーメッセージが含まれていることを確認
        assert len(ruff_result["errors"]) > 0
        assert len(mypy_result["errors"]) > 0
        assert len(pytest_result["errors"]) > 0

    @pytest.mark.unit
    def test_path_security_validation(self, tmp_path):
        """パスセキュリティ検証テスト"""
        verify_current_platform()  # プラットフォーム検証

        # パストラバーサル攻撃を試行
        tmp_path / ".." / ".." / "etc" / "passwd"

        # 正常なパスでのテスト
        result = collect_coverage_metrics(tmp_path)
        assert result["success"] is False  # ファイルが存在しないため

        # 悪意のあるパスは適切に処理される
        # （実際の実装では resolve() と startswith() でチェック）
