"""
テスト設定とフィクスチャ

このモジュールでは、全テストで共通して使用される
フィクスチャとテスト設定を定義します。
"""

import os
import platform
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """一時ディレクトリフィクスチャ"""
    with tempfile.TemporaryDirectory() as temp_dir_str:
        yield Path(temp_dir_str)


@pytest.fixture
def sample_config() -> dict[str, Any]:
    """サンプル設定フィクスチャ"""
    return {
        "github_token": "test_token_12345",
        "github_username": "test_user",
        "clone_destination": "/tmp/test_repos",
        "dest": "/tmp/test_repos",
        "use_ssh": False,
        "max_retries": 3,
        "retry_delay": 1,
    }


@pytest.fixture
def ci_environment() -> dict[str, str]:
    """CI環境変数フィクスチャ"""
    return {
        "CI": "true",
        "GITHUB_ACTIONS": "true",
        "RUNNER_OS": platform.system(),
        "GITHUB_WORKFLOW": "Test Workflow",
        "GITHUB_RUN_ID": "123456789",
    }


def pytest_configure(config):
    """pytest設定"""
    # カスタムマーカーを登録
    config.addinivalue_line("markers", "unit: 単体テスト")
    config.addinivalue_line("markers", "integration: 統合テスト")
    config.addinivalue_line("markers", "slow: 実行時間が長いテスト")
    config.addinivalue_line("markers", "network: ネットワーク接続が必要なテスト")


def pytest_collection_modifyitems(config, items):
    """テスト収集時の処理"""
    # CI環境でない場合、統合テストをスキップ
    if not os.environ.get("CI") and not os.environ.get("INTEGRATION_TESTS"):
        skip_integration = pytest.mark.skip(reason="統合テストはCI環境でのみ実行")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)

    # ネットワークテストのスキップ処理
    if not os.environ.get("NETWORK_TESTS"):
        skip_network = pytest.mark.skip(reason="ネットワークテストは明示的に有効化された場合のみ実行")
        for item in items:
            if "network" in item.keywords:
                item.add_marker(skip_network)


@pytest.fixture(autouse=True)
def setup_test_environment():
    """テスト環境の自動セットアップ"""
    # テスト実行前の処理
    original_env = os.environ.copy()

    # テスト用環境変数を設定
    test_env = {
        "PYTEST_RUNNING": "true",
        "LOG_LEVEL": "DEBUG",
    }

    for key, value in test_env.items():
        os.environ[key] = value

    yield

    # テスト実行後のクリーンアップ
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_github_api_response():
    """GitHub APIレスポンスのモック"""
    return {
        "user_info": {
            "login": "test_user",
            "name": "Test User",
            "email": "test@example.com",
            "public_repos": 10,
        },
        "repositories": [
            {
                "name": "test-repo-1",
                "full_name": "test_user/test-repo-1",
                "clone_url": "https://github.com/test_user/test-repo-1.git",
                "ssh_url": "git@github.com:test_user/test-repo-1.git",
                "description": "テストリポジトリ1",
                "private": False,
                "default_branch": "main",
            },
            {
                "name": "test-repo-2",
                "full_name": "test_user/test-repo-2",
                "clone_url": "https://github.com/test_user/test-repo-2.git",
                "ssh_url": "git@github.com:test_user/test-repo-2.git",
                "description": "テストリポジトリ2",
                "private": True,
                "default_branch": "develop",
            },
        ],
    }


def is_platform_available(platform_name: str) -> bool:
    """指定されたプラットフォームが利用可能かチェック"""
    current_platform = platform.system().lower()

    platform_mapping = {
        "windows": "windows",
        "linux": "linux",
        "darwin": "macos",
        "macos": "darwin",
    }

    expected_platform = platform_mapping.get(platform_name.lower(), platform_name.lower())
    return current_platform == expected_platform or current_platform in expected_platform


def skip_if_not_platform(platform_name: str):
    """指定されたプラットフォームでない場合はスキップするデコレータ"""
    return pytest.mark.skipif(not is_platform_available(platform_name), reason=f"{platform_name}環境でのみ実行")


def skip_if_no_network():
    """ネットワーク接続がない場合はスキップするデコレータ"""
    return pytest.mark.skipif(
        not os.environ.get("NETWORK_TESTS"), reason="ネットワークテストは明示的に有効化された場合のみ実行"
    )


def skip_if_not_ci():
    """CI環境でない場合はスキップするデコレータ"""
    return pytest.mark.skipif(not os.environ.get("CI"), reason="CI環境でのみ実行")


# プラットフォーム固有のスキップ条件
skip_on_windows = pytest.mark.skipif(platform.system() == "Windows", reason="Windows環境では実行しない")

skip_on_unix = pytest.mark.skipif(platform.system() != "Windows", reason="Unix系環境では実行しない")

skip_on_macos = pytest.mark.skipif(platform.system() == "Darwin", reason="macOS環境では実行しない")

# CI環境固有のスキップ条件
skip_if_not_github_actions = pytest.mark.skipif(
    not os.environ.get("GITHUB_ACTIONS"), reason="GitHub Actions環境でのみ実行"
)

# パフォーマンステスト用のスキップ条件
skip_slow_tests = pytest.mark.skipif(
    not os.environ.get("RUN_SLOW_TESTS"), reason="低速テストは明示的に有効化された場合のみ実行"
)
