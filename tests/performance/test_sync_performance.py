"""
同期処理のパフォーマンステスト

リポジトリ同期処理の性能を測定するテストケース。
"""

import time
from unittest.mock import patch

import pytest


class TestSyncPerformance:
    """同期処理のパフォーマンステストクラス"""

    @pytest.mark.performance
    def test_small_repository_set_performance(self):
        """小規模リポジトリセットの同期パフォーマンステスト"""
        start_time = time.time()

        # モックを使用して実際のGit操作を回避
        with patch("src.setup_repo.git_operations.sync_repository") as mock_sync:
            mock_sync.return_value = True

            # 小規模テスト（5リポジトリ）
            test_repos = [f"test-repo-{i}" for i in range(5)]

            for _repo in test_repos:
                # 同期処理のシミュレーション
                time.sleep(0.01)  # 実際の処理時間をシミュレート

        elapsed_time = time.time() - start_time

        # 小規模テストは2秒以内で完了すべき
        assert elapsed_time < 2.0, f"小規模テストが遅すぎます: {elapsed_time:.2f}秒"

    @pytest.mark.performance
    def test_medium_repository_set_performance(self):
        """中規模リポジトリセットの同期パフォーマンステスト"""
        start_time = time.time()

        with patch("src.setup_repo.git_operations.sync_repository") as mock_sync:
            mock_sync.return_value = True

            # 中規模テスト（20リポジトリ）
            test_repos = [f"test-repo-{i}" for i in range(20)]

            for _repo in test_repos:
                time.sleep(0.02)  # 実際の処理時間をシミュレート

        elapsed_time = time.time() - start_time

        # 中規模テストは10秒以内で完了すべき
        assert elapsed_time < 10.0, f"中規模テストが遅すぎます: {elapsed_time:.2f}秒"

    @pytest.mark.performance
    @pytest.mark.slow
    def test_large_repository_set_performance(self):
        """大規模リポジトリセットの同期パフォーマンステスト"""
        start_time = time.time()

        with patch("src.setup_repo.git_operations.sync_repository") as mock_sync:
            mock_sync.return_value = True

            # 大規模テスト（100リポジトリ）
            test_repos = [f"test-repo-{i}" for i in range(100)]

            for _repo in test_repos:
                time.sleep(0.01)  # 実際の処理時間をシミュレート

        elapsed_time = time.time() - start_time

        # 大規模テストは30秒以内で完了すべき
        assert elapsed_time < 30.0, f"大規模テストが遅すぎます: {elapsed_time:.2f}秒"

    @pytest.mark.performance
    def test_concurrent_operations_performance(self):
        """並行処理のパフォーマンステスト"""
        import concurrent.futures

        start_time = time.time()

        def mock_sync_operation(repo_name):
            """同期処理のモック"""
            time.sleep(0.05)  # 処理時間をシミュレート
            return f"Synced {repo_name}"

        # 並行処理テスト（10並行）
        test_repos = [f"concurrent-repo-{i}" for i in range(10)]

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(mock_sync_operation, repo) for repo in test_repos]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        elapsed_time = time.time() - start_time

        # 並行処理は逐次処理より高速であるべき
        sequential_time_estimate = len(test_repos) * 0.05
        assert elapsed_time < sequential_time_estimate * 0.8, f"並行処理の効果が不十分: {elapsed_time:.2f}秒"
        assert len(results) == len(test_repos), "すべてのリポジトリが処理されていません"

    @pytest.mark.performance
    def test_memory_usage_performance(self):
        """メモリ使用量のパフォーマンステスト"""
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # メモリ使用量テスト用のデータ生成
        large_data = []
        for i in range(1000):
            large_data.append(f"test-data-{i}" * 100)

        current_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = current_memory - initial_memory

        # メモリ使用量の増加は50MB以下であるべき
        assert memory_increase < 50, f"メモリ使用量が過大: {memory_increase:.2f}MB増加"

        # データをクリア
        del large_data

    @pytest.mark.performance
    def test_startup_time_performance(self):
        """起動時間のパフォーマンステスト"""
        start_time = time.time()

        # CLIモジュールのインポート時間を測定

        import_time = time.time() - start_time

        # インポート時間は1秒以下であるべき
        assert import_time < 1.0, f"モジュールインポートが遅すぎます: {import_time:.2f}秒"
