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


@pytest.fixture(params=["windows", "linux", "macos", "wsl"])
def platform(request):
    """プラットフォーム名フィクスチャ"""
    return request.param


@pytest.fixture
def platform_mocker():
    """プラットフォームモッカーフィクスチャ"""
    # CI環境では実際のプラットフォームでのみテストを実行するため、
    # モッカーは無効化する
    is_ci = os.environ.get("CI", "").lower() in ("true", "1")
    is_precommit = os.environ.get("PRE_COMMIT", "").lower() in ("true", "1")

    if is_ci or is_precommit:
        # CI/Pre-commit環境では何もしないダミーコンテキストマネージャーを返す
        return None

    from contextlib import contextmanager
    from unittest.mock import patch

    @contextmanager
    def mock_platform(platform_name: str):
        patches = []
        try:
            if platform_name == "windows":
                patches.append(patch("platform.system", return_value="Windows"))
                patches.append(patch("platform.release", return_value="10"))
                patches.append(patch("os.name", "nt"))
            elif platform_name == "linux":
                patches.append(patch("platform.system", return_value="Linux"))
                patches.append(patch("platform.release", return_value="5.4.0"))
                patches.append(patch("os.name", "posix"))
            elif platform_name == "macos":
                patches.append(patch("platform.system", return_value="Darwin"))
                patches.append(patch("platform.release", return_value="20.6.0"))
                patches.append(patch("os.name", "posix"))
            elif platform_name == "wsl":
                patches.append(patch("platform.system", return_value="Linux"))
                patches.append(patch("platform.release", return_value="5.4.0-microsoft-standard"))
                patches.append(patch("os.name", "posix"))
                patches.append(patch("os.path.exists", return_value=True))

            # パッチを開始
            for p in patches:
                p.start()

            yield type(
                "MockConfig",
                (),
                {
                    "config": {
                        "system": patches[0].return_value if patches else platform_name,
                        "release": patches[1].return_value if len(patches) > 1 else "unknown",
                        "os_name": patches[2].new if len(patches) > 2 else "unknown",
                    },
                    "get_expected_lock_implementation_type": lambda: (
                        "WindowsLockImplementation"
                        if platform_name == "windows"
                        else "UnixLockImplementation"
                        if platform_name in ["linux", "macos", "wsl"]
                        else "FallbackLockImplementation"
                    ),
                    "supports_fcntl": lambda: platform_name in ["linux", "macos", "wsl"],
                    "supports_msvcrt": lambda: platform_name == "windows",
                    "is_unix_like": lambda: platform_name in ["linux", "macos", "wsl"],
                },
            )()

        finally:
            # パッチを停止
            for p in reversed(patches):
                p.stop()

    return mock_platform


@pytest.fixture
def module_availability_mocker():
    """モジュール可用性モッカーフィクスチャ"""
    # CI環境では実際のプラットフォームでのみテストを実行するため、
    # モッカーは無効化する
    is_ci = os.environ.get("CI", "").lower() in ("true", "1")
    is_precommit = os.environ.get("PRE_COMMIT", "").lower() in ("true", "1")

    if is_ci or is_precommit:
        # CI/Pre-commit環境では何もしないダミー関数を返す
        def dummy_mocker(**kwargs):
            from contextlib import nullcontext

            return nullcontext()

        return dummy_mocker

    from contextlib import contextmanager
    from unittest.mock import patch

    @contextmanager
    def mock_module_availability(**kwargs):
        fcntl_available = kwargs.get("fcntl_available", True)
        msvcrt_available = kwargs.get("msvcrt_available", True)

        patches = []
        try:
            # fcntlモジュールの可用性をモック
            if not fcntl_available:

                def mock_fcntl_import(name, *args, **kwargs):
                    if name == "fcntl":
                        raise ImportError("No module named 'fcntl'")
                    return __import__(name, *args, **kwargs)

                patches.append(patch("builtins.__import__", side_effect=mock_fcntl_import))

            # msvcrtモジュールの可用性をモック
            if not msvcrt_available:

                def mock_msvcrt_import(name, *args, **kwargs):
                    if name == "msvcrt":
                        raise ImportError("No module named 'msvcrt'")
                    return __import__(name, *args, **kwargs)

                patches.append(patch("builtins.__import__", side_effect=mock_msvcrt_import))

            # パッチを開始
            for p in patches:
                p.start()

            yield

        finally:
            # パッチを停止
            for p in reversed(patches):
                p.stop()

    return mock_module_availability


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

        def run_on_all_platforms(self, test_function, platform_mocker):
            """全プラットフォームでテスト関数を実行"""
            platforms = ["windows", "linux", "macos", "wsl"]
            results = {}

            # CI環境では実際のプラットフォームでのみテスト
            is_ci = os.environ.get("CI", "").lower() in ("true", "1")
            is_precommit = os.environ.get("PRE_COMMIT", "").lower() in ("true", "1")

            if is_ci or is_precommit:
                current_platform = platform.system().lower()
                if current_platform == "windows":
                    platform_name = "windows"
                elif current_platform == "linux":
                    platform_name = "linux"
                elif current_platform == "darwin":
                    platform_name = "macos"
                else:
                    platform_name = "linux"  # デフォルト

                try:
                    result = test_function(platform_name)
                    results[platform_name] = {"success": True, "result": result}
                except Exception as e:
                    results[platform_name] = {"success": False, "error": str(e)}

                return results

            # 非CI環境では全プラットフォームでテスト
            for platform_name in platforms:
                try:
                    if platform_mocker:
                        with platform_mocker(platform_name):
                            result = test_function(platform_name)
                    else:
                        result = test_function(platform_name)
                    results[platform_name] = {"success": True, "result": result}
                except Exception as e:
                    results[platform_name] = {"success": False, "error": str(e)}

            return results

        def assert_consistent_behavior(self, results, expected_status="success"):
            """一貫した動作をアサート"""
            for platform_name, result in results.items():
                if expected_status == "success":
                    assert result["success"], f"{platform_name}でテストが失敗: {result.get('error', 'Unknown error')}"
                elif expected_status == "failure":
                    assert not result["success"], f"{platform_name}でテストが成功してしまいました"

    return CrossPlatformHelper()
