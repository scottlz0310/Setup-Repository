"""
CLI機能のテスト

マルチプラットフォームテスト方針に準拠したCLI機能のテスト
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from setup_repo.cli import migration_cli, quality_cli, setup_cli, sync_cli, trend_cli
from tests.multiplatform.helpers import verify_current_platform


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

    def test_trend_cli_clean_action_basic(self):
        """トレンドCLI クリーンアクション基本テスト"""
        args = Mock()
        args.project_root = None
        args.trend_file = None
        args.action = "clean"
        args.keep_days = 30

        with (
            patch("setup_repo.cli.QualityTrendManager") as mock_manager,
            patch("setup_repo.cli.safe_path_join") as mock_path_join,
        ):
            mock_path_join.side_effect = [Path.cwd(), Path("output/quality-trends"), Path("trend-data.json")]
            mock_instance = Mock()
            mock_instance.load_trend_data.return_value = []
            mock_manager.return_value = mock_instance

            with patch("builtins.print"):
                trend_cli(args)

            mock_instance.load_trend_data.assert_called_once()

    def test_trend_cli_clean_action_without_keep_days(self):
        """トレンドCLI クリーンアクション（保持日数未指定）テスト"""
        args = Mock()
        args.project_root = None
        args.trend_file = None
        args.action = "clean"
        args.keep_days = None

        with (
            patch("setup_repo.cli.QualityTrendManager") as mock_manager,
            patch("setup_repo.cli.safe_path_join") as mock_path_join,
        ):
            mock_path_join.side_effect = [Path.cwd(), Path("output/quality-trends"), Path("trend-data.json")]
            mock_instance = Mock()
            mock_manager.return_value = mock_instance

            with patch("builtins.print") as mock_print:
                trend_cli(args)

            mock_print.assert_called_with("--keep-daysオプションを指定してください")

    def test_quality_cli_invalid_project_root(self):
        """品質CLI 不正なプロジェクトルートエラーテスト"""
        args = Mock()
        args.project_root = "../../../etc/passwd"
        args.output = None
        args.save_trend = False

        with (
            patch("setup_repo.cli.safe_path_join", side_effect=ValueError("不正なパス")),
            pytest.raises(ValueError, match="不正なプロジェクトルートパス"),
        ):
            quality_cli(args)

    def test_quality_cli_with_save_trend(self):
        """品質CLI トレンドデータ保存テスト"""
        args = Mock()
        args.project_root = None
        args.output = None
        args.save_trend = True

        with (
            patch("setup_repo.cli.QualityMetricsCollector") as mock_collector,
            patch("setup_repo.cli.QualityTrendManager") as mock_trend_manager,
            patch("setup_repo.cli.safe_path_join") as mock_path_join,
        ):
            mock_path_join.side_effect = [Path.cwd(), Path("output/quality-trends"), Path("trend-data.json")]
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

            mock_trend_instance = Mock()
            mock_trend_manager.return_value = mock_trend_instance

            with patch("builtins.print"):
                quality_cli(args)

            mock_trend_instance.add_data_point.assert_called_once_with(mock_metrics)

    def test_quality_cli_failing_quality_gate(self):
        """品質CLI 品質基準未達成テスト"""
        args = Mock()
        args.project_root = None
        args.output = None
        args.save_trend = False

        with (
            patch("setup_repo.cli.QualityMetricsCollector") as mock_collector,
            patch("builtins.exit") as mock_exit,
        ):
            mock_instance = Mock()
            mock_metrics = Mock()
            mock_metrics.get_quality_score.return_value = 50.0
            mock_metrics.test_coverage = 60.0
            mock_metrics.ruff_issues = 10
            mock_metrics.mypy_errors = 5
            mock_metrics.security_vulnerabilities = 2
            mock_metrics.is_passing.return_value = False
            mock_instance.collect_all_metrics.return_value = mock_metrics
            mock_instance.save_metrics_report.return_value = "report.json"
            mock_collector.return_value = mock_instance

            with patch("builtins.print"):
                quality_cli(args)

            mock_exit.assert_called_once_with(1)

    def test_migration_cli_check(self):
        """マイグレーションCLI チェックテスト"""
        args = Mock()
        args.project_root = None
        args.action = "check"

        with (
            patch("setup_repo.cli.MigrationManager") as mock_manager,
            patch("builtins.print"),
        ):
            mock_instance = Mock()
            mock_result = {
                "current_version": "1.0.0",
                "target_version": "1.2.0",
                "migration_needed": True,
                "changes": [{"description": "新しい設定項目", "type": "config_update"}],
            }
            mock_instance.check_migration_needed.return_value = mock_result
            mock_manager.return_value = mock_instance

            migration_cli(args)

            mock_instance.check_migration_needed.assert_called_once()

    def test_migration_cli_run(self):
        """マイグレーションCLI 実行テスト"""
        args = Mock()
        args.project_root = None
        args.action = "run"
        args.no_backup = False

        with (
            patch("setup_repo.cli.MigrationManager") as mock_manager,
            patch("builtins.print"),
        ):
            mock_instance = Mock()
            mock_result = {
                "success": True,
                "message": "マイグレーションが完了しました",
                "backup_path": "/path/to/backup.tar.gz",
                "migration_result": {"migrations": [{"description": "設定ファイルを更新しました"}]},
            }
            mock_instance.run_migration.return_value = mock_result
            mock_manager.return_value = mock_instance

            migration_cli(args)

            mock_instance.run_migration.assert_called_once_with(backup=True)

    def test_migration_cli_rollback(self):
        """マイグレーションCLI ロールバックテスト"""
        args = Mock()
        args.project_root = None
        args.action = "rollback"
        args.backup_name = "test_backup"

        with (
            patch("setup_repo.cli.MigrationManager") as mock_manager,
            patch("builtins.print"),
        ):
            mock_instance = Mock()
            mock_result = {"success": True, "message": "バックアップ 'test_backup' からロールバックしました"}
            mock_instance.rollback_migration.return_value = mock_result
            mock_manager.return_value = mock_instance

            migration_cli(args)

            mock_instance.rollback_migration.assert_called_once_with("test_backup")

    def test_migration_cli_run_failure(self):
        """マイグレーションCLI 実行失敗テスト"""
        args = Mock()
        args.project_root = None
        args.action = "run"
        args.no_backup = False

        with (
            patch("setup_repo.cli.MigrationManager") as mock_manager,
            patch("builtins.print"),
            patch("builtins.exit") as mock_exit,
        ):
            mock_instance = Mock()
            mock_result = {"success": False, "error": "マイグレーション失敗", "backup_path": "/path/to/backup.tar.gz"}
            mock_instance.run_migration.return_value = mock_result
            mock_manager.return_value = mock_instance

            migration_cli(args)

            mock_exit.assert_called_once_with(1)

    def test_migration_cli_invalid_project_root(self):
        """マイグレーションCLI 不正なプロジェクトルートエラーテスト"""
        args = Mock()
        args.project_root = "../../../etc/passwd"
        args.action = "check"

        with (
            patch("setup_repo.cli.safe_path_join", side_effect=ValueError("不正なパス")),
            pytest.raises(ValueError, match="不正なプロジェクトルートパス"),
        ):
            migration_cli(args)
