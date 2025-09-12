#!/usr/bin/env python3
"""
CI/CDパイプライン最適化スクリプト

CI/CDパイプラインの実行時間を分析し、最適化提案を行います。
"""

import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class PipelineMetrics:
    """パイプライン実行メトリクス"""

    stage_name: str
    start_time: float
    end_time: float
    duration: float
    success: bool
    cache_hit: bool = False
    parallel_workers: int = 1


class CIPipelineOptimizer:
    """CI/CDパイプライン最適化クラス"""

    def __init__(self):
        self.metrics: list[PipelineMetrics] = []
        self.cache_strategies = {
            "dependencies": ["~/.cache/uv", ".venv"],
            "test_cache": [".pytest_cache", ".mypy_cache", ".ruff_cache"],
            "build_cache": ["dist/", "build/"],
        }

    def measure_stage(self, stage_name: str, command: list[str], parallel_workers: int = 1) -> PipelineMetrics:
        """ステージの実行時間を測定"""
        print(f"🔧 実行中: {stage_name}")

        start_time = time.perf_counter()

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=1800,  # 30分タイムアウト
            )
            success = result.returncode == 0

            if not success:
                print(f"❌ {stage_name} 失敗:")
                print(result.stderr)

        except subprocess.TimeoutExpired:
            print(f"⏰ {stage_name} タイムアウト")
            success = False
        except Exception as e:
            print(f"❌ {stage_name} エラー: {e}")
            success = False

        end_time = time.perf_counter()
        duration = end_time - start_time

        metrics = PipelineMetrics(
            stage_name=stage_name,
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            success=success,
            parallel_workers=parallel_workers,
        )

        self.metrics.append(metrics)

        status = "✅" if success else "❌"
        print(f"{status} {stage_name} 完了 ({duration:.2f}秒)")

        return metrics

    def check_cache_effectiveness(self) -> dict[str, Any]:
        """キャッシュの効果を分析"""
        cache_analysis = {}

        for cache_type, paths in self.cache_strategies.items():
            cache_info = {"exists": [], "sizes": [], "total_size_mb": 0}

            for path in paths:
                path_obj = Path(path)
                if path_obj.exists():
                    cache_info["exists"].append(str(path))

                    if path_obj.is_file():
                        size = path_obj.stat().st_size
                        cache_info["sizes"].append(size)
                        cache_info["total_size_mb"] += size / 1024 / 1024
                    elif path_obj.is_dir():
                        total_size = sum(f.stat().st_size for f in path_obj.rglob("*") if f.is_file())
                        cache_info["sizes"].append(total_size)
                        cache_info["total_size_mb"] += total_size / 1024 / 1024

            cache_analysis[cache_type] = cache_info

        return cache_analysis

    def analyze_parallel_efficiency(self) -> dict[str, Any]:
        """並列処理の効率を分析"""
        parallel_stages = [m for m in self.metrics if m.parallel_workers > 1]

        if not parallel_stages:
            return {"message": "並列処理ステージが見つかりません"}

        analysis = {
            "parallel_stages": len(parallel_stages),
            "average_workers": sum(m.parallel_workers for m in parallel_stages) / len(parallel_stages),
            "total_parallel_time": sum(m.duration for m in parallel_stages),
            "recommendations": [],
        }

        # 並列処理の効率性をチェック
        for stage in parallel_stages:
            if stage.duration > 300:  # 5分以上
                analysis["recommendations"].append(f"{stage.stage_name}: 実行時間が長いため、より多くのワーカーを検討")
            elif stage.parallel_workers > 8:
                analysis["recommendations"].append(f"{stage.stage_name}: ワーカー数が多すぎる可能性があります")

        return analysis

    def generate_optimization_report(self) -> dict[str, Any]:
        """最適化レポートを生成"""
        total_duration = sum(m.duration for m in self.metrics)
        successful_stages = [m for m in self.metrics if m.success]
        failed_stages = [m for m in self.metrics if not m.success]

        # 最も時間のかかるステージを特定
        slowest_stages = sorted(self.metrics, key=lambda x: x.duration, reverse=True)[:3]

        cache_analysis = self.check_cache_effectiveness()
        parallel_analysis = self.analyze_parallel_efficiency()

        report = {
            "summary": {
                "total_duration": total_duration,
                "successful_stages": len(successful_stages),
                "failed_stages": len(failed_stages),
                "total_stages": len(self.metrics),
            },
            "slowest_stages": [
                {
                    "name": stage.stage_name,
                    "duration": stage.duration,
                    "workers": stage.parallel_workers,
                }
                for stage in slowest_stages
            ],
            "cache_analysis": cache_analysis,
            "parallel_analysis": parallel_analysis,
            "recommendations": self._generate_recommendations(),
        }

        return report

    def _generate_recommendations(self) -> list[str]:
        """最適化推奨事項を生成"""
        recommendations = []

        # 実行時間ベースの推奨事項
        long_stages = [m for m in self.metrics if m.duration > 180]  # 3分以上
        if long_stages:
            recommendations.append(f"長時間実行ステージ ({len(long_stages)}個) の並列化を検討してください")

        # 失敗ステージの推奨事項
        failed_stages = [m for m in self.metrics if not m.success]
        if failed_stages:
            recommendations.append(f"失敗ステージ ({len(failed_stages)}個) のエラーハンドリングを改善してください")

        # キャッシュの推奨事項
        cache_analysis = self.check_cache_effectiveness()
        for cache_type, info in cache_analysis.items():
            if not info["exists"]:
                recommendations.append(f"{cache_type} キャッシュが設定されていません")
            elif info["total_size_mb"] > 1000:  # 1GB以上
                recommendations.append(f"{cache_type} キャッシュサイズが大きすぎます ({info['total_size_mb']:.1f}MB)")

        return recommendations

    def save_report(self, output_file: str = "ci-optimization-report.json") -> None:
        """レポートをファイルに保存"""
        report = self.generate_optimization_report()

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"📊 最適化レポートを保存しました: {output_file}")


