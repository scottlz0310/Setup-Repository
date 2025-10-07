#!/usr/bin/env python3
"""ブランチクリーンナップモジュールのテスト"""

import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from setup_repo.branch_cleanup import BranchCleanup


@pytest.fixture
def temp_git_repo(tmp_path: Path) -> Path:
    """テスト用の一時Gitリポジトリを作成"""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )
    return repo_path


@pytest.fixture
def cleanup(temp_git_repo: Path) -> BranchCleanup:
    """BranchCleanupインスタンスを作成"""
    return BranchCleanup(temp_git_repo)


class TestBranchCleanupInit:
    """BranchCleanup初期化のテスト"""

    def test_init_with_path_object(self, temp_git_repo: Path) -> None:
        """Pathオブジェクトで初期化"""
        cleanup = BranchCleanup(temp_git_repo)
        assert cleanup.repo_path == temp_git_repo

    def test_init_with_string_path(self, temp_git_repo: Path) -> None:
        """文字列パスで初期化"""
        cleanup = BranchCleanup(str(temp_git_repo))
        assert cleanup.repo_path == temp_git_repo


class TestListRemoteBranches:
    """リモートブランチ一覧取得のテスト"""

    @patch("setup_repo.branch_cleanup.safe_subprocess")
    def test_list_remote_branches_success(self, mock_subprocess: MagicMock, cleanup: BranchCleanup) -> None:
        """リモートブランチ一覧取得成功"""
        mock_subprocess.return_value = MagicMock(
            stdout="origin/feature-1|2024-01-15 10:00:00 +0000|Alice\norigin/feature-2|2024-01-20 15:30:00 +0000|Bob\n"
        )

        branches = cleanup.list_remote_branches()

        assert len(branches) == 2
        assert branches[0]["name"] == "origin/feature-1"
        assert branches[0]["author"] == "Alice"
        assert branches[1]["name"] == "origin/feature-2"
        assert branches[1]["author"] == "Bob"

    @patch("setup_repo.branch_cleanup.safe_subprocess")
    def test_list_remote_branches_skip_head(self, mock_subprocess: MagicMock, cleanup: BranchCleanup) -> None:
        """HEADブランチをスキップ"""
        mock_subprocess.return_value = MagicMock(
            stdout=(
                "origin/HEAD -> origin/main|2024-01-15 10:00:00 +0000|System\n"
                "origin/feature-1|2024-01-15 10:00:00 +0000|Alice\n"
            )
        )

        branches = cleanup.list_remote_branches()

        assert len(branches) == 1
        assert branches[0]["name"] == "origin/feature-1"

    @patch("setup_repo.branch_cleanup.safe_subprocess")
    def test_list_remote_branches_empty(self, mock_subprocess: MagicMock, cleanup: BranchCleanup) -> None:
        """リモートブランチが空"""
        mock_subprocess.return_value = MagicMock(stdout="")

        branches = cleanup.list_remote_branches()

        assert branches == []

    @patch("setup_repo.branch_cleanup.safe_subprocess")
    def test_list_remote_branches_error(self, mock_subprocess: MagicMock, cleanup: BranchCleanup) -> None:
        """Git コマンドエラー"""
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, "git")

        branches = cleanup.list_remote_branches()

        assert branches == []


class TestListMergedBranches:
    """マージ済みブランチ一覧取得のテスト"""

    @patch("setup_repo.branch_cleanup.safe_subprocess")
    def test_list_merged_branches_success(self, mock_subprocess: MagicMock, cleanup: BranchCleanup) -> None:
        """マージ済みブランチ一覧取得成功"""
        mock_subprocess.return_value = MagicMock(stdout="  origin/feature-1\n  origin/feature-2\n  origin/main\n")

        branches = cleanup.list_merged_branches("origin/main")

        assert len(branches) == 2
        assert "origin/feature-1" in branches
        assert "origin/feature-2" in branches
        assert "origin/main" not in branches

    @patch("setup_repo.branch_cleanup.safe_subprocess")
    def test_list_merged_branches_skip_head(self, mock_subprocess: MagicMock, cleanup: BranchCleanup) -> None:
        """HEADブランチをスキップ"""
        mock_subprocess.return_value = MagicMock(stdout="  origin/HEAD -> origin/main\n  origin/feature-1\n")

        branches = cleanup.list_merged_branches("origin/main")

        assert len(branches) == 1
        assert "origin/feature-1" in branches

    @patch("setup_repo.branch_cleanup.safe_subprocess")
    def test_list_merged_branches_error(self, mock_subprocess: MagicMock, cleanup: BranchCleanup) -> None:
        """Git コマンドエラー"""
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, "git")

        branches = cleanup.list_merged_branches("origin/main")

        assert branches == []


class TestListStaleBranches:
    """古いブランチ一覧取得のテスト"""

    @patch("setup_repo.branch_cleanup.safe_subprocess")
    def test_list_stale_branches_success(self, mock_subprocess: MagicMock, cleanup: BranchCleanup) -> None:
        """古いブランチ一覧取得成功"""
        old_date = (datetime.now() - timedelta(days=100)).strftime("%Y-%m-%d %H:%M:%S +0000")
        recent_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S +0000")

        mock_subprocess.return_value = MagicMock(
            stdout=f"origin/old-feature|{old_date}|Alice\norigin/recent-feature|{recent_date}|Bob\n"
        )

        branches = cleanup.list_stale_branches(90)

        assert len(branches) == 1
        assert branches[0]["name"] == "origin/old-feature"

    @patch("setup_repo.branch_cleanup.safe_subprocess")
    def test_list_stale_branches_custom_days(self, mock_subprocess: MagicMock, cleanup: BranchCleanup) -> None:
        """カスタム日数指定"""
        old_date = (datetime.now() - timedelta(days=200)).strftime("%Y-%m-%d %H:%M:%S +0000")

        mock_subprocess.return_value = MagicMock(stdout=f"origin/old-feature|{old_date}|Alice\n")

        branches = cleanup.list_stale_branches(180)

        assert len(branches) == 1


