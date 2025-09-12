"""
テスト共通設定とフィクスチャ

このモジュールは全テストで共有される設定とフィクスチャを提供します。
"""

import os
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """一時ディレクトリを作成するフィクスチャ"""
    with tempfile.TemporaryDirectory() as temp_dir_str:
        yield Path(temp_dir_str)


@pytest.fixture
def mock_env() -> Generator[dict[str, str], None, None]:
    """環境変数をモックするフィクスチャ"""
    original_env = os.environ.copy()
    try:
        os.environ.clear()
        yield os.environ
    finally:
        os.environ.clear()
        os.environ.update(original_env)


class PlatformMocker:
    """プラットフォーム固有の動作をモックするためのヘルパークラス"""

    # サポートされているプラットフォーム
    SUPPORTED_PLATFORMS = ["windows", "linux", "macos", "wsl"]

    # プラットフォーム固有の設定
    PLATFORM_CONFIGS = {
        "windows": {
            "system": "Windows",
            "os_name": "nt",
            "release": "10.0.19041",
            "fcntl_available": False,
            "msvcrt_available": True,
            "path_separator": "\\",
            "proc_version_exists": False,
        },
        "linux": {
            "system": "Linux",
            "os_name": "posix",
            "release": "5.4.0-generic",
            "fcntl_available": True,
            "msvcrt_available": False,
            "path_separator": "/",
            "proc_version_exists": False,
        },
        "macos": {
            "system": "Darwin",
            "os_name": "posix",
            "release": "21.0.0",
            "fcntl_available": True,
            "msvcrt_available": False,
            "path_separator": "/",
            "proc_version_exists": False,
        },
        "wsl": {
            "system": "Linux",
            "os_name": "posix",
            "release": "5.4.0-microsoft-standard-WSL2",
            "fcntl_available": True,
            "msvcrt_available": False,
            "path_separator": "/",
            "proc_version_exists": True,
        },
    }

    def __init__(self, platform: str):
        """
        プラットフォームモッカーを初期化

        Args:
            platform: モックするプラットフォーム名
        """
        if platform not in self.SUPPORTED_PLATFORMS:
            raise ValueError(f"Unsupported platform: {platform}. Supported: {self.SUPPORTED_PLATFORMS}")

        self.platform = platform
        self.config = self.PLATFORM_CONFIGS[platform]
        self.patches = []

    def __enter__(self):
        """コンテキストマネージャーの開始"""
        # platform.system()のモック
        system_patch = patch("platform.system", return_value=self.config["system"])
        self.patches.append(system_patch)
        system_patch.start()

        # platform.release()のモック
        release_patch = patch("platform.release", return_value=self.config["release"])
        self.patches.append(release_patch)
        release_patch.start()

        # os.nameのモック（Windowsの場合はパスライブラリの問題を回避）
        if self.platform != "windows":
            os_name_patch = patch("os.name", self.config["os_name"])
            self.patches.append(os_name_patch)
            os_name_patch.start()

        # モジュール可用性フラグのモック
        fcntl_patch = patch("src.setup_repo.utils.FCNTL_AVAILABLE", self.config["fcntl_available"])
        self.patches.append(fcntl_patch)
        fcntl_patch.start()

        msvcrt_patch = patch("src.setup_repo.utils.MSVCRT_AVAILABLE", self.config["msvcrt_available"])
        self.patches.append(msvcrt_patch)
        msvcrt_patch.start()

        # /proc/versionファイルの存在をモック
        proc_version_exists = self.config.get("proc_version_exists", False)
        if proc_version_exists:
            # WSLの場合、/proc/versionファイルが存在し、適切な内容を返すようにモック
            proc_version_content = (
                "Linux version 5.4.0-microsoft-standard-WSL2 (Microsoft) #1 SMP Wed Mar 2 00:56:28 UTC 2021"
            )

            # 元のopen関数を保存
            original_open = open

            def mock_open_proc_version(*args, **kwargs):
                if args and args[0] == "/proc/version":
                    from io import StringIO

                    return StringIO(proc_version_content)
                # 他のファイルは元のopen関数で開く
                return original_open(*args, **kwargs)

            open_patch = patch("builtins.open", side_effect=mock_open_proc_version)
            self.patches.append(open_patch)
            open_patch.start()

            # 元のos.path.exists関数を保存
            original_exists = os.path.exists

            exists_patch = patch(
                "os.path.exists",
                side_effect=lambda path: (path == "/proc/version" or original_exists(path)),
            )
            self.patches.append(exists_patch)
            exists_patch.start()
        else:
            # Linuxの場合、/proc/versionファイルが存在しないか、
            # microsoftが含まれない内容にする
            # 元のos.path.exists関数を保存
            original_exists = os.path.exists

            exists_patch = patch(
                "os.path.exists",
                side_effect=lambda path: (False if path == "/proc/version" else original_exists(path)),
            )
            self.patches.append(exists_patch)
            exists_patch.start()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャーの終了"""
        for patch_obj in reversed(self.patches):
            patch_obj.stop()
        self.patches.clear()

    def get_expected_lock_implementation_type(self) -> str:
        """期待されるロック実装タイプを取得"""
        if self.platform == "windows":
            return "WindowsLockImplementation"
        elif self.platform in ["linux", "macos", "wsl"]:
            return "UnixLockImplementation"
        else:
            return "FallbackLockImplementation"

    def is_unix_like(self) -> bool:
        """Unix系プラットフォームかどうかを判定"""
        return self.platform in ["linux", "macos", "wsl"]

    def supports_fcntl(self) -> bool:
        """fcntlモジュールをサポートするかどうかを判定"""
        return self.config["fcntl_available"]

    def supports_msvcrt(self) -> bool:
        """msvcrtモジュールをサポートするかどうかを判定"""
        return self.config["msvcrt_available"]


@pytest.fixture
def platform_mocker():
    """プラットフォームモッカーのファクトリフィクスチャ"""

    def _create_mocker(platform: str) -> PlatformMocker:
        return PlatformMocker(platform)

    return _create_mocker


class ModuleAvailabilityMocker:
    """モジュール可用性をモックするためのヘルパークラス"""

    def __init__(self, fcntl_available: bool = True, msvcrt_available: bool = True):
        """
        モジュール可用性モッカーを初期化

        Args:
            fcntl_available: fcntlモジュールが利用可能かどうか
            msvcrt_available: msvcrtモジュールが利用可能かどうか
        """
        self.fcntl_available = fcntl_available
        self.msvcrt_available = msvcrt_available
        self.patches = []

    def __enter__(self):
        """コンテキストマネージャーの開始"""
        # モジュール可用性フラグのモック
        fcntl_patch = patch("src.setup_repo.utils.FCNTL_AVAILABLE", self.fcntl_available)
        self.patches.append(fcntl_patch)
        fcntl_patch.start()

        msvcrt_patch = patch("src.setup_repo.utils.MSVCRT_AVAILABLE", self.msvcrt_available)
        self.patches.append(msvcrt_patch)
        msvcrt_patch.start()

        # 実際のモジュールインポートのモック（必要に応じて）
        if not self.fcntl_available:
            # fcntlモジュールが利用できない場合のモック
            fcntl_import_patch = patch.dict("sys.modules", {"fcntl": None})
            self.patches.append(fcntl_import_patch)
            fcntl_import_patch.start()

        if not self.msvcrt_available:
            # msvcrtモジュールが利用できない場合のモック
            msvcrt_import_patch = patch.dict("sys.modules", {"msvcrt": None})
            self.patches.append(msvcrt_import_patch)
            msvcrt_import_patch.start()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャーの終了"""
        for patch_obj in reversed(self.patches):
            patch_obj.stop()
        self.patches.clear()