def run_optimized_pipeline():
    """最適化されたパイプラインを実行"""
    optimizer = CIPipelineOptimizer()

    # 依存関係インストール
    optimizer.measure_stage("依存関係インストール", ["uv", "sync", "--dev"])

    # リンティング（並列実行）
    optimizer.measure_stage(
        "Ruff リンティング",
        ["uv", "run", "ruff", "check", ".", "--output-format=json"],
        parallel_workers=1,
    )

    # 型チェック
    optimizer.measure_stage("MyPy 型チェック", ["uv", "run", "mypy", "src/"])

    # 並列テスト実行
    cpu_count = os.cpu_count() or 4
    test_workers = max(1, int(cpu_count * 0.75))

    optimizer.measure_stage(
        "並列テスト実行",
        [
            "uv",
            "run",
            "pytest",
            "tests/",
            "-n",
            str(test_workers),
            "--dist",
            "worksteal",
            "--cov=src/setup_repo",
            "--cov-report=xml",
            "--junit-xml=test-results.xml",
        ],
        parallel_workers=test_workers,
    )

    # パフォーマンステスト（条件付き）
    if os.environ.get("RUN_PERFORMANCE_TESTS", "false").lower() == "true":
        optimizer.measure_stage(
            "パフォーマンステスト",
            [
                "uv",
                "run",
                "pytest",
                "tests/performance/",
                "-m",
                "performance and not slow",
                "--json-report",
                "--json-report-file=performance-report.json",
            ],
        )

    # レポート生成
    optimizer.save_report()

    # 結果サマリーを表示
    report = optimizer.generate_optimization_report()

    print("\n" + "=" * 60)
    print("📊 CI/CD パイプライン最適化レポート")
    print("=" * 60)

    summary = report["summary"]
    print(f"総実行時間: {summary['total_duration']:.2f}秒")
    print(f"成功ステージ: {summary['successful_stages']}/{summary['total_stages']}")

    if report["recommendations"]:
        print("\n🔧 最適化推奨事項:")
        for i, rec in enumerate(report["recommendations"], 1):
            print(f"  {i}. {rec}")

    print("\n最も時間のかかるステージ:")
    for stage in report["slowest_stages"]:
        print(f"  - {stage['name']}: {stage['duration']:.2f}秒 (ワーカー数: {stage['workers']})")

    # 失敗があった場合は終了コード1を返す
    if summary["failed_stages"] > 0:
        print(f"\n❌ {summary['failed_stages']}個のステージが失敗しました")
        return 1

    print("\n✅ 全ステージが正常に完了しました")
    return 0


def main():
    """メイン関数"""
    if len(sys.argv) > 1 and sys.argv[1] == "--analyze-only":
        # 既存のレポートを分析のみ
        report_file = "ci-optimization-report.json"
        if Path(report_file).exists():
            with open(report_file, encoding="utf-8") as f:
                report = json.load(f)

            print("📊 既存の最適化レポート分析:")
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print(f"❌ レポートファイルが見つかりません: {report_file}")
            return 1
    else:
        # パイプラインを実行
        return run_optimized_pipeline()


if __name__ == "__main__":
    sys.exit(main())
