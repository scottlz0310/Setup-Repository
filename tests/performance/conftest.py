"""
パフォーマンステスト用のpytestフィクスチャ設定
"""

import os
import time

import psutil
import pytest


@pytest.fixture(scope="session")
def performance_monitor():
    """パフォーマンス監視用フィクスチャ"""

    class PerformanceMonitor:
        def __init__(self):
            self.process = psutil.Process(os.getpid())
            self.start_time = time.time()
            self.start_memory = self.process.memory_info().rss / 1024 / 1024  # MB

        def get_elapsed_time(self):
            return time.time() - self.start_time

        def get_memory_usage(self):
            current_memory = self.process.memory_info().rss / 1024 / 1024  # MB
            return current_memory - self.start_memory

        def reset(self):
            self.start_time = time.time()
            self.start_memory = self.process.memory_info().rss / 1024 / 1024  # MB

    return PerformanceMonitor()


@pytest.fixture
def benchmark_timer():
    """ベンチマーク用タイマーフィクスチャ"""

    class BenchmarkTimer:
        def __init__(self):
            self.start_time = None
            self.end_time = None

        def start(self):
            self.start_time = time.perf_counter()

        def stop(self):
            self.end_time = time.perf_counter()

        def elapsed(self):
            if self.start_time is None or self.end_time is None:
                return None
            return self.end_time - self.start_time

    return BenchmarkTimer()


def pytest_configure(config):
    """pytest設定"""
    config.addinivalue_line("markers", "performance: パフォーマンステストマーカー")
    config.addinivalue_line("markers", "slow: 実行時間の長いテストマーカー")


def pytest_collection_modifyitems(config, items):
    """テスト収集時の設定変更"""
    for item in items:
        # パフォーマンステストにマーカーを自動追加
        if "performance" in item.nodeid:
            item.add_marker(pytest.mark.performance)

        # 大規模テストにslowマーカーを自動追加
        if "large" in item.name.lower():
            item.add_marker(pytest.mark.slow)
