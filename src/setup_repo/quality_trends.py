"""品質トレンド分析と可視化モジュール

このモジュールは品質メトリクスの履歴データを管理し、
トレンド分析と可視化機能を提供します。
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from .quality_logger import QualityLogger, get_quality_logger
from .quality_metrics import QualityMetrics


@dataclass
class TrendDataPoint:
    """トレンドデータポイント"""

    timestamp: str
    commit_hash: str
    quality_score: float
    coverage: float
    ruff_issues: int
    mypy_errors: int
    security_vulnerabilities: int
    test_passed: int
    test_failed: int

    @classmethod
    def from_metrics(cls, metrics: QualityMetrics) -> "TrendDataPoint":
        """QualityMetricsからTrendDataPointを作成"""
        return cls(
            timestamp=metrics.timestamp,
            commit_hash=metrics.commit_hash,
            quality_score=metrics.get_quality_score(),
            coverage=metrics.test_coverage,
            ruff_issues=metrics.ruff_issues,
            mypy_errors=metrics.mypy_errors,
            security_vulnerabilities=metrics.security_vulnerabilities,
            test_passed=metrics.test_passed,
            test_failed=metrics.test_failed,
        )


@dataclass
class TrendAnalysis:
    """トレンド分析結果"""

    period_days: int
    data_points: int
    quality_score_trend: str  # "improving", "declining", "stable"
    coverage_trend: str
    average_quality_score: float
    average_coverage: float
    best_quality_score: float
    worst_quality_score: float
    recent_issues: list[str]
    recommendations: list[str]


class QualityTrendManager:
    """品質トレンド管理クラス"""

    def __init__(self, trend_file: Optional[Path] = None, logger: Optional[QualityLogger] = None) -> None:
        self.trend_file = trend_file or Path("quality-trends/trend-data.json")
        self.logger = logger or get_quality_logger("setup_repo.quality_trends")

    def load_trend_data(self) -> list[TrendDataPoint]:
        """トレンドデータを読み込み"""
        if not self.trend_file.exists():
            return []

        try:
            with open(self.trend_file, encoding="utf-8") as f:
                data = json.load(f)

            return [TrendDataPoint(**point) for point in data]
        except (json.JSONDecodeError, TypeError, KeyError) as e:
            self.logger.error(f"トレンドデータ読み込みエラー: {e}")
            return []

    def save_trend_data(self, data_points: list[TrendDataPoint]) -> None:
        """トレンドデータを保存"""
        self.trend_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(self.trend_file, "w", encoding="utf-8") as f:
                json.dump(
                    [asdict(point) for point in data_points],
                    f,
                    indent=2,
                    ensure_ascii=False,
                )

            self.logger.info(f"トレンドデータを保存しました: {self.trend_file}")
        except Exception as e:
            self.logger.error(f"トレンドデータ保存エラー: {e}")

    def add_data_point(self, metrics: QualityMetrics, max_points: int = 100) -> None:
        """新しいデータポイントを追加"""
        data_points = self.load_trend_data()
        new_point = TrendDataPoint.from_metrics(metrics)

        # 同じコミットハッシュのデータがある場合は更新
        existing_index = None
        for i, point in enumerate(data_points):
            if point.commit_hash == new_point.commit_hash:
                existing_index = i
                break

        if existing_index is not None:
            data_points[existing_index] = new_point
        else:
            data_points.append(new_point)

        # タイムスタンプでソートし、最新のmax_points件のみ保持
        data_points.sort(key=lambda x: x.timestamp)
        data_points = data_points[-max_points:]

        self.save_trend_data(data_points)

    def analyze_trend(self, days: int = 30) -> TrendAnalysis:
        """トレンド分析を実行"""
        data_points = self.load_trend_data()

        if not data_points:
            return TrendAnalysis(
                period_days=days,
                data_points=0,
                quality_score_trend="stable",
                coverage_trend="stable",
                average_quality_score=0.0,
                average_coverage=0.0,
                best_quality_score=0.0,
                worst_quality_score=0.0,
                recent_issues=[],
                recommendations=["データが不足しています。品質メトリクスの収集を開始してください。"],
            )

        # 指定期間内のデータを抽出
        from datetime import timezone

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        recent_points = [
            point
            for point in data_points
            if datetime.fromisoformat(point.timestamp.replace("Z", "+00:00")) >= cutoff_date
        ]

        if not recent_points:
            recent_points = data_points[-10:]  # 最新10件を使用

        # 基本統計
        quality_scores = [point.quality_score for point in recent_points]
        coverages = [point.coverage for point in recent_points]

        avg_quality = sum(quality_scores) / len(quality_scores)
        avg_coverage = sum(coverages) / len(coverages)
        best_quality = max(quality_scores)
        worst_quality = min(quality_scores)

        # トレンド分析
        quality_trend = self._analyze_trend_direction(quality_scores)
        coverage_trend = self._analyze_trend_direction(coverages)

        # 最近の問題を特定
        recent_issues = self._identify_recent_issues(recent_points)

        # 推奨事項を生成
        recommendations = self._generate_recommendations(recent_points, avg_quality, avg_coverage)

        return TrendAnalysis(
            period_days=days,
            data_points=len(recent_points),
            quality_score_trend=quality_trend,
            coverage_trend=coverage_trend,
            average_quality_score=avg_quality,
            average_coverage=avg_coverage,
            best_quality_score=best_quality,
            worst_quality_score=worst_quality,
            recent_issues=recent_issues,
            recommendations=recommendations,
        )

    def _analyze_trend_direction(self, values: list[float]) -> str:
        """値の傾向を分析"""
        if len(values) < 3:
            return "stable"

        # 線形回帰の傾きを計算
        n = len(values)
        x_values = list(range(n))

        sum_x = sum(x_values)
        sum_y = sum(values)
        sum_xy = sum(x * y for x, y in zip(x_values, values))
        sum_x2 = sum(x * x for x in x_values)

        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)

        if slope > 0.5:
            return "improving"
        elif slope < -0.5:
            return "declining"
        else:
            return "stable"

    def _identify_recent_issues(self, data_points: list[TrendDataPoint]) -> list[str]:
        """最近の問題を特定"""
        issues: list[str] = []

        if not data_points:
            return issues

        latest = data_points[-1]

        if latest.quality_score < 70:
            issues.append(f"品質スコアが低下しています ({latest.quality_score:.1f}%)")

        if latest.coverage < 80:
            issues.append(f"テストカバレッジが不足しています ({latest.coverage:.1f}%)")

        if latest.ruff_issues > 0:
            issues.append(f"Ruffエラーが{latest.ruff_issues}件あります")

        if latest.mypy_errors > 0:
            issues.append(f"MyPyエラーが{latest.mypy_errors}件あります")

        if latest.security_vulnerabilities > 0:
            issues.append(f"セキュリティ脆弱性が{latest.security_vulnerabilities}件あります")

        if latest.test_failed > 0:
            issues.append(f"テストが{latest.test_failed}件失敗しています")

        return issues

    def _generate_recommendations(
        self, data_points: list[TrendDataPoint], avg_quality: float, avg_coverage: float
    ) -> list[str]:
        """推奨事項を生成"""
        recommendations: list[str] = []

        if not data_points:
            return recommendations

        latest = data_points[-1]

        # 品質スコア関連
        if avg_quality < 80:
            recommendations.append(
                "品質スコアを向上させるため、リンティングエラーと型チェックエラーの修正に取り組んでください"
            )

        # カバレッジ関連
        if avg_coverage < 80:
            recommendations.append("テストカバレッジを向上させるため、新しいテストケースの追加を検討してください")

        # セキュリティ関連
        if latest.security_vulnerabilities > 0:
            recommendations.append("セキュリティ脆弱性の修正を優先的に行ってください")

        # トレンド関連
        quality_scores = [point.quality_score for point in data_points]
        if len(quality_scores) >= 3:
            trend = self._analyze_trend_direction(quality_scores)
            if trend == "declining":
                recommendations.append("品質スコアが低下傾向にあります。コードレビューとテストの強化を検討してください")

        # 一般的な推奨事項
        if not recommendations:
            recommendations.append("品質基準を維持できています。継続的な改善を心がけてください")

        return recommendations

    def generate_html_report(self, output_file: Optional[Path] = None) -> Path:
        """HTML形式のトレンドレポートを生成"""
        if output_file is None:
            output_file = self.trend_file.parent / "trend-report.html"

        data_points = self.load_trend_data()
        analysis = self.analyze_trend()

        html_content = self._generate_html_content(data_points, analysis)

        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        self.logger.info(f"HTMLレポートを生成しました: {output_file}")
        return output_file

    def _generate_html_content(self, data_points: list[TrendDataPoint], analysis: TrendAnalysis) -> str:
        """HTML内容を生成"""
        import html

        # データをJavaScript用に変換（HTMLエスケープ済み）
        chart_data = json.dumps([asdict(point) for point in data_points], ensure_ascii=False)

        # 分析結果のHTMLエスケープ
        escaped_issues = [html.escape(issue) for issue in analysis.recent_issues]
        escaped_recommendations = [html.escape(rec) for rec in analysis.recommendations]

        return f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>品質トレンドレポート</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            text-align: center;
            margin-bottom: 30px;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .metric-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            border-left: 4px solid #007bff;
        }}
        .metric-value {{
            font-size: 2em;
            font-weight: bold;
            color: #007bff;
        }}
        .metric-label {{
            color: #666;
            margin-top: 5px;
        }}
        .chart-container {{
            margin: 30px 0;
            height: 400px;
        }}
        .issues-section, .recommendations-section {{
            margin: 30px 0;
        }}
        .issues-section h3, .recommendations-section h3 {{
            color: #333;
            border-bottom: 2px solid #007bff;
            padding-bottom: 10px;
        }}
        .issue-item, .recommendation-item {{
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 5px;
            padding: 10px;
            margin: 10px 0;
        }}
        .recommendation-item {{
            background: #d1ecf1;
            border-color: #bee5eb;
        }}
        .trend-indicator {{
            display: inline-block;
            padding: 5px 10px;
            border-radius: 15px;
            font-size: 0.8em;
            font-weight: bold;
        }}
        .trend-improving {{ background: #d4edda; color: #155724; }}
        .trend-declining {{ background: #f8d7da; color: #721c24; }}
        .trend-stable {{ background: #e2e3e5; color: #383d41; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 品質トレンドレポート</h1>

        <div class="summary">
            <div class="metric-card">
                <div class="metric-value">{analysis.average_quality_score:.1f}%</div>
                <div class="metric-label">平均品質スコア</div>
                <div class="trend-indicator trend-{analysis.quality_score_trend}">
                    {{
                        '向上中' if analysis.quality_score_trend == 'improving'
                        else '低下中' if analysis.quality_score_trend == 'declining'
                        else '安定'
                    }}
                </div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{analysis.average_coverage:.1f}%</div>
                <div class="metric-label">平均カバレッジ</div>
                <div class="trend-indicator trend-{analysis.coverage_trend}">
                    {{
                        '向上中' if analysis.coverage_trend == 'improving'
                        else '低下中' if analysis.coverage_trend == 'declining'
                        else '安定'
                    }}
                </div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{analysis.data_points}</div>
                <div class="metric-label">データポイント数</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{analysis.period_days}</div>
                <div class="metric-label">分析期間（日）</div>
            </div>
        </div>

        <div class="chart-container">
            <canvas id="qualityChart"></canvas>
        </div>

        <div class="chart-container">
            <canvas id="coverageChart"></canvas>
        </div>

        <div class="chart-container">
            <canvas id="issuesChart"></canvas>
        </div>

        {
            f'''
        <div class="issues-section">
            <h3>🚨 最近の問題</h3>
            {
                "".join(f'<div class="issue-item">{issue}</div>' for issue in escaped_issues)
                if escaped_issues
                else "<p>問題は検出されていません。</p>"
            }
        '''
            if analysis.recent_issues
            else ""
        }

        <div class="recommendations-section">
            <h3>💡 推奨事項</h3>
            {"".join(f'<div class="recommendation-item">{rec}</div>' for rec in escaped_recommendations)}
        </div>
    </div>

    <script>
        const data = {chart_data};
        const labels = data.map(d => new Date(d.timestamp).toLocaleDateString('ja-JP'));

        // 品質スコアチャート
        new Chart(document.getElementById('qualityChart'), {{
            type: 'line',
            data: {{
                labels: labels,
                datasets: [{{
                    label: '品質スコア',
                    data: data.map(d => d.quality_score),
                    borderColor: 'rgb(75, 192, 192)',
                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                    tension: 0.1,
                    fill: true
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    title: {{
                        display: true,
                        text: '品質スコアトレンド'
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        max: 100
                    }}
                }}
            }}
        }});

        // カバレッジチャート
        new Chart(document.getElementById('coverageChart'), {{
            type: 'line',
            data: {{
                labels: labels,
                datasets: [{{
                    label: 'テストカバレッジ',
                    data: data.map(d => d.coverage),
                    borderColor: 'rgb(255, 99, 132)',
                    backgroundColor: 'rgba(255, 99, 132, 0.2)',
                    tension: 0.1,
                    fill: true
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    title: {{
                        display: true,
                        text: 'テストカバレッジトレンド'
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        max: 100
                    }}
                }}
            }}
        }});

        // エラー数チャート
        new Chart(document.getElementById('issuesChart'), {{
            type: 'bar',
            data: {{
                labels: labels,
                datasets: [
                    {{
                        label: 'Ruffエラー',
                        data: data.map(d => d.ruff_issues),
                        backgroundColor: 'rgba(255, 206, 86, 0.8)'
                    }},
                    {{
                        label: 'MyPyエラー',
                        data: data.map(d => d.mypy_errors),
                        backgroundColor: 'rgba(54, 162, 235, 0.8)'
                    }},
                    {{
                        label: 'セキュリティ脆弱性',
                        data: data.map(d => d.security_vulnerabilities),
                        backgroundColor: 'rgba(255, 99, 132, 0.8)'
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    title: {{
                        display: true,
                        text: 'エラー数トレンド'
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>"""
