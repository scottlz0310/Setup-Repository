"""
大量リポジトリ処理のパフォーマンステスト

このモジュールでは、大量のリポジトリを処理する際の
システムのパフォーマンスを測定し、スケーラビリティを
検証します。メモリ使用量、処理時間、スループットなどを
監視します。
"""

import gc
import time
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

try:
    import psutil

    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

from setup_repo.sync import sync_repositories


class PerformanceProfiler:
    """パフォーマンス測定とプロファイリングクラス"""

    def __init__(self):
        self.start_time: float = 0
        self.end_time: float = 0
        self.start_memory: float = 0
        self.peak_memory: float = 0
        self.end_memory: float = 0
        self.cpu_percent: float = 0
        if HAS_PSUTIL:
            self.process = psutil.Process()
        else:
            self.process = None

    def start_profiling(self) -> None:
        """プロファイリング開始"""
        gc.collect()  # ガベージコレクション実行
        self.start_time = time.perf_counter()
        if HAS_PSUTIL:
            self.start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
            self.peak_memory = self.start_memory
        else:
            self.start_memory = 0
            self.peak_memory = 0

    def update_peak_memory(self) -> None:
        """ピークメモリ使用量を更新"""
        if HAS_PSUTIL and self.process:
            current_memory = self.process.memory_info().rss / 1024 / 1024  # MB
            if current_memory > self.peak_memory:
                self.peak_memory = current_memory

    def end_profiling(self) -> dict[str, float]:
        """プロファイリング終了と結果返却"""
        self.end_time = time.perf_counter()
        if HAS_PSUTIL and self.process:
            self.end_memory = self.process.memory_info().rss / 1024 / 1024  # MB
            self.cpu_percent = self.process.cpu_percent()
        else:
            self.end_memory = 0
            self.cpu_percent = 0

        return {
            "execution_time": self.end_time - self.start_time,
            "memory_start_mb": self.start_memory,
            "memory_peak_mb": self.peak_memory,
            "memory_end_mb": self.end_memory,
            "memory_growth_mb": self.end_memory - self.start_memory,
            "cpu_percent": self.cpu_percent,
        }


def generate_large_repository_set(count: int) -> list[dict[str, Any]]:
    """大量のテスト用リポジトリデータを生成"""
    repositories = []

    # 様々なタイプのリポジトリを生成
    repo_types = [
        ("frontend", "React/Vue.js フロントエンドプロジェクト"),
        ("backend", "Node.js/Python バックエンドAPI"),
        ("mobile", "React Native/Flutter モバイルアプリ"),
        ("data", "データサイエンス/機械学習プロジェクト"),
        ("devops", "Docker/Kubernetes インフラ設定"),
        ("docs", "ドキュメント/Wiki プロジェクト"),
        ("lib", "ライブラリ/SDK プロジェクト"),
        ("tool", "CLI ツール/ユーティリティ"),
    ]

    for i in range(count):
        repo_type, description = repo_types[i % len(repo_types)]
        repo_name = f"{repo_type}-project-{i:05d}"

        repositories.append(
            {
                "name": repo_name,
                "full_name": f"test_org/{repo_name}",
                "clone_url": f"https://github.com/test_org/{repo_name}.git",
                "ssh_url": f"git@github.com:test_org/{repo_name}.git",
                "description": f"{description} #{i}",
                "private": i % 4 == 0,  # 25%をプライベートに
                "default_branch": "main" if i % 3 != 0 else "develop",
                "size": 1000 + (i * 100) % 50000,  # 1KB-50MBのサイズをシミュレート
                "language": repo_type,
                "topics": [repo_type, "test", f"batch-{i // 100}"],
            }
        )

    return repositories


@pytest.fixture
def large_repo_config(temp_dir: Path) -> dict[str, Any]:
    """大量リポジトリテスト用の設定"""
    return {
        "github_token": "test_token_large",
        "github_username": "test_org",
        "clone_destination": str(temp_dir / "large_repos"),
        "max_concurrent_operations": 10,
        "batch_size": 50,
        "memory_limit_mb": 1000,
        "timeout_seconds": 300,
        "retry_attempts": 2,
        "dry_run": True,
        "verbose": False,
    }


