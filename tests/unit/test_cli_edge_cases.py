"""CLIコマンドのエッジケースとエラーハンドリングテスト"""

import os
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.setup_repo.cli import quality_cli, sync_cli, trend_cli

from ..multiplatform.helpers import verify_current_platform


class TestCLIEdgeCases:
    """CLIコマンドのエッジケーステスト"""

    @pytest.mark.unit
    def test_sync_cli_with_all_options(self, temp_dir):
        """sync_cliの全オプション指定テスト"""
        verify_current_platform()

        # モック引数オブジェクト
        args = Mock()
        args.owner = "test_owner"
        args.dest = str(temp_dir)
        args.dry_run = True
        args.force = True
        args.use_https = True
        args.sync_only = True
        args.auto_stash = True
        args.skip_uv_install = True

        # 設定読み込みとリポジトリ同期をモック
        with (
            patch("src.setup_repo.cli.load_config") as mock_load_config,
            patch("src.setup_repo.cli.sync_repositories") as mock_sync,
        ):
            mock_load_config.return_value = {
                "github_token": "test_token",
                "use_https": False,  # コマンドライン引数で上書きされる
                "sync_only": False,  # コマンドライン引数で上書きされる
            }

            sync_cli(args)

            # sync_repositoriesが正しい設定で呼ばれることを確認
            mock_sync.assert_called_once()
            called_config = mock_sync.call_args[0][0]

            assert called_config["owner"] == "test_owner"
            assert called_config["dest"] == str(temp_dir)
            assert called_config["dry_run"] is True
            assert called_config["force"] is True
            assert called_config["use_https"] is True  # 上書きされた値
            assert called_config["sync_only"] is True  # 上書きされた値
            assert called_config["auto_stash"] is True
            assert called_config["skip_uv_install"] is True

    @pytest.mark.unit
    def test_sync_cli_with_minimal_options(self):
        """sync_cliの最小オプション指定テスト"""
        verify_current_platform()

        # モック引数オブジェクト（最小限）
        args = Mock()
        args.owner = None
        args.dest = None
        args.dry_run = False
        args.force = False
        args.use_https = False
        args.sync_only = False
        args.auto_stash = False
        args.skip_uv_install = False

        with (
            patch("src.setup_repo.cli.load_config") as mock_load_config,
            patch("src.setup_repo.cli.sync_repositories") as mock_sync,
        ):
            mock_load_config.return_value = {
                "github_token": "test_token",
                "owner": "default_owner",
                "dest": "/default/path",
            }

            sync_cli(args)

            # デフォルト設定が使用されることを確認
            mock_sync.assert_called_once()
            called_config = mock_sync.call_args[0][0]

            assert called_config["owner"] == "default_owner"
            assert called_config["dest"] == "/default/path"
            assert called_config["dry_run"] is False
            assert called_config["force"] is False

    @pytest.mark.unit
    def test_quality_cli_with_relative_path(self, temp_dir):
        """quality_cliの相対パス指定テスト"""
        verify_current_platform()

        # テスト用プロジェクトディレクトリ
        project_dir = temp_dir / "test_project"
        project_dir.mkdir()

        args = Mock()
        args.project_root = "test_project"  # 相対パス
        args.output = None
        args.save_trend = False

        with (
            patch("pathlib.Path.cwd", return_value=temp_dir),
            patch("src.setup_repo.cli.QualityMetricsCollector") as mock_collector_class,
            patch("src.setup_repo.cli.QualityTrendManager"),
        ):
            # モックメトリクス
            mock_metrics = Mock()
            mock_metrics.get_quality_score.return_value = 85.5
            mock_metrics.test_coverage = 90.0
            mock_metrics.ruff_issues = 2
            mock_metrics.mypy_errors = 1
            mock_metrics.security_vulnerabilities = 0
            mock_metrics.is_passing.return_value = True

            mock_collector = Mock()
            mock_collector.collect_all_metrics.return_value = mock_metrics
            mock_collector.save_metrics_report.return_value = project_dir / "report.json"
            mock_collector_class.return_value = mock_collector

            with patch("builtins.print") as mock_print:
                quality_cli(args)

            # 相対パスが正しく解決されることを確認（パス正規化で比較）
            called_path = mock_collector_class.call_args[0][0]
            assert called_path.resolve() == project_dir.resolve()

            # 出力メッセージの確認
            print_calls = [call[0][0] for call in mock_print.call_args_list]
            assert any("品質メトリクス収集完了" in call for call in print_calls)
            assert any("品質スコア: 85.5/100" in call for call in print_calls)

    @pytest.mark.unit
    def test_quality_cli_with_absolute_path_security_check(self, temp_dir):
        """quality_cliの絶対パスセキュリティチェックテスト"""
        verify_current_platform()

        # 現在のディレクトリ外の絶対パス
        external_path = Path("/external/path").resolve()

        args = Mock()
        args.project_root = str(external_path)
        args.output = None
        args.save_trend = False

        # テスト環境でない場合のセキュリティチェック
        with (
            patch.dict(os.environ, {}, clear=True),  # PYTEST_CURRENT_TESTとCIを削除
            patch("pathlib.Path.cwd", return_value=temp_dir),
            pytest.raises(ValueError, match="不正なプロジェクトルートパス"),
        ):
            quality_cli(args)

    @pytest.mark.unit
    def test_quality_cli_with_test_environment_bypass(self, temp_dir):
        """quality_cliのテスト環境でのセキュリティチェック回避テスト"""
        verify_current_platform()

        external_path = Path("/external/path").resolve()

        args = Mock()
        args.project_root = str(external_path)
        args.output = None
        args.save_trend = False

        # テスト環境でのセキュリティチェック回避
        with (
            patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "test_quality_cli"}),
            patch("src.setup_repo.cli.QualityMetricsCollector") as mock_collector_class,
        ):
            mock_metrics = Mock()
            mock_metrics.get_quality_score.return_value = 75.0
            mock_metrics.test_coverage = 80.0
            mock_metrics.ruff_issues = 5
            mock_metrics.mypy_errors = 3
            mock_metrics.security_vulnerabilities = 1
            mock_metrics.is_passing.return_value = False

            mock_collector = Mock()
            mock_collector.collect_all_metrics.return_value = mock_metrics
            mock_collector.save_metrics_report.return_value = external_path / "report.json"
            mock_collector_class.return_value = mock_collector

            with patch("builtins.print"), patch("builtins.exit") as mock_exit:
                quality_cli(args)

                # 品質基準を満たしていない場合はexit(1)が呼ばれる
                mock_exit.assert_called_once_with(1)

    @pytest.mark.unit
    def test_quality_cli_with_trend_saving(self, temp_dir):
        """quality_cliのトレンドデータ保存テスト"""
        verify_current_platform()

        project_dir = temp_dir / "test_project"
        project_dir.mkdir()

        args = Mock()
        args.project_root = str(project_dir)
        args.output = None
        args.save_trend = True

        with (
            patch("src.setup_repo.cli.QualityMetricsCollector") as mock_collector_class,
            patch("src.setup_repo.cli.QualityTrendManager") as mock_trend_class,
        ):
            mock_metrics = Mock()
            mock_metrics.get_quality_score.return_value = 95.0
            mock_metrics.test_coverage = 95.0
            mock_metrics.ruff_issues = 0
            mock_metrics.mypy_errors = 0
            mock_metrics.security_vulnerabilities = 0
            mock_metrics.is_passing.return_value = True

            mock_collector = Mock()
            mock_collector.collect_all_metrics.return_value = mock_metrics
            mock_collector.save_metrics_report.return_value = project_dir / "report.json"
            mock_collector_class.return_value = mock_collector

            mock_trend_manager = Mock()
            mock_trend_class.return_value = mock_trend_manager

            with patch("builtins.print") as mock_print:
                quality_cli(args)

            # トレンドマネージャーが正しく初期化されることを確認（パス正規化で比較）
            expected_trend_file = project_dir / "quality-trends" / "trend-data.json"
            called_path = mock_trend_class.call_args[0][0]
            assert called_path.resolve() == expected_trend_file.resolve()

            # トレンドデータが追加されることを確認
            mock_trend_manager.add_data_point.assert_called_once_with(mock_metrics)

            # トレンド更新メッセージの確認
            print_calls = [call[0][0] for call in mock_print.call_args_list]
            assert any("トレンドデータを更新しました" in call for call in print_calls)

    @pytest.mark.unit
    def test_trend_cli_analyze_action(self, temp_dir):
        """trend_cliの分析アクション テスト"""
        verify_current_platform()

        project_dir = temp_dir / "test_project"
        project_dir.mkdir()

        args = Mock()
        args.project_root = str(project_dir)
        args.trend_file = None
        args.action = "analyze"
        args.days = 30

        with patch("src.setup_repo.cli.QualityTrendManager") as mock_trend_class:
            # モック分析結果
            mock_analysis = Mock()
            mock_analysis.period_days = 30
            mock_analysis.data_points = 15
            mock_analysis.average_quality_score = 87.5
            mock_analysis.average_coverage = 85.2
            mock_analysis.quality_score_trend = "improving"
            mock_analysis.coverage_trend = "stable"
            mock_analysis.recent_issues = ["カバレッジが低下", "新しい脆弱性検出"]
            mock_analysis.recommendations = ["テストを追加", "依存関係を更新"]

            mock_trend_manager = Mock()
            mock_trend_manager.analyze_trend.return_value = mock_analysis
            mock_trend_class.return_value = mock_trend_manager

            with patch("builtins.print") as mock_print:
                trend_cli(args)

            # 分析が実行されることを確認
            mock_trend_manager.analyze_trend.assert_called_once_with(30)

            # 出力内容の確認
            print_calls = [call[0][0] for call in mock_print.call_args_list]
            assert any("品質トレンド分析" in call for call in print_calls)
            assert any("分析期間: 30日" in call for call in print_calls)
            assert any("平均品質スコア: 87.5%" in call for call in print_calls)

    @pytest.mark.unit
    def test_trend_cli_report_action(self, temp_dir):
        """trend_cliのレポート生成アクション テスト"""
        verify_current_platform()

        project_dir = temp_dir / "test_project"
        project_dir.mkdir()

        args = Mock()
        args.project_root = str(project_dir)
        args.trend_file = None
        args.action = "report"
        args.output = None

        with patch("src.setup_repo.cli.QualityTrendManager") as mock_trend_class:
            mock_trend_manager = Mock()
            report_file = project_dir / "quality-trends" / "trend-report.html"
            mock_trend_manager.generate_html_report.return_value = report_file
            mock_trend_class.return_value = mock_trend_manager

            with patch("builtins.print") as mock_print:
                trend_cli(args)

            # HTMLレポート生成が実行されることを確認（パス正規化で比較）
            expected_output = project_dir / "quality-trends" / "trend-report.html"
            called_path = mock_trend_manager.generate_html_report.call_args[0][0]
            assert called_path.resolve() == expected_output.resolve()

            # 出力メッセージの確認
            print_calls = [call[0][0] for call in mock_print.call_args_list]
            assert any("HTMLレポートを生成しました" in call for call in print_calls)

    @pytest.mark.unit
    def test_trend_cli_clean_action_with_keep_days(self, temp_dir):
        """trend_cliのクリーンアクション（保持日数指定）テスト"""
        verify_current_platform()

        project_dir = temp_dir / "test_project"
        project_dir.mkdir()

        args = Mock()
        args.project_root = str(project_dir)
        args.trend_file = None
        args.action = "clean"
        args.keep_days = 90

        with patch("src.setup_repo.cli.QualityTrendManager") as mock_trend_class:
            # モックデータポイント
            from datetime import datetime, timedelta

            old_point = Mock()
            old_point.timestamp = (datetime.now() - timedelta(days=120)).isoformat()

            recent_point = Mock()
            recent_point.timestamp = (datetime.now() - timedelta(days=30)).isoformat()

            mock_data_points = [old_point, recent_point]

            mock_trend_manager = Mock()
            mock_trend_manager.load_trend_data.return_value = mock_data_points
            mock_trend_class.return_value = mock_trend_manager

            with patch("builtins.print") as mock_print:
                trend_cli(args)

            # データの読み込みと保存が実行されることを確認
            mock_trend_manager.load_trend_data.assert_called_once()
            mock_trend_manager.save_trend_data.assert_called_once()

            # 削除されたデータ数の確認
            saved_data = mock_trend_manager.save_trend_data.call_args[0][0]
            assert len(saved_data) == 1  # 古いデータが1件削除される

            # 出力メッセージの確認
            print_calls = [call[0][0] for call in mock_print.call_args_list]
            assert any("1件の古いデータを削除しました" in call for call in print_calls)

    @pytest.mark.unit
    def test_trend_cli_clean_action_without_keep_days(self, temp_dir):
        """trend_cliのクリーンアクション（保持日数未指定）テスト"""
        verify_current_platform()

        project_dir = temp_dir / "test_project"
        project_dir.mkdir()

        args = Mock()
        args.project_root = str(project_dir)
        args.trend_file = None
        args.action = "clean"
        args.keep_days = None

        with patch("src.setup_repo.cli.QualityTrendManager") as mock_trend_class:
            mock_trend_manager = Mock()
            mock_trend_class.return_value = mock_trend_manager

            with patch("builtins.print") as mock_print:
                trend_cli(args)

            # データの読み込みは実行されるが、保存は実行されない
            mock_trend_manager.load_trend_data.assert_called_once()
            mock_trend_manager.save_trend_data.assert_not_called()

            # エラーメッセージの確認
            print_calls = [call[0][0] for call in mock_print.call_args_list]
            assert any("--keep-daysオプションを指定してください" in call for call in print_calls)

    @pytest.mark.unit
    def test_trend_cli_with_custom_trend_file_security_check(self, temp_dir):
        """trend_cliのカスタムトレンドファイルセキュリティチェックテスト"""
        verify_current_platform()

        project_dir = temp_dir / "test_project"
        project_dir.mkdir()

        # プロジェクトルート外のトレンドファイル
        external_trend_file = "/external/trend-data.json"

        args = Mock()
        args.project_root = str(project_dir)
        args.trend_file = external_trend_file
        args.action = "analyze"
        args.days = 30

        # テスト環境でない場合のセキュリティチェック
        with (
            patch.dict(os.environ, {}, clear=True),
            pytest.raises(ValueError, match="不正なプロジェクトルートパス"),
        ):
            trend_cli(args)

    @pytest.mark.unit
    def test_trend_cli_with_custom_output_file(self, temp_dir):
        """trend_cliのカスタム出力ファイル指定テスト"""
        verify_current_platform()

        project_dir = temp_dir / "test_project"
        project_dir.mkdir()

        custom_output = temp_dir / "custom_report.html"

        args = Mock()
        args.project_root = str(project_dir)
        args.trend_file = None
        args.action = "report"
        args.output = str(custom_output)

        with patch("src.setup_repo.cli.QualityTrendManager") as mock_trend_class:
            mock_trend_manager = Mock()
            mock_trend_manager.generate_html_report.return_value = custom_output
            mock_trend_class.return_value = mock_trend_manager

            with patch("builtins.print"):
                trend_cli(args)

            # カスタム出力ファイルが使用されることを確認
            mock_trend_manager.generate_html_report.assert_called_once_with(custom_output)
