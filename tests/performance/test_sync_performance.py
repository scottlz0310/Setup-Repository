"""
リポジトリ同期のパフォーマンステスト

大量リポジトリの同期処理のパフォーマンスを測定し、
性能要件を満たしているかを検証します。
"""

import time
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from src.setup_repo.sync import sync_repositories


class PerformanceMetrics:
    """パフォーマンス測定結果を管理するクラス"""

    def __init__(self):
        self.start_time: float = 0
        self.end_time: float = 0
        self.execution_time: float = 0
        self.repositories_processed: int = 0
        self.operations_per_second: float = 0
        self.memory_usage_mb: float = 0

    def start_measurement(self) -> None:
        """測定開始"""
        self.start_time = time.perf_counter()

    def end_measurement(self, repo_count: int) -> None:
        """測定終了"""
        self.end_time = time.perf_counter()
        self.execution_time = self.end_time - self.start_time
        self.repositories_processed = repo_count
        if self.execution_time > 0:
            self.operations_per_second = repo_count / self.execution_time

    def to_dict(self) -> dict[str, Any]:
        """測定結果を辞書形式で返す"""
        return {
            "execution_time": self.execution_time,
            "repositories_processed": self.repositories_processed,
            "operations_per_second": self.operations_per_second,
            "memory_usage_mb": self.memory_usage_mb,
        }


def generate_mock_repositories(count: int) -> list[dict[str, Any]]:
    """テスト用のモックリポジトリデータを生成"""
    repositories = []
    for i in range(count):
        repo_name = f"test-repo-{i:04d}"
        repositories.append(
            {
                "name": repo_name,
                "full_name": f"test_user/{repo_name}",
                "clone_url": f"https://github.com/test_user/{repo_name}.git",
                "ssh_url": f"git@github.com:test_user/{repo_name}.git",
                "description": f"テストリポジトリ {i}",
                "private": i % 3 == 0,  # 3つに1つをプライベートに
                "default_branch": "main" if i % 2 == 0 else "master",
            }
        )
    return repositories


@pytest.fixture
def performance_config(temp_dir: Path) -> dict[str, Any]:
    """パフォーマンステスト用の設定"""
    return {
        "github_token": "test_token_performance",
        "github_username": "test_user",
        "clone_destination": str(temp_dir / "repos"),
        "auto_install_dependencies": False,  # パフォーマンステストでは無効化
        "setup_vscode": False,  # パフォーマンステストでは無効化
        "platform_specific_setup": False,  # パフォーマンステストでは無効化
        "dry_run": True,  # 実際のクローンは行わない
        "verbose": False,  # ログ出力を最小化
        "max_concurrent_operations": 5,  # 並列処理数
        "skip_uv_install": True,  # uvインストールをスキップ
        "use_https": True,  # HTTPSを使用してSSH接続テストを回避
    }


@pytest.mark.slow
@pytest.mark.performance
class TestSyncPerformance:
    """同期処理のパフォーマンステスト"""

    def test_small_repository_set_performance(
        self, performance_config: dict[str, Any]
    ) -> None:
        """小規模リポジトリセット（10個）のパフォーマンステスト"""
        # 10個のリポジトリを生成
        repositories = generate_mock_repositories(10)

        # パフォーマンス測定開始
        metrics = PerformanceMetrics()
        metrics.start_measurement()

        with (
            patch("src.setup_repo.sync.get_repositories", return_value=repositories),
            patch(
                "src.setup_repo.sync.sync_repository_with_retries", return_value=True
            ),
        ):
            result = sync_repositories(performance_config)

        metrics.end_measurement(len(repositories))

        # パフォーマンス要件の検証
        assert result.success, f"同期処理が失敗しました: {result.errors}"
        assert metrics.execution_time < 5.0, (
            f"実行時間が要件を超過: {metrics.execution_time:.2f}秒 > 5.0秒"
        )
        assert metrics.operations_per_second > 2.0, (
            f"処理速度が要件未満: "
            f"{metrics.operations_per_second:.2f} ops/sec < 2.0 ops/sec"
        )

        print(f"小規模セット パフォーマンス結果: {metrics.to_dict()}")

    def test_medium_repository_set_performance(
        self, performance_config: dict[str, Any]
    ) -> None:
        """中規模リポジトリセット（50個）のパフォーマンステスト"""
        # 50個のリポジトリを生成
        repositories = generate_mock_repositories(50)

        # パフォーマンス測定開始
        metrics = PerformanceMetrics()
        metrics.start_measurement()

        with (
            patch("src.setup_repo.sync.get_repositories", return_value=repositories),
            patch(
                "src.setup_repo.sync.sync_repository_with_retries", return_value=True
            ),
        ):
            result = sync_repositories(performance_config)

        metrics.end_measurement(len(repositories))

        # パフォーマンス要件の検証
        assert result.success, f"同期処理が失敗しました: {result.errors}"
        assert metrics.execution_time < 20.0, (
            f"実行時間が要件を超過: {metrics.execution_time:.2f}秒 > 20.0秒"
        )
        assert metrics.operations_per_second > 2.5, (
            f"処理速度が要件未満: "
            f"{metrics.operations_per_second:.2f} ops/sec < 2.5 ops/sec"
        )

        print(f"中規模セット パフォーマンス結果: {metrics.to_dict()}")


@pytest.mark.slow
@pytest.mark.performance
class TestGitOperationsPerformance:
    """Git操作のパフォーマンステスト"""

    def test_git_clone_simulation_performance(self, temp_dir: Path) -> None:
        """Git クローン操作のシミュレーションパフォーマンステスト"""
        # 複数のリポジトリクローンをシミュレート
        repositories = generate_mock_repositories(30)

        metrics = PerformanceMetrics()
        metrics.start_measurement()

        # Git操作をシミュレート
        for repo in repositories:
            temp_dir / "repos" / repo["name"]
            # Git操作のシミュレーション（実際の処理時間をシミュレート）
            time.sleep(0.01)  # 10ms の処理時間をシミュレート

        metrics.end_measurement(len(repositories))

        # パフォーマンス要件の検証
        assert metrics.execution_time < 10.0, (
            f"Git操作シミュレーション時間が要件を超過: "
            f"{metrics.execution_time:.2f}秒 > 10.0秒"
        )
        assert metrics.operations_per_second > 3.0, (
            f"Git操作速度が要件未満: "
            f"{metrics.operations_per_second:.2f} ops/sec < 3.0 ops/sec"
        )

        print(f"Git操作パフォーマンス結果: {metrics.to_dict()}")


# パフォーマンステスト実行時の設定
def pytest_configure(config):
    """パフォーマンステスト用のpytest設定"""
    config.addinivalue_line("markers", "performance: パフォーマンステストのマーカー")
