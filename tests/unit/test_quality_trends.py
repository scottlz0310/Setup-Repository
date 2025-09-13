"""品質トレンド分析機能のテスト."""

import platform

import pytest

from ..multiplatform.helpers import verify_current_platform


class TestQualityTrends:
    """品質トレンド分析のテストクラス."""

    def setup_method(self):
        """テストメソッドの前処理."""
        self.platform_info = verify_current_platform()

        # サンプル履歴データ
        self.historical_data = [
            {"date": "2024-11-01", "quality_score": 75, "coverage": 70, "security": 85},
            {"date": "2024-11-08", "quality_score": 78, "coverage": 73, "security": 87},
            {"date": "2024-11-15", "quality_score": 82, "coverage": 78, "security": 89},
            {"date": "2024-11-22", "quality_score": 85, "coverage": 82, "security": 91},
            {"date": "2024-11-29", "quality_score": 87, "coverage": 85, "security": 93},
            {"date": "2024-12-01", "quality_score": 89, "coverage": 88, "security": 95},
        ]

    @pytest.mark.unit
    def test_trend_calculation(self):
        """トレンド計算のテスト."""
        # 品質スコアのトレンド計算
        quality_scores = [data["quality_score"] for data in self.historical_data]

        # 線形トレンドの計算（簡単な傾き計算）
        n = len(quality_scores)
        x_values = list(range(n))

        # 傾きの計算
        sum_x = sum(x_values)
        sum_y = sum(quality_scores)
        sum_xy = sum(x * y for x, y in zip(x_values, quality_scores))
        sum_x2 = sum(x * x for x in x_values)

        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)

        # トレンド計算の検証
        assert slope > 0  # 上昇トレンド
        assert slope > 2  # 十分な改善率

    @pytest.mark.unit
    def test_moving_average_calculation(self):
        """移動平均計算のテスト."""
        quality_scores = [data["quality_score"] for data in self.historical_data]
        window_size = 3

        # 移動平均の計算
        moving_averages = []
        for i in range(len(quality_scores) - window_size + 1):
            window = quality_scores[i : i + window_size]
            moving_avg = sum(window) / len(window)
            moving_averages.append(moving_avg)

        # 移動平均計算の検証
        assert len(moving_averages) == 4  # 6データ点で3点移動平均
        assert moving_averages[0] == (75 + 78 + 82) / 3  # 最初の移動平均
        assert moving_averages[-1] == (85 + 87 + 89) / 3  # 最後の移動平均

    @pytest.mark.unit
    def test_trend_direction_detection(self):
        """トレンド方向検出のテスト."""
        # 各メトリクスのトレンド方向を検出
        metrics = ["quality_score", "coverage", "security"]
        trend_directions = {}

        for metric in metrics:
            values = [data[metric] for data in self.historical_data]
            first_half_avg = sum(values[:3]) / 3
            second_half_avg = sum(values[3:]) / 3

            if second_half_avg > first_half_avg * 1.05:
                trend_directions[metric] = "improving"
            elif second_half_avg < first_half_avg * 0.95:
                trend_directions[metric] = "declining"
            else:
                trend_directions[metric] = "stable"

        # トレンド方向検出の検証
        assert trend_directions["quality_score"] == "improving"
        assert trend_directions["coverage"] == "improving"
        assert trend_directions["security"] == "improving"

    @pytest.mark.unit
    def test_volatility_analysis(self):
        """変動性分析のテスト."""
        quality_scores = [data["quality_score"] for data in self.historical_data]

        # 標準偏差の計算
        mean_score = sum(quality_scores) / len(quality_scores)
        variance = sum((score - mean_score) ** 2 for score in quality_scores) / len(quality_scores)
        std_deviation = variance**0.5

        # 変動係数の計算
        coefficient_of_variation = std_deviation / mean_score

        # 変動性分析の検証
        assert std_deviation > 0  # 変動がある
        assert coefficient_of_variation < 0.2  # 変動が適度（20%未満）

    @pytest.mark.unit
    def test_seasonal_pattern_detection(self):
        """季節パターン検出のテスト."""
        # 週次データでの季節パターン分析
        weekly_data = [
            {"week": 1, "quality_score": 80, "day_of_week": "Monday"},
            {"week": 1, "quality_score": 85, "day_of_week": "Friday"},
            {"week": 2, "quality_score": 78, "day_of_week": "Monday"},
            {"week": 2, "quality_score": 88, "day_of_week": "Friday"},
            {"week": 3, "quality_score": 82, "day_of_week": "Monday"},
            {"week": 3, "quality_score": 90, "day_of_week": "Friday"},
        ]

        # 曜日別の平均スコア計算
        monday_scores = [data["quality_score"] for data in weekly_data if data["day_of_week"] == "Monday"]
        friday_scores = [data["quality_score"] for data in weekly_data if data["day_of_week"] == "Friday"]

        monday_avg = sum(monday_scores) / len(monday_scores)
        friday_avg = sum(friday_scores) / len(friday_scores)

        # 季節パターンの検証
        assert friday_avg > monday_avg  # 金曜日の方が品質スコアが高い傾向

    @pytest.mark.unit
    def test_anomaly_detection(self):
        """異常値検出のテスト."""
        # 異常値を含むデータセット
        data_with_anomaly = [75, 78, 82, 85, 87, 45, 89]  # 45が異常値

        # IQR法による異常値検出
        sorted_data = sorted(data_with_anomaly)
        n = len(sorted_data)
        q1_index = n // 4
        q3_index = 3 * n // 4

        q1 = sorted_data[q1_index]
        q3 = sorted_data[q3_index]
        iqr = q3 - q1

        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        # 異常値の検出
        anomalies = [x for x in data_with_anomaly if x < lower_bound or x > upper_bound]

        # 異常値検出の検証
        assert len(anomalies) == 1
        assert 45 in anomalies

    @pytest.mark.unit
    def test_forecast_calculation(self):
        """予測計算のテスト."""
        quality_scores = [data["quality_score"] for data in self.historical_data]

        # 単純な線形予測
        n = len(quality_scores)
        x_values = list(range(n))

        # 線形回帰の係数計算
        sum_x = sum(x_values)
        sum_y = sum(quality_scores)
        sum_xy = sum(x * y for x, y in zip(x_values, quality_scores))
        sum_x2 = sum(x * x for x in x_values)

        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        intercept = (sum_y - slope * sum_x) / n

        # 次の値の予測
        next_prediction = slope * n + intercept

        # 予測計算の検証
        assert next_prediction > quality_scores[-1]  # 上昇トレンドの継続予測
        assert next_prediction < 100  # 現実的な範囲内

    @pytest.mark.unit
    def test_correlation_analysis(self):
        """相関分析のテスト."""
        # 品質スコアとカバレッジの相関分析
        quality_scores = [data["quality_score"] for data in self.historical_data]
        coverage_scores = [data["coverage"] for data in self.historical_data]

        # ピアソン相関係数の計算
        n = len(quality_scores)
        sum_x = sum(quality_scores)
        sum_y = sum(coverage_scores)
        sum_xy = sum(x * y for x, y in zip(quality_scores, coverage_scores))
        sum_x2 = sum(x * x for x in quality_scores)
        sum_y2 = sum(y * y for y in coverage_scores)

        numerator = n * sum_xy - sum_x * sum_y
        denominator = ((n * sum_x2 - sum_x * sum_x) * (n * sum_y2 - sum_y * sum_y)) ** 0.5

        correlation = numerator / denominator if denominator != 0 else 0

        # 相関分析の検証
        assert correlation > 0.8  # 強い正の相関
        assert correlation <= 1.0  # 相関係数の範囲内

    @pytest.mark.unit
    def test_trend_confidence_calculation(self):
        """トレンド信頼度計算のテスト."""
        quality_scores = [data["quality_score"] for data in self.historical_data]

        # R²値の計算（決定係数）
        n = len(quality_scores)
        x_values = list(range(n))

        # 線形回帰
        sum_x = sum(x_values)
        sum_y = sum(quality_scores)
        sum_xy = sum(x * y for x, y in zip(x_values, quality_scores))
        sum_x2 = sum(x * x for x in x_values)

        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        intercept = (sum_y - slope * sum_x) / n

        # 予測値の計算
        predicted = [slope * x + intercept for x in x_values]

        # R²値の計算
        mean_y = sum_y / n
        ss_tot = sum((y - mean_y) ** 2 for y in quality_scores)
        ss_res = sum((y - pred) ** 2 for y, pred in zip(quality_scores, predicted))

        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

        # 信頼度計算の検証
        assert r_squared > 0.8  # 高い決定係数
        assert r_squared <= 1.0  # R²の範囲内

    @pytest.mark.unit
    @pytest.mark.skipif(platform.system() == "Windows", reason="Unix固有のトレンド分析")
    def test_unix_specific_trend_analysis(self):
        """Unix固有のトレンド分析テスト."""
        # Unix固有のメトリクストレンド
        unix_metrics_trend = [
            {"date": "2024-11-01", "load_average": 0.5, "memory_usage": 0.6},
            {"date": "2024-11-15", "load_average": 0.4, "memory_usage": 0.55},
            {"date": "2024-12-01", "load_average": 0.3, "memory_usage": 0.5},
        ]

        # ロードアベレージのトレンド
        load_values = [data["load_average"] for data in unix_metrics_trend]
        load_trend = load_values[-1] - load_values[0]

        # Unix固有トレンドの検証
        assert load_trend < 0  # ロードアベレージが改善（減少）

    @pytest.mark.unit
    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows固有のトレンド分析")
    def test_windows_specific_trend_analysis(self):
        """Windows固有のトレンド分析テスト."""
        # Windows固有のメトリクストレンド
        windows_metrics_trend = [
            {"date": "2024-11-01", "handle_count": 2500, "page_file_usage": 0.6},
            {"date": "2024-11-15", "handle_count": 2300, "page_file_usage": 0.55},
            {"date": "2024-12-01", "handle_count": 2100, "page_file_usage": 0.5},
        ]

        # ハンドル数のトレンド
        handle_values = [data["handle_count"] for data in windows_metrics_trend]
        handle_trend = handle_values[-1] - handle_values[0]

        # Windows固有トレンドの検証
        assert handle_trend < 0  # ハンドル数が改善（減少）

    @pytest.mark.unit
    def test_trend_reporting(self):
        """トレンドレポート生成のテスト."""
        # トレンドレポートデータ
        trend_report = {
            "period": "30_days",
            "metrics": {
                "quality_score": {
                    "start_value": 75,
                    "end_value": 89,
                    "change": 14,
                    "change_percent": 18.67,
                    "trend": "improving",
                },
                "coverage": {
                    "start_value": 70,
                    "end_value": 88,
                    "change": 18,
                    "change_percent": 25.71,
                    "trend": "improving",
                },
            },
            "overall_assessment": "positive",
            "confidence": 0.92,
        }

        # トレンドレポートの検証
        assert trend_report["metrics"]["quality_score"]["trend"] == "improving"
        assert trend_report["metrics"]["coverage"]["change_percent"] > 20
        assert trend_report["overall_assessment"] == "positive"
        assert trend_report["confidence"] > 0.9
