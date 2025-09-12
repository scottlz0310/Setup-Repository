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
from typing import Any, Optional, Union

from .quality_collectors import (
    collect_coverage_metrics,
    collect_mypy_metrics,
    collect_pytest_metrics,
    collect_ruff_metrics,
)
from .quality_errors import (
    SecurityScanError,
)
from .quality_logger import (
    QualityLogger,
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
            result = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
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

    def to_dict(self) -> dict[str, Any]:
        """辞書形式に変換"""
        return asdict(self)


@dataclass
class BuildResult:
    """ビルド結果を管理するデータモデル"""

    status: QualityCheckStatus
    metrics: QualityMetrics
    errors: list[str]
    warnings: list[str]
    duration_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
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

    def collect_ruff_metrics(self) -> dict[str, Any]:
        """Ruffリンティングメトリクスを収集"""
        return collect_ruff_metrics(self.project_root, self.logger)

    def collect_mypy_metrics(self) -> dict[str, Any]:
        """MyPy型チェックメトリクスを収集"""
        return collect_mypy_metrics(self.project_root, self.logger)

    def collect_test_metrics(self, parallel_workers: Union[str, int] = "auto") -> dict[str, Any]:
        """テストメトリクスを収集（並列実行対応）"""
        return collect_pytest_metrics(self.project_root, self.logger, parallel_workers)

    def collect_security_metrics(self) -> dict[str, Any]:
        """セキュリティメトリクスを収集"""
        self.logger.log_quality_check_start("Security")

        vulnerability_count = 0
        vulnerabilities = []
        errors = []
        warnings = []
        tools_available = {"bandit": False, "safety": False}

        # セキュリティツールの利用可能性をチェック
        try:
            result = subprocess.run(
                ["uv", "run", "bandit", "--version"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=False,
            )
            tools_available["bandit"] = result.returncode == 0
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        try:
            result = subprocess.run(
                ["uv", "run", "safety", "--version"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=False,
            )
            tools_available["safety"] = result.returncode == 0
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        # Banditセキュリティチェック
        if tools_available["bandit"]:
            try:
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
                    except json.JSONDecodeError as e:
                        warnings.append(f"Bandit出力の解析に失敗: {e}")
                elif result.returncode != 0:
                    warnings.append(f"Banditが警告付きで終了: {result.stderr}")

            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                errors.append(f"Banditセキュリティチェックの実行に失敗: {e}")
        else:
            warnings.append("Banditが利用できません。セキュリティグループの依存関係をインストールしてください")

        # Safetyチェック（依存関係の脆弱性）
        if tools_available["safety"]:
            try:
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
                    except json.JSONDecodeError as e:
                        warnings.append(f"Safety出力の解析に失敗: {e}")
                elif result.returncode != 0:
                    warnings.append(f"Safetyが警告付きで終了: {result.stderr}")

            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                errors.append(f"Safetyチェックの実行に失敗: {e}")
        else:
            warnings.append("Safetyが利用できません。セキュリティグループの依存関係をインストールしてください")

        # 成功判定: 重大なエラーがなく、利用可能なツールで脆弱性が見つからない場合
        has_critical_errors = len(errors) > 0
        has_vulnerabilities = vulnerability_count > 0
        no_tools_available = not any(tools_available.values())

        # ツールが利用できない場合は警告として扱い、失敗とはしない
        # CI環境では依存関係のインストールに失敗することがあるため、ツールが利用できない場合も成功とする
        success = not has_critical_errors and (not has_vulnerabilities or no_tools_available)

        metrics_result = {
            "success": success,
            "vulnerability_count": vulnerability_count,
            "vulnerabilities": vulnerabilities,
            "errors": errors,
            "warnings": warnings,
            "tools_available": tools_available,
            "no_tools_available": no_tools_available,
        }

        if success:
            if no_tools_available:
                self.logger.log_quality_check_success(
                    "Security",
                    {
                        "vulnerability_count": vulnerability_count,
                        "status": "スキップ（セキュリティツールが利用できません）",
                        "available_tools": [k for k, v in tools_available.items() if v],
                    },
                )
            else:
                self.logger.log_quality_check_success(
                    "Security",
                    {
                        "vulnerability_count": vulnerability_count,
                        "available_tools": [k for k, v in tools_available.items() if v],
                    },
                )
        else:
            error = SecurityScanError(
                f"{vulnerability_count}件のセキュリティ脆弱性が見つかりました",
                vulnerabilities,
            )
            self.logger.log_quality_check_failure("Security", error)

        # 警告がある場合はログ出力
        for warning in warnings:
            self.logger.warning(warning)

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

    def save_metrics_report(self, metrics: QualityMetrics, output_file: Optional[Path] = None) -> Path:
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


# 後方互換性のためのエイリアス
__all__ = [
    "QualityCheckStatus",
    "QualityMetrics",
    "BuildResult",
    "QualityMetricsCollector",
    # コレクター関数（後方互換性）
    "collect_ruff_metrics",
    "collect_mypy_metrics",
    "collect_pytest_metrics",
    "collect_coverage_metrics",
]
