"""品質メトリクスのセキュリティ機能テスト."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from setup_repo.quality_logger import QualityLogger
from setup_repo.quality_metrics import QualityMetricsCollector


class TestQualityMetricsCollectorSecurity:
    """QualityMetricsCollectorのセキュリティ機能テスト."""

    def setup_method(self):
        """テストメソッドの前処理."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.mock_logger = Mock(spec=QualityLogger)
        self.collector = QualityMetricsCollector(project_root=self.temp_dir, logger=self.mock_logger)

    @pytest.mark.unit
    @patch("setup_repo.quality_metrics.safe_subprocess")
    @patch.dict("os.environ", {"CI": "false"})
    def test_collect_security_metrics_no_tools(self, mock_subprocess):
        """セキュリティツールなしでのメトリクス収集テスト."""
        # ツールのバージョンチェックが失敗
        mock_subprocess.return_value.returncode = 1

        result = self.collector.collect_security_metrics()

        assert result["success"] is True  # ツールなしでも成功
        assert result["vulnerability_count"] == 0
        assert result["no_tools_available"] is True
        assert result["ci_environment"] is False
        assert len(result["warnings"]) >= 2  # bandit, safetyの警告

    @pytest.mark.unit
    @patch("setup_repo.quality_metrics.safe_subprocess")
    @patch.dict("os.environ", {"CI": "true"})
    def test_collect_security_metrics_ci_environment(self, mock_subprocess):
        """CI環境でのセキュリティメトリクス収集テスト."""
        # ツールのバージョンチェックが失敗
        mock_subprocess.return_value.returncode = 1

        result = self.collector.collect_security_metrics()

        assert result["success"] is True
        assert result["ci_environment"] is True
        self.mock_logger.log_quality_check_success.assert_called_once()

    @pytest.mark.unit
    @patch("setup_repo.quality_metrics.safe_subprocess")
    @patch.dict("os.environ", {"CI": "false"})
    def test_collect_security_metrics_bandit_success(self, mock_subprocess):
        """Bandit成功でのセキュリティメトリクス収集テスト."""

        def subprocess_side_effect(cmd, **kwargs):
            mock_result = Mock()
            if "bandit" in cmd and "--version" in cmd:
                mock_result.returncode = 0
                mock_result.stdout = "bandit 1.7.0"
            elif "safety" in cmd and "--version" in cmd:
                mock_result.returncode = 1  # safety利用不可
            elif "bandit" in cmd and "-f" in cmd and "json" in cmd:
                mock_result.returncode = 0
                mock_result.stdout = json.dumps({"results": []})
            else:
                mock_result.returncode = 1
                mock_result.stdout = ""
                mock_result.stderr = ""
            return mock_result

        mock_subprocess.side_effect = subprocess_side_effect

        result = self.collector.collect_security_metrics()

        assert result["success"] is True
        assert result["vulnerability_count"] == 0
        assert result["tools_available"]["bandit"] is True
        assert result["tools_available"]["safety"] is False

    @pytest.mark.unit
    @patch("setup_repo.quality_metrics.safe_subprocess")
    @patch.dict("os.environ", {"CI": "false"})
    def test_collect_security_metrics_bandit_vulnerabilities(self, mock_subprocess):
        """Banditで脆弱性発見時のテスト."""

        def subprocess_side_effect(cmd, **kwargs):
            mock_result = Mock()
            if "bandit" in cmd and "--version" in cmd:
                mock_result.returncode = 0
                mock_result.stdout = "bandit 1.7.0"
            elif "safety" in cmd and "--version" in cmd:
                mock_result.returncode = 1
            elif "bandit" in cmd and "-f" in cmd and "json" in cmd:
                mock_result.returncode = 0
                mock_result.stdout = json.dumps(
                    {
                        "results": [
                            {"issue_severity": "HIGH", "issue_text": "SQL injection vulnerability"},
                            {"issue_severity": "MEDIUM", "issue_text": "Hardcoded password"},
                        ]
                    }
                )
            else:
                mock_result.returncode = 1
                mock_result.stdout = ""
                mock_result.stderr = ""
            return mock_result

        mock_subprocess.side_effect = subprocess_side_effect

        result = self.collector.collect_security_metrics()

        assert result["success"] is False
        assert result["vulnerability_count"] == 2
        assert len(result["vulnerabilities"]) == 2
        self.mock_logger.log_quality_check_failure.assert_called_once()

    @pytest.mark.unit
    @patch("setup_repo.quality_metrics.safe_subprocess")
    @patch.dict("os.environ", {"CI": "false"})
    def test_collect_security_metrics_safety_success(self, mock_subprocess):
        """Safety成功でのセキュリティメトリクス収集テスト."""

        def subprocess_side_effect(cmd, **kwargs):
            mock_result = Mock()
            if "bandit" in cmd and "--version" in cmd:
                mock_result.returncode = 1  # bandit利用不可
            elif "safety" in cmd and "--version" in cmd:
                mock_result.returncode = 0
                mock_result.stdout = "safety 2.0.0"
            elif "safety" in cmd and "check" in cmd:
                mock_result.returncode = 0
                mock_result.stdout = json.dumps([])
            else:
                mock_result.returncode = 1
                mock_result.stdout = ""
                mock_result.stderr = ""
            return mock_result

        mock_subprocess.side_effect = subprocess_side_effect

        result = self.collector.collect_security_metrics()

        assert result["success"] is True
        assert result["vulnerability_count"] == 0
        assert result["tools_available"]["bandit"] is False
        assert result["tools_available"]["safety"] is True

    @pytest.mark.unit
    @patch("setup_repo.quality_metrics.safe_subprocess")
    @patch.dict("os.environ", {"CI": "false"})
    def test_collect_security_metrics_safety_vulnerabilities(self, mock_subprocess):
        """Safetyで脆弱性発見時のテスト."""

        def subprocess_side_effect(cmd, **kwargs):
            mock_result = Mock()
            if "bandit" in cmd and "--version" in cmd:
                mock_result.returncode = 1
            elif "safety" in cmd and "--version" in cmd:
                mock_result.returncode = 0
                mock_result.stdout = "safety 2.0.0"
            elif "safety" in cmd and "check" in cmd:
                mock_result.returncode = 0
                mock_result.stdout = json.dumps(
                    [
                        {"vulnerability": "CVE-2021-1234", "package": "requests"},
                        {"vulnerability": "CVE-2021-5678", "package": "urllib3"},
                    ]
                )
            else:
                mock_result.returncode = 1
                mock_result.stdout = ""
                mock_result.stderr = ""
            return mock_result

        mock_subprocess.side_effect = subprocess_side_effect

        result = self.collector.collect_security_metrics()

        assert result["success"] is False
        assert result["vulnerability_count"] == 2
        assert len(result["vulnerabilities"]) == 2

    @pytest.mark.unit
    @patch("setup_repo.quality_metrics.safe_subprocess")
    @patch.dict("os.environ", {"CI": "false"})
    def test_collect_security_metrics_json_parse_error(self, mock_subprocess):
        """JSON解析エラー時のテスト."""

        def subprocess_side_effect(cmd, **kwargs):
            mock_result = Mock()
            if "bandit" in cmd and "--version" in cmd:
                mock_result.returncode = 0
                mock_result.stdout = "bandit 1.7.0"
            elif "safety" in cmd and "--version" in cmd:
                mock_result.returncode = 1
            elif "bandit" in cmd and "-f" in cmd and "json" in cmd:
                mock_result.returncode = 0
                mock_result.stdout = "invalid json"
            else:
                mock_result.returncode = 1
                mock_result.stdout = ""
                mock_result.stderr = ""
            return mock_result

        mock_subprocess.side_effect = subprocess_side_effect

        result = self.collector.collect_security_metrics()

        assert result["success"] is True  # JSON解析エラーは警告扱い
        assert result["vulnerability_count"] == 0
        assert len(result["warnings"]) >= 1

    @pytest.mark.unit
    @patch("setup_repo.quality_metrics.safe_subprocess")
    @patch.dict("os.environ", {"CI": "false"})
    def test_collect_security_metrics_subprocess_error(self, mock_subprocess):
        """サブプロセスエラー時のテスト."""

        def subprocess_side_effect(cmd, **kwargs):
            mock_result = Mock()
            if "bandit" in cmd and "--version" in cmd:
                mock_result.returncode = 0
                mock_result.stdout = "bandit 1.7.0"
            elif "safety" in cmd and "--version" in cmd:
                mock_result.returncode = 1
            elif "bandit" in cmd and "-f" in cmd and "json" in cmd:
                raise FileNotFoundError("Command not found")
            else:
                mock_result.returncode = 1
                mock_result.stdout = ""
                mock_result.stderr = ""
            return mock_result

        mock_subprocess.side_effect = subprocess_side_effect

        result = self.collector.collect_security_metrics()

        assert result["success"] is False
        assert len(result["errors"]) >= 1
        self.mock_logger.log_quality_check_failure.assert_called_once()

    @pytest.mark.unit
    @patch("setup_repo.quality_metrics.safe_subprocess")
    @patch.dict("os.environ", {"CI": "true"})
    def test_collect_security_metrics_ci_with_vulnerabilities(self, mock_subprocess):
        """CI環境で脆弱性がある場合のテスト."""

        def subprocess_side_effect(cmd, **kwargs):
            mock_result = Mock()
            if "bandit" in cmd and "--version" in cmd:
                mock_result.returncode = 0
                mock_result.stdout = "bandit 1.7.0"
            elif "safety" in cmd and "--version" in cmd:
                mock_result.returncode = 1
            elif "bandit" in cmd and "-f" in cmd and "json" in cmd:
                mock_result.returncode = 0
                mock_result.stdout = json.dumps(
                    {"results": [{"issue_severity": "HIGH", "issue_text": "Vulnerability"}]}
                )
            else:
                mock_result.returncode = 1
                mock_result.stdout = ""
                mock_result.stderr = ""
            return mock_result

        mock_subprocess.side_effect = subprocess_side_effect

        result = self.collector.collect_security_metrics()

        # CI環境では脆弱性があっても成功（重大エラーがない限り）
        assert result["success"] is True
        assert result["vulnerability_count"] == 1
        assert result["ci_environment"] is True

    @pytest.mark.unit
    @patch("setup_repo.quality_metrics.safe_subprocess")
    @patch.dict("os.environ", {"CI": "false"})
    def test_collect_security_metrics_warning_logging(self, mock_subprocess):
        """警告ログ出力のテスト."""

        def subprocess_side_effect(cmd, **kwargs):
            mock_result = Mock()
            if "bandit" in cmd and "--version" in cmd:
                mock_result.returncode = 0
                mock_result.stdout = "bandit 1.7.0"
            elif "safety" in cmd and "--version" in cmd:
                mock_result.returncode = 1
            elif "bandit" in cmd and "-f" in cmd and "json" in cmd:
                mock_result.returncode = 1
                mock_result.stdout = ""
                mock_result.stderr = "Warning: some issue"
            else:
                mock_result.returncode = 1
                mock_result.stdout = ""
                mock_result.stderr = ""
            return mock_result

        mock_subprocess.side_effect = subprocess_side_effect

        result = self.collector.collect_security_metrics()

        # 警告がログ出力されることを確認
        assert len(result["warnings"]) >= 1
        self.mock_logger.warning.assert_called()

    @pytest.mark.unit
    @patch("setup_repo.quality_metrics.safe_subprocess")
    @patch.dict("os.environ", {"CI": "true"})
    def test_collect_security_metrics_ci_warning_logging(self, mock_subprocess):
        """CI環境での警告ログ出力のテスト."""

        def subprocess_side_effect(cmd, **kwargs):
            mock_result = Mock()
            if "bandit" in cmd and "--version" in cmd:
                mock_result.returncode = 0
                mock_result.stdout = "bandit 1.7.0"
            elif "safety" in cmd and "--version" in cmd:
                mock_result.returncode = 1
            elif "bandit" in cmd and "-f" in cmd and "json" in cmd:
                mock_result.returncode = 1
                mock_result.stdout = ""
                mock_result.stderr = "Warning: some issue"
            else:
                mock_result.returncode = 1
                mock_result.stdout = ""
                mock_result.stderr = ""
            return mock_result

        mock_subprocess.side_effect = subprocess_side_effect

        result = self.collector.collect_security_metrics()

        # CI環境では警告レベルを下げる
        assert len(result["warnings"]) >= 1
        self.mock_logger.info.assert_called()

    @pytest.mark.unit
    @patch("setup_repo.quality_metrics.collect_ruff_metrics")
    @patch("setup_repo.quality_metrics.collect_mypy_metrics")
    @patch("setup_repo.quality_metrics.collect_pytest_metrics")
    def test_collect_all_metrics(self, mock_pytest, mock_mypy, mock_ruff):
        """全メトリクス収集テスト."""
        # モックの戻り値を設定
        mock_ruff.return_value = {"issue_count": 5}
        mock_mypy.return_value = {"error_count": 3}
        mock_pytest.return_value = {"coverage_percent": 85.0, "tests_passed": 95, "tests_failed": 2}

        # セキュリティメトリクスをモック
        with patch.object(self.collector, "collect_security_metrics") as mock_security:
            mock_security.return_value = {"vulnerability_count": 1}

            metrics = self.collector.collect_all_metrics()

        assert metrics.ruff_issues == 5
        assert metrics.mypy_errors == 3
        assert metrics.test_coverage == 85.0
        assert metrics.test_passed == 95
        assert metrics.test_failed == 2
        assert metrics.security_vulnerabilities == 1

        self.mock_logger.info.assert_called_with("品質メトリクス収集を開始します")
        self.mock_logger.log_metrics_summary.assert_called_once()

    @pytest.mark.unit
    def test_save_metrics_report(self):
        """メトリクスレポート保存テスト."""
        from setup_repo.quality_metrics import QualityMetrics

        output_file = self.temp_dir / "test-report.json"

        metrics = QualityMetrics(
            ruff_issues=5,
            mypy_errors=3,
            test_coverage=85.0,
        )

        result_file = self.collector.save_metrics_report(metrics, output_file)

        assert result_file == output_file
        assert output_file.exists()

        # ファイル内容を確認
        with open(output_file, encoding="utf-8") as f:
            data = json.load(f)

        assert data["metrics"]["ruff_issues"] == 5
        assert data["metrics"]["mypy_errors"] == 3
        assert data["metrics"]["test_coverage"] == 85.0
        assert "quality_score" in data
        assert "passing" in data

        self.mock_logger.info.assert_called()

    @pytest.mark.unit
    def test_save_metrics_report_invalid_path(self):
        """無効なパスでのメトリクスレポート保存テスト."""
        from setup_repo.quality_metrics import QualityMetrics

        metrics = QualityMetrics()
        # セキュリティバグ修正後は危険なパスが拒否される
        dangerous_paths = [
            Path("/etc/passwd"),  # システムファイル
            Path("../../../etc/passwd"),  # パストラバーサル
            Path("file<>.json"),  # 無効文字
        ]

        for dangerous_path in dangerous_paths:
            # セキュリティ検証で拒否されるValueErrorが発生する
            with pytest.raises(ValueError, match="Unsafe file path detected"):
                self.collector.save_metrics_report(metrics, dangerous_path)

    @pytest.mark.unit
    def test_save_metrics_report_default_path(self):
        """デフォルトパスでのメトリクスレポート保存テスト."""
        from setup_repo.quality_metrics import QualityMetrics

        metrics = QualityMetrics()
        result_file = self.collector.save_metrics_report(metrics)

        # デフォルトパスで保存されることを確認
        assert result_file is not None
        assert result_file.exists()
        assert "quality-report" in result_file.name