@pytest.fixture
def module_availability_mocker():
    """モジュール可用性モッカーのファクトリフィクスチャ"""

    def _create_mocker(fcntl_available: bool = True, msvcrt_available: bool = True) -> ModuleAvailabilityMocker:
        return ModuleAvailabilityMocker(fcntl_available, msvcrt_available)

    return _create_mocker


class CrossPlatformTestHelper:
    """クロスプラットフォームテストを支援するヘルパークラス"""

    @staticmethod
    def run_on_all_platforms(test_func, platform_mocker_factory, *args, **kwargs):
        """
        全プラットフォームでテスト関数を実行

        Args:
            test_func: 実行するテスト関数
            platform_mocker_factory: プラットフォームモッカーファクトリ
            *args: テスト関数に渡す引数
            **kwargs: テスト関数に渡すキーワード引数
        """
        results = {}
        for platform in PlatformMocker.SUPPORTED_PLATFORMS:
            with platform_mocker_factory(platform):
                try:
                    result = test_func(platform, *args, **kwargs)
                    results[platform] = {"success": True, "result": result}
                except Exception as e:
                    results[platform] = {"success": False, "error": str(e)}
        return results

    @staticmethod
    def assert_consistent_behavior(results: dict[str, dict[str, Any]], expected_behavior: str = "success"):
        """
        全プラットフォームで一貫した動作を確認

        Args:
            results: run_on_all_platformsの結果
            expected_behavior: 期待される動作（"success" または "failure"）
        """
        for platform, result in results.items():
            if expected_behavior == "success":
                assert result["success"], f"Platform {platform} failed: {result.get('error', 'Unknown error')}"
            elif expected_behavior == "failure":
                assert not result["success"], f"Platform {platform} should have failed but succeeded"


@pytest.fixture
def cross_platform_helper():
    """クロスプラットフォームテストヘルパーのフィクスチャ"""
    return CrossPlatformTestHelper()


# プラットフォーム固有のテストマーカー
pytest.mark.windows = pytest.mark.parametrize("platform", ["windows"])
pytest.mark.linux = pytest.mark.parametrize("platform", ["linux"])
pytest.mark.macos = pytest.mark.parametrize("platform", ["macos"])
pytest.mark.wsl = pytest.mark.parametrize("platform", ["wsl"])
pytest.mark.unix_like = pytest.mark.parametrize("platform", ["linux", "macos", "wsl"])
pytest.mark.all_platforms = pytest.mark.parametrize("platform", PlatformMocker.SUPPORTED_PLATFORMS)


