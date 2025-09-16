"""品質トレンド分析機能の包括的テスト."""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock

import pytest

from setup_repo.quality_logger import QualityLogger
from setup_repo.quality_metrics import QualityMetrics
from setup_repo.quality_trends import QualityTrendManager, TrendAnalysis, TrendDataPoint


class TestTrendDataPoint:
    """TrendDataPointクラスのテスト."""

    @pytest.mark.unit
    def test_from_metrics(self):
        """QualityMetricsからTrendDataPointを作成するテスト."""
        metrics = QualityMetrics(
            timestamp="2024-01-01T00:00:00Z",
            commit_hash="abc123",
            ruff_issues=5,
            mypy_errors=3,
            test_coverage=85.5,
            test_passed=95,
            test_failed=2,
            security_vulnerabilities=1,
        )

        data_point = TrendDataPoint.from_metrics(metrics)

        assert data_point.timestamp == "2024-01-01T00:00:00Z"
        assert data_point.commit_hash == "abc123"
        assert data_point.ruff_issues == 5
        assert data_point.mypy_errors == 3
        assert data_point.coverage == 85.5
        assert data_point.test_passed == 95
        assert data_point.test_failed == 2
        assert data_point.security_vulnerabilities == 1
        assert isinstance(data_point.quality_score, float)


