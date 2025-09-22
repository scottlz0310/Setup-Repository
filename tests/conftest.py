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
    """統合テスト用のサンプル設定"""
    return {
        # setup.pyが期待するフラット構造のフィールド
        "github_token": "test_token_123",
        "github_username": "test_user",
        "clone_destination": "/tmp/test_repos",
        # 階層構造も維持（後方互換性のため）
        "github": {"username": "test_user", "token": "test_token_123"},
        "repositories": {
            "base_path": "/tmp/test_repos",
            "include_forks": False,
            "include_private": True,
        },
        "platform": {"detected": "linux", "package_manager": "apt"},
        "logging": {"level": "INFO", "file": "/tmp/test.log"},
    }


@pytest.fixture
def config_file(temp_dir: Path, sample_config: dict[str, Any]) -> Path:
    """設定ファイルフィクスチャ"""
    import json

    config_file_path = temp_dir / "config.json"
    with open(config_file_path, "w", encoding="utf-8") as f:
        json.dump(sample_config, f, indent=2, ensure_ascii=False)
    return config_file_path


@pytest.fixture
def mock_github_api():
    """GitHub APIモックフィクスチャ"""
    from unittest.mock import Mock

    mock = Mock()
    mock.get_user_repos.return_value = [
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
            "private": False,
            "default_branch": "main",
        },
    ]
    mock.get_user_info.return_value = {"login": "test_user"}

    return mock


@pytest.fixture
def mock_git_operations():
    """Git操作モックフィクスチャ"""
    from unittest.mock import Mock

    mock = Mock()
    mock.clone_repository.return_value = True
    mock.pull_repository.return_value = True
    mock.get_repository_status.return_value = {"clean": True}
    mock.is_git_repository.return_value = True

    return mock


# mock_platform_detectorフィクスチャを削除 - ルールに従い実環境でのテストのみ実行
# プラットフォーム依存のテストは実環境で実行し、合わない場合はスキップする


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
    # ネットワークテストのスキップ処理（明示的に有効化された場合のみ実行）
    if not os.environ.get("NETWORK_TESTS"):
        skip_network = pytest.mark.skip(reason="ネットワークテストは明示的に有効化された場合のみ実行")
        for item in items:
            if "network" in item.keywords:
                item.add_marker(skip_network)


@pytest.fixture
def setup_test_environment():
    """テスト環境のセットアップ（必要な場合のみ使用）"""
    # テスト実行前の処理

    # テスト用環境変数を設定
    test_env = {
        "PYTEST_RUNNING": "true",
        "LOG_LEVEL": "ERROR",  # DEBUGからERRORに変更して高速化
    }

    for key, value in test_env.items():
        os.environ[key] = value

    yield

    # テスト実行後のクリーンアップ
    for key in test_env:
        os.environ.pop(key, None)


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


@pytest.fixture
def current_platform():
    """現在のプラットフォーム名フィクスチャ"""
    current = platform.system().lower()
    platform_mapping = {
        "windows": "windows",
        "linux": "linux",
        "darwin": "macos",
    }
    return platform_mapping.get(current, "unknown")


# プラットフォームモッカーは削除 - 実環境でのテストのみ実行


# モジュール可用性モッカーは削除 - 実環境でのテストのみ実行


@pytest.fixture
def cross_platform_helper():
    """クロスプラットフォームヘルパーフィクスチャ"""

    class CrossPlatformHelper:
        def get_platform_specific_path(self, platform_name: str, base_path: str) -> str:
            if platform_name == "windows":
                return base_path.replace("/", "\\")
            return base_path

        def get_platform_specific_command(self, platform_name: str, command: str) -> str:
            if platform_name == "windows":
                return f"{command}.exe"
            return command

        def run_on_current_platform_only(self, test_function):
            """現在のプラットフォームでのみテスト関数を実行"""
            current_platform = platform.system().lower()
            platform_mapping = {
                "windows": "windows",
                "linux": "linux",
                "darwin": "macos",
            }
            platform_name = platform_mapping.get(current_platform, "unknown")

            try:
                result = test_function(platform_name)
                return {platform_name: {"success": True, "result": result}}
            except Exception as e:
                return {platform_name: {"success": False, "error": str(e)}}

        def assert_consistent_behavior(self, results, expected_status="success"):
            """一貫した動作をアサート"""
            for platform_name, result in results.items():
                if expected_status == "success":
                    assert result["success"], f"{platform_name}でテストが失敗: {result.get('error', 'Unknown error')}"
                elif expected_status == "failure":
                    assert not result["success"], f"{platform_name}でテストが成功してしまいました"

    return CrossPlatformHelper()


# カスタムアサーション関数
def assert_config_valid(config: dict[str, Any]) -> None:
    """設定の妥当性をチェック"""
    # 階層構造の設定をチェック
    assert "github" in config, "必須キー 'github' が設定にありません"
    assert "token" in config["github"], "必須キー 'github.token' が設定にありません"
    assert "username" in config["github"], "必須キー 'github.username' が設定にありません"
    assert "repositories" in config, "必須キー 'repositories' が設定にありません"
    assert "base_path" in config["repositories"], "必須キー 'repositories.base_path' が設定にありません"

    # 値の存在チェック
    assert config["github"]["token"], "キー 'github.token' の値が空です"
    assert config["github"]["username"], "キー 'github.username' の値が空です"
    assert config["repositories"]["base_path"], "キー 'repositories.base_path' の値が空です"


def assert_file_exists_with_content(file_path: Path, expected_content: str) -> None:
    """ファイルの存在と内容をチェック"""
    assert file_path.exists(), f"ファイル {file_path} が存在しません"
    actual_content = file_path.read_text(encoding="utf-8")
    assert actual_content == expected_content, (
        f"ファイル内容が一致しません。期待値: {expected_content}, 実際: {actual_content}"
    )


def assert_directory_structure(base_dir: Path, expected_structure: dict[str, Any]) -> None:
    """ディレクトリ構造をチェック"""
    for name, content in expected_structure.items():
        path = base_dir / name
        assert path.exists(), f"パス {path} が存在しません"

        if isinstance(content, dict):
            # サブディレクトリの場合
            assert path.is_dir(), f"{path} はディレクトリではありません"
            assert_directory_structure(path, content)
        else:
            # ファイルの場合
            assert path.is_file(), f"{path} はファイルではありません"
            actual_content = path.read_text(encoding="utf-8")
            assert actual_content == content, f"ファイル {path} の内容が一致しません"
