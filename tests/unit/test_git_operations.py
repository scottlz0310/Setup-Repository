"""
Git操作機能のテスト

マルチプラットフォームテスト方針に準拠したGit操作機能のテスト
"""

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from setup_repo.git_operations import (
    GitOperations,
    choose_clone_url,
    create_git_operations,
    sync_repository,
    sync_repository_with_retries,
)
from tests.multiplatform.helpers import (
    get_platform_specific_config,
    verify_current_platform,
)


class TestGitOperations:
    """Git操作機能のテスト"""

    def test_git_operations_init(self):
        """GitOperationsクラスの初期化テスト"""
        verify_current_platform()  # プラットフォーム検証

        config = {"use_https": False}
        git_ops = GitOperations(config)
        assert git_ops.config == config

    def test_is_git_repository(self):
        """Gitリポジトリ判定テスト"""
        git_ops = GitOperations()

        with tempfile.TemporaryDirectory() as temp_dir:
            # .gitディレクトリを作成
            git_dir = Path(temp_dir) / ".git"
            git_dir.mkdir()

            assert git_ops.is_git_repository(temp_dir) is True

        with tempfile.TemporaryDirectory() as temp_dir:
            assert git_ops.is_git_repository(temp_dir) is False

    def test_clone_repository(self):
        """リポジトリクローンテスト（実環境）"""
        git_ops = GitOperations()

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = Path(temp_dir) / "test_repo"

            # 破壊的操作（実際のクローン）のみモック
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0)
                result = git_ops.clone_repository("https://github.com/test/repo.git", str(dest_path))
                assert result is True
                mock_run.assert_called_once()

            # エラーケースのテスト
            with patch("subprocess.run") as mock_run:
                mock_run.side_effect = subprocess.CalledProcessError(1, "git")
                result = git_ops.clone_repository("https://github.com/test/repo.git", str(dest_path))
                assert result is False

    def test_pull_repository(self):
        """リポジトリプルテスト（実環境）"""
        git_ops = GitOperations()

        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir) / "test_repo"
            repo_path.mkdir()

            # 破壊的操作（実際のプル）のみモック
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0)
                result = git_ops.pull_repository(str(repo_path))
                assert result is True
                mock_run.assert_called_once()

            # エラーケースのテスト
            with patch("subprocess.run") as mock_run:
                mock_run.side_effect = subprocess.CalledProcessError(1, "git")
                result = git_ops.pull_repository(str(repo_path))
                assert result is False

    def test_choose_clone_url_https(self):
        """HTTPS URL選択テスト"""
        repo = {
            "clone_url": "https://github.com/test/repo.git",
            "ssh_url": "git@github.com:test/repo.git",
            "full_name": "test/repo",
        }

        url = choose_clone_url(repo, use_https=True)
        assert url == "https://github.com/test/repo.git"

    def test_choose_clone_url_ssh(self):
        """SSH URL選択テスト（実環境）"""
        repo = {
            "clone_url": "https://github.com/test/repo.git",
            "ssh_url": "git@github.com:test/repo.git",
            "full_name": "test/repo",
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            # 実際のSSHキーファイルを作成
            ssh_key_path = Path(temp_dir) / ".ssh" / "id_rsa"
            ssh_key_path.parent.mkdir(parents=True)
            ssh_key_path.write_text("dummy ssh key")

            # 外部コマンドのみモック
            with (
                patch("pathlib.Path.exists", return_value=True),
                patch("subprocess.run") as mock_run,
            ):
                mock_run.return_value = Mock(returncode=1)
                url = choose_clone_url(repo, use_https=False)
                assert url == "git@github.com:test/repo.git"

    def test_sync_repository(self):
        """リポジトリ同期テスト"""
        repo = {"name": "test-repo"}

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_dir = Path(temp_dir)

            with patch("setup_repo.git_operations._sync_repository_once") as mock_sync:
                mock_sync.return_value = True

                result = sync_repository(repo, dest_dir, dry_run=False)
                assert result is True

    def test_sync_repository_with_retries(self):
        """リトライ付きリポジトリ同期テスト"""
        repo = {"name": "test-repo"}
        config = {"max_retries": 2, "dry_run": False}

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_dir = Path(temp_dir)

            with patch("setup_repo.git_operations._sync_repository_once") as mock_sync, patch("builtins.print"):
                mock_sync.return_value = True

                result = sync_repository_with_retries(repo, dest_dir, config)
                assert result is True

    def test_create_git_operations(self):
        """GitOperationsインスタンス作成テスト"""
        config = {"use_https": True}
        git_ops = create_git_operations(config)

        assert isinstance(git_ops, GitOperations)
        assert git_ops.config == config

    @pytest.mark.integration
    def test_git_operations_integration(self):
        """Git操作統合テスト"""
        verify_current_platform()  # プラットフォーム検証
        get_platform_specific_config()  # プラットフォーム設定取得

        config = {"use_https": True, "max_retries": 1}
        GitOperations(config)

        repo = {
            "name": "test-repo",
            "clone_url": "https://github.com/test/repo.git",
            "ssh_url": "git@github.com:test/repo.git",
            "full_name": "test/repo",
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_dir = Path(temp_dir)

            # クローンURL選択のテスト
            url = choose_clone_url(repo, use_https=True)
            assert url == "https://github.com/test/repo.git"

            # 同期テスト（破壊的操作のみモック）
            with patch("setup_repo.git_operations._sync_repository_once") as mock_sync:
                mock_sync.return_value = True
                result = sync_repository(repo, dest_dir)
                assert result is True
