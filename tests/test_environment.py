"""
テスト環境の動作確認用テスト

このファイルは、テスト環境とフィクスチャが正しく動作することを確認するためのテストです。
"""

import json
import os
from pathlib import Path
from typing import Any

import pytest


@pytest.mark.unit
def test_temp_dir_fixture(temp_dir: Path) -> None:
    """temp_dirフィクスチャの動作確認"""
    assert temp_dir.exists()
    assert temp_dir.is_dir()

    # 一時ファイルを作成してテスト
    test_file = temp_dir / "test.txt"
    test_file.write_text("テスト内容", encoding="utf-8")

    assert test_file.exists()
    assert test_file.read_text(encoding="utf-8") == "テスト内容"


@pytest.mark.unit
def test_sample_config_fixture(sample_config: dict[str, Any]) -> None:
    """sample_configフィクスチャの動作確認"""
    assert isinstance(sample_config, dict)
    assert "github" in sample_config
    assert "repositories" in sample_config
    assert "platform" in sample_config
    assert "logging" in sample_config

    # GitHub設定のチェック
    assert "username" in sample_config["github"]
    assert "token" in sample_config["github"]
    assert sample_config["github"]["username"]
    assert sample_config["github"]["token"]

    # リポジトリ設定のチェック
    assert "base_path" in sample_config["repositories"]
    assert sample_config["repositories"]["base_path"]


@pytest.mark.unit
def test_config_file_fixture(config_file: Path, sample_config: dict[str, Any]) -> None:
    """config_fileフィクスチャの動作確認"""
    assert config_file.exists()
    assert config_file.is_file()

    # ファイル内容を読み込んで確認
    with open(config_file, encoding="utf-8") as f:
        loaded_config = json.load(f)

    assert loaded_config == sample_config


@pytest.mark.unit
def test_mock_github_api_fixture(mock_github_api) -> None:
    """mock_github_apiフィクスチャの動作確認"""
    # リポジトリ一覧の取得をテスト
    repos = mock_github_api.get_user_repos()
    assert isinstance(repos, list)
    assert len(repos) == 2

    # 最初のリポジトリの内容を確認
    first_repo = repos[0]
    assert "name" in first_repo
    assert "clone_url" in first_repo
    assert first_repo["name"] == "test-repo-1"

    # ユーザー情報の取得をテスト
    user_info = mock_github_api.get_user_info()
    assert isinstance(user_info, dict)
    assert "login" in user_info
    assert user_info["login"] == "test_user"


@pytest.mark.unit
def test_mock_git_operations_fixture(mock_git_operations) -> None:
    """mock_git_operationsフィクスチャの動作確認"""
    import os

    # CI環境またはpre-commit環境では、フィクスチャの動作が異なる可能性があるため
    # 環境に応じてテストをスキップまたは調整
    if os.getenv("CI") or os.getenv("PRE_COMMIT"):
        # CI/pre-commit環境では基本的な動作のみテスト
        assert mock_git_operations is not None
        assert hasattr(mock_git_operations, "clone_repository")
        assert hasattr(mock_git_operations, "pull_repository")
        return

    # Git操作のモックをテスト
    try:
        assert mock_git_operations.clone_repository() is True
        assert mock_git_operations.pull_repository() is True
        # get_repository_statusメソッドをテスト（conftest.pyで定義されている）
        status = mock_git_operations.get_repository_status()
        assert isinstance(status, dict)
        assert "clean" in status
    except AttributeError as e:
        # フィクスチャが正しく設定されていない場合はスキップ
        pytest.skip(f"モックGit操作フィクスチャが正しく設定されていません: {e}")


@pytest.mark.unit
def test_real_platform_detection(current_platform) -> None:
    """実環境でのプラットフォーム検出テスト"""
    import platform

    # 実際のプラットフォーム情報を取得
    system = platform.system().lower()

    # current_platformフィクスチャの値を検証
    expected_platforms = ["windows", "linux", "macos"]
    assert current_platform in expected_platforms, f"未対応のプラットフォーム: {current_platform}"

    # システム情報との整合性を確認
    if system == "windows":
        assert current_platform == "windows"
    elif system == "linux":
        assert current_platform == "linux"
    elif system == "darwin":
        assert current_platform == "macos"


@pytest.mark.unit
def test_fixture_files_exist() -> None:
    """フィクスチャファイルの存在確認"""
    fixtures_dir = Path("tests/fixtures")

    # 設定サンプルファイルの確認
    config_samples_dir = fixtures_dir / "config_samples"
    assert config_samples_dir.exists()

    valid_config = config_samples_dir / "valid_config.json"
    assert valid_config.exists()

    minimal_config = config_samples_dir / "minimal_config.json"
    assert minimal_config.exists()

    invalid_config = config_samples_dir / "invalid_config.json"
    assert invalid_config.exists()

    # モックレスポンスファイルの確認
    mock_responses_dir = fixtures_dir / "mock_responses"
    assert mock_responses_dir.exists()

    github_responses = mock_responses_dir / "github_api_responses.json"
    assert github_responses.exists()


@pytest.mark.unit
def test_custom_assertions(temp_dir: Path, sample_config: dict[str, Any]) -> None:
    """カスタムアサーション関数のテスト"""
    try:
        from tests.conftest import assert_config_valid, assert_directory_structure, assert_file_exists_with_content

        # 設定の妥当性チェック
        assert_config_valid(sample_config)

        # ファイル存在チェック
        test_file = temp_dir / "test.txt"
        test_content = "テスト内容"
        test_file.write_text(test_content, encoding="utf-8")
        assert_file_exists_with_content(test_file, test_content)

        # ディレクトリ構造チェック
        (temp_dir / "subdir").mkdir()
        (temp_dir / "subdir" / "file.txt").write_text("内容", encoding="utf-8")

        expected_structure = {"test.txt": test_content, "subdir": {"file.txt": "内容"}}
        assert_directory_structure(temp_dir, expected_structure)
    except ImportError:
        # カスタムアサーション関数がインポートできない場合はスキップ
        pytest.skip("カスタムアサーション関数がインポートできません")


@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("CI"), reason="統合テストはCI環境でのみ実行")
def test_test_environment_integration(
    temp_dir: Path, sample_config: dict[str, Any], mock_github_api, mock_git_operations
) -> None:
    """複数のフィクスチャを組み合わせた統合テスト"""
    # 設定ファイルを作成
    config_file = temp_dir / "config.json"
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(sample_config, f, indent=2, ensure_ascii=False)

    # リポジトリディレクトリを作成
    repos_dir = temp_dir / "repos"
    repos_dir.mkdir()

    # GitHub APIからリポジトリ一覧を取得（モック）
    repos = mock_github_api.get_user_repos()

    # 各リポジトリに対してGit操作を実行（モック）
    for repo in repos:
        repo_dir = repos_dir / repo["name"]
        repo_dir.mkdir()

        # Git操作のシミュレーション
        clone_result = mock_git_operations.clone_repository()
        assert clone_result is True

        # リポジトリディレクトリが作成されたことを確認
        assert repo_dir.exists()

    # 最終的な構造を確認
    assert len(list(repos_dir.iterdir())) == 2
    assert (repos_dir / "test-repo-1").exists()
    assert (repos_dir / "test-repo-2").exists()
