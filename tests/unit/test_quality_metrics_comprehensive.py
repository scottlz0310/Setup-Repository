"""品質メトリクス機能の包括的テスト."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from setup_repo.quality_logger import QualityLogger
from setup_repo.quality_metrics import (
    BuildResult,
    QualityCheckStatus,
    QualityMetrics,
    QualityMetricsCollector,
)


class TestQualityCheckStatus:
    """QualityCheckStatusクラスのテスト."""

    @pytest.mark.unit
    def test_enum_values(self):
        """列挙値のテスト."""
        assert QualityCheckStatus.PASSED.value == "passed"
        assert QualityCheckStatus.FAILED.value == "failed"
        assert QualityCheckStatus.WARNING.value == "warning"
        assert QualityCheckStatus.SKIPPED.value == "skipped"


class TestQualityMetrics:
    """QualityMetricsクラスのテスト."""

    @pytest.mark.unit
    def test_init_default_values(self):
        """デフォルト値での初期化テスト."""
        metrics = QualityMetrics()

        assert metrics.ruff_issues == 0
        assert metrics.mypy_errors == 0
        assert metrics.test_coverage == 0.0
        assert metrics.test_passed == 0
        assert metrics.test_failed == 0
        assert metrics.security_vulnerabilities == 0
        assert metrics.timestamp != ""
        assert metrics.commit_hash != ""

    @pytest.mark.unit
    def test_init_with_values(self):
        """値指定での初期化テスト."""
        timestamp = "2024-01-01T00:00:00"
        commit_hash = "abc123"

        metrics = QualityMetrics(
            ruff_issues=5,
            mypy_errors=3,
            test_coverage=85.5,
            test_passed=95,
            test_failed=2,
            security_vulnerabilities=1,
            timestamp=timestamp,
            commit_hash=commit_hash,
        )

        assert metrics.ruff_issues == 5
        assert metrics.mypy_errors == 3
        assert metrics.test_coverage == 85.5
        assert metrics.test_passed == 95
        assert metrics.test_failed == 2
        assert metrics.security_vulnerabilities == 1
        assert metrics.timestamp == timestamp
        assert metrics.commit_hash == commit_hash

    @pytest.mark.unit
    @patch("setup_repo.quality_metrics.safe_subprocess")
    def test_get_current_commit_hash_success(self, mock_subprocess):
        """コミットハッシュ取得成功テスト."""
        mock_result = Mock()
        mock_result.stdout = "abcdef1234567890\n"
        mock_subprocess.return_value = mock_result

        metrics = QualityMetrics()
        commit_hash = metrics._get_current_commit_hash()

        assert commit_hash == "abcdef12"
        # safe_subprocessが2回呼ばれることを確認（初期化時とメソッド呼び出し時）
        assert mock_subprocess.call_count == 2
        mock_subprocess.assert_called_with(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True)

    @pytest.mark.unit
    @patch("setup_repo.quality_metrics.safe_subprocess")
    def test_get_current_commit_hash_error(self, mock_subprocess):
        """コミットハッシュ取得エラーテスト."""
        mock_subprocess.side_effect = FileNotFoundError()

        metrics = QualityMetrics()
        commit_hash = metrics._get_current_commit_hash()

        assert commit_hash == "unknown"

    @pytest.mark.unit
    def test_is_passing_all_good(self):
        """全て良好な場合のテスト."""
        metrics = QualityMetrics(
            ruff_issues=0,
            mypy_errors=0,
            test_coverage=75.0,  # pyproject.tomlの設定70%以上
            test_passed=100,
            test_failed=0,
            security_vulnerabilities=0,
        )

        assert metrics.is_passing() is True

    @pytest.mark.unit
    def test_is_passing_with_issues(self):
        """問題がある場合のテスト."""
        # Ruffエラーがある場合
        metrics = QualityMetrics(ruff_issues=1)
        assert metrics.is_passing() is False

        # MyPyエラーがある場合
        metrics = QualityMetrics(mypy_errors=1)
        assert metrics.is_passing() is False

        # カバレッジが低い場合（pyproject.tomlの設定70%未満）
        metrics = QualityMetrics(test_coverage=69.0)
        assert metrics.is_passing() is False

        # テスト失敗がある場合
        metrics = QualityMetrics(test_failed=1)
        assert metrics.is_passing() is False

        # セキュリティ脆弱性がある場合（CI環境以外）
        import os

        original_ci = os.environ.get("CI")
        try:
            # CI環境変数を一時的に削除してローカル環境をシミュレート
            if "CI" in os.environ:
                del os.environ["CI"]
            metrics = QualityMetrics(security_vulnerabilities=1)
            assert metrics.is_passing() is False
        finally:
            # CI環境変数を復元
            if original_ci is not None:
                os.environ["CI"] = original_ci

    @pytest.mark.unit
    def test_is_passing_custom_coverage(self):
        """カスタムカバレッジ閾値のテスト."""
        metrics = QualityMetrics(test_coverage=75.0)

        assert metrics.is_passing(min_coverage=70.0) is True
        assert metrics.is_passing(min_coverage=80.0) is False

    @pytest.mark.unit
    def test_get_quality_score_perfect(self):
        """完璧な品質スコアのテスト."""
        metrics = QualityMetrics(
            ruff_issues=0,
            mypy_errors=0,
            test_coverage=100.0,
            test_passed=100,
            test_failed=0,
            security_vulnerabilities=0,
        )

        assert metrics.get_quality_score() == 100.0

    @pytest.mark.unit
    def test_get_quality_score_with_issues(self):
        """問題がある場合の品質スコアテスト."""
        import os

        original_ci = os.environ.get("CI")
        try:
            # CI環境変数を一時的に削除してローカル環境をシミュレート
            if "CI" in os.environ:
                del os.environ["CI"]

            metrics = QualityMetrics(
                ruff_issues=5,  # -10点 (min(5*2, 20))
                mypy_errors=3,  # -9点 (min(3*3, 30))
                test_coverage=60.0,  # -5点 (70-60)*0.5 (pyproject.tomlの設定70%基準)
                test_passed=95,
                test_failed=2,  # -10点 (min(2*5, 25))
                security_vulnerabilities=1,  # -2点 (min(1*2, 30)) ローカル環境
            )

            expected_score = 100.0 - 10 - 9 - 5 - 10 - 2  # = 64.0
            assert metrics.get_quality_score() == expected_score
        finally:
            # CI環境変数を復元
            if original_ci is not None:
                os.environ["CI"] = original_ci

    @pytest.mark.unit
    def test_get_quality_score_maximum_deductions(self):
        """最大減点の品質スコアテスト."""
        metrics = QualityMetrics(
            ruff_issues=20,  # 最大-20点
            mypy_errors=15,  # 最大-30点
            test_coverage=0.0,  # -40点
            test_passed=50,
            test_failed=10,  # 最大-25点
            security_vulnerabilities=10,  # 最大-50点
        )

        score = metrics.get_quality_score()
        assert score >= 0.0  # 最低0点

    @pytest.mark.unit
    def test_items_method(self):
        """itemsメソッドのテスト."""
        metrics = QualityMetrics(
            ruff_issues=5,
            mypy_errors=3,
            test_coverage=85.0,
        )

        items = list(metrics.items())
        assert len(items) > 0

        # 辞書のキーと値のペアが含まれることを確認
        item_dict = dict(items)
        assert item_dict["ruff_issues"] == 5
        assert item_dict["mypy_errors"] == 3
        assert item_dict["test_coverage"] == 85.0

    @pytest.mark.unit
    def test_to_dict_method(self):
        """to_dictメソッドのテスト."""
        metrics = QualityMetrics(
            ruff_issues=5,
            mypy_errors=3,
            test_coverage=85.0,
        )

        result = metrics.to_dict()
        assert isinstance(result, dict)
        assert result["ruff_issues"] == 5
        assert result["mypy_errors"] == 3
        assert result["test_coverage"] == 85.0


class TestBuildResult:
    """BuildResultクラスのテスト."""

    @pytest.mark.unit
    def test_init(self):
        """初期化テスト."""
        metrics = QualityMetrics()
        result = BuildResult(
            status=QualityCheckStatus.PASSED,
            metrics=metrics,
            errors=["error1"],
            warnings=["warning1"],
            duration_seconds=10.5,
        )

        assert result.status == QualityCheckStatus.PASSED
        assert result.metrics == metrics
        assert result.errors == ["error1"]
        assert result.warnings == ["warning1"]
        assert result.duration_seconds == 10.5

    @pytest.mark.unit
    def test_to_dict(self):
        """to_dictメソッドのテスト."""
        metrics = QualityMetrics(ruff_issues=5)
        result = BuildResult(
            status=QualityCheckStatus.FAILED,
            metrics=metrics,
            errors=["error1"],
            warnings=["warning1"],
            duration_seconds=15.0,
        )

        result_dict = result.to_dict()

        assert result_dict["status"] == "failed"
        assert isinstance(result_dict["metrics"], dict)
        assert result_dict["metrics"]["ruff_issues"] == 5
        assert result_dict["errors"] == ["error1"]
        assert result_dict["warnings"] == ["warning1"]
        assert result_dict["duration_seconds"] == 15.0


class TestQualityMetricsCollector:
    """QualityMetricsCollectorクラスのテスト."""

    def setup_method(self):
        """テストメソッドの前処理."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.mock_logger = Mock(spec=QualityLogger)
        self.collector = QualityMetricsCollector(project_root=self.temp_dir, logger=self.mock_logger)

    @pytest.mark.unit
    def test_init_default_values(self):
        """デフォルト値での初期化テスト."""
        collector = QualityMetricsCollector()
        assert collector.project_root == Path.cwd()
        assert collector.logger is not None

    @pytest.mark.unit
    @patch("setup_repo.quality_metrics.collect_ruff_metrics")
    def test_collect_ruff_metrics(self, mock_collect):
        """Ruffメトリクス収集テスト."""
        expected_result = {"issue_count": 5}
        mock_collect.return_value = expected_result

        result = self.collector.collect_ruff_metrics()

        assert result == expected_result
        mock_collect.assert_called_once_with(self.temp_dir, self.mock_logger)

    @pytest.mark.unit
    @patch("setup_repo.quality_metrics.collect_mypy_metrics")
    def test_collect_mypy_metrics(self, mock_collect):
        """MyPyメトリクス収集テスト."""
        expected_result = {"error_count": 3}
        mock_collect.return_value = expected_result

        result = self.collector.collect_mypy_metrics()

        assert result == expected_result
        mock_collect.assert_called_once_with(self.temp_dir, self.mock_logger)

    @pytest.mark.unit
    @patch("setup_repo.quality_metrics.collect_pytest_metrics")
    def test_collect_test_metrics(self, mock_collect):
        """テストメトリクス収集テスト."""
        expected_result = {"tests_passed": 100, "tests_failed": 0}
        mock_collect.return_value = expected_result

        result = self.collector.collect_test_metrics()

        assert result == expected_result
        mock_collect.assert_called_once_with(self.temp_dir, self.mock_logger, "auto", 80.0, False)

    @pytest.mark.unit
    @patch("setup_repo.quality_metrics.collect_pytest_metrics")
    def test_collect_test_metrics_with_params(self, mock_collect):
        """パラメータ付きテストメトリクス収集テスト."""
        expected_result = {"tests_passed": 50, "tests_failed": 5}
        mock_collect.return_value = expected_result

        result = self.collector.collect_test_metrics(
            parallel_workers=4, coverage_threshold=90.0, skip_integration_tests=True
        )

        assert result == expected_result
        mock_collect.assert_called_once_with(self.temp_dir, self.mock_logger, 4, 90.0, True)
