"""品質トレンド機能のテスト"""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from setup_repo.quality_metrics import QualityMetrics
from setup_repo.quality_trends import QualityTrendManager, TrendDataPoint


class TestTrendDataPoint:
    """TrendDataPointクラスのテスト"""

    def test_trend_data_point_initialization(self):
        """TrendDataPointの初期化テスト"""
        point = TrendDataPoint(
            timestamp="2024-01-01T00:00:00",
            commit_hash="abc12345",
            quality_score=85.5,
            coverage=90.0,
            ruff_issues=2,
            mypy_errors=1,
            security_vulnerabilities=0,
            test_passed=20,
            test_failed=0,
        )

        assert point.timestamp == "2024-01-01T00:00:00"
        assert point.commit_hash == "abc12345"
        assert point.quality_score == 85.5
        assert point.coverage == 90.0
        assert point.ruff_issues == 2
        assert point.mypy_errors == 1
        assert point.security_vulnerabilities == 0
        assert point.test_passed == 20
        assert point.test_failed == 0

    def test_from_metrics(self):
        """QualityMetricsからTrendDataPointを作成するテスト"""
        metrics = QualityMetrics(
            ruff_issues=3,
            mypy_errors=2,
            test_coverage=85.0,
            test_passed=15,
            test_failed=1,
            security_vulnerabilities=0,
            timestamp="2024-01-01T00:00:00",
            commit_hash="def67890",
        )

        point = TrendDataPoint.from_metrics(metrics)

        assert point.timestamp == "2024-01-01T00:00:00"
        assert point.commit_hash == "def67890"
        assert point.coverage == 85.0
        assert point.ruff_issues == 3
        assert point.mypy_errors == 2
        assert point.security_vulnerabilities == 0
        assert point.test_passed == 15
        assert point.test_failed == 1
        assert point.quality_score == metrics.get_quality_score()


