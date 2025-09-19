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

    def test_is_git_repository_value_error(self):
        """Gitリポジトリ判定でValueError例外処理テスト"""
        git_ops = GitOperations()

        # safe_path_joinがValueErrorを発生させる場合
        with patch("setup_repo.git_operations.safe_path_join") as mock_join:
            mock_join.side_effect = ValueError("Invalid path")
            result = git_ops.is_git_repository("/some/path")
            assert result is False

    def test_choose_clone_url_invalid_data_types(self):
        """不正なデータ型でのURL選択テスト"""
        # 不正なデータ型のrepo
        repo = {
            "clone_url": 123,  # 数値（不正）
            "ssh_url": None,  # None（不正）
            "full_name": "test/repo",
        }

        # HTTPSフォールバック（88行目）
        url = choose_clone_url(repo, use_https=True)
        assert url == ""  # 不正なデータ型は空文字列に変換

    def test_choose_clone_url_invalid_full_name(self):
        """不正なfull_nameでのHTTPSフォールバックテスト"""
        repo = {
            "clone_url": "https://github.com/test/repo.git",
            "ssh_url": "git@github.com:test/repo.git",
            "full_name": 123,  # 不正なデータ型
        }

        with patch("pathlib.Path.exists", return_value=True):
            # full_nameが無効な場合はHTTPSにフォールバック（88行目）
            url = choose_clone_url(repo, use_https=False)
            assert url == "https://github.com/test/repo.git"

    def test_sync_repository_with_sync_only(self):
        """sync_only機能テスト"""
        repo = {"name": "test-repo"}
        config = {"sync_only": True, "dry_run": False}

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_dir = Path(temp_dir)

            # リポジトリが存在しない場合、sync_onlyでスキップ（130-131行目）
            with patch("builtins.print") as mock_print:
                result = sync_repository_with_retries(repo, dest_dir, config)
                assert result is True
                mock_print.assert_any_call("   ⏭️  test-repo: 新規クローンをスキップ（sync_only有効）")

    def test_sync_repository_dry_run_update(self):
        """dry_run機能での更新テスト"""
        repo = {"name": "test-repo"}
        config = {"dry_run": True, "auto_stash": False}

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_dir = Path(temp_dir)
            repo_path = dest_dir / "test-repo"
            repo_path.mkdir()

            # dry_runでの更新（142-143行目）
            with patch("builtins.print") as mock_print:
                result = sync_repository_with_retries(repo, dest_dir, config)
                assert result is True
                mock_print.assert_any_call("   ✅ test-repo: 更新予定")

    def test_sync_repository_dry_run_clone(self):
        """dry_run機能でのクローンテスト"""
        repo = {"name": "test-repo", "clone_url": "https://github.com/test/repo.git"}
        config = {"dry_run": True}

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_dir = Path(temp_dir)

            # dry_runでのクローン（150行目）
            with patch("builtins.print") as mock_print:
                result = sync_repository_with_retries(repo, dest_dir, config)
                assert result is True
                mock_print.assert_any_call("   ✅ test-repo: クローン予定")

    def test_sync_repository_with_auto_stash(self):
        """auto_stash機能テスト"""
        repo = {"name": "test-repo"}
        config = {"auto_stash": True, "dry_run": False}

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_dir = Path(temp_dir)
            repo_path = dest_dir / "test-repo"
            repo_path.mkdir()

            with (
                patch("setup_repo.git_operations._auto_stash_changes") as mock_stash,
                patch("setup_repo.git_operations._auto_pop_stash") as mock_pop,
                patch("setup_repo.git_operations.safe_subprocess") as mock_subprocess,
                patch("builtins.print"),
            ):
                mock_stash.return_value = True  # stash成功
                mock_subprocess.return_value = Mock(returncode=0)

                # auto_stash機能（162-166, 171行目）
                result = sync_repository_with_retries(repo, dest_dir, config)
                assert result is True
                mock_stash.assert_called_once_with(repo_path)
                mock_pop.assert_called_once_with(repo_path)

    def test_sync_repository_auto_stash_error_recovery(self):
        """auto_stashエラー時の復旧テスト"""
        repo = {"name": "test-repo"}
        config = {"auto_stash": True, "dry_run": False}

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_dir = Path(temp_dir)
            repo_path = dest_dir / "test-repo"
            repo_path.mkdir()

            with (
                patch("setup_repo.git_operations._auto_stash_changes") as mock_stash,
                patch("setup_repo.git_operations._auto_pop_stash") as mock_pop,
                patch("setup_repo.git_operations.safe_subprocess") as mock_subprocess,
                patch("builtins.print"),
            ):
                mock_stash.return_value = True  # stash成功
                mock_subprocess.side_effect = subprocess.CalledProcessError(1, "git", stderr="pull failed")

                # エラー時もpopを試行（179-180行目）
                result = sync_repository_with_retries(repo, dest_dir, config)
                assert result is False
                mock_stash.assert_called_once_with(repo_path)
                mock_pop.assert_called_once_with(repo_path)  # エラー時もpop

    def test_auto_stash_changes_with_changes(self):
        """変更がある場合のauto_stashテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            with patch("setup_repo.git_operations.safe_subprocess") as mock_subprocess:
                # git statusで変更を検出
                mock_subprocess.side_effect = [
                    Mock(stdout="M  file.txt\n", returncode=0),  # 変更あり
                    Mock(returncode=0),  # stash成功
                ]

                from setup_repo.git_operations import _auto_stash_changes

                result = _auto_stash_changes(repo_path)
                assert result is True
                assert mock_subprocess.call_count == 2

    def test_auto_stash_changes_no_changes(self):
        """変更がない場合のauto_stashテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            with patch("setup_repo.git_operations.safe_subprocess") as mock_subprocess:
                # git statusで変更なし
                mock_subprocess.return_value = Mock(stdout="", returncode=0)

                from setup_repo.git_operations import _auto_stash_changes

                result = _auto_stash_changes(repo_path)
                assert result is False
                assert mock_subprocess.call_count == 1

    def test_auto_stash_changes_error(self):
        """auto_stashエラー処理テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            with (
                patch("setup_repo.git_operations.safe_subprocess") as mock_subprocess,
                patch("logging.getLogger") as mock_logger,
            ):
                mock_subprocess.side_effect = subprocess.CalledProcessError(1, "git")
                mock_log = Mock()
                mock_logger.return_value = mock_log

                from setup_repo.git_operations import _auto_stash_changes

                result = _auto_stash_changes(repo_path)
                assert result is False
                mock_log.debug.assert_called_once()

    def test_auto_pop_stash_success(self):
        """auto_pop_stash成功テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            with patch("setup_repo.git_operations.safe_subprocess") as mock_subprocess:
                mock_subprocess.return_value = Mock(returncode=0)

                from setup_repo.git_operations import _auto_pop_stash

                result = _auto_pop_stash(repo_path)
                assert result is True

    def test_auto_pop_stash_error(self):
        """auto_pop_stashエラー処理テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            with patch("setup_repo.git_operations.safe_subprocess") as mock_subprocess:
                mock_subprocess.side_effect = subprocess.CalledProcessError(1, "git")

                from setup_repo.git_operations import _auto_pop_stash

                result = _auto_pop_stash(repo_path)
                assert result is False

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
