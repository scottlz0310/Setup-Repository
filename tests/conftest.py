"""
プロジェクト共通のpytestフィクスチャとテスト設定

このファイルには、全テストで共通して使用されるフィクスチャと
テスト環境の設定を定義します。
"""

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Generator
from unittest.mock import Mock, patch

import pytest


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """一時ディレクトリを作成するフィクスチャ"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def temp_config_dir(temp_dir: Path) -> Path:
    """一時的な設定ディレクトリを作成するフィクスチャ"""
    config_dir = temp_dir / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


@pytest.fixture
def sample_config() -> Dict[str, Any]:
    """サンプル設定データを提供するフィクスチャ"""
    return {
        "github_token": "test_token_12345",
        "github_username": "test_user",
        "clone_destination": "/tmp/test_repos",
        "auto_install_dependencies": True,
        "setup_vscode": True,
        "platform_specific_setup": True,
        "dry_run": False,
        "verbose": True
    }


@pytest.fixture
def config_file(temp_config_dir: Path, sample_config: Dict[str, Any]) -> Path:
    """一時的な設定ファイルを作成するフィクスチャ"""
    config_file = temp_config_dir / "config.local.json"
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(sample_config, f, indent=2, ensure_ascii=False)
    return config_file


@pytest.fixture
def mock_github_api() -> Mock:
    """GitHub APIのモックを提供するフィクスチャ"""
    mock = Mock()
    
    # サンプルリポジトリデータ
    mock.get_user_repos.return_value = [
        {
            "name": "test-repo-1",
            "clone_url": "https://github.com/test_user/test-repo-1.git",
            "description": "テストリポジトリ1",
            "private": False,
            "default_branch": "main"
        },
        {
            "name": "test-repo-2", 
            "clone_url": "https://github.com/test_user/test-repo-2.git",
            "description": "テストリポジトリ2",
            "private": True,
            "default_branch": "master"
        }
    ]
    
    mock.get_user_info.return_value = {
        "login": "test_user",
        "name": "Test User",
        "email": "test@example.com"
    }
    
    return mock


@pytest.fixture
def mock_git_operations() -> Mock:
    """Git操作のモックを提供するフィクスチャ"""
    mock = Mock()
    
    # 成功時の戻り値を設定
    mock.clone_repository.return_value = True
    mock.pull_repository.return_value = True
    mock.is_git_repository.return_value = True
    mock.get_current_branch.return_value = "main"
    mock.get_remote_url.return_value = "https://github.com/test_user/test-repo.git"
    
    return mock


@pytest.fixture
def mock_platform_detector() -> Mock:
    """プラットフォーム検出のモックを提供するフィクスチャ"""
    mock = Mock()
    
    # デフォルトでLinuxプラットフォームを返す
    mock.detect_platform.return_value = "linux"
    mock.is_wsl.return_value = False
    mock.get_package_manager.return_value = "apt"
    
    return mock


@pytest.fixture
def mock_subprocess() -> Generator[Mock, None, None]:
    """subprocessモジュールのモックを提供するフィクスチャ"""
    with patch("subprocess.run") as mock_run:
        # 成功時の戻り値を設定
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "success"
        mock_run.return_value.stderr = ""
        yield mock_run


@pytest.fixture
def mock_file_system(temp_dir: Path) -> Generator[Path, None, None]:
    """ファイルシステム操作用の一時ディレクトリを提供するフィクスチャ"""
    # テスト用のディレクトリ構造を作成
    test_repo_dir = temp_dir / "repos"
    test_repo_dir.mkdir(parents=True, exist_ok=True)
    
    # サンプルリポジトリディレクトリを作成
    (test_repo_dir / "test-repo-1").mkdir()
    (test_repo_dir / "test-repo-2").mkdir()
    
    yield test_repo_dir


@pytest.fixture
def mock_environment_variables() -> Generator[None, None, None]:
    """環境変数のモックを提供するフィクスチャ"""
    original_env = os.environ.copy()
    
    # テスト用環境変数を設定
    test_env = {
        "GITHUB_TOKEN": "test_env_token",
        "GITHUB_USERNAME": "test_env_user",
        "HOME": "/tmp/test_home",
        "USERPROFILE": "C:\\Users\\TestUser"  # Windows用
    }
    
    os.environ.update(test_env)
    
    try:
        yield
    finally:
        # 元の環境変数を復元
        os.environ.clear()
        os.environ.update(original_env)


@pytest.fixture
def capture_logs(caplog: pytest.LogCaptureFixture) -> pytest.LogCaptureFixture:
    """ログキャプチャを設定するフィクスチャ"""
    caplog.set_level("DEBUG")
    return caplog


# テストマーカーの設定
def pytest_configure(config: pytest.Config) -> None:
    """pytestの設定を行う"""
    config.addinivalue_line(
        "markers", "unit: 単体テストのマーカー"
    )
    config.addinivalue_line(
        "markers", "integration: 統合テストのマーカー"
    )
    config.addinivalue_line(
        "markers", "slow: 実行時間の長いテストのマーカー"
    )


# テスト実行前の共通セットアップ
@pytest.fixture(autouse=True)
def setup_test_environment() -> Generator[None, None, None]:
    """各テスト実行前の共通セットアップ"""
    # テスト開始前の処理
    original_cwd = os.getcwd()
    
    try:
        yield
    finally:
        # テスト終了後のクリーンアップ
        os.chdir(original_cwd)


# カスタムアサーション関数
def assert_config_valid(config: Dict[str, Any]) -> None:
    """設定データの妥当性をチェックするアサーション関数"""
    required_keys = ["github_token", "github_username", "clone_destination"]
    
    for key in required_keys:
        assert key in config, f"必須キー '{key}' が設定に含まれていません"
        assert config[key], f"キー '{key}' の値が空です"


def assert_file_exists_with_content(file_path: Path, expected_content: str = None) -> None:
    """ファイルの存在と内容をチェックするアサーション関数"""
    assert file_path.exists(), f"ファイル {file_path} が存在しません"
    assert file_path.is_file(), f"{file_path} はファイルではありません"
    
    if expected_content is not None:
        actual_content = file_path.read_text(encoding="utf-8")
        assert expected_content in actual_content, f"期待する内容がファイルに含まれていません"


def assert_directory_structure(base_dir: Path, expected_structure: Dict[str, Any]) -> None:
    """ディレクトリ構造をチェックするアサーション関数"""
    for name, content in expected_structure.items():
        path = base_dir / name
        
        if isinstance(content, dict):
            assert path.is_dir(), f"ディレクトリ {path} が存在しません"
            assert_directory_structure(path, content)
        else:
            assert path.is_file(), f"ファイル {path} が存在しません"
            if content:  # 内容が指定されている場合
                assert_file_exists_with_content(path, content)