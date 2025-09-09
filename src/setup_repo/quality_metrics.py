"""品質メトリクス収集と管理モジュール

このモジュールは以下の品質メトリクスを収集・管理します：
- Ruffリンティングエラー
- MyPy型チェックエラー
- テストカバレッジ
- セキュリティ脆弱性
- テスト結果
"""

import json
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .quality_logger import (
    CoverageError,
    MyPyError,
    QualityLogger,
    RuffError,
    SecurityScanError,
    TestFailureError,
    get_quality_logger,
)


class QualityCheckStatus(Enum):
    """品質チェックのステータス"""

    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


@dataclass
class QualityMetrics:
    """品質メトリクスを管理するデータモデル"""

    ruff_issues: int = 0
    mypy_errors: int = 0
    test_coverage: float = 0.0
    test_passed: int = 0
    test_failed: int = 0
    security_vulnerabilities: int = 0
    timestamp: str = ""
    commit_hash: str = ""

    def __post_init__(self) -> None:
        """初期化後の処理"""
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
        if not self.commit_hash:
            self.commit_hash = self._get_current_commit_hash()

    def _get_current_commit_hash(self) -> str:
        """現在のコミットハッシュを取得"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
            )
            return result.stdout.strip()[:8]  # 短縮ハッシュ
        except (subprocess.CalledProcessError, FileNotFoundError):
            return "unknown"

    def is_passing(self, min_coverage: float = 80.0) -> bool:
        """品質基準を満たしているかチェック"""
        return (
            self.ruff_issues == 0
            and self.mypy_errors == 0
            and self.test_coverage >= min_coverage
            and self.test_failed == 0
            and self.security_vulnerabilities == 0
        )

    def get_quality_score(self) -> float:
        """品質スコアを計算（0-100）"""
        score = 100.0

        # リンティングエラーによる減点
        score -= min(self.ruff_issues * 2, 20)

        # 型チェックエラーによる減点
        score -= min(self.mypy_errors * 3, 30)

        # カバレッジによる減点
        if self.test_coverage < 80:
            score -= (80 - self.test_coverage) * 0.5

        # テスト失敗による減点
        score -= min(self.test_failed * 5, 25)

        # セキュリティ脆弱性による減点
        score -= min(self.security_vulnerabilities * 10, 50)

        return max(score, 0.0)

    def items(self):
        """辞書のようにitemsメソッドを提供"""
        return asdict(self).items()

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return asdict(self)


@dataclass
class BuildResult:
    """ビルド結果を管理するデータモデル"""

    status: QualityCheckStatus
    metrics: QualityMetrics
    errors: List[str]
    warnings: List[str]
    duration_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "status": self.status.value,
            "metrics": asdict(self.metrics),
            "errors": self.errors,
            "warnings": self.warnings,
            "duration_seconds": self.duration_seconds,
        }


# QualityLoggerクラスは quality_logger.py に移動されました


class QualityMetricsCollector:
    """品質メトリクス収集クラス"""

    def __init__(
        self,
        project_root: Optional[Path] = None,
        logger: Optional[QualityLogger] = None,
    ) -> None:
        self.project_root = project_root or Path.cwd()
        self.logger = logger or get_quality_logger()

    def collect_ruff_metrics(self) -> Dict[str, Any]:
        """Ruffリンティングメトリクスを収集"""
        self.logger.log_quality_check_start("Ruff")

        try:
            # Ruffチェック実行
            result = subprocess.run(
                ["uv", "run", "ruff", "check", ".", "--output-format=json"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=False,
            )

            if result.stdout:
                issues = json.loads(result.stdout)
                issue_count = len(issues)
            else:
                issues = []
                issue_count = 0

            success = result.returncode == 0

            metrics_result = {
                "success": success,
                "issue_count": issue_count,
                "issues": issues,
                "errors": []
                if success
                else [f"Ruffチェックで{issue_count}件の問題が見つかりました"],
            }

            if success:
                self.logger.log_quality_check_success(
                    "Ruff", {"issue_count": issue_count}
                )
            else:
                error = RuffError(
                    f"Ruffリンティングで{issue_count}件の問題が見つかりました", issues
                )
                self.logger.log_quality_check_failure("Ruff", error)

            return metrics_result

        except (
            subprocess.CalledProcessError,
            json.JSONDecodeError,
            FileNotFoundError,
        ) as e:
            error = RuffError(f"Ruffメトリクス収集エラー: {str(e)}")
            self.logger.log_quality_check_failure("Ruff", error)
            return {"success": False, "issue_count": 0, "errors": [str(e)]}

    def collect_mypy_metrics(self) -> Dict[str, Any]:
        """MyPy型チェックメトリクスを収集"""
        self.logger.log_quality_check_start("MyPy")

        try:
            # MyPyチェック実行
            result = subprocess.run(
                ["uv", "run", "mypy", "src/", "--no-error-summary"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=False,
            )

            # エラー行数をカウント
            error_lines = [
                line
                for line in result.stdout.split("\n")
                if line.strip() and "error:" in line
            ]
            error_count = len(error_lines)

            success = result.returncode == 0

            metrics_result = {
                "success": success,
                "error_count": error_count,
                "error_details": error_lines[:10],  # 最初の10個のエラーを保存
                "errors": []
                if success
                else [f"MyPyで{error_count}件のエラーが見つかりました"],
            }

            if success:
                self.logger.log_quality_check_success(
                    "MyPy", {"error_count": error_count}
                )
            else:
                error = MyPyError(
                    f"MyPy型チェックで{error_count}件のエラーが見つかりました",
                    error_lines,
                )
                self.logger.log_quality_check_failure("MyPy", error)

            return metrics_result

        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            error = MyPyError(f"MyPyメトリクス収集エラー: {str(e)}")
            self.logger.log_quality_check_failure("MyPy", error)
            return {"success": False, "error_count": 0, "errors": [str(e)]}

    def collect_test_metrics(
        self, parallel_workers: Union[str, int] = "auto"
    ) -> Dict[str, Any]:
        """テストメトリクスを収集（並列実行対応）"""
        self.logger.log_quality_check_start("Tests")

        try:
            # 並列実行用のコマンドを構築
            cmd = [
                "uv",
                "run",
                "pytest",
                "--cov=src/setup_repo",
                "--cov-report=json",
                "--json-report",
                "--json-report-file=test-report.json",
            ]

            # 並列実行設定
            if parallel_workers != "1" and parallel_workers != 1:
                if parallel_workers == "auto":
                    import os

                    cpu_count = os.cpu_count() or 4
                    workers = max(1, int(cpu_count * 0.75))
                else:
                    workers = (
                        int(parallel_workers)
                        if isinstance(parallel_workers, str)
                        else parallel_workers
                    )

                if workers > 1:
                    cmd.extend(["-n", str(workers), "--dist", "worksteal"])
                    self.logger.info(f"並列テスト実行: {workers}ワーカー")

            # Pytestでカバレッジ付きテスト実行
            result = subprocess.run(
                cmd, cwd=self.project_root, capture_output=True, text=True, check=False
            )

            # カバレッジ情報を読み取り
            coverage_file = self.project_root / "coverage.json"
            coverage_percent = 0.0
            if coverage_file.exists():
                try:
                    with open(coverage_file, encoding="utf-8") as f:
                        coverage_data = json.load(f)
                        coverage_percent = coverage_data.get("totals", {}).get(
                            "percent_covered", 0.0
                        )
                except (json.JSONDecodeError, KeyError):
                    pass

            # テスト結果を読み取り
            test_report_file = self.project_root / "test-report.json"
            passed = failed = 0
            failed_tests = []
            if test_report_file.exists():
                try:
                    with open(test_report_file, encoding="utf-8") as f:
                        test_data = json.load(f)
                        summary = test_data.get("summary", {})
                        passed = summary.get("passed", 0)
                        failed = summary.get("failed", 0)

                        # 失敗したテストの詳細を取得
                        for test in test_data.get("tests", []):
                            if test.get("outcome") == "failed":
                                failed_tests.append(test.get("nodeid", "unknown"))

                except (json.JSONDecodeError, KeyError):
                    pass

            success = result.returncode == 0 and failed == 0

            metrics_result = {
                "success": success,
                "coverage_percent": coverage_percent,
                "tests_passed": passed,
                "tests_failed": failed,
                "failed_tests": failed_tests,
                "errors": [] if success else [f"テストで{failed}件の失敗がありました"],
            }

            if success:
                self.logger.log_quality_check_success(
                    "Tests",
                    {"coverage": coverage_percent, "passed": passed, "failed": failed},
                )
            else:
                # カバレッジ不足の場合は専用エラー
                if coverage_percent < 80.0:
                    error = CoverageError(
                        f"カバレッジが不足しています: {coverage_percent:.1f}% (必要: 80.0%)",
                        coverage_percent,
                        80.0,
                    )
                else:
                    error = TestFailureError(
                        f"テストで{failed}件の失敗がありました",
                        failed_tests,
                        coverage_percent,
                    )
                self.logger.log_quality_check_failure("Tests", error)

            return metrics_result

        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            error = TestFailureError(f"テストメトリクス収集エラー: {str(e)}")
            self.logger.log_quality_check_failure("Tests", error)
            return {
                "success": False,
                "coverage_percent": 0.0,
                "tests_passed": 0,
                "tests_failed": 0,
                "errors": [str(e)],
            }

    def collect_security_metrics(self) -> Dict[str, Any]:
        """セキュリティメトリクスを収集"""
        self.logger.log_quality_check_start("Security")

        vulnerability_count = 0
        vulnerabilities = []
        errors = []

        try:
            # Banditセキュリティチェック
            result = subprocess.run(
                ["uv", "run", "bandit", "-r", "src/", "-f", "json"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=False,
            )

            if result.stdout:
                try:
                    bandit_data = json.loads(result.stdout)
                    bandit_results = bandit_data.get("results", [])
                    vulnerability_count += len(bandit_results)
                    vulnerabilities.extend(bandit_results)
                except json.JSONDecodeError:
                    pass

        except (subprocess.CalledProcessError, FileNotFoundError):
            errors.append("Banditセキュリティチェックを実行できませんでした")

        try:
            # Safetyチェック（依存関係の脆弱性）
            result = subprocess.run(
                ["uv", "run", "safety", "check", "--json"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=False,
            )

            if result.stdout:
                try:
                    safety_data = json.loads(result.stdout)
                    if isinstance(safety_data, list):
                        vulnerability_count += len(safety_data)
                        vulnerabilities.extend(safety_data)
                except json.JSONDecodeError:
                    pass

        except (subprocess.CalledProcessError, FileNotFoundError):
            errors.append("Safetyチェックを実行できませんでした")

        success = vulnerability_count == 0 and len(errors) == 0

        metrics_result = {
            "success": success,
            "vulnerability_count": vulnerability_count,
            "vulnerabilities": vulnerabilities,
            "errors": errors if not success else [],
        }

        if success:
            self.logger.log_quality_check_success(
                "Security", {"vulnerability_count": vulnerability_count}
            )
        else:
            error = SecurityScanError(
                f"{vulnerability_count}件のセキュリティ脆弱性が見つかりました",
                vulnerabilities,
            )
            self.logger.log_quality_check_failure("Security", error)

        return metrics_result

    def collect_all_metrics(self) -> QualityMetrics:
        """すべての品質メトリクスを収集"""
        self.logger.info("品質メトリクス収集を開始します")

        # 各メトリクスを収集
        ruff_metrics = self.collect_ruff_metrics()
        mypy_metrics = self.collect_mypy_metrics()
        test_metrics = self.collect_test_metrics()
        security_metrics = self.collect_security_metrics()

        # QualityMetricsオブジェクトを作成
        metrics = QualityMetrics(
            ruff_issues=ruff_metrics.get("issue_count", 0),
            mypy_errors=mypy_metrics.get("error_count", 0),
            test_coverage=test_metrics.get("coverage_percent", 0.0),
            test_passed=test_metrics.get("tests_passed", 0),
            test_failed=test_metrics.get("tests_failed", 0),
            security_vulnerabilities=security_metrics.get("vulnerability_count", 0),
        )

        # メトリクス概要をログ
        metrics_summary = {
            "品質スコア": f"{metrics.get_quality_score():.1f}/100",
            "Ruffエラー": metrics.ruff_issues,
            "MyPyエラー": metrics.mypy_errors,
            "テストカバレッジ": f"{metrics.test_coverage:.1f}%",
            "テスト成功": metrics.test_passed,
            "テスト失敗": metrics.test_failed,
            "セキュリティ脆弱性": metrics.security_vulnerabilities,
            "品質基準達成": metrics.is_passing(),
        }

        self.logger.log_metrics_summary(metrics_summary)
        return metrics

    def save_metrics_report(
        self, metrics: QualityMetrics, output_file: Optional[Path] = None
    ) -> Path:
        """メトリクスレポートをJSONファイルに保存"""
        if output_file is None:
            output_file = self.project_root / "quality-report.json"

        report_data = {
            "timestamp": metrics.timestamp,
            "commit_hash": metrics.commit_hash,
            "metrics": asdict(metrics),
            "quality_score": metrics.get_quality_score(),
            "passing": metrics.is_passing(),
        }

        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        self.logger.info(f"品質レポートを保存しました: {output_file}")
        return output_file