class TestQualityTrendManager:
    """QualityTrendManagerクラスのテスト"""

    def test_trend_manager_initialization(self):
        """QualityTrendManagerの初期化テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            trend_file = Path(temp_dir) / "trend-data.json"
            manager = QualityTrendManager(trend_file)

            assert manager.trend_file == trend_file
            assert manager.logger is not None

    def test_load_trend_data_empty(self):
        """空のトレンドデータ読み込みテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            trend_file = Path(temp_dir) / "trend-data.json"
            manager = QualityTrendManager(trend_file)

            data_points = manager.load_trend_data()

            assert data_points == []

    def test_load_trend_data_with_data(self):
        """データありのトレンドデータ読み込みテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            trend_file = Path(temp_dir) / "trend-data.json"

            # テストデータを作成
            test_data = [
                {
                    "timestamp": "2024-01-01T00:00:00",
                    "commit_hash": "abc12345",
                    "quality_score": 85.0,
                    "coverage": 90.0,
                    "ruff_issues": 1,
                    "mypy_errors": 0,
                    "security_vulnerabilities": 0,
                    "test_passed": 20,
                    "test_failed": 0,
                }
            ]

            with open(trend_file, "w", encoding="utf-8") as f:
                json.dump(test_data, f)

            manager = QualityTrendManager(trend_file)
            data_points = manager.load_trend_data()

            assert len(data_points) == 1
            assert data_points[0].timestamp == "2024-01-01T00:00:00"
            assert data_points[0].commit_hash == "abc12345"
            assert data_points[0].quality_score == 85.0

    def test_save_trend_data(self):
        """トレンドデータ保存テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            trend_file = Path(temp_dir) / "trend-data.json"
            manager = QualityTrendManager(trend_file)

            data_points = [
                TrendDataPoint(
                    timestamp="2024-01-01T00:00:00",
                    commit_hash="abc12345",
                    quality_score=85.0,
                    coverage=90.0,
                    ruff_issues=1,
                    mypy_errors=0,
                    security_vulnerabilities=0,
                    test_passed=20,
                    test_failed=0,
                )
            ]

            manager.save_trend_data(data_points)

            assert trend_file.exists()

            # 保存されたデータを確認
            with open(trend_file, encoding="utf-8") as f:
                saved_data = json.load(f)

            assert len(saved_data) == 1
            assert saved_data[0]["timestamp"] == "2024-01-01T00:00:00"
            assert saved_data[0]["commit_hash"] == "abc12345"

    def test_add_data_point_new(self):
        """新しいデータポイント追加テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            trend_file = Path(temp_dir) / "trend-data.json"
            manager = QualityTrendManager(trend_file)

            metrics = QualityMetrics(
                ruff_issues=2,
                test_coverage=85.0,
                timestamp="2024-01-01T00:00:00",
                commit_hash="abc12345",
            )

            manager.add_data_point(metrics)

            data_points = manager.load_trend_data()
            assert len(data_points) == 1
            assert data_points[0].commit_hash == "abc12345"

    def test_add_data_point_update_existing(self):
        """既存データポイント更新テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            trend_file = Path(temp_dir) / "trend-data.json"
            manager = QualityTrendManager(trend_file)

            # 最初のデータポイントを追加
            metrics1 = QualityMetrics(
                ruff_issues=2,
                test_coverage=85.0,
                timestamp="2024-01-01T00:00:00",
                commit_hash="abc12345",
            )
            manager.add_data_point(metrics1)

            # 同じコミットハッシュで更新
            metrics2 = QualityMetrics(
                ruff_issues=1,  # 改善
                test_coverage=90.0,  # 改善
                timestamp="2024-01-01T01:00:00",  # 時刻は異なる
                commit_hash="abc12345",  # 同じコミット
            )
            manager.add_data_point(metrics2)

            data_points = manager.load_trend_data()
            assert len(data_points) == 1  # 1つのデータポイントのみ
            assert data_points[0].ruff_issues == 1  # 更新された値
            assert data_points[0].coverage == 90.0  # 更新された値

    def test_analyze_trend_no_data(self):
        """データなしでのトレンド分析テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            trend_file = Path(temp_dir) / "trend-data.json"
            manager = QualityTrendManager(trend_file)

            analysis = manager.analyze_trend()

            assert analysis.data_points == 0
            assert analysis.quality_score_trend == "stable"
            assert analysis.coverage_trend == "stable"
            assert analysis.average_quality_score == 0.0
            assert analysis.average_coverage == 0.0
            assert analysis.recommendations

    def test_analyze_trend_with_data(self):
        """データありでのトレンド分析テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            trend_file = Path(temp_dir) / "trend-data.json"
            manager = QualityTrendManager(trend_file)

            # テストデータを作成（改善傾向）
            now = datetime.now()
            test_data = []
            for i in range(5):
                point = TrendDataPoint(
                    timestamp=(now - timedelta(days=4 - i)).isoformat(),
                    commit_hash=f"commit{i}",
                    quality_score=70.0 + i * 5,  # 70, 75, 80, 85, 90 (改善傾向)
                    coverage=80.0 + i * 2,  # 80, 82, 84, 86, 88 (改善傾向)
                    ruff_issues=5 - i,  # 5, 4, 3, 2, 1 (改善)
                    mypy_errors=3 - i if i < 3 else 0,  # 3, 2, 1, 0, 0
                    security_vulnerabilities=0,
                    test_passed=15 + i,
                    test_failed=0,
                )
                test_data.append(point)

            manager.save_trend_data(test_data)

            analysis = manager.analyze_trend(days=7)

            assert analysis.data_points == 5
            assert analysis.quality_score_trend == "improving"
            assert analysis.coverage_trend == "improving"
            assert analysis.average_quality_score == 80.0  # (70+75+80+85+90)/5
            assert analysis.average_coverage == 84.0  # (80+82+84+86+88)/5
            assert analysis.best_quality_score == 90.0
            assert analysis.worst_quality_score == 70.0

    def test_analyze_trend_direction_improving(self):
        """改善傾向の分析テスト"""
        manager = QualityTrendManager()
        values = [70.0, 75.0, 80.0, 85.0, 90.0]  # 明確な改善傾向

        trend = manager._analyze_trend_direction(values)

        assert trend == "improving"

    def test_analyze_trend_direction_declining(self):
        """低下傾向の分析テスト"""
        manager = QualityTrendManager()
        values = [90.0, 85.0, 80.0, 75.0, 70.0]  # 明確な低下傾向

        trend = manager._analyze_trend_direction(values)

        assert trend == "declining"

    def test_analyze_trend_direction_stable(self):
        """安定傾向の分析テスト"""
        manager = QualityTrendManager()
        values = [80.0, 81.0, 79.0, 80.5, 80.2]  # 安定

        trend = manager._analyze_trend_direction(values)

        assert trend == "stable"

    def test_identify_recent_issues(self):
        """最近の問題特定テスト"""
        manager = QualityTrendManager()

        # 問題のあるデータポイント
        data_points = [
            TrendDataPoint(
                timestamp="2024-01-01T00:00:00",
                commit_hash="abc12345",
                quality_score=65.0,  # 低い品質スコア
                coverage=75.0,  # 低いカバレッジ
                ruff_issues=5,  # Ruffエラーあり
                mypy_errors=3,  # MyPyエラーあり
                security_vulnerabilities=1,  # セキュリティ脆弱性あり
                test_passed=15,
                test_failed=2,  # テスト失敗あり
            )
        ]

        issues = manager._identify_recent_issues(data_points)

        assert len(issues) == 6  # すべての問題が検出される
        assert any("品質スコアが低下" in issue for issue in issues)
        assert any("テストカバレッジが不足" in issue for issue in issues)
        assert any("Ruffエラーが5件" in issue for issue in issues)
        assert any("MyPyエラーが3件" in issue for issue in issues)
        assert any("セキュリティ脆弱性が1件" in issue for issue in issues)
        assert any("テストが2件失敗" in issue for issue in issues)

    def test_generate_recommendations(self):
        """推奨事項生成テスト"""
        manager = QualityTrendManager()

        # 品質の低いデータポイント
        data_points = [
            TrendDataPoint(
                timestamp="2024-01-01T00:00:00",
                commit_hash="abc12345",
                quality_score=70.0,  # 低い品質スコア
                coverage=75.0,  # 低いカバレッジ
                ruff_issues=0,
                mypy_errors=0,
                security_vulnerabilities=1,  # セキュリティ脆弱性あり
                test_passed=15,
                test_failed=0,
            )
        ]

        recommendations = manager._generate_recommendations(data_points, 70.0, 75.0)

        assert len(recommendations) >= 2
        assert any("品質スコアを向上" in rec for rec in recommendations)
        assert any("テストカバレッジを向上" in rec for rec in recommendations)
        assert any("セキュリティ脆弱性の修正" in rec for rec in recommendations)

    def test_generate_html_report(self):
        """HTMLレポート生成テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            trend_file = Path(temp_dir) / "trend-data.json"
            manager = QualityTrendManager(trend_file)

            # テストデータを作成
            test_data = [
                TrendDataPoint(
                    timestamp="2024-01-01T00:00:00",
                    commit_hash="abc12345",
                    quality_score=85.0,
                    coverage=90.0,
                    ruff_issues=1,
                    mypy_errors=0,
                    security_vulnerabilities=0,
                    test_passed=20,
                    test_failed=0,
                )
            ]
            manager.save_trend_data(test_data)

            output_file = Path(temp_dir) / "report.html"
            result_file = manager.generate_html_report(output_file)

            assert result_file.exists()
            assert result_file == output_file

            # HTMLファイルの内容を確認
            with open(result_file, encoding="utf-8") as f:
                html_content = f.read()

            assert "品質トレンドレポート" in html_content
            assert "chart.js" in html_content
            assert "qualityChart" in html_content
            assert "coverageChart" in html_content
