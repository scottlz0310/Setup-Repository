"""
CLI機能のテスト

マルチプラットフォームテスト方針に準拠したCLI機能のテスト
"""

from pathlib import Path
from unittest.mock import Mock, patch

from setup_repo.cli import (
    quality_cli,
    setup_cli,
    sync_cli,
    trend_cli,
)
from tests.multiplatform.helpers import (
    verify_current_platform,
)


class TestCLI:
    """CLI機能のテスト"""

    def test_setup_cli_success(self):
        """setupCLI実行成功テスト"""
        verify_current_platform()  # プラットフォーム検証

        args = Mock()

        with patch("setup_repo.cli.run_interactive_setup") as mock_setup:
            setup_cli(args)
            mock_setup.assert_called_once()

    def test_sync_cli_success(self):
        """syncCLI実行成功テスト"""
        verify_current_platform()  # プラットフォーム検証

        args = Mock()
        args.owner = None
        args.dest = None
        args.dry_run = False
        args.force = False
        args.use_https = False
        args.sync_only = False
        args.auto_stash = False
        args.skip_uv_install = False

        with patch("setup_repo.cli.load_config") as mock_load, patch("setup_repo.cli.sync_repositories") as mock_sync:
            mock_load.return_value = {
                "use_https": False,
                "sync_only": False,
                "auto_stash": False,
                "skip_uv_install": False,
            }
            sync_cli(args)
            mock_sync.assert_called_once()

    def test_quality_cli_success(self):
        """qualityCLI実行成功テスト"""
        verify_current_platform()  # プラットフォーム検証

        args = Mock()
        args.project_root = None
        args.output = None
        args.save_trend = False

        with patch("setup_repo.cli.QualityMetricsCollector") as mock_collector:
            mock_instance = Mock()
            mock_metrics = Mock()
            mock_metrics.get_quality_score.return_value = 85.0
            mock_metrics.test_coverage = 90.0
            mock_metrics.ruff_issues = 2
            mock_metrics.mypy_errors = 1
            mock_metrics.security_vulnerabilities = 0
            mock_metrics.is_passing.return_value = True
            mock_instance.collect_all_metrics.return_value = mock_metrics
            mock_instance.save_metrics_report.return_value = "report.json"
            mock_collector.return_value = mock_instance

            with patch("builtins.print"):
                quality_cli(args)

            mock_collector.assert_called_once()
            mock_instance.collect_all_metrics.assert_called_once()

    def test_trend_cli_analyze(self):
        """trendCLI分析テスト"""
        args = Mock()
        args.project_root = None
        args.trend_file = None
        args.action = "analyze"
        args.days = 30

        with patch("setup_repo.cli.QualityTrendManager") as mock_manager:
            mock_instance = Mock()
            mock_analysis = Mock()
            mock_analysis.period_days = 30
            mock_analysis.data_points = 10
            mock_analysis.average_quality_score = 85.0
            mock_analysis.average_coverage = 90.0
            mock_analysis.quality_score_trend = "improving"
            mock_analysis.coverage_trend = "stable"
            mock_analysis.recent_issues = []
            mock_analysis.recommendations = ["Keep up the good work"]
            mock_instance.analyze_trend.return_value = mock_analysis
            mock_manager.return_value = mock_instance

            with patch("builtins.print"):
                trend_cli(args)

            mock_manager.assert_called_once()
            mock_instance.analyze_trend.assert_called_once_with(30)

    def test_quality_cli_with_project_root(self):
        """品質CLI プロジェクトルート指定テスト"""
        args = Mock()
        args.project_root = "test_project"
        args.output = None
        args.save_trend = False

        with (
            patch("setup_repo.cli.QualityMetricsCollector") as mock_collector,
            patch("setup_repo.cli.safe_path_join") as mock_path_join,
        ):
            mock_path_join.return_value = Path("test_project")
            mock_instance = Mock()
            mock_metrics = Mock()
            mock_metrics.get_quality_score.return_value = 85.0
            mock_metrics.test_coverage = 90.0
            mock_metrics.ruff_issues = 0
            mock_metrics.mypy_errors = 0
            mock_metrics.security_vulnerabilities = 0
            mock_metrics.is_passing.return_value = True
            mock_instance.collect_all_metrics.return_value = mock_metrics
            mock_instance.save_metrics_report.return_value = "report.json"
            mock_collector.return_value = mock_instance

            with patch("builtins.print"):
                quality_cli(args)

            mock_collector.assert_called_once_with(Path("test_project"))

    def test_trend_cli_report_action(self):
        """トレンドCLI レポート生成テスト"""
        args = Mock()
        args.project_root = None
        args.trend_file = None
        args.action = "report"
        args.output = None

        with (
            patch("setup_repo.cli.QualityTrendManager") as mock_manager,
            patch("setup_repo.cli.safe_path_join") as mock_path_join,
        ):
            mock_path_join.return_value = Path("trend-report.html")
            mock_instance = Mock()
            mock_instance.generate_html_report.return_value = Path("report.html")
            mock_manager.return_value = mock_instance

            with patch("builtins.print"):
                trend_cli(args)

            mock_instance.generate_html_report.assert_called_once()
