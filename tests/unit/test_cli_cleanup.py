"""
CLIブランチクリーンナップ機能のテスト
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from setup_repo.cli import cleanup_cli


class TestCleanupCLI:
    """ブランチクリーンナップCLI機能のテスト"""

    def test_cleanup_cli_list_all_branches(self, tmp_path: Path) -> None:
        """全ブランチ一覧表示テスト"""
        args = Mock()
        args.repo_path = None
        args.action = "list"
        args.merged = False
        args.stale = False
        args.base_branch = None
        args.days = None

        with (
            patch("setup_repo.cli.Path.cwd", return_value=tmp_path),
            patch("setup_repo.cli.BranchCleanup") as mock_cleanup,
            patch("builtins.print"),
        ):
            # .gitディレクトリを作成
            (tmp_path / ".git").mkdir()

            mock_instance = Mock()
            mock_instance.list_remote_branches.return_value = [
                {"name": "origin/feature-1", "last_commit_date": "2024-01-15 10:00:00 +0000"},
                {"name": "origin/feature-2", "last_commit_date": "2024-01-20 15:30:00 +0000"},
            ]
            mock_cleanup.return_value = mock_instance

            cleanup_cli(args)

            mock_instance.list_remote_branches.assert_called_once()

    def test_cleanup_cli_list_merged_branches(self, tmp_path: Path) -> None:
        """マージ済みブランチ一覧表示テスト"""
        args = Mock()
        args.repo_path = None
        args.action = "list"
        args.merged = True
        args.stale = False
        args.base_branch = None
        args.days = None

        with (
            patch("setup_repo.cli.Path.cwd", return_value=tmp_path),
            patch("setup_repo.cli.BranchCleanup") as mock_cleanup,
            patch("builtins.print"),
        ):
            (tmp_path / ".git").mkdir()

            mock_instance = Mock()
            mock_instance.list_merged_branches.return_value = ["origin/feature-1", "origin/feature-2"]
            mock_cleanup.return_value = mock_instance

            cleanup_cli(args)

            mock_instance.list_merged_branches.assert_called_once_with("origin/main")

    def test_cleanup_cli_list_stale_branches(self, tmp_path: Path) -> None:
        """古いブランチ一覧表示テスト"""
        args = Mock()
        args.repo_path = None
        args.action = "list"
        args.merged = False
        args.stale = True
        args.base_branch = None
        args.days = 90

        with (
            patch("setup_repo.cli.Path.cwd", return_value=tmp_path),
            patch("setup_repo.cli.BranchCleanup") as mock_cleanup,
            patch("builtins.print"),
        ):
            (tmp_path / ".git").mkdir()

            mock_instance = Mock()
            mock_instance.list_stale_branches.return_value = [
                {"name": "origin/old-feature", "last_commit_date": "2023-01-15 10:00:00 +0000"}
            ]
            mock_cleanup.return_value = mock_instance

            cleanup_cli(args)

            mock_instance.list_stale_branches.assert_called_once_with(90)

    def test_cleanup_cli_clean_merged_branches(self, tmp_path: Path) -> None:
        """マージ済みブランチクリーンナップテスト"""
        args = Mock()
        args.repo_path = None
        args.action = "clean"
        args.merged = True
        args.stale = False
        args.base_branch = None
        args.days = None
        args.dry_run = False
        args.yes = True

        with (
            patch("setup_repo.cli.Path.cwd", return_value=tmp_path),
            patch("setup_repo.cli.BranchCleanup") as mock_cleanup,
            patch("builtins.print"),
        ):
            (tmp_path / ".git").mkdir()

            mock_instance = Mock()
            mock_instance.cleanup_merged_branches.return_value = {
                "deleted": 2,
                "failed": 0,
                "skipped": 0,
                "branches": ["origin/feature-1", "origin/feature-2"],
            }
            mock_cleanup.return_value = mock_instance

            cleanup_cli(args)

            mock_instance.cleanup_merged_branches.assert_called_once_with(
                base_branch="origin/main", dry_run=False, auto_confirm=True
            )

    def test_cleanup_cli_clean_stale_branches(self, tmp_path: Path) -> None:
        """古いブランチクリーンナップテスト"""
        args = Mock()
        args.repo_path = None
        args.action = "clean"
        args.merged = False
        args.stale = True
        args.base_branch = None
        args.days = 90
        args.dry_run = False
        args.yes = True

        with (
            patch("setup_repo.cli.Path.cwd", return_value=tmp_path),
            patch("setup_repo.cli.BranchCleanup") as mock_cleanup,
            patch("builtins.print"),
        ):
            (tmp_path / ".git").mkdir()

            mock_instance = Mock()
            mock_instance.cleanup_stale_branches.return_value = {
                "deleted": 1,
                "failed": 0,
                "skipped": 0,
                "branches": ["origin/old-feature"],
            }
            mock_cleanup.return_value = mock_instance

            cleanup_cli(args)

            mock_instance.cleanup_stale_branches.assert_called_once_with(days=90, dry_run=False, auto_confirm=True)

    def test_cleanup_cli_clean_dry_run(self, tmp_path: Path) -> None:
        """ドライランテスト"""
        args = Mock()
        args.repo_path = None
        args.action = "clean"
        args.merged = True
        args.stale = False
        args.base_branch = None
        args.days = None
        args.dry_run = True
        args.yes = False

        with (
            patch("setup_repo.cli.Path.cwd", return_value=tmp_path),
            patch("setup_repo.cli.BranchCleanup") as mock_cleanup,
            patch("builtins.print"),
        ):
            (tmp_path / ".git").mkdir()

            mock_instance = Mock()
            mock_instance.cleanup_merged_branches.return_value = {
                "deleted": 2,
                "failed": 0,
                "skipped": 0,
                "branches": [],
            }
            mock_cleanup.return_value = mock_instance

            cleanup_cli(args)

            mock_instance.cleanup_merged_branches.assert_called_once_with(
                base_branch="origin/main", dry_run=True, auto_confirm=False
            )

    def test_cleanup_cli_not_git_repo(self, tmp_path: Path) -> None:
        """Gitリポジトリでない場合のエラーテスト"""
        args = Mock()
        args.repo_path = None
        args.action = "list"
        args.merged = False
        args.stale = False

        with (
            patch("setup_repo.cli.Path.cwd", return_value=tmp_path),
            patch("builtins.print"),
            patch("builtins.exit") as mock_exit,
        ):
            cleanup_cli(args)

            mock_exit.assert_called_once_with(1)

    def test_cleanup_cli_clean_without_option(self, tmp_path: Path) -> None:
        """--mergedまたは--staleなしでcleanを実行した場合のエラーテスト"""
        args = Mock()
        args.repo_path = None
        args.action = "clean"
        args.merged = False
        args.stale = False
        args.base_branch = None
        args.days = None
        args.dry_run = False
        args.yes = False

        with (
            patch("setup_repo.cli.Path.cwd", return_value=tmp_path),
            patch("builtins.print"),
            patch("builtins.exit") as mock_exit,
        ):
            (tmp_path / ".git").mkdir()

            cleanup_cli(args)

            mock_exit.assert_called_once_with(1)

    def test_cleanup_cli_invalid_action(self, tmp_path: Path) -> None:
        """不正なアクションのエラーテスト"""
        args = Mock()
        args.repo_path = None
        args.action = "invalid"

        with (
            patch("setup_repo.cli.Path.cwd", return_value=tmp_path),
            patch("builtins.print") as mock_print,
        ):
            (tmp_path / ".git").mkdir()

            cleanup_cli(args)

            mock_print.assert_called_with("エラー: 不正なアクション。list/clean のいずれかを指定してください")

    def test_cleanup_cli_custom_base_branch(self, tmp_path: Path) -> None:
        """カスタムベースブランチ指定テスト"""
        args = Mock()
        args.repo_path = None
        args.action = "clean"
        args.merged = True
        args.stale = False
        args.base_branch = "origin/develop"
        args.days = None
        args.dry_run = False
        args.yes = True

        with (
            patch("setup_repo.cli.Path.cwd", return_value=tmp_path),
            patch("setup_repo.cli.BranchCleanup") as mock_cleanup,
            patch("builtins.print"),
        ):
            (tmp_path / ".git").mkdir()

            mock_instance = Mock()
            mock_instance.cleanup_merged_branches.return_value = {
                "deleted": 1,
                "failed": 0,
                "skipped": 0,
                "branches": ["origin/feature-1"],
            }
            mock_cleanup.return_value = mock_instance

            cleanup_cli(args)

            mock_instance.cleanup_merged_branches.assert_called_once_with(
                base_branch="origin/develop", dry_run=False, auto_confirm=True
            )

    def test_cleanup_cli_invalid_repo_path(self) -> None:
        """不正なリポジトリパスのエラーテスト"""
        args = Mock()
        args.repo_path = "../../../etc/passwd"
        args.action = "list"

        with (
            patch("setup_repo.cli.safe_path_join", side_effect=ValueError("不正なパス")),
            pytest.raises(ValueError, match="不正なリポジトリパス"),
        ):
            cleanup_cli(args)

    def test_cleanup_cli_with_custom_repo_path(self, tmp_path: Path) -> None:
        """カスタムリポジトリパス指定テスト"""
        custom_repo = tmp_path / "custom_repo"
        custom_repo.mkdir()
        (custom_repo / ".git").mkdir()

        args = Mock()
        args.repo_path = "custom_repo"
        args.action = "list"
        args.merged = False
        args.stale = False
        args.base_branch = None
        args.days = None

        with (
            patch("setup_repo.cli.Path.cwd", return_value=tmp_path),
            patch("setup_repo.cli.safe_path_join", return_value=custom_repo),
            patch("setup_repo.cli.BranchCleanup") as mock_cleanup,
            patch("builtins.print"),
        ):
            mock_instance = Mock()
            mock_instance.list_remote_branches.return_value = []
            mock_cleanup.return_value = mock_instance

            cleanup_cli(args)

            mock_cleanup.assert_called_once_with(custom_repo)