# テスト環境の設定
def pytest_configure(config):
    """pytest設定の初期化"""
    # カスタムマーカーの登録
    config.addinivalue_line("markers", "unit: 単体テスト")
    config.addinivalue_line("markers", "integration: 統合テスト")
    config.addinivalue_line("markers", "cross_platform: クロスプラットフォームテスト")
    config.addinivalue_line("markers", "windows: Windows固有テスト")
    config.addinivalue_line("markers", "linux: Linux固有テスト")
    config.addinivalue_line("markers", "macos: macOS固有テスト")
    config.addinivalue_line("markers", "wsl: WSL固有テスト")
    config.addinivalue_line("markers", "unix_like: Unix系プラットフォームテスト")
    config.addinivalue_line("markers", "all_platforms: 全プラットフォームテスト")


# 統合テスト用フィクスチャ
@pytest.fixture
def sample_config() -> dict[str, Any]:
    """統合テスト用のサンプル設定（後方互換性を維持）"""
    return {
        # 新しい構造
        "github": {"username": "test_user", "token": "test_token_123"},
        "repositories": {
            "base_path": "/tmp/test_repos",
            "include_forks": False,
            "include_private": True,
        },
        "platform": {"detected": "linux", "package_manager": "apt"},
        "logging": {"level": "INFO", "file": "/tmp/test.log"},
        # 後方互換性のための古い構造
        "github_token": "test_token_123",
        "github_username": "test_user",
        "clone_destination": "/tmp/test_repos",
        "owner": "test_user",
        "dest": "/tmp/test_repos",
    }


@pytest.fixture
def config_file(temp_dir: Path, sample_config: dict[str, Any]) -> Path:
    """設定ファイルのフィクスチャ"""
    import json

    config_path = temp_dir / "config.json"
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(sample_config, f, indent=2)
    return config_path


@pytest.fixture
def mock_github_api():
    """GitHub APIのモックフィクスチャ"""
    mock_api = MagicMock()

    # ユーザー情報のモック
    mock_api.get_user_info.return_value = {
        "login": "test_user",
        "name": "Test User",
        "public_repos": 10,
        "private_repos": 5,
    }

    # リポジトリ一覧のモック
    mock_api.get_user_repos.return_value = [
        {
            "name": "test-repo-1",
            "full_name": "test_user/test-repo-1",
            "clone_url": "https://github.com/test_user/test-repo-1.git",
            "private": False,
            "fork": False,
        },
        {
            "name": "test-repo-2",
            "full_name": "test_user/test-repo-2",
            "clone_url": "https://github.com/test_user/test-repo-2.git",
            "private": True,
            "fork": False,
        },
    ]

    return mock_api


@pytest.fixture
def mock_git_operations():
    """Git操作のモックフィクスチャ"""
    mock_git = MagicMock()

    # Git操作の成功を模擬
    mock_git.clone_repository.return_value = True
    mock_git.pull_repository.return_value = True
    mock_git.get_repository_status.return_value = {
        "clean": True,
        "ahead": 0,
        "behind": 0,
    }

    return mock_git


@pytest.fixture
def mock_platform_detector():
    """プラットフォーム検出のモックフィクスチャ"""
    mock_detector = MagicMock()
    mock_detector.detect_platform.return_value = "linux"
    mock_detector.get_package_manager.return_value = "apt"
    return mock_detector


@pytest.fixture
def mock_subprocess():
    """subprocessのモックフィクスチャ"""
    with patch("subprocess.run") as mock_run, patch("subprocess.Popen") as mock_popen:
        # 成功ケースのデフォルト設定
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="success",
            stderr="",
        )
        mock_popen.return_value = MagicMock(
            returncode=0,
            communicate=lambda: ("success", ""),
        )
        yield {"run": mock_run, "popen": mock_popen}


@pytest.fixture
def test_lock():
    """テスト用の一意なプロセスロックフィクスチャ"""
    import uuid

    from src.setup_repo.utils import ProcessLock

    # テスト用の一意なロックファイルを作成
    test_id = uuid.uuid4().hex[:8]
    lock = ProcessLock.create_test_lock(f"pytest-{test_id}")

    yield lock

    # テスト後のクリーンアップ
    try:
        if lock.lock_fd is not None:
            lock.release()
        if lock.lock_file.exists():
            lock.lock_file.unlink()
    except Exception as e:
        # クリーンアップエラーをログに記録
        import logging

        logging.getLogger(__name__).warning(f"テストロッククリーンアップエラー: {e}")


# テスト実行前の環境クリーンアップ
@pytest.fixture(autouse=True)
def clean_test_environment():
    """テスト実行前後の環境クリーンアップ"""
    # テスト実行前のクリーンアップ
    yield
    # テスト実行後のクリーンアップ（必要に応じて）
