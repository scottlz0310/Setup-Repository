#!/usr/bin/env python3
"""
品質監視システム

このモジュールは、コード品質の継続的監視、トレンド分析、アラート機能を提供します。
月次の責任分離レビューと品質メトリクス監視の仕組みを構築します。
"""

import json
import logging
import statistics
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

try:
    from setup_repo.security_helpers import safe_subprocess
except ImportError:  # pragma: no cover - fallback for direct script execution
    src_path = Path.cwd() / "src"
    if src_path.exists() and str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
    from setup_repo.security_helpers import safe_subprocess


@dataclass
class QualityMetrics:
    """品質メトリクスのデータモデル"""

    timestamp: datetime
    commit_sha: str
    branch: str
    test_coverage: float
    ruff_issues: int
    mypy_errors: int
    pyright_errors: int
    test_passed: int
    test_failed: int
    quality_score: float

    def to_dict(self) -> dict[str, Any]:
        """辞書形式に変換"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "commit_sha": self.commit_sha,
            "branch": self.branch,
            "test_coverage": self.test_coverage,
            "ruff_issues": self.ruff_issues,
            "pyright_errors": self.pyright_errors,
            "mypy_errors": self.mypy_errors,
            "test_passed": self.test_passed,
            "test_failed": self.test_failed,
            "quality_score": self.quality_score,
        }


@dataclass
class QualityThresholds:
    """品質閾値の設定"""

    min_coverage: float = 80.0
    max_ruff_issues: int = 10
    max_pyright_errors: int = 5
    max_mypy_errors: int = 5
    min_quality_score: float = 80.0

    # アラート閾値
    coverage_alert_threshold: float = 75.0
    quality_score_alert_threshold: float = 70.0


@dataclass
class ResponsibilityModule:
    """責任分離モジュールの情報"""

    name: str
    functions: list[str]
    responsibilities: list[str]
    coverage: float
    complexity_score: float
    last_modified: datetime


class QualityMonitor:
    """品質監視システムのメインクラス"""

    def __init__(self, project_root: Path | None = None):
        """
        品質監視システムを初期化

        Args:
            project_root: プロジェクトルートディレクトリ
        """
        self.project_root = project_root or Path.cwd()
        self.metrics_dir = self.project_root / "quality-history"
        self.reports_dir = self.project_root / "quality-reports"
        self.metrics_dir.mkdir(exist_ok=True)
        self.reports_dir.mkdir(exist_ok=True)

        # ログ設定
        self.logger = self._setup_logging()

        # 品質閾値設定
        self.thresholds = QualityThresholds()

    def _setup_logging(self) -> logging.Logger:
        """ログ設定を初期化"""
        logger = logging.getLogger("quality_monitor")
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            # コンソールハンドラー
            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)

            # ファイルハンドラー
            log_file = self.project_root / "logs" / "quality.log"
            log_file.parent.mkdir(exist_ok=True)
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)

        return logger

    def collect_quality_metrics(self) -> QualityMetrics | None:
        """
        現在の品質メトリクスを収集

        Returns:
            品質メトリクス、または収集に失敗した場合はNone
        """
        self.logger.info("品質メトリクスを収集中...")

        try:
            # Git情報を取得（セキュアなコマンド実行）
            commit_result = safe_subprocess(
                ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=self.project_root, timeout=10
            )
            commit_sha = commit_result.stdout.strip()

            branch_result = safe_subprocess(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=10,
            )
            branch = branch_result.stdout.strip()

            # カバレッジデータを収集（セキュアなコマンド実行）
            coverage_result = safe_subprocess(
                [
                    "uv",
                    "run",
                    "pytest",
                    "--cov=src/setup_repo",
                    "--cov-report=json:coverage.json",
                    "--quiet",
                ],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300,
                check=False,
            )

            test_coverage = 0.0
            test_passed = 0
            test_failed = 0

            if coverage_result.returncode == 0:
                try:
                    with open(self.project_root / "coverage.json") as f:
                        cov_data = json.load(f)
                    test_coverage = cov_data["totals"]["percent_covered"]
                except Exception as e:
                    self.logger.warning(f"カバレッジデータの解析に失敗: {e}")

            # テスト結果を収集（セキュアなコマンド実行）
            test_result = safe_subprocess(
                [
                    "uv",
                    "run",
                    "pytest",
                    "--json-report",
                    "--json-report-file=test-report.json",
                    "--quiet",
                ],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300,
                check=False,
            )

            if test_result.returncode in [0, 1]:  # 0=成功, 1=テスト失敗
                try:
                    with open(self.project_root / "test-report.json") as f:
                        test_data = json.load(f)
                    summary = test_data.get("summary", {})
                    test_passed = summary.get("passed", 0)
                    test_failed = summary.get("failed", 0)
                except Exception as e:
                    self.logger.warning(f"テストレポートの解析に失敗: {e}")

            # Ruff問題を収集（セキュアなコマンド実行）
            ruff_result = safe_subprocess(
                ["uv", "run", "ruff", "check", ".", "--output-format=json"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )

            ruff_issues = 0
            if ruff_result.stdout:
                try:
                    ruff_data = json.loads(ruff_result.stdout)
                    ruff_issues = len(ruff_data)
                except Exception as e:
                    self.logger.warning(f"Ruffレポートの解析に失敗: {e}")

            # Pyright / BasedPyright 型チェックを実行してエラー数を収集
            pyright_errors = 0
            try:
                # Try basedpyright then pyright as fallback
                result = None
                for cmd in [["uv", "run", "basedpyright", "src/"], ["uv", "run", "pyright", "src/"]]:
                    try:
                        result = safe_subprocess(
                            cmd, cwd=self.project_root, capture_output=True, text=True, timeout=120, check=False
                        )
                        break
                    except Exception:
                        result = None
                        continue

                if result and result.stdout:
                    pyright_errors = len(
                        [line for line in result.stdout.split("\n") if line.strip() and "error" in line.lower()]
                    )
                elif result and result.returncode != 0 and result.stderr:
                    pyright_errors = len(
                        [line for line in result.stderr.split("\n") if line.strip() and "error" in line.lower()]
                    )
            except Exception as e:
                self.logger.warning(f"BasedPyright/pyright レポートの解析に失敗: {e}")

            # 品質スコアを計算
            # Use pyright_errors for scoring, keep mypy_errors as compatibility alias
            quality_score = self._calculate_quality_score(test_coverage, ruff_issues, pyright_errors, test_failed)

            metrics = QualityMetrics(
                timestamp=datetime.now(),
                commit_sha=commit_sha,
                branch=branch,
                test_coverage=test_coverage,
                ruff_issues=ruff_issues,
                mypy_errors=pyright_errors,
                pyright_errors=pyright_errors,
                test_passed=test_passed,
                test_failed=test_failed,
                quality_score=quality_score,
            )

            # メトリクスを保存
            self._save_metrics(metrics)

            return metrics

        except Exception as e:
            self.logger.error(f"品質メトリクスの収集中にエラーが発生しました: {e}")
            return None

    def _calculate_quality_score(
        self, coverage: float, ruff_issues: int, pyright_errors: int, test_failed: int
    ) -> float:
        """
        品質スコアを計算

        Args:
            coverage: テストカバレッジ
            ruff_issues: Ruff問題数
            pyright_errors: Pyrightエラー数
            test_failed: テスト失敗数

        Returns:
            品質スコア (0-100)
        """
        score = 100.0

        # カバレッジによる減点
        if coverage < 80:
            score -= (80 - coverage) * 2

        # Ruff問題による減点
        score -= ruff_issues * 0.5

        # MyPyエラーによる減点
        score -= pyright_errors * 1.0

        # テスト失敗による減点
        score -= test_failed * 5.0

        return max(0.0, score)

    def _save_metrics(self, metrics: QualityMetrics) -> None:
        """メトリクスをファイルに保存"""
        timestamp_str = metrics.timestamp.strftime("%Y%m%d_%H%M%S")
        filename = f"metrics_{timestamp_str}.json"
        filepath = self.metrics_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(metrics.to_dict(), f, indent=2, ensure_ascii=False)

        # 最新のメトリクスファイルも更新
        latest_path = self.metrics_dir / "latest-metrics.json"
        with open(latest_path, "w", encoding="utf-8") as f:
            json.dump(metrics.to_dict(), f, indent=2, ensure_ascii=False)

    def get_historical_metrics(self, days: int = 30) -> list[QualityMetrics]:
        """
        過去の品質メトリクスを取得

        Args:
            days: 取得する日数

        Returns:
            過去の品質メトリクスのリスト
        """
        historical_data = []
        cutoff_time = datetime.now() - timedelta(days=days)

        # メトリクスファイルを日付順でソート
        metric_files = sorted(
            self.metrics_dir.glob("metrics_*.json"),
            key=lambda x: x.stat().st_mtime,
            reverse=True,
        )

        for metric_file in metric_files:
            if datetime.fromtimestamp(metric_file.stat().st_mtime) < cutoff_time:
                break

            try:
                with open(metric_file, encoding="utf-8") as f:
                    data = json.load(f)

                # Backward compatibility: prefer 'pyright_errors' key if present, otherwise use 'mypy_errors'
                mypy_val = data.get("mypy_errors", 0)
                pyright_val = data.get("pyright_errors", mypy_val)
                metrics = QualityMetrics(
                    timestamp=datetime.fromisoformat(data["timestamp"]),
                    commit_sha=data["commit_sha"],
                    branch=data["branch"],
                    test_coverage=data["test_coverage"],
                    ruff_issues=data["ruff_issues"],
                    mypy_errors=mypy_val,
                    pyright_errors=pyright_val,
                    test_passed=data["test_passed"],
                    test_failed=data["test_failed"],
                    quality_score=data["quality_score"],
                )
                historical_data.append(metrics)

            except Exception as e:
                self.logger.warning(f"メトリクスファイルの読み込みに失敗: {metric_file} - {e}")

        return historical_data

    def compare_with_baseline(self, metrics: QualityMetrics) -> dict[str, Any]:
        """
        ベースラインとの比較

        Args:
            metrics: 現在のメトリクス

        Returns:
            比較結果
        """
        historical_data = self.get_historical_metrics(30)

        if len(historical_data) < 2:
            return {"error": "比較には最低2つのデータポイントが必要です"}

        # 過去30日間の平均を計算
        coverages = [m.test_coverage for m in historical_data[1:]]  # 現在を除く
        ruff_issues = [m.ruff_issues for m in historical_data[1:]]
        pyright_errors = [getattr(m, "pyright_errors", m.mypy_errors) for m in historical_data[1:]]
        quality_scores = [m.quality_score for m in historical_data[1:]]

        baseline = {
            "coverage_avg": statistics.mean(coverages) if coverages else 0,
            "ruff_issues_avg": statistics.mean(ruff_issues) if ruff_issues else 0,
            "pyright_errors_avg": statistics.mean(pyright_errors) if pyright_errors else 0,
            "quality_score_avg": statistics.mean(quality_scores) if quality_scores else 0,
        }

        comparison = {
            "coverage_diff": metrics.test_coverage - baseline["coverage_avg"],
            "ruff_issues_diff": metrics.ruff_issues - baseline["ruff_issues_avg"],
            "pyright_errors_diff": getattr(metrics, "pyright_errors", metrics.mypy_errors)
            - baseline.get("pyright_errors_avg", baseline.get("mypy_errors_avg", 0)),
            "quality_score_diff": metrics.quality_score - baseline["quality_score_avg"],
            "baseline": baseline,
            "current": metrics.to_dict(),
        }

        return comparison

    def generate_quality_trend_report(self) -> dict[str, Any]:
        """
        品質トレンドレポートを生成

        Returns:
            トレンドレポート
        """
        self.logger.info("品質トレンドレポートを生成中...")

        historical_data = self.get_historical_metrics(90)  # 90日間

        if len(historical_data) < 7:
            return {"error": "トレンド分析には最低7つのデータポイントが必要です"}

        # 週次トレンドを計算
        weekly_trends = self._calculate_weekly_trends(historical_data)

        # 月次サマリーを計算
        monthly_summary = self._calculate_monthly_summary(historical_data)

        # 品質改善提案を生成
        improvement_suggestions = self._generate_improvement_suggestions(historical_data)

        report = {
            "generated_at": datetime.now().isoformat(),
            "data_points": len(historical_data),
            "period_days": 90,
            "weekly_trends": weekly_trends,
            "monthly_summary": monthly_summary,
            "improvement_suggestions": improvement_suggestions,
        }

        # レポートファイルを保存
        report_file = self.reports_dir / f"quality_trend_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        self.logger.info(f"品質トレンドレポートを保存しました: {report_file}")

        return report

    def _calculate_weekly_trends(self, historical_data: list[QualityMetrics]) -> dict[str, Any]:
        """週次トレンドを計算"""
        if len(historical_data) < 14:
            return {"error": "週次トレンド計算には最低14日分のデータが必要です"}

        # 最新の7日間と前の7日間を比較
        recent_week = historical_data[:7]
        previous_week = historical_data[7:14]

        recent_avg = {
            "coverage": statistics.mean([m.test_coverage for m in recent_week]),
            "ruff_issues": statistics.mean([m.ruff_issues for m in recent_week]),
            "pyright_errors": statistics.mean([getattr(m, "pyright_errors", m.mypy_errors) for m in recent_week]),
            "quality_score": statistics.mean([m.quality_score for m in recent_week]),
        }

        previous_avg = {
            "coverage": statistics.mean([m.test_coverage for m in previous_week]),
            "ruff_issues": statistics.mean([m.ruff_issues for m in previous_week]),
            "pyright_errors": statistics.mean([getattr(m, "pyright_errors", m.mypy_errors) for m in previous_week]),
            "quality_score": statistics.mean([m.quality_score for m in previous_week]),
        }

        trends = {
            "coverage_trend": recent_avg["coverage"] - previous_avg["coverage"],
            "ruff_issues_trend": recent_avg["ruff_issues"] - previous_avg["ruff_issues"],
            "pyright_errors_trend": recent_avg.get("pyright_errors", recent_avg.get("mypy_errors"))
            - previous_avg.get("pyright_errors", previous_avg.get("mypy_errors")),
            "quality_score_trend": recent_avg["quality_score"] - previous_avg["quality_score"],
            "recent_week": recent_avg,
            "previous_week": previous_avg,
        }

        return trends

    def _calculate_monthly_summary(self, historical_data: list[QualityMetrics]) -> dict[str, Any]:
        """月次サマリーを計算"""
        if not historical_data:
            return {"error": "データが不足しています"}

        # 最新30日間のデータを使用
        monthly_data = historical_data[:30] if len(historical_data) >= 30 else historical_data

        summary = {
            "period_days": len(monthly_data),
            "coverage": {
                "avg": statistics.mean([m.test_coverage for m in monthly_data]),
                "min": min([m.test_coverage for m in monthly_data]),
                "max": max([m.test_coverage for m in monthly_data]),
                "std": statistics.stdev([m.test_coverage for m in monthly_data]) if len(monthly_data) > 1 else 0,
            },
            "ruff_issues": {
                "avg": statistics.mean([m.ruff_issues for m in monthly_data]),
                "min": min([m.ruff_issues for m in monthly_data]),
                "max": max([m.ruff_issues for m in monthly_data]),
            },
            "pyright_errors": {
                "avg": statistics.mean([getattr(m, "pyright_errors", m.mypy_errors) for m in monthly_data]),
                "min": min([getattr(m, "pyright_errors", m.mypy_errors) for m in monthly_data]),
                "max": max([getattr(m, "pyright_errors", m.mypy_errors) for m in monthly_data]),
            },
            "quality_score": {
                "avg": statistics.mean([m.quality_score for m in monthly_data]),
                "min": min([m.quality_score for m in monthly_data]),
                "max": max([m.quality_score for m in monthly_data]),
                "std": statistics.stdev([m.quality_score for m in monthly_data]) if len(monthly_data) > 1 else 0,
            },
        }

        return summary

    def _generate_improvement_suggestions(self, historical_data: list[QualityMetrics]) -> list[str]:
        """品質改善提案を生成"""
        suggestions = []

        if not historical_data:
            return suggestions

        latest = historical_data[0]

        # カバレッジ改善提案
        if latest.test_coverage < self.thresholds.min_coverage:
            suggestions.append(
                f"テストカバレッジが目標値を下回っています "
                f"({latest.test_coverage:.2f}% < {self.thresholds.min_coverage}%)。"
                "低カバレッジモジュールのテスト追加を検討してください。"
            )

        # Ruff問題改善提案
        if latest.ruff_issues > self.thresholds.max_ruff_issues:
            suggestions.append(
                f"Ruff問題が多すぎます "
                f"({latest.ruff_issues} > {self.thresholds.max_ruff_issues})。"
                "コードスタイルの統一とリファクタリングを検討してください。"
            )

        # Pyrightエラー改善提案（互換性のため mypy_errors も考慮）
        pyright_count_latest = getattr(latest, "pyright_errors", latest.mypy_errors)
        pyright_threshold = getattr(self.thresholds, "max_pyright_errors", self.thresholds.max_mypy_errors)
        if pyright_count_latest > pyright_threshold:
            suggestions.append(
                f"Pyrightエラーが多すぎます "
                f"({pyright_count_latest} > {pyright_threshold})。"
                "型ヒントの追加と型安全性の向上を検討してください。"
            )

        # 品質スコア改善提案
        if latest.quality_score < self.thresholds.min_quality_score:
            suggestions.append(
                f"品質スコアが目標値を下回っています "
                f"({latest.quality_score:.1f} < {self.thresholds.min_quality_score})。"
                "包括的な品質改善計画の実施を検討してください。"
            )

        # トレンド分析による提案
        if len(historical_data) >= 7:
            recent_scores = [m.quality_score for m in historical_data[:7]]
            if len(recent_scores) > 1:
                trend = recent_scores[0] - recent_scores[-1]
                if trend < -5:
                    suggestions.append("品質スコアが低下傾向にあります。継続的な品質監視と改善活動を強化してください。")

        return suggestions

    def check_quality_gates(self) -> tuple[bool, list[str]]:
        """
        品質ゲートをチェック

        Returns:
            (品質ゲートを通過したか, 警告メッセージのリスト)
        """
        metrics = self.collect_quality_metrics()
        if not metrics:
            return False, ["品質メトリクスの収集に失敗しました"]

        warnings = []
        passed = True

        # カバレッジチェック
        if metrics.test_coverage < self.thresholds.min_coverage:
            warnings.append(
                f"カバレッジが目標値を下回っています: {metrics.test_coverage:.2f}% < {self.thresholds.min_coverage}%"
            )
            passed = False

        # テスト失敗チェック
        if metrics.test_failed > 0:
            warnings.append(f"テストが失敗しています: {metrics.test_failed}件")
            passed = False

        # 品質スコアチェック
        if metrics.quality_score < self.thresholds.min_quality_score:
            warnings.append(
                f"品質スコアが目標値を下回っています: {metrics.quality_score:.1f} < {self.thresholds.min_quality_score}"
            )
            passed = False

        # 警告レベルのチェック
        if metrics.ruff_issues > self.thresholds.max_ruff_issues:
            warnings.append(f"Ruff問題が多すぎます: {metrics.ruff_issues}件")

        pyright_count_metrics = getattr(metrics, "pyright_errors", metrics.mypy_errors)
        if pyright_count_metrics > getattr(self.thresholds, "max_pyright_errors", self.thresholds.max_mypy_errors):
            warnings.append(f"Pyrightエラーが多すぎます: {pyright_count_metrics}件")

        return passed, warnings

    def send_quality_alert(self, metrics: QualityMetrics, warnings: list[str]) -> None:
        """
        品質アラートを送信

        Args:
            metrics: 品質メトリクス
            warnings: 警告メッセージのリスト
        """
        self.logger.warning(f"品質アラート: 品質スコア {metrics.quality_score:.1f}")

        for warning in warnings:
            self.logger.warning(f"  - {warning}")

        # アラートファイルを作成（CI/CDで検出可能）
        alert_file = self.project_root / "quality_alert.txt"
        with open(alert_file, "w", encoding="utf-8") as f:
            f.write(f"品質アラート - {datetime.now().isoformat()}\n")
            f.write(f"品質スコア: {metrics.quality_score:.1f}\n")
            f.write(f"カバレッジ: {metrics.test_coverage:.2f}%\n")
            f.write("警告:\n")
            for warning in warnings:
                f.write(f"  - {warning}\n")

    def analyze_responsibility_separation(self) -> dict[str, Any]:
        """
        責任分離の分析

        Returns:
            責任分離分析結果
        """
        self.logger.info("責任分離分析を実行中...")

        src_dir = self.project_root / "src" / "setup_repo"
        modules = []

        for py_file in src_dir.glob("*.py"):
            if py_file.name == "__init__.py":
                continue

            try:
                # ファイルの関数数を数える
                with open(py_file, encoding="utf-8") as f:
                    content = f.read()

                # 簡単な関数カウント（def で始まる行）
                function_count = len([line for line in content.split("\n") if line.strip().startswith("def ")])

                # ファイルサイズ
                file_size = len(content.split("\n"))

                # 最終更新日時
                last_modified = datetime.fromtimestamp(py_file.stat().st_mtime)

                modules.append(
                    {
                        "name": py_file.stem,
                        "function_count": function_count,
                        "file_size": file_size,
                        "last_modified": last_modified.isoformat(),
                        "complexity_score": min(100, max(0, 100 - (function_count * 5) - (file_size / 10))),
                    }
                )

            except Exception as e:
                self.logger.warning(f"モジュール分析に失敗: {py_file} - {e}")

        # 責任分離の評価
        large_modules = [m for m in modules if m["function_count"] > 8]
        complex_modules = [m for m in modules if m["complexity_score"] < 70]

        analysis = {
            "analyzed_at": datetime.now().isoformat(),
            "total_modules": len(modules),
            "large_modules": len(large_modules),
            "complex_modules": len(complex_modules),
            "modules": modules,
            "recommendations": [],
        }

        # 推奨事項を生成
        if large_modules:
            analysis["recommendations"].append(
                f"{len(large_modules)}個のモジュールが8関数を超えています。分割を検討してください。"
            )

        if complex_modules:
            analysis["recommendations"].append(
                f"{len(complex_modules)}個のモジュールが複雑すぎます。リファクタリングを検討してください。"
            )

        return analysis


def main():
    """メイン実行関数"""
    import argparse

    parser = argparse.ArgumentParser(description="品質監視システム")
    parser.add_argument("--collect-metrics", action="store_true", help="品質メトリクスを収集")
    parser.add_argument("--check-gates", action="store_true", help="品質ゲートをチェック")
    parser.add_argument("--generate-trend-report", action="store_true", help="トレンドレポートを生成")
    parser.add_argument("--analyze-responsibility", action="store_true", help="責任分離を分析")
    parser.add_argument("--project-root", type=Path, help="プロジェクトルートディレクトリ")

    args = parser.parse_args()

    monitor = QualityMonitor(args.project_root)

    if args.collect_metrics:
        metrics = monitor.collect_quality_metrics()
        if metrics:
            print("品質メトリクスを収集しました:")
            print(f"  カバレッジ: {metrics.test_coverage:.2f}%")
            print(f"  品質スコア: {metrics.quality_score:.1f}")
            print(f"  Ruff問題: {metrics.ruff_issues}件")
            print(f"  Pyrightエラー: {metrics.pyright_errors}件")
            print(f"  MyPyエラー (互換): {metrics.mypy_errors}件")
        else:
            print("品質メトリクスの収集に失敗しました")
            sys.exit(1)

    elif args.check_gates:
        passed, warnings = monitor.check_quality_gates()
        if passed:
            print("✅ 品質ゲートを通過しました")
        else:
            print("❌ 品質ゲートを通過できませんでした:")
            for warning in warnings:
                print(f"  - {warning}")
            sys.exit(1)

    elif args.generate_trend_report:
        report = monitor.generate_quality_trend_report()
        if "error" in report:
            print(f"エラー: {report['error']}")
        else:
            print("品質トレンドレポートを生成しました:")
            print(f"  データポイント: {report['data_points']}")
            print(f"  期間: {report['period_days']}日")
            if report.get("improvement_suggestions"):
                print("  改善提案:")
                for suggestion in report["improvement_suggestions"]:
                    print(f"    - {suggestion}")

    elif args.analyze_responsibility:
        analysis = monitor.analyze_responsibility_separation()
        print("責任分離分析結果:")
        print(f"  総モジュール数: {analysis['total_modules']}")
        print(f"  大きなモジュール: {analysis['large_modules']}")
        print(f"  複雑なモジュール: {analysis['complex_modules']}")
        if analysis["recommendations"]:
            print("  推奨事項:")
            for rec in analysis["recommendations"]:
                print(f"    - {rec}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
