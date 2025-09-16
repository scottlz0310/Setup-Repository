"""品質メトリクス機能のテスト."""

import json
import platform

import pytest

from setup_repo.quality_metrics import QualityMetrics

from ..multiplatform.helpers import verify_current_platform


class TestQualityMetrics:
    """品質メトリクス機能のテストクラス."""

    def setup_method(self):
        """テストメソッドの前処理."""
        self.platform_info = verify_current_platform()

    @pytest.mark.unit
    def test_code_quality_metrics(self):
        """コード品質メトリクスの計算テスト."""
        # コード品質データのモック
        code_metrics = {
            "lines_of_code": 5000,
            "cyclomatic_complexity": 15,
            "maintainability_index": 75,
            "technical_debt_ratio": 0.05,
            "code_duplication": 0.03,
        }

        # 品質スコアの計算
        quality_score = (
            (100 - code_metrics["cyclomatic_complexity"]) * 0.3
            + code_metrics["maintainability_index"] * 0.4
            + (100 - code_metrics["technical_debt_ratio"] * 100) * 0.2
            + (100 - code_metrics["code_duplication"] * 100) * 0.1
        )

        # メトリクス計算の検証
        assert quality_score > 80  # 良好な品質スコア
        assert code_metrics["technical_debt_ratio"] < 0.1  # 技術的負債が低い

    @pytest.mark.unit
    def test_test_coverage_metrics(self):
        """テストカバレッジメトリクスの計算テスト."""
        # カバレッジデータのモック
        coverage_metrics = {
            "line_coverage": 85.5,
            "branch_coverage": 78.2,
            "function_coverage": 92.1,
            "statement_coverage": 87.3,
            "missing_lines": 145,
            "total_lines": 1000,
        }

        # 総合カバレッジスコアの計算
        overall_coverage = (
            coverage_metrics["line_coverage"] * 0.4
            + coverage_metrics["branch_coverage"] * 0.3
            + coverage_metrics["function_coverage"] * 0.2
            + coverage_metrics["statement_coverage"] * 0.1
        )

        # カバレッジメトリクスの検証
        assert overall_coverage > 80
        assert coverage_metrics["missing_lines"] / coverage_metrics["total_lines"] < 0.2

    @pytest.mark.unit
    def test_security_metrics(self):
        """セキュリティメトリクスの計算テスト."""
        # セキュリティデータのモック
        security_metrics = {
            "vulnerabilities": {"critical": 0, "high": 1, "medium": 3, "low": 2},
            "security_hotspots": 5,
            "security_rating": "B",
            "reliability_rating": "A",
        }

        # セキュリティスコアの計算
        vuln_score = (
            security_metrics["vulnerabilities"]["critical"] * 10
            + security_metrics["vulnerabilities"]["high"] * 5
            + security_metrics["vulnerabilities"]["medium"] * 2
            + security_metrics["vulnerabilities"]["low"] * 1
        )

        security_score = max(0, 100 - vuln_score)

        # セキュリティメトリクスの検証
        assert security_score == 87  # 100 - (0*10 + 1*5 + 3*2 + 2*1) = 87
        assert security_metrics["vulnerabilities"]["critical"] == 0

    @pytest.mark.unit
    def test_performance_metrics(self):
        """パフォーマンスメトリクスの計算テスト."""
        # パフォーマンスデータのモック
        performance_metrics = {
            "build_time": 120.5,
            "test_execution_time": 45.2,
            "lint_time": 8.3,
            "memory_usage": 512,  # MB
            "cpu_usage": 75,  # %
            "disk_io": 1024,  # MB
        }

        # パフォーマンススコアの計算
        total_time = (
            performance_metrics["build_time"]
            + performance_metrics["test_execution_time"]
            + performance_metrics["lint_time"]
        )

        # パフォーマンスメトリクスの検証
        assert total_time == 174.0
        assert performance_metrics["memory_usage"] < 1024  # 1GB未満
        assert performance_metrics["cpu_usage"] < 90  # CPU使用率90%未満

    @pytest.mark.unit
    def test_maintainability_metrics(self):
        """保守性メトリクスの計算テスト."""
        # 保守性データのモック
        maintainability_metrics = {
            "cyclomatic_complexity": 12,
            "cognitive_complexity": 8,
            "nesting_depth": 3,
            "function_length": 25,
            "class_coupling": 6,
            "documentation_coverage": 78,
        }

        # 保守性スコアの計算
        complexity_penalty = (
            maintainability_metrics["cyclomatic_complexity"] * 2
            + maintainability_metrics["cognitive_complexity"] * 3
            + maintainability_metrics["nesting_depth"] * 5
        )

        maintainability_score = max(
            0, 100 - complexity_penalty + maintainability_metrics["documentation_coverage"] * 0.2
        )

        # 保守性メトリクスの検証
        assert maintainability_score > 0
        assert maintainability_metrics["function_length"] < 50  # 関数の長さが適切

    @pytest.mark.unit
    def test_trend_analysis(self):
        """トレンド分析メトリクスのテスト."""
        # 履歴データのモック
        historical_data = [
            {"date": "2024-11-01", "quality_score": 82, "coverage": 80},
            {"date": "2024-11-15", "quality_score": 85, "coverage": 83},
            {"date": "2024-12-01", "quality_score": 87, "coverage": 85},
        ]

        # トレンド計算
        quality_trend = historical_data[-1]["quality_score"] - historical_data[0]["quality_score"]
        coverage_trend = historical_data[-1]["coverage"] - historical_data[0]["coverage"]

        # トレンド分析の検証
        assert quality_trend == 5  # 品質スコアが5ポイント向上
        assert coverage_trend == 5  # カバレッジが5ポイント向上
        assert quality_trend > 0  # 改善傾向

    @pytest.mark.unit
    def test_composite_score_calculation(self):
        """総合スコア計算のテスト."""
        # 各メトリクスのスコア
        metric_scores = {
            "code_quality": 85,
            "test_coverage": 88,
            "security": 92,
            "performance": 78,
            "maintainability": 82,
        }

        # 重み付け設定
        weights = {
            "code_quality": 0.25,
            "test_coverage": 0.25,
            "security": 0.25,
            "performance": 0.15,
            "maintainability": 0.10,
        }

        # 総合スコアの計算
        composite_score = sum(metric_scores[metric] * weights[metric] for metric in metric_scores)

        # 総合スコア計算の検証
        assert abs(composite_score - 86.15) < 0.1  # 期待値との誤差確認
        assert composite_score > 80  # 良好な総合スコア

    @pytest.mark.unit
    def test_threshold_validation(self):
        """閾値検証のテスト."""
        # 閾値設定
        thresholds = {
            "code_quality": {"min": 80, "target": 90},
            "test_coverage": {"min": 75, "target": 85},
            "security": {"min": 90, "target": 95},
            "performance": {"min": 70, "target": 85},
        }

        # 現在の値
        current_values = {"code_quality": 85, "test_coverage": 88, "security": 92, "performance": 78}

        # 閾値チェック
        validation_results = {}
        for metric, value in current_values.items():
            threshold = thresholds[metric]
            validation_results[metric] = {
                "meets_minimum": value >= threshold["min"],
                "meets_target": value >= threshold["target"],
                "status": "PASS" if value >= threshold["min"] else "FAIL",
            }

        # 閾値検証の確認
        assert all(result["meets_minimum"] for result in validation_results.values())
        assert validation_results["test_coverage"]["meets_target"] is True
        assert validation_results["performance"]["meets_target"] is False

    @pytest.mark.unit
    def test_metrics_export(self):
        """メトリクスエクスポート機能のテスト."""
        # エクスポート用データ
        export_data = {
            "timestamp": "2024-12-01T10:00:00Z",
            "platform": self.platform_info.name,
            "python_version": "3.9.0",
            "metrics": {
                "code_quality": 85,
                "test_coverage": 88,
                "security": 92,
                "performance": 78,
                "maintainability": 82,
            },
            "composite_score": 85.05,
            "grade": "B+",
        }

        # JSON形式でのエクスポート
        json_export = json.dumps(export_data, indent=2)

        # エクスポート機能の検証
        assert json_export is not None
        parsed_data = json.loads(json_export)
        assert parsed_data["composite_score"] == 85.05
        assert parsed_data["grade"] == "B+"

    @pytest.mark.unit
    @pytest.mark.skipif(platform.system() == "Windows", reason="Unix固有のメトリクス")
    def test_unix_specific_metrics(self):
        """Unix固有のメトリクス計算テスト."""
        # Unix固有のメトリクス
        unix_metrics = {"file_permissions": 755, "process_count": 25, "memory_fragmentation": 0.15, "disk_usage": 0.65}

        # Unix固有メトリクスの検証
        assert unix_metrics["file_permissions"] == 755
        assert unix_metrics["disk_usage"] < 0.8  # ディスク使用率80%未満

    @pytest.mark.unit
    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows固有のメトリクス")
    def test_windows_specific_metrics(self):
        """Windows固有のメトリクス計算テスト."""
        # Windows固有のメトリクス
        windows_metrics = {"registry_entries": 150, "service_count": 45, "handle_count": 2500, "page_file_usage": 0.45}

        # Windows固有メトリクスの検証
        assert windows_metrics["registry_entries"] > 0
        assert windows_metrics["page_file_usage"] < 0.8  # ページファイル使用率80%未満

    @pytest.mark.unit
    def test_quality_metrics_creation(self):
        """QualityMetricsオブジェクト作成テスト"""
        metrics = QualityMetrics(
            ruff_issues=5, mypy_errors=2, test_coverage=85.5, test_passed=100, test_failed=2, security_vulnerabilities=0
        )

        assert metrics.ruff_issues == 5
        assert metrics.mypy_errors == 2
        assert metrics.test_coverage == 85.5
        assert metrics.test_passed == 100
        assert metrics.test_failed == 2
        assert metrics.security_vulnerabilities == 0

    @pytest.mark.unit
    def test_quality_score_calculation(self):
        """品質スコア計算テスト"""
        metrics = QualityMetrics(
            ruff_issues=0, mypy_errors=0, test_coverage=90.0, test_passed=100, test_failed=0, security_vulnerabilities=0
        )

        score = metrics.get_quality_score()
        assert score == 100.0

    @pytest.mark.unit
    def test_is_passing_check(self):
        """品質基準チェックテスト"""
        passing_metrics = QualityMetrics(
            ruff_issues=0, mypy_errors=0, test_coverage=85.0, test_passed=100, test_failed=0, security_vulnerabilities=0
        )

        failing_metrics = QualityMetrics(
            ruff_issues=5, mypy_errors=2, test_coverage=70.0, test_passed=95, test_failed=5, security_vulnerabilities=1
        )

        assert passing_metrics.is_passing() is True
        assert failing_metrics.is_passing() is False
