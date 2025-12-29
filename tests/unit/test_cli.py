"""Tests for CLI."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from setup_repo.cli.app import app
from setup_repo.models.repository import Repository
from setup_repo.models.result import ProcessResult, ResultStatus, SyncSummary

runner = CliRunner()


class TestAppCallback:
    """Tests for main app callback."""

    def test_help(self) -> None:
        """Test --help option."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "setup-repo" in result.stdout or "GitHub" in result.stdout

    def test_no_args_shows_help(self) -> None:
        """Test no arguments shows help and exits with code 2."""
        result = runner.invoke(app, [])
        # no_args_is_help=True causes exit code 2
        assert result.exit_code == 2
        assert "Usage" in result.stdout


class TestSyncCommand:
    """Tests for sync command."""

    def test_sync_help(self) -> None:
        """Test sync --help."""
        result = runner.invoke(app, ["sync", "--help"])
        assert result.exit_code == 0
        assert "owner" in result.stdout.lower() or "Owner" in result.stdout

    @patch("setup_repo.cli.commands.sync.get_settings")
    def test_sync_no_owner(self, mock_settings: MagicMock) -> None:
        """Test sync without owner."""
        mock_settings.return_value = MagicMock(
            github_owner="",
            github_token=None,
            workspace_dir=Path("/tmp"),
            git_ssl_no_verify=False,
        )

        result = runner.invoke(app, ["sync"])
        assert result.exit_code == 1
        assert "owner" in result.stdout.lower() or "Error" in result.stdout

    @patch("setup_repo.cli.commands.sync.ParallelProcessor")
    @patch("setup_repo.cli.commands.sync.GitOperations")
    @patch("setup_repo.cli.commands.sync.GitHubClient")
    @patch("setup_repo.cli.commands.sync.get_settings")
    def test_sync_success(
        self,
        mock_settings: MagicMock,
        mock_client_class: MagicMock,
        mock_git_class: MagicMock,
        mock_processor_class: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test successful sync."""
        # Setup mocks
        mock_settings.return_value = MagicMock(
            github_owner="test-user",
            github_token="token",
            workspace_dir=tmp_path,
            git_ssl_no_verify=False,
            use_https=True,
        )

        mock_client = MagicMock()
        mock_client.get_repositories.return_value = [
            Repository(
                name="repo1",
                full_name="test-user/repo1",
                clone_url="https://github.com/test-user/repo1.git",
                ssh_url="git@github.com:test-user/repo1.git",
            ),
        ]
        mock_client_class.return_value = mock_client

        mock_processor = MagicMock()
        mock_processor.process.return_value = SyncSummary(
            total=1,
            success=1,
            failed=0,
            skipped=0,
            duration=1.0,
            results=[
                ProcessResult(
                    repo_name="repo1",
                    status=ResultStatus.SUCCESS,
                    message="Cloned",
                )
            ],
        )
        mock_processor_class.return_value = mock_processor

        result = runner.invoke(app, ["sync"])
        assert result.exit_code == 0

    @patch("setup_repo.cli.commands.sync.GitHubClient")
    @patch("setup_repo.cli.commands.sync.get_settings")
    def test_sync_no_repos(
        self,
        mock_settings: MagicMock,
        mock_client_class: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test sync with no repositories."""
        mock_settings.return_value = MagicMock(
            github_owner="test-user",
            github_token="token",
            workspace_dir=tmp_path,
            git_ssl_no_verify=False,
        )

        mock_client = MagicMock()
        mock_client.get_repositories.return_value = []
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["sync"])
        assert result.exit_code == 0
        assert "Warning" in result.stdout or "No" in result.stdout

    @patch("setup_repo.cli.commands.sync.GitHubClient")
    @patch("setup_repo.cli.commands.sync.get_settings")
    def test_sync_dry_run(
        self,
        mock_settings: MagicMock,
        mock_client_class: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test sync dry-run mode."""
        mock_settings.return_value = MagicMock(
            github_owner="test-user",
            github_token="token",
            workspace_dir=tmp_path,
            git_ssl_no_verify=False,
        )

        mock_client = MagicMock()
        mock_client.get_repositories.return_value = [
            Repository(
                name="repo1",
                full_name="test-user/repo1",
                clone_url="https://github.com/test-user/repo1.git",
                ssh_url="git@github.com:test-user/repo1.git",
            ),
        ]
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["sync", "--dry-run"])
        assert result.exit_code == 0
        assert "would be synced" in result.stdout


class TestCleanupCommand:
    """Tests for cleanup command."""

    def test_cleanup_help(self) -> None:
        """Test cleanup --help."""
        result = runner.invoke(app, ["cleanup", "--help"])
        assert result.exit_code == 0
        assert "base" in result.stdout.lower() or "branch" in result.stdout.lower()

    def test_cleanup_not_git_repo(self, tmp_path: Path) -> None:
        """Test cleanup on non-git directory."""
        result = runner.invoke(app, ["cleanup", str(tmp_path)])
        assert result.exit_code == 1
        assert "Git" in result.stdout or "repository" in result.stdout.lower()

    @patch("setup_repo.cli.commands.cleanup.GitOperations")
    def test_cleanup_no_branches(
        self,
        mock_git_class: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test cleanup with no merged branches."""
        # Create .git directory
        (tmp_path / ".git").mkdir()

        mock_git = MagicMock()
        mock_git.get_merged_branches.return_value = []
        mock_git_class.return_value = mock_git

        result = runner.invoke(app, ["cleanup", str(tmp_path)])
        assert result.exit_code == 0
        assert "No" in result.stdout or "✓" in result.stdout

    @patch("setup_repo.cli.commands.cleanup.GitOperations")
    def test_cleanup_dry_run(
        self,
        mock_git_class: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test cleanup dry-run mode."""
        (tmp_path / ".git").mkdir()

        mock_git = MagicMock()
        mock_git.get_merged_branches.return_value = ["feature/done", "bugfix/fixed"]
        mock_git_class.return_value = mock_git

        result = runner.invoke(app, ["cleanup", str(tmp_path), "--dry-run"])
        assert result.exit_code == 0
        assert "would be deleted" in result.stdout

    @patch("setup_repo.cli.commands.cleanup.GitOperations")
    def test_cleanup_with_force(
        self,
        mock_git_class: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test cleanup with force flag."""
        (tmp_path / ".git").mkdir()

        mock_git = MagicMock()
        mock_git.get_merged_branches.return_value = ["feature/done"]
        mock_git.delete_branch.return_value = True
        mock_git_class.return_value = mock_git

        result = runner.invoke(app, ["cleanup", str(tmp_path), "--force"])
        assert result.exit_code == 0
        assert "deleted" in result.stdout


class TestOutputHelpers:
    """Tests for output helper functions."""

    def test_show_summary(self) -> None:
        """Test show_summary function."""
        from setup_repo.cli.output import show_summary

        summary = SyncSummary(
            total=3,
            success=2,
            failed=1,
            skipped=0,
            duration=5.0,
            results=[
                ProcessResult(
                    repo_name="repo1",
                    status=ResultStatus.SUCCESS,
                    message="Done",
                ),
                ProcessResult(
                    repo_name="repo2",
                    status=ResultStatus.SUCCESS,
                    message="Done",
                ),
                ProcessResult(
                    repo_name="repo3",
                    status=ResultStatus.FAILED,
                    error="Failed",
                ),
            ],
        )

        # Should not raise
        show_summary(summary)

    def test_show_error(self) -> None:
        """Test show_error function."""
        from setup_repo.cli.output import show_error

        # Should not raise
        show_error("Test error message")

    def test_show_warning(self) -> None:
        """Test show_warning function."""
        from setup_repo.cli.output import show_warning

        # Should not raise
        show_warning("Test warning message")

    def test_show_success(self) -> None:
        """Test show_success function."""
        from setup_repo.cli.output import show_success

        # Should not raise
        show_success("Test success message")