class TestQualityTrendManager:
    """QualityTrendManagerクラスのテスト."""

    def setup_method(self):
        """テストメソッドの前処理."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.trend_file = self.temp_dir / "trend-data.json"
        self.mock_logger = Mock(spec=QualityLogger)
        self.manager = QualityTrendManager(trend_file=self.trend_file, logger=self.mock_logger)

    @pytest.mark.unit
    def test_init_default_values(self):
        """デフォルト値での初期化テスト."""
        manager = QualityTrendManager()
        assert manager.trend_file == Path("quality-trends/trend-data.json")
        assert manager.logger is not None

    @pytest.mark.unit
    def test_load_trend_data_empty_file(self):
        """存在しないファイルからのデータ読み込みテスト."""
        data = self.manager.load_trend_data()
        assert data == []

    @pytest.mark.unit
    def test_load_trend_data_valid_file(self):
        """有効なファイルからのデータ読み込みテスト."""
        # テストデータを作成
        test_data = [
            {
                "timestamp": "2024-01-01T00:00:00Z",
                "commit_hash": "abc123",
                "quality_score": 85.0,
                "coverage": 80.0,
                "ruff_issues": 2,
                "mypy_errors": 1,
                "security_vulnerabilities": 0,
                "test_passed": 100,
                "test_failed": 0,
            }
        ]

        # ファイルに書き込み
        self.trend_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.trend_file, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        # データ読み込み
        data = self.manager.load_trend_data()

        assert len(data) == 1
        assert data[0].timestamp == "2024-01-01T00:00:00Z"
        assert data[0].commit_hash == "abc123"
        assert data[0].quality_score == 85.0

    @pytest.mark.unit
    def test_load_trend_data_invalid_json(self):
        """無効なJSONファイルからの読み込みテスト."""
        # 無効なJSONファイルを作成
        self.trend_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.trend_file, "w", encoding="utf-8") as f:
            f.write("invalid json")

        data = self.manager.load_trend_data()

        assert data == []
        self.mock_logger.error.assert_called_once()

    @pytest.mark.unit
    def test_load_trend_data_invalid_structure(self):
        """無効な構造のJSONファイルからの読み込みテスト."""
        # 無効な構造のJSONファイルを作成
        self.trend_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.trend_file, "w", encoding="utf-8") as f:
            json.dump([{"invalid": "structure"}], f)

        data = self.manager.load_trend_data()

        assert data == []
        self.mock_logger.error.assert_called_once()

    @pytest.mark.unit
    def test_save_trend_data(self):
        """トレンドデータ保存テスト."""
        data_points = [
            TrendDataPoint(
                timestamp="2024-01-01T00:00:00Z",
                commit_hash="abc123",
                quality_score=85.0,
                coverage=80.0,
                ruff_issues=2,
                mypy_errors=1,
                security_vulnerabilities=0,
                test_passed=100,
                test_failed=0,
            )
        ]

        self.manager.save_trend_data(data_points)

        # ファイルが作成されたことを確認
        assert self.trend_file.exists()

        # 内容を確認
        with open(self.trend_file, encoding="utf-8") as f:
            saved_data = json.load(f)

        assert len(saved_data) == 1
        assert saved_data[0]["timestamp"] == "2024-01-01T00:00:00Z"
        assert saved_data[0]["commit_hash"] == "abc123"

        self.mock_logger.info.assert_called_once()

    @pytest.mark.unit
    def test_save_trend_data_error(self):
        """トレンドデータ保存エラーテスト."""
        # 書き込み不可能なパスを設定（ファイル名に無効文字を使用）
        import platform

        if platform.system() == "Windows":
            # Windowsで無効なファイル名文字を使用
            invalid_path = self.temp_dir / "invalid<>file.json"
        else:
            # Unix系で無効なパスを使用
            invalid_path = Path("/invalid/path/trend-data.json")

        manager = QualityTrendManager(trend_file=invalid_path, logger=self.mock_logger)

        data_points = [
            TrendDataPoint(
                timestamp="2024-01-01T00:00:00Z",
                commit_hash="abc123",
                quality_score=85.0,
                coverage=80.0,
                ruff_issues=2,
                mypy_errors=1,
                security_vulnerabilities=0,
                test_passed=100,
                test_failed=0,
            )
        ]

        manager.save_trend_data(data_points)

        # エラーログが呼ばれることを確認
        self.mock_logger.error.assert_called()

    @pytest.mark.unit
    def test_add_data_point_new(self):
        """新しいデータポイント追加テスト."""
        metrics = QualityMetrics(
            timestamp="2024-01-01T00:00:00Z",
            commit_hash="abc123",
            ruff_issues=2,
            mypy_errors=1,
            test_coverage=85.0,
            test_passed=100,
            test_failed=0,
            security_vulnerabilities=0,
        )

        self.manager.add_data_point(metrics)

        # データが保存されたことを確認
        data = self.manager.load_trend_data()
        assert len(data) == 1
        assert data[0].commit_hash == "abc123"

    @pytest.mark.unit
    def test_add_data_point_update_existing(self):
        """既存データポイント更新テスト."""
        # 既存データを作成
        existing_metrics = QualityMetrics(
            timestamp="2024-01-01T00:00:00Z",
            commit_hash="abc123",
            ruff_issues=5,
            mypy_errors=3,
            test_coverage=75.0,
            test_passed=90,
            test_failed=5,
            security_vulnerabilities=1,
        )
        self.manager.add_data_point(existing_metrics)

        # 同じコミットハッシュで更新
        updated_metrics = QualityMetrics(
            timestamp="2024-01-01T01:00:00Z",
            commit_hash="abc123",
            ruff_issues=2,
            mypy_errors=1,
            test_coverage=85.0,
            test_passed=100,
            test_failed=0,
            security_vulnerabilities=0,
        )
        self.manager.add_data_point(updated_metrics)

        # データが更新されたことを確認
        data = self.manager.load_trend_data()
        assert len(data) == 1
        assert data[0].ruff_issues == 2
        assert data[0].coverage == 85.0

    @pytest.mark.unit
    def test_add_data_point_max_points_limit(self):
        """最大データポイント数制限テスト."""
        # 複数のデータポイントを追加
        for i in range(5):
            metrics = QualityMetrics(
                timestamp=f"2024-01-0{i + 1}T00:00:00Z",
                commit_hash=f"commit{i}",
                ruff_issues=i,
                mypy_errors=i,
                test_coverage=80.0 + i,
                test_passed=100,
                test_failed=0,
                security_vulnerabilities=0,
            )
            self.manager.add_data_point(metrics, max_points=3)

        # 最新3件のみ保持されることを確認
        data = self.manager.load_trend_data()
        assert len(data) == 3
        assert data[0].commit_hash == "commit2"
        assert data[-1].commit_hash == "commit4"

    @pytest.mark.unit
    def test_analyze_trend_no_data(self):
        """データなしでのトレンド分析テスト."""
        analysis = self.manager.analyze_trend()

        assert analysis.period_days == 30
        assert analysis.data_points == 0
        assert analysis.quality_score_trend == "stable"
        assert analysis.coverage_trend == "stable"
        assert analysis.average_quality_score == 0.0
        assert analysis.average_coverage == 0.0
        assert analysis.best_quality_score == 0.0
        assert analysis.worst_quality_score == 0.0
        assert analysis.recent_issues == []
        assert len(analysis.recommendations) == 1
        assert "データが不足" in analysis.recommendations[0]

    @pytest.mark.unit
    def test_analyze_trend_with_data(self):
        """データありでのトレンド分析テスト."""
        # テストデータを準備
        now = datetime.now()
        test_data = []
        for i in range(5):
            timestamp = (now - timedelta(days=i)).isoformat() + "Z"
            data_point = TrendDataPoint(
                timestamp=timestamp,
                commit_hash=f"commit{i}",
                quality_score=80.0 + i * 2,
                coverage=75.0 + i * 3,
                ruff_issues=5 - i,
                mypy_errors=3 - i,
                security_vulnerabilities=0,
                test_passed=100,
                test_failed=0,
            )
            test_data.append(data_point)

        # データを保存
        self.manager.save_trend_data(test_data)

        # 分析実行
        analysis = self.manager.analyze_trend(days=10)

        assert analysis.period_days == 10
        assert analysis.data_points == 5
        assert analysis.average_quality_score > 0
        assert analysis.average_coverage > 0
        assert analysis.best_quality_score >= analysis.worst_quality_score

    @pytest.mark.unit
    def test_analyze_trend_direction_improving(self):
        """改善トレンド分析テスト."""
        values = [70.0, 75.0, 80.0, 85.0, 90.0]
        trend = self.manager._analyze_trend_direction(values)
        assert trend == "improving"

    @pytest.mark.unit
    def test_analyze_trend_direction_declining(self):
        """悪化トレンド分析テスト."""
        values = [90.0, 85.0, 80.0, 75.0, 70.0]
        trend = self.manager._analyze_trend_direction(values)
        assert trend == "declining"

    @pytest.mark.unit
    def test_analyze_trend_direction_stable(self):
        """安定トレンド分析テスト."""
        values = [80.0, 81.0, 79.0, 80.5, 80.2]
        trend = self.manager._analyze_trend_direction(values)
        assert trend == "stable"

    @pytest.mark.unit
    def test_analyze_trend_direction_insufficient_data(self):
        """データ不足でのトレンド分析テスト."""
        values = [80.0, 85.0]
        trend = self.manager._analyze_trend_direction(values)
        assert trend == "stable"

    @pytest.mark.unit
    def test_identify_recent_issues_no_issues(self):
        """問題なしでの最近の問題特定テスト."""
        data_points = [
            TrendDataPoint(
                timestamp="2024-01-01T00:00:00Z",
                commit_hash="abc123",
                quality_score=90.0,
                coverage=85.0,
                ruff_issues=0,
                mypy_errors=0,
                security_vulnerabilities=0,
                test_passed=100,
                test_failed=0,
            )
        ]

        issues = self.manager._identify_recent_issues(data_points)
        assert issues == []

    @pytest.mark.unit
    def test_identify_recent_issues_with_problems(self):
        """問題ありでの最近の問題特定テスト."""
        data_points = [
            TrendDataPoint(
                timestamp="2024-01-01T00:00:00Z",
                commit_hash="abc123",
                quality_score=65.0,  # 低い品質スコア
                coverage=75.0,  # 低いカバレッジ
                ruff_issues=5,  # Ruffエラー
                mypy_errors=3,  # MyPyエラー
                security_vulnerabilities=2,  # セキュリティ脆弱性
                test_passed=95,
                test_failed=5,  # テスト失敗
            )
        ]

        issues = self.manager._identify_recent_issues(data_points)

        assert len(issues) == 6
        assert any("品質スコアが低下" in issue for issue in issues)
        assert any("カバレッジが不足" in issue for issue in issues)
        assert any("Ruffエラーが5件" in issue for issue in issues)
        assert any("MyPyエラーが3件" in issue for issue in issues)
        assert any("セキュリティ脆弱性が2件" in issue for issue in issues)
        assert any("テストが5件失敗" in issue for issue in issues)

    @pytest.mark.unit
    def test_identify_recent_issues_empty_data(self):
        """空データでの最近の問題特定テスト."""
        issues = self.manager._identify_recent_issues([])
        assert issues == []

    @pytest.mark.unit
    def test_generate_recommendations_good_quality(self):
        """高品質での推奨事項生成テスト."""
        data_points = [
            TrendDataPoint(
                timestamp="2024-01-01T00:00:00Z",
                commit_hash="abc123",
                quality_score=90.0,
                coverage=85.0,
                ruff_issues=0,
                mypy_errors=0,
                security_vulnerabilities=0,
                test_passed=100,
                test_failed=0,
            )
        ]

        recommendations = self.manager._generate_recommendations(data_points, 90.0, 85.0)

        assert len(recommendations) == 1
        assert "品質基準を維持" in recommendations[0]

    @pytest.mark.unit
    def test_generate_recommendations_low_quality(self):
        """低品質での推奨事項生成テスト."""
        data_points = [
            TrendDataPoint(
                timestamp="2024-01-01T00:00:00Z",
                commit_hash="abc123",
                quality_score=70.0,
                coverage=70.0,
                ruff_issues=5,
                mypy_errors=3,
                security_vulnerabilities=2,
                test_passed=90,
                test_failed=10,
            )
        ]

        recommendations = self.manager._generate_recommendations(data_points, 70.0, 70.0)

        assert len(recommendations) >= 3
        assert any("品質スコアを向上" in rec for rec in recommendations)
        assert any("カバレッジを向上" in rec for rec in recommendations)
        assert any("セキュリティ脆弱性の修正" in rec for rec in recommendations)

    @pytest.mark.unit
    def test_generate_recommendations_declining_trend(self):
        """悪化トレンドでの推奨事項生成テスト."""
        # 悪化トレンドのデータを作成
        data_points = []
        for i in range(5):
            data_point = TrendDataPoint(
                timestamp=f"2024-01-0{i + 1}T00:00:00Z",
                commit_hash=f"commit{i}",
                quality_score=90.0 - i * 5,  # 悪化トレンド
                coverage=85.0,
                ruff_issues=0,
                mypy_errors=0,
                security_vulnerabilities=0,
                test_passed=100,
                test_failed=0,
            )
            data_points.append(data_point)

        recommendations = self.manager._generate_recommendations(data_points, 75.0, 85.0)

        assert any("低下傾向" in rec for rec in recommendations)

    @pytest.mark.unit
    def test_generate_recommendations_empty_data(self):
        """空データでの推奨事項生成テスト."""
        recommendations = self.manager._generate_recommendations([], 0.0, 0.0)
        assert recommendations == []

    @pytest.mark.unit
    def test_generate_html_report(self):
        """HTMLレポート生成テスト."""
        # テストデータを準備
        data_points = [
            TrendDataPoint(
                timestamp="2024-01-01T00:00:00Z",
                commit_hash="abc123",
                quality_score=85.0,
                coverage=80.0,
                ruff_issues=2,
                mypy_errors=1,
                security_vulnerabilities=0,
                test_passed=100,
                test_failed=0,
            )
        ]
        self.manager.save_trend_data(data_points)

        # HTMLレポート生成
        output_file = self.temp_dir / "test-report.html"
        result_file = self.manager.generate_html_report(output_file)

        assert result_file == output_file
        assert output_file.exists()

        # HTMLファイルの内容を確認
        with open(output_file, encoding="utf-8") as f:
            content = f.read()

        assert "品質トレンドレポート" in content
        assert "chart.js" in content.lower()  # Chart.jsライブラリ
        assert "85.0%" in content  # 品質スコア

        self.mock_logger.info.assert_called()

    @pytest.mark.unit
    def test_generate_html_report_default_path(self):
        """デフォルトパスでのHTMLレポート生成テスト."""
        # テストデータを準備
        data_points = [
            TrendDataPoint(
                timestamp="2024-01-01T00:00:00Z",
                commit_hash="abc123",
                quality_score=85.0,
                coverage=80.0,
                ruff_issues=0,
                mypy_errors=0,
                security_vulnerabilities=0,
                test_passed=100,
                test_failed=0,
            )
        ]
        self.manager.save_trend_data(data_points)

        # デフォルトパスでHTMLレポート生成
        result_file = self.manager.generate_html_report()

        expected_path = self.trend_file.parent / "trend-report.html"
        assert result_file == expected_path
        assert expected_path.exists()

    @pytest.mark.unit
    def test_generate_html_content_with_issues(self):
        """問題ありでのHTML内容生成テスト."""
        data_points = [
            TrendDataPoint(
                timestamp="2024-01-01T00:00:00Z",
                commit_hash="abc123",
                quality_score=65.0,
                coverage=70.0,
                ruff_issues=5,
                mypy_errors=3,
                security_vulnerabilities=1,
                test_passed=90,
                test_failed=10,
            )
        ]

        analysis = TrendAnalysis(
            period_days=30,
            data_points=1,
            quality_score_trend="declining",
            coverage_trend="stable",
            average_quality_score=65.0,
            average_coverage=70.0,
            best_quality_score=65.0,
            worst_quality_score=65.0,
            recent_issues=["品質スコアが低下しています", "カバレッジが不足しています"],
            recommendations=["品質向上に取り組んでください"],
        )

        html_content = self.manager._generate_html_content(data_points, analysis)

        assert "品質トレンドレポート" in html_content
        assert "65.0%" in html_content
        assert "品質スコアが低下" in html_content
        assert "品質向上に取り組んで" in html_content
        assert "chart.js" in html_content.lower()

    @pytest.mark.unit
    def test_generate_html_content_no_issues(self):
        """問題なしでのHTML内容生成テスト."""
        data_points = [
            TrendDataPoint(
                timestamp="2024-01-01T00:00:00Z",
                commit_hash="abc123",
                quality_score=90.0,
                coverage=85.0,
                ruff_issues=0,
                mypy_errors=0,
                security_vulnerabilities=0,
                test_passed=100,
                test_failed=0,
            )
        ]

        analysis = TrendAnalysis(
            period_days=30,
            data_points=1,
            quality_score_trend="stable",
            coverage_trend="stable",
            average_quality_score=90.0,
            average_coverage=85.0,
            best_quality_score=90.0,
            worst_quality_score=90.0,
            recent_issues=[],
            recommendations=["品質基準を維持できています"],
        )

        html_content = self.manager._generate_html_content(data_points, analysis)

        assert "品質トレンドレポート" in html_content
        assert "90.0%" in html_content
        assert "品質基準を維持" in html_content
        assert "問題は検出されていません" in html_content or "recent_issues" not in html_content

    @pytest.mark.unit
    def test_analyze_trend_with_recent_data_only(self):
        """最近のデータのみでのトレンド分析テスト."""
        # 古いデータと新しいデータを混在させる
        old_date = datetime.now() - timedelta(days=60)
        recent_date = datetime.now() - timedelta(days=5)

        test_data = [
            TrendDataPoint(
                timestamp=old_date.isoformat() + "Z",
                commit_hash="old_commit",
                quality_score=50.0,
                coverage=40.0,
                ruff_issues=10,
                mypy_errors=5,
                security_vulnerabilities=3,
                test_passed=80,
                test_failed=20,
            ),
            TrendDataPoint(
                timestamp=recent_date.isoformat() + "Z",
                commit_hash="recent_commit",
                quality_score=85.0,
                coverage=80.0,
                ruff_issues=2,
                mypy_errors=1,
                security_vulnerabilities=0,
                test_passed=100,
                test_failed=0,
            ),
        ]

        self.manager.save_trend_data(test_data)

        # 30日間の分析（古いデータは除外される）
        analysis = self.manager.analyze_trend(days=30)

        # 最近のデータのみが使用されることを確認
        assert analysis.data_points == 1
        assert analysis.average_quality_score == 85.0
        assert analysis.average_coverage == 80.0

    @pytest.mark.unit
    def test_analyze_trend_fallback_to_latest_10(self):
        """期間内データなしでの最新10件フォールバックテスト."""
        # 全て古いデータを作成
        old_date = datetime.now() - timedelta(days=100)
        test_data = []
        for i in range(15):
            data_point = TrendDataPoint(
                timestamp=(old_date + timedelta(days=i)).isoformat() + "Z",
                commit_hash=f"commit{i}",
                quality_score=80.0 + i,
                coverage=75.0 + i,
                ruff_issues=0,
                mypy_errors=0,
                security_vulnerabilities=0,
                test_passed=100,
                test_failed=0,
            )
            test_data.append(data_point)

        self.manager.save_trend_data(test_data)

        # 30日間の分析（期間内にデータがないため最新10件を使用）
        analysis = self.manager.analyze_trend(days=30)

        # 最新10件が使用されることを確認
        assert analysis.data_points == 10
        assert analysis.average_quality_score > 80.0