class TestDeleteRemoteBranch:
    """リモートブランチ削除のテスト"""

    @patch("setup_repo.branch_cleanup.safe_subprocess")
    def test_delete_remote_branch_dry_run(self, mock_subprocess: MagicMock, cleanup: BranchCleanup) -> None:
        """ドライラン実行"""
        result = cleanup.delete_remote_branch("origin/feature-1", dry_run=True)

        assert result is True
        mock_subprocess.assert_not_called()

    @patch("setup_repo.branch_cleanup.safe_subprocess")
    def test_delete_remote_branch_success(self, mock_subprocess: MagicMock, cleanup: BranchCleanup) -> None:
        """ブランチ削除成功"""
        mock_subprocess.return_value = MagicMock()

        result = cleanup.delete_remote_branch("origin/feature-1", dry_run=False)

        assert result is True
        mock_subprocess.assert_called_once()

    @patch("setup_repo.branch_cleanup.safe_subprocess")
    def test_delete_remote_branch_error(self, mock_subprocess: MagicMock, cleanup: BranchCleanup) -> None:
        """ブランチ削除失敗"""
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, "git", stderr="error")

        result = cleanup.delete_remote_branch("origin/feature-1", dry_run=False)

        assert result is False


class TestCleanupMergedBranches:
    """マージ済みブランチクリーンナップのテスト"""

    @patch("setup_repo.branch_cleanup.BranchCleanup.list_merged_branches")
    def test_cleanup_merged_branches_empty(self, mock_list: MagicMock, cleanup: BranchCleanup) -> None:
        """マージ済みブランチが空"""
        mock_list.return_value = []

        result = cleanup.cleanup_merged_branches()

        assert result["deleted"] == 0
        assert result["failed"] == 0
        assert result["skipped"] == 0

    @patch("setup_repo.branch_cleanup.BranchCleanup.delete_remote_branch")
    @patch("setup_repo.branch_cleanup.BranchCleanup.list_merged_branches")
    def test_cleanup_merged_branches_dry_run(
        self, mock_list: MagicMock, mock_delete: MagicMock, cleanup: BranchCleanup
    ) -> None:
        """ドライラン実行"""
        mock_list.return_value = ["origin/feature-1", "origin/feature-2"]
        mock_delete.return_value = True

        result = cleanup.cleanup_merged_branches(dry_run=True)

        assert result["deleted"] == 2
        assert result["failed"] == 0

    @patch("builtins.input", return_value="n")
    @patch("setup_repo.branch_cleanup.BranchCleanup.list_merged_branches")
    def test_cleanup_merged_branches_user_cancel(
        self, mock_list: MagicMock, mock_input: MagicMock, cleanup: BranchCleanup
    ) -> None:
        """ユーザーがキャンセル"""
        mock_list.return_value = ["origin/feature-1"]

        result = cleanup.cleanup_merged_branches(auto_confirm=False)

        assert result["skipped"] == 1

    @patch("setup_repo.branch_cleanup.BranchCleanup.delete_remote_branch")
    @patch("setup_repo.branch_cleanup.BranchCleanup.list_merged_branches")
    def test_cleanup_merged_branches_auto_confirm(
        self, mock_list: MagicMock, mock_delete: MagicMock, cleanup: BranchCleanup
    ) -> None:
        """自動確認で実行"""
        mock_list.return_value = ["origin/feature-1", "origin/feature-2"]
        mock_delete.return_value = True

        result = cleanup.cleanup_merged_branches(auto_confirm=True)

        assert result["deleted"] == 2
        assert result["failed"] == 0


class TestCleanupStaleBranches:
    """古いブランチクリーンナップのテスト"""

    @patch("setup_repo.branch_cleanup.BranchCleanup.list_stale_branches")
    def test_cleanup_stale_branches_empty(self, mock_list: MagicMock, cleanup: BranchCleanup) -> None:
        """古いブランチが空"""
        mock_list.return_value = []

        result = cleanup.cleanup_stale_branches(days=90)

        assert result["deleted"] == 0
        assert result["failed"] == 0
        assert result["skipped"] == 0

    @patch("setup_repo.branch_cleanup.BranchCleanup.delete_remote_branch")
    @patch("setup_repo.branch_cleanup.BranchCleanup.list_stale_branches")
    def test_cleanup_stale_branches_success(
        self, mock_list: MagicMock, mock_delete: MagicMock, cleanup: BranchCleanup
    ) -> None:
        """古いブランチクリーンナップ成功"""
        mock_list.return_value = [
            {"name": "origin/old-1", "last_commit_date": "2023-01-01"},
            {"name": "origin/old-2", "last_commit_date": "2023-02-01"},
        ]
        mock_delete.return_value = True

        result = cleanup.cleanup_stale_branches(days=90, auto_confirm=True)

        assert result["deleted"] == 2
        assert result["failed"] == 0