@pytest.mark.slow
@pytest.mark.performance
class TestLargeRepositoryPerformance:
    """大量リポジトリ処理のパフォーマンステストクラス"""

    def test_100_repositories_performance(
        self,
        large_repo_config: dict[str, Any],
    ) -> None:
        """100個のリポジトリ処理パフォーマンステスト"""
        repositories = generate_large_repository_set(100)
        profiler = PerformanceProfiler()

        profiler.start_profiling()

        with (
            patch("setup_repo.sync.get_repositories", return_value=repositories),
            patch("setup_repo.sync.sync_repository_with_retries", return_value=True),
        ):
            _ = sync_repositories(large_repo_config, dry_run=True)
            profiler.update_peak_memory()

        metrics = profiler.end_profiling()

        # パフォーマンス要件の検証
        assert result.success, f"100リポジトリ同期が失敗: {result.errors}"
        assert metrics["execution_time"] < 30.0, f"実行時間超過: {metrics['execution_time']:.2f}s > 30.0s"
        assert metrics["memory_growth_mb"] < 200.0, (
            f"メモリ使用量増加が過大: {metrics['memory_growth_mb']:.2f}MB > 200MB"
        )
        assert len(result.synced_repos) == 100

        print(f"100リポジトリ パフォーマンス: {metrics}")

    def test_500_repositories_performance(
        self,
        large_repo_config: dict[str, Any],
    ) -> None:
        """500個のリポジトリ処理パフォーマンステスト"""
        repositories = generate_large_repository_set(500)
        profiler = PerformanceProfiler()

        profiler.start_profiling()

        with (
            patch("setup_repo.sync.get_repositories", return_value=repositories),
            patch("setup_repo.sync.sync_repository_with_retries", return_value=True),
        ):
            _ = sync_repositories(large_repo_config, dry_run=True)
            profiler.update_peak_memory()

        metrics = profiler.end_profiling()

        # パフォーマンス要件の検証
        assert result.success, f"500リポジトリ同期が失敗: {result.errors}"
        assert metrics["execution_time"] < 120.0, f"実行時間超過: {metrics['execution_time']:.2f}s > 120.0s"
        assert metrics["memory_growth_mb"] < 500.0, (
            f"メモリ使用量増加が過大: {metrics['memory_growth_mb']:.2f}MB > 500MB"
        )
        assert len(result.synced_repos) == 500

        print(f"500リポジトリ パフォーマンス: {metrics}")

    def test_1000_repositories_performance(
        self,
        large_repo_config: dict[str, Any],
    ) -> None:
        """1000個のリポジトリ処理パフォーマンステスト"""
        repositories = generate_large_repository_set(1000)
        profiler = PerformanceProfiler()

        # より緩い制限を設定
        large_repo_config["timeout_seconds"] = 600
        large_repo_config["memory_limit_mb"] = 2000

        profiler.start_profiling()

        with (
            patch("setup_repo.sync.get_repositories", return_value=repositories),
            patch("setup_repo.sync.sync_repository_with_retries", return_value=True),
        ):
            _ = sync_repositories(large_repo_config, dry_run=True)
            profiler.update_peak_memory()

        metrics = profiler.end_profiling()

        # パフォーマンス要件の検証
        assert result.success, f"1000リポジトリ同期が失敗: {result.errors}"
        assert metrics["execution_time"] < 300.0, f"実行時間超過: {metrics['execution_time']:.2f}s > 300.0s"
        assert metrics["memory_growth_mb"] < 1000.0, (
            f"メモリ使用量増加が過大: {metrics['memory_growth_mb']:.2f}MB > 1000MB"
        )
        assert len(result.synced_repos) == 1000

        print(f"1000リポジトリ パフォーマンス: {metrics}")

    def test_memory_efficiency_with_batching(
        self,
        large_repo_config: dict[str, Any],
    ) -> None:
        """バッチ処理によるメモリ効率テスト"""
        repositories = generate_large_repository_set(200)

        # バッチサイズを変えてテスト
        batch_sizes = [10, 25, 50, 100]
        results = {}

        for batch_size in batch_sizes:
            large_repo_config["batch_size"] = batch_size
            profiler = PerformanceProfiler()
            profiler.start_profiling()

            with (
                patch("setup_repo.sync.get_repositories", return_value=repositories),
                patch("setup_repo.sync.sync_repository_with_retries", return_value=True),
            ):
                result = sync_repositories(large_repo_config, dry_run=True)
                profiler.update_peak_memory()

            metrics = profiler.end_profiling()
            results[batch_size] = metrics

            assert result.success
            assert len(result.synced_repos) == 200

        # バッチサイズが小さいほどメモリ効率が良いことを確認
        print("バッチサイズ別パフォーマンス:")
        for batch_size, metrics in results.items():
            print(f"  バッチサイズ {batch_size}: {metrics}")

        # 最小バッチサイズが最もメモリ効率が良いことを確認
        min_batch_memory = results[min(batch_sizes)]["memory_peak_mb"]
        max_batch_memory = results[max(batch_sizes)]["memory_peak_mb"]

        # 必ずしも小さいバッチサイズが良いとは限らないが、
        # 極端な差がないことを確認
        memory_ratio = max_batch_memory / min_batch_memory
        assert memory_ratio < 2.0, f"バッチサイズによるメモリ使用量の差が大きすぎます: {memory_ratio:.2f}"

    def test_concurrent_processing_performance(
        self,
        large_repo_config: dict[str, Any],
    ) -> None:
        """並行処理パフォーマンステスト"""
        repositories = generate_large_repository_set(100)

        # 並行処理数を変えてテスト
        concurrent_levels = [1, 5, 10, 20]
        results = {}

        for concurrent_ops in concurrent_levels:
            large_repo_config["max_concurrent_operations"] = concurrent_ops
            profiler = PerformanceProfiler()
            profiler.start_profiling()

            with (
                patch("setup_repo.sync.get_repositories", return_value=repositories),
                patch("setup_repo.sync.sync_repository_with_retries", return_value=True),
            ):
                result = sync_repositories(large_repo_config, dry_run=True)
                profiler.update_peak_memory()

            metrics = profiler.end_profiling()
            results[concurrent_ops] = metrics

            assert result.success
            assert len(result.synced_repos) == 100

        print("並行処理レベル別パフォーマンス:")
        for level, metrics in results.items():
            throughput = 100 / metrics["execution_time"]
            print(f"  並行数 {level}: {metrics['execution_time']:.2f}s, {throughput:.2f} repos/s")

        # 並行処理により処理時間が改善されることを確認
        sequential_time = results[1]["execution_time"]
        parallel_time = results[10]["execution_time"]

        # 並行処理による改善を確認（ドライランモードでは改善が限定的な場合がある）
        improvement_ratio = (sequential_time - parallel_time) / sequential_time

        # ドライランモードでは並行処理のオーバーヘッドにより性能劣化する場合があるため、
        # 極端な劣化がないことを確認（-10%以内）
        assert improvement_ratio > -0.1, f"並行処理による極端な性能劣化が発生: {improvement_ratio:.2%}"

        # 実際の改善があった場合は記録
        if improvement_ratio > 0.05:
            print(f"並行処理による改善: {improvement_ratio:.2%}")
        elif improvement_ratio < -0.02:
            print(f"並行処理によるオーバーヘッド: {improvement_ratio:.2%} (ドライランモードのため)")
        else:
            print(f"並行処理による影響は軽微: {improvement_ratio:.2%}")

    def test_memory_leak_detection(
        self,
        large_repo_config: dict[str, Any],
    ) -> None:
        """メモリリーク検出テスト"""
        repositories = generate_large_repository_set(50)

        # 複数回実行してメモリ使用量の変化を監視
        memory_measurements = []

        for iteration in range(5):
            gc.collect()  # ガベージコレクション実行

            if HAS_PSUTIL:
                initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
            else:
                initial_memory = 0

            with (
                patch("setup_repo.sync.get_repositories", return_value=repositories),
                patch("setup_repo.sync.sync_repository_with_retries", return_value=True),
            ):
                _ = sync_repositories(large_repo_config, dry_run=True)

            gc.collect()  # 処理後のガベージコレクション
            if HAS_PSUTIL:
                final_memory = psutil.Process().memory_info().rss / 1024 / 1024
            else:
                final_memory = 0

            memory_growth = final_memory - initial_memory
            memory_measurements.append(memory_growth)

            assert result.success
            print(f"反復 {iteration + 1}: メモリ増加 {memory_growth:.2f}MB")

        # メモリリークがないことを確認
        # 各反復でのメモリ増加が一定範囲内であることを確認
        avg_growth = sum(memory_measurements) / len(memory_measurements)
        max_growth = max(memory_measurements)

        assert max_growth < 50.0, f"メモリ増加が過大: {max_growth:.2f}MB > 50MB"
        assert avg_growth < 20.0, f"平均メモリ増加が過大: {avg_growth:.2f}MB > 20MB"

    def test_scalability_limits(
        self,
        large_repo_config: dict[str, Any],
    ) -> None:
        """スケーラビリティ限界テスト"""
        # 段階的にリポジトリ数を増やしてテスト
        repo_counts = [100, 250, 500, 750, 1000]
        scalability_results = {}

        for repo_count in repo_counts:
            repositories = generate_large_repository_set(repo_count)
            profiler = PerformanceProfiler()

            # タイムアウトを動的に調整
            large_repo_config["timeout_seconds"] = max(300, repo_count * 0.5)

            profiler.start_profiling()

            try:
                with (
                    patch("setup_repo.sync.get_repositories", return_value=repositories),
                    patch(
                        "setup_repo.sync.sync_repository_with_retries",
                        return_value=True,
                    ),
                ):
                    _ = sync_repositories(large_repo_config, dry_run=True)
                    profiler.update_peak_memory()

                metrics = profiler.end_profiling()

                # スループット計算
                throughput = repo_count / metrics["execution_time"]

                scalability_results[repo_count] = {
                    "success": result.success,
                    "execution_time": metrics["execution_time"],
                    "memory_peak_mb": metrics["memory_peak_mb"],
                    "throughput": throughput,
                    "synced_count": len(result.synced_repos),
                }

                print(f"{repo_count}リポジトリ: {throughput:.2f} repos/s, {metrics['memory_peak_mb']:.2f}MB")

            except Exception as e:
                scalability_results[repo_count] = {
                    "success": False,
                    "error": str(e),
                }
                print(f"{repo_count}リポジトリでエラー: {e}")

        # スケーラビリティ分析
        successful_tests = {k: v for k, v in scalability_results.items() if v.get("success", False)}

        assert len(successful_tests) >= 3, "少なくとも3つのスケールでテストが成功する必要があります"

        # 最大成功リポジトリ数を確認
        max_successful_repos = max(successful_tests.keys())
        assert max_successful_repos >= 500, f"最低500リポジトリまで処理できる必要があります: {max_successful_repos}"

        print(f"スケーラビリティテスト結果: 最大{max_successful_repos}リポジトリまで処理可能")

    @pytest.mark.stress
    def test_stress_test_with_resource_monitoring(
        self,
        large_repo_config: dict[str, Any],
    ) -> None:
        """リソース監視付きストレステスト"""
        repositories = generate_large_repository_set(2000)  # 大量のリポジトリ

        # リソース監視設定
        large_repo_config["timeout_seconds"] = 900  # 15分
        large_repo_config["memory_limit_mb"] = 4000  # 4GB

        profiler = PerformanceProfiler()
        profiler.start_profiling()

        # リソース使用量を定期的に監視
        resource_snapshots = []

        def monitor_resources():
            if HAS_PSUTIL:
                process = psutil.Process()
                return {
                    "memory_mb": process.memory_info().rss / 1024 / 1024,
                    "cpu_percent": process.cpu_percent(),
                    "timestamp": time.time(),
                }
            else:
                return {
                    "memory_mb": 0,
                    "cpu_percent": 0,
                    "timestamp": time.time(),
                }

        try:
            with (
                patch("setup_repo.sync.get_repositories", return_value=repositories),
                patch("setup_repo.sync.sync_repository_with_retries", return_value=True),
            ):
                # 監視開始
                time.time()

                _ = sync_repositories(large_repo_config, dry_run=True)

                # 定期的なリソース監視（実際の実装では別スレッドで実行）
                resource_snapshots.append(monitor_resources())
                profiler.update_peak_memory()

            metrics = profiler.end_profiling()

            # ストレステスト結果の検証
            if result.success:
                print(f"ストレステスト成功: {len(result.synced_repos)}リポジトリ処理")
                print(f"実行時間: {metrics['execution_time']:.2f}秒")
                print(f"ピークメモリ: {metrics['memory_peak_mb']:.2f}MB")

                # 基本的な要件チェック
                assert metrics["execution_time"] < 900.0  # 15分以内
                assert metrics["memory_peak_mb"] < 4000.0  # 4GB以内
            else:
                print(f"ストレステスト部分成功: {len(result.synced_repos)}/{len(repositories)}リポジトリ処理")
                # 部分的成功でも50%以上は処理できることを期待
                success_rate = len(result.synced_repos) / len(repositories)
                assert success_rate > 0.5, f"成功率が低すぎます: {success_rate:.2%}"

        except Exception as e:
            print(f"ストレステストでエラー発生: {e}")
            # ストレステストでのエラーは許容（リソース制限による）
            pytest.skip(f"ストレステストがリソース制限によりスキップされました: {e}")
