"""CLI コマンドハンドラーのテスト"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.setup_repo.cli import quality_cli, setup_cli, sync_cli, trend_cli
from src.setup_repo.quality_metrics import QualityMetrics
from src.setup_repo.quality_trends import TrendAnalysis


class TestSetupCli:
    """setup_cli関数のテスト"""

    @patch("src.setup_repo.cli.run_interactive_setup")
    def test_setup_cli_success(self, mock_run_setup):
        """正常なセットアップ実行のテスト"""
        # Arrange
        mock_run_setup.return_value = True
        args = Mock()

        # Act
        setup_cli(args)

        # Assert
        mock_run_setup.assert_called_once()

    @patch("src.setup_repo.cli.run_interactive_setup")
    def test_setup_cli_failure(self, mock_run_setup):
        """セットアップ失敗時のテスト"""
        # Arrange
        mock_run_setup.return_value = False
        args = Mock()

        # Act
        setup_cli(args)

        # Assert
        mock_run_setup.assert_called_once()

    @patch("src.setup_repo.cli.run_interactive_setup")
    def test_setup_cli_exception(self, mock_run_setup):
        """セットアップ中の例外処理テスト"""
        # Arrange
        mock_run_setup.side_effect = Exception("セットアップエラー")
        args = Mock()

        # Act & Assert
        with pytest.raises(Exception, match="セットアップエラー"):
            setup_cli(args)


class TestSyncCli:
    """sync_cli関数のテスト"""

    @patch("src.setup_repo.cli.sync_repositories")
    @patch("src.setup_repo.cli.load_config")
    def test_sync_cli_basic(self, mock_load_config, mock_sync):
        """基本的な同期実行のテスト"""
        # Arrange
        mock_config = {
            "owner": "test_owner",
            "dest": "/test/dest",
            "use_https": False,
            "sync_only": False,
            "auto_stash": False,
            "skip_uv_install": False,
        }
        mock_load_config.return_value = mock_config
        mock_sync.return_value = Mock(success=True)

        args = Mock()
        args.owner = None
        args.dest = None
        args.dry_run = False
        args.force = False
        args.use_https = False
        args.sync_only = False
        args.auto_stash = False
        args.skip_uv_install = False

        # Act
        sync_cli(args)

        # Assert
        mock_load_config.assert_called_once()
        mock_sync.assert_called_once()

        # 設定が正しく渡されているかチェック
        call_args = mock_sync.call_args[0][0]
        assert call_args["owner"] == "test_owner"
        assert call_args["dest"] == "/test/dest"
        assert call_args["dry_run"] is False
        assert call_args["force"] is False

    @patch("src.setup_repo.cli.sync_repositories")
    @patch("src.setup_repo.cli.load_config")
    def test_sync_cli_with_args_override(self, mock_load_config, mock_sync):
        """コマンドライン引数による設定上書きのテスト"""
        # Arrange
        mock_config = {
            "owner": "config_owner",
            "dest": "/config/dest",
            "use_https": False,
            "sync_only": False,
            "auto_stash": False,
            "skip_uv_install": False,
        }
        mock_load_config.return_value = mock_config
        mock_sync.return_value = Mock(success=True)

        args = Mock()
        args.owner = "args_owner"
        args.dest = "/args/dest"
        args.dry_run = True
        args.force = True
        args.use_https = True
        args.sync_only = True
        args.auto_stash = True
        args.skip_uv_install = True

        # Act
        sync_cli(args)

        # Assert
        call_args = mock_sync.call_args[0][0]
        assert call_args["owner"] == "args_owner"  # 引数で上書き
        assert call_args["dest"] == "/args/dest"  # 引数で上書き
        assert call_args["dry_run"] is True
        assert call_args["force"] is True
        assert call_args["use_https"] is True
        assert call_args["sync_only"] is True
        assert call_args["auto_stash"] is True
        assert call_args["skip_uv_install"] is True

    @patch("src.setup_repo.cli.sync_repositories")
    @patch("src.setup_repo.cli.load_config")
    def test_sync_cli_config_fallback(self, mock_load_config, mock_sync):
        """設定ファイルからのフォールバック値のテスト"""
        # Arrange
        mock_config = {
            "use_https": True,
            "sync_only": True,
            "auto_stash": True,
            "skip_uv_install": True,
        }
        mock_load_config.return_value = mock_config
        mock_sync.return_value = Mock(success=True)

        args = Mock()
        args.owner = None
        args.dest = None
        args.dry_run = False
        args.force = False
        args.use_https = False  # Falseだが設定ファイルのTrueが使用される
        args.sync_only = False  # Falseだが設定ファイルのTrueが使用される
        args.auto_stash = False  # Falseだが設定ファイルのTrueが使用される
        args.skip_uv_install = False  # Falseだが設定ファイルのTrueが使用される

        # Act
        sync_cli(args)

        # Assert
        call_args = mock_sync.call_args[0][0]
        assert call_args["use_https"] is True
        assert call_args["sync_only"] is True
        assert call_args["auto_stash"] is True
        assert call_args["skip_uv_install"] is True

    @patch("src.setup_repo.cli.sync_repositories")
    @patch("src.setup_repo.cli.load_config")
    def test_sync_cli_exception(self, mock_load_config, mock_sync):
        """同期中の例外処理テスト"""
        # Arrange
        mock_load_config.return_value = {}
        mock_sync.side_effect = Exception("同期エラー")

        args = Mock()
        args.owner = None
        args.dest = None
        args.dry_run = False
        args.force = False
        args.use_https = False
        args.sync_only = False
        args.auto_stash = False
        args.skip_uv_install = False

        # Act & Assert
        with pytest.raises(Exception, match="同期エラー"):
            sync_cli(args)


class TestQualityCli:
    """quality_cli関数のテスト"""

    @patch("src.setup_repo.cli.QualityTrendManager")
    @patch("src.setup_repo.cli.QualityMetricsCollector")
    @patch("builtins.print")
    def test_quality_cli_basic(self, mock_print, mock_collector_class, mock_trend_class):
        """基本的な品質メトリクス収集のテスト"""
        # Arrange
        mock_metrics = QualityMetrics(
            ruff_issues=5,
            mypy_errors=3,
            test_coverage=85.5,
            test_passed=100,
            test_failed=2,
            security_vulnerabilities=1,
        )
        mock_metrics.get_quality_score = Mock(return_value=75.5)
        mock_metrics.is_passing = Mock(return_value=False)

        mock_collector = Mock()
        mock_collector.collect_all_metrics.return_value = mock_metrics
        mock_collector.save_metrics_report.return_value = Path("/test/report.json")
        mock_collector_class.return_value = mock_collector

        args = Mock()
        args.project_root = "/test/project"
        args.output = "/test/output.json"
        args.save_trend = False

        # Act
        with pytest.raises(SystemExit) as exc_info:
            quality_cli(args)

        # Assert
        assert exc_info.value.code == 1  # 品質基準を満たしていないため
        # Windowsではパスが異なる形式になるため、パスの最終部分を確認
        call_args = mock_collector_class.call_args[0][0]
        assert call_args.name == "project"
        mock_collector.collect_all_metrics.assert_called_once()
        mock_collector.save_metrics_report.assert_called_once_with(mock_metrics, Path("/test/output.json"))

        # 出力内容の確認
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("品質スコア: 75.5/100" in call for call in print_calls)
        assert any("テストカバレッジ: 85.5%" in call for call in print_calls)
        assert any("品質基準を満たしていません" in call for call in print_calls)

    @patch("src.setup_repo.cli.QualityTrendManager")
    @patch("src.setup_repo.cli.QualityMetricsCollector")
    @patch("builtins.print")
    def test_quality_cli_with_trend_save(self, mock_print, mock_collector_class, mock_trend_class):
        """トレンドデータ保存付きのテスト"""
        # Arrange
        mock_metrics = QualityMetrics()
        mock_metrics.get_quality_score = Mock(return_value=90.0)
        mock_metrics.is_passing = Mock(return_value=True)

        mock_collector = Mock()
        mock_collector.collect_all_metrics.return_value = mock_metrics
        mock_collector.save_metrics_report.return_value = Path("/test/report.json")
        mock_collector_class.return_value = mock_collector

        mock_trend_manager = Mock()
        mock_trend_class.return_value = mock_trend_manager

        args = Mock()
        args.project_root = None  # デフォルト値を使用
        args.output = None  # デフォルト値を使用
        args.save_trend = True

        # Act
        quality_cli(args)

        # Assert
        mock_trend_manager.add_data_point.assert_called_once_with(mock_metrics)
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("トレンドデータを更新しました" in call for call in print_calls)
        assert any("品質基準を満たしています" in call for call in print_calls)

    @patch("src.setup_repo.cli.QualityMetricsCollector")
    def test_quality_cli_exception(self, mock_collector_class):
        """品質チェック中の例外処理テスト"""
        # Arrange
        mock_collector_class.side_effect = Exception("メトリクス収集エラー")

        args = Mock()
        args.project_root = None
        args.output = None
        args.save_trend = False

        # Act & Assert
        with pytest.raises(Exception, match="メトリクス収集エラー"):
            quality_cli(args)


class TestTrendCli:
    """trend_cli関数のテスト"""

    @patch("src.setup_repo.cli.QualityTrendManager")
    @patch("builtins.print")
    def test_trend_cli_analyze(self, mock_print, mock_trend_class):
        """トレンド分析のテスト"""
        # Arrange
        mock_analysis = TrendAnalysis(
            period_days=30,
            data_points=15,
            quality_score_trend="improving",
            coverage_trend="stable",
            average_quality_score=85.5,
            average_coverage=78.2,
            best_quality_score=92.0,
            worst_quality_score=75.0,
            recent_issues=["テストカバレッジが不足しています"],
            recommendations=["テストケースを追加してください"],
        )

        mock_trend_manager = Mock()
        mock_trend_manager.analyze_trend.return_value = mock_analysis
        mock_trend_class.return_value = mock_trend_manager

        args = Mock()
        args.project_root = "/test/project"
        args.trend_file = "/test/trend.json"
        args.action = "analyze"
        args.days = 30

        # Act
        trend_cli(args)

        # Assert
        # Windowsではパスが異なる形式になるため、パスの最終部分を確認
        call_args = mock_trend_class.call_args[0][0]
        assert call_args.name == "trend.json"
        mock_trend_manager.analyze_trend.assert_called_once_with(30)

        # 出力内容の確認
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("品質トレンド分析" in call for call in print_calls)
        assert any("分析期間: 30日" in call for call in print_calls)
        assert any("平均品質スコア: 85.5%" in call for call in print_calls)

    @patch("src.setup_repo.cli.QualityTrendManager")
    @patch("builtins.print")
    def test_trend_cli_report(self, mock_print, mock_trend_class):
        """HTMLレポート生成のテスト"""
        # Arrange
        mock_trend_manager = Mock()
        mock_trend_manager.generate_html_report.return_value = Path("/test/report.html")
        mock_trend_class.return_value = mock_trend_manager

        args = Mock()
        args.project_root = None
        args.trend_file = None
        args.action = "report"
        args.output = "/test/custom_report.html"

        # Act
        trend_cli(args)

        # Assert
        mock_trend_manager.generate_html_report.assert_called_once_with(Path("/test/custom_report.html"))
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("HTMLレポートを生成しました" in call for call in print_calls)

    @patch("src.setup_repo.cli.QualityTrendManager")
    @patch("builtins.print")
    def test_trend_cli_clean(self, mock_print, mock_trend_class):
        """古いデータ削除のテスト"""
        # Arrange
        # データポイントのモック
        old_point = Mock()
        old_point.timestamp = "2023-12-01T00:00:00"
        new_point = Mock()
        new_point.timestamp = "2024-01-10T00:00:00"

        mock_trend_manager = Mock()
        mock_trend_manager.load_trend_data.return_value = [old_point, new_point]
        mock_trend_class.return_value = mock_trend_manager

        args = Mock()
        args.project_root = None
        args.trend_file = None
        args.action = "clean"
        args.keep_days = 10

        # Act
        trend_cli(args)

        # Assert
        mock_trend_manager.save_trend_data.assert_called_once()
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        # 削除されたデータ数の確認は実装に依存するため、メッセージの存在のみ確認
        assert any("古いデータを削除しました" in call for call in print_calls)

    @patch("src.setup_repo.cli.QualityTrendManager")
    @patch("builtins.print")
    def test_trend_cli_clean_no_keep_days(self, mock_print, mock_trend_class):
        """keep_daysオプション未指定時のテスト"""
        # Arrange
        mock_trend_manager = Mock()
        mock_trend_class.return_value = mock_trend_manager

        args = Mock()
        args.project_root = None
        args.trend_file = None
        args.action = "clean"
        args.keep_days = None

        # Act
        trend_cli(args)

        # Assert
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("--keep-daysオプションを指定してください" in call for call in print_calls)

    @patch("src.setup_repo.cli.QualityTrendManager")
    def test_trend_cli_exception(self, mock_trend_class):
        """トレンド処理中の例外処理テスト"""
        # Arrange
        mock_trend_class.side_effect = Exception("トレンド処理エラー")

        args = Mock()
        args.project_root = None
        args.trend_file = None
        args.action = "analyze"
        args.days = 30

        # Act & Assert
        with pytest.raises(Exception, match="トレンド処理エラー"):
            trend_cli(args)


class TestCliEdgeCases:
    """CLIのエッジケースとエラーハンドリングのテスト"""

    @patch("src.setup_repo.cli.load_config")
    def test_sync_cli_empty_config(self, mock_load_config):
        """空の設定でのsync_cliテスト"""
        # Arrange
        mock_load_config.return_value = {}

        args = Mock()
        args.owner = None
        args.dest = None
        args.dry_run = False
        args.force = False
        args.use_https = False
        args.sync_only = False
        args.auto_stash = False
        args.skip_uv_install = False

        # Act
        with patch("src.setup_repo.cli.sync_repositories") as mock_sync:
            sync_cli(args)

        # Assert
        call_args = mock_sync.call_args[0][0]
        assert call_args.get("owner") is None
        assert call_args.get("dest") is None
        assert call_args["use_https"] is False
        assert call_args["sync_only"] is False

    def test_quality_cli_default_paths(self):
        """デフォルトパス使用時のquality_cliテスト"""
        # Arrange
        args = Mock()
        args.project_root = None
        args.output = None
        args.save_trend = False

        # Act
        with patch("src.setup_repo.cli.QualityMetricsCollector") as mock_collector_class:
            mock_metrics = Mock()
            mock_metrics.get_quality_score.return_value = 90.0
            mock_metrics.is_passing.return_value = True
            # フォーマット文字列で使用される属性を設定
            mock_metrics.test_coverage = 85.5
            mock_metrics.ruff_issues = 0
            mock_metrics.mypy_errors = 0
            mock_metrics.security_vulnerabilities = 0
            mock_metrics.test_passed = 100
            mock_metrics.test_failed = 0

            mock_collector = Mock()
            mock_collector.collect_all_metrics.return_value = mock_metrics
            mock_collector.save_metrics_report.return_value = Path("/test/report.json")
            mock_collector_class.return_value = mock_collector

            with patch("builtins.print"):
                quality_cli(args)

        # Assert
        # Path.cwd()が使用されることを確認
        mock_collector_class.assert_called_once_with(Path.cwd())
        # デフォルトのoutput_file（None）が渡されることを確認
        mock_collector.save_metrics_report.assert_called_once_with(mock_metrics, None)

    def test_trend_cli_default_paths(self):
        """デフォルトパス使用時のtrend_cliテスト"""
        # Arrange
        args = Mock()
        args.project_root = None
        args.trend_file = None
        args.action = "analyze"
        args.days = 30

        # Act
        with patch("src.setup_repo.cli.QualityTrendManager") as mock_trend_class:
            mock_analysis = Mock()
            mock_analysis.period_days = 30
            mock_analysis.data_points = 0
            mock_analysis.recent_issues = []
            mock_analysis.recommendations = []
            # フォーマット文字列で使用される属性を設定
            mock_analysis.average_quality_score = 85.5
            mock_analysis.average_coverage = 78.2
            mock_analysis.quality_score_trend = "improving"
            mock_analysis.coverage_trend = "stable"

            mock_trend_manager = Mock()
            mock_trend_manager.analyze_trend.return_value = mock_analysis
            mock_trend_class.return_value = mock_trend_manager

            with patch("builtins.print"):
                trend_cli(args)

        # Assert
        # デフォルトのtrend_fileパスが使用されることを確認
        expected_path = Path.cwd() / "quality-trends" / "trend-data.json"
        mock_trend_class.assert_called_once_with(expected_path)
