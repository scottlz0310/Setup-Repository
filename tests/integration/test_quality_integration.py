"""品質メトリクス機能の統合テスト"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from setup_repo.quality_metrics import QualityMetrics, QualityMetricsCollector
from setup_repo.quality_trends import QualityTrendManager


class TestQualityIntegration:
    """品質メトリクス機能の統合テスト"""

    def test_full_quality_workflow(self):
        """品質メトリクス収集からトレンド分析までの完全なワークフローテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)

            # 1. 品質メトリクス収集のモック
            collector = QualityMetricsCollector(project_root)

            # モックデータを使用してメトリクスを作成
            metrics = QualityMetrics(
                ruff_issues=2,
                mypy_errors=1,
                test_coverage=85.5,
                test_passed=18,
                test_failed=1,
                security_vulnerabilities=0,
                timestamp="2024-01-01T00:00:00",
                commit_hash="abc12345",
            )

            # 2. レポート保存
            report_file = collector.save_metrics_report(metrics)
            assert report_file.exists()

            # レポート内容を確認
            with open(report_file, encoding="utf-8") as f:
                report_data = json.load(f)

            assert report_data["metrics"]["ruff_issues"] == 2
            assert report_data["metrics"]["test_coverage"] == 85.5
            assert report_data["quality_score"] > 0

            # 3. トレンドデータに追加
            trend_manager = QualityTrendManager(
                project_root / "quality-trends" / "trend-data.json"
            )
            trend_manager.add_data_point(metrics)

            # トレンドデータが保存されたことを確認
            data_points = trend_manager.load_trend_data()
            assert len(data_points) == 1
            assert data_points[0].commit_hash == "abc12345"

            # 4. トレンド分析
            analysis = trend_manager.analyze_trend()
            assert analysis.data_points == 1
            assert analysis.average_quality_score > 0

            # 5. HTMLレポート生成
            html_report = trend_manager.generate_html_report()
            assert html_report.exists()

            # HTMLファイルの基本的な内容を確認
            with open(html_report, encoding="utf-8") as f:
                html_content = f.read()

            assert "品質トレンドレポート" in html_content
            assert "chart.js" in html_content

    def test_multiple_data_points_trend_analysis(self):
        """複数のデータポイントでのトレンド分析テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            trend_manager = QualityTrendManager(project_root / "trend-data.json")

            # 複数のメトリクスデータを作成（改善傾向）
            metrics_data = [
                QualityMetrics(
                    ruff_issues=5,
                    mypy_errors=3,
                    test_coverage=70.0,
                    test_passed=15,
                    test_failed=2,
                    security_vulnerabilities=1,
                    timestamp=f"2024-01-0{i + 1}T00:00:00",
                    commit_hash=f"commit{i}",
                )
                for i in range(5)
            ]

            # 改善傾向を作成
            for i, metrics in enumerate(metrics_data):
                metrics.ruff_issues = 5 - i  # 5, 4, 3, 2, 1
                metrics.mypy_errors = max(0, 3 - i)  # 3, 2, 1, 0, 0
                metrics.test_coverage = 70.0 + i * 5  # 70, 75, 80, 85, 90
                metrics.test_failed = max(0, 2 - i)  # 2, 1, 0, 0, 0
                metrics.security_vulnerabilities = 1 if i == 0 else 0  # 最初だけ脆弱性

                trend_manager.add_data_point(metrics)

            # トレンド分析
            analysis = trend_manager.analyze_trend()

            assert analysis.data_points == 5
            assert analysis.quality_score_trend == "improving"
            assert analysis.coverage_trend == "improving"
            assert analysis.average_coverage == 80.0  # (70+75+80+85+90)/5

            # 最新の状態では問題が解決されているはず
            recent_issues = analysis.recent_issues
            # 最新のデータでは品質が向上しているので、問題は少ないはず
            assert (
                len([issue for issue in recent_issues if "セキュリティ脆弱性" in issue])
                == 0
            )

    @patch("subprocess.run")
    def test_real_metrics_collection_simulation(self, mock_run):
        """実際のメトリクス収集のシミュレーションテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)

            # subprocess.runのモック設定
            def mock_subprocess_side_effect(*args, **kwargs):
                command = args[0]

                if "ruff" in command:
                    # Ruffの結果をモック
                    mock_result = type("MockResult", (), {})()
                    mock_result.returncode = 0
                    mock_result.stdout = "[]"  # エラーなし
                    return mock_result

                elif "mypy" in command:
                    # MyPyの結果をモック
                    mock_result = type("MockResult", (), {})()
                    mock_result.returncode = 0
                    mock_result.stdout = ""  # エラーなし
                    return mock_result

                elif "pytest" in command:
                    # Pytestの結果をモック
                    mock_result = type("MockResult", (), {})()
                    mock_result.returncode = 0
                    mock_result.stdout = ""
                    return mock_result

                elif "bandit" in command:
                    # Banditの結果をモック
                    mock_result = type("MockResult", (), {})()
                    mock_result.returncode = 0
                    mock_result.stdout = '{"results": []}'
                    return mock_result

                elif "safety" in command:
                    # Safetyの結果をモック
                    mock_result = type("MockResult", (), {})()
                    mock_result.returncode = 0
                    mock_result.stdout = "[]"
                    return mock_result

                else:
                    # デフォルトの結果
                    mock_result = type("MockResult", (), {})()
                    mock_result.returncode = 0
                    mock_result.stdout = ""
                    return mock_result

            mock_run.side_effect = mock_subprocess_side_effect

            # カバレッジファイルとテストレポートファイルを作成
            coverage_file = project_root / "coverage.json"
            coverage_data = {"totals": {"percent_covered": 92.5}}
            with open(coverage_file, "w") as f:
                json.dump(coverage_data, f)

            test_report_file = project_root / "test-report.json"
            test_data = {"summary": {"passed": 25, "failed": 0}}
            with open(test_report_file, "w") as f:
                json.dump(test_data, f)

            # メトリクス収集実行
            collector = QualityMetricsCollector(project_root)
            metrics = collector.collect_all_metrics()

            # 結果を確認
            assert metrics.ruff_issues == 0
            assert metrics.mypy_errors == 0
            assert metrics.test_coverage == 92.5
            assert metrics.test_passed == 25
            assert metrics.test_failed == 0
            assert metrics.security_vulnerabilities == 0

            # 品質基準を満たしているはず
            assert metrics.is_passing(80.0) is True

            # 品質スコアが高いはず
            quality_score = metrics.get_quality_score()
            assert quality_score >= 95.0  # 問題がないので高スコア

    def test_quality_degradation_detection(self):
        """品質低下の検出テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            trend_manager = QualityTrendManager(project_root / "trend-data.json")

            # 品質低下のシナリオを作成

            # 最初は良好な状態
            good_metrics = QualityMetrics(
                ruff_issues=0,
                mypy_errors=0,
                test_coverage=90.0,
                test_passed=20,
                test_failed=0,
                security_vulnerabilities=0,
                timestamp="2024-01-01T00:00:00",
                commit_hash="good_commit",
            )
            trend_manager.add_data_point(good_metrics)

            # 徐々に品質が低下
            for i in range(1, 4):
                degraded_metrics = QualityMetrics(
                    ruff_issues=i * 2,  # 2, 4, 6
                    mypy_errors=i,  # 1, 2, 3
                    test_coverage=90.0 - i * 10,  # 80, 70, 60
                    test_passed=20 - i,  # 19, 18, 17
                    test_failed=i,  # 1, 2, 3
                    security_vulnerabilities=1 if i >= 2 else 0,  # 2回目から脆弱性
                    timestamp=f"2024-01-0{i + 1}T00:00:00",
                    commit_hash=f"bad_commit_{i}",
                )
                trend_manager.add_data_point(degraded_metrics)

            # トレンド分析
            analysis = trend_manager.analyze_trend()

            # 低下傾向が検出されるはず
            assert analysis.quality_score_trend == "declining"
            assert analysis.coverage_trend == "declining"

            # 最近の問題が多数検出されるはず
            assert analysis.recent_issues

            # 推奨事項が提供されるはず
            assert analysis.recommendations
            assert any("品質スコア" in rec for rec in analysis.recommendations)

    def test_trend_data_persistence(self):
        """トレンドデータの永続化テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            trend_file = Path(temp_dir) / "trend-data.json"

            # 最初のマネージャーでデータを保存
            manager1 = QualityTrendManager(trend_file)
            metrics1 = QualityMetrics(
                ruff_issues=1,
                test_coverage=85.0,
                timestamp="2024-01-01T00:00:00",
                commit_hash="commit1",
            )
            manager1.add_data_point(metrics1)

            # 新しいマネージャーで同じファイルを読み込み
            manager2 = QualityTrendManager(trend_file)
            data_points = manager2.load_trend_data()

            assert len(data_points) == 1
            assert data_points[0].commit_hash == "commit1"
            assert data_points[0].coverage == 85.0

            # さらにデータを追加
            metrics2 = QualityMetrics(
                ruff_issues=0,
                test_coverage=90.0,
                timestamp="2024-01-02T00:00:00",
                commit_hash="commit2",
            )
            manager2.add_data_point(metrics2)

            # 3つ目のマネージャーで確認
            manager3 = QualityTrendManager(trend_file)
            data_points = manager3.load_trend_data()

            assert len(data_points) == 2
            assert data_points[0].commit_hash == "commit1"  # 時系列順
            assert data_points[1].commit_hash == "commit2"
