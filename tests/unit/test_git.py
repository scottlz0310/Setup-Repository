"""Tests for Git operations."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from setup_repo.core.git import GitOperations
from setup_repo.models.result import ResultStatus


class TestGitOperations:
    """Tests for GitOperations class."""

    def test_init_defaults(self) -> None:
        """Test default initialization."""
        git = GitOperations()
        assert git.auto_prune is True
        assert git.auto_stash is False
        assert git.ssl_no_verify is False

    def test_init_custom(self) -> None:
        """Test custom initialization."""
        git = GitOperations(
            auto_prune=False,
            auto_stash=True,
            ssl_no_verify=True,
        )
        assert git.auto_prune is False
        assert git.auto_stash is True
        assert git.ssl_no_verify is True

    def test_get_env_without_ssl_no_verify(self) -> None:
        """Test _get_env returns None when ssl_no_verify is False."""
        git = GitOperations(ssl_no_verify=False)
        assert git._get_env() is None

    def test_get_env_with_ssl_no_verify(self) -> None:
        """Test _get_env returns env dict with GIT_SSL_NO_VERIFY."""
        git = GitOperations(ssl_no_verify=True)
        env = git._get_env()
        assert env is not None
        assert env.get("GIT_SSL_NO_VERIFY") == "1"


class TestClone:
    """Tests for clone method."""

    @patch("subprocess.run")
    def test_clone_success(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Test successful clone."""
        mock_run.return_value = MagicMock(returncode=0)

        git = GitOperations()
        dest = tmp_path / "test-repo"
        result = git.clone("https://github.com/user/test-repo.git", dest)

        assert result.status == ResultStatus.SUCCESS
        assert result.repo_name == "test-repo"
        assert "Cloned" in result.message

    @patch("subprocess.run")
    def test_clone_with_branch(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Test clone with specific branch."""
        mock_run.return_value = MagicMock(returncode=0)

        git = GitOperations()
        dest = tmp_path / "test-repo"
        git.clone("https://github.com/user/test-repo.git", dest, branch="develop")

        call_args = mock_run.call_args[0][0]
        assert "--branch" in call_args
        assert "develop" in call_args

    @patch("subprocess.run")
    def test_clone_failure(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Test clone failure."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "git", stderr="fatal: repository not found")

        git = GitOperations()
        dest = tmp_path / "test-repo"
        result = git.clone("https://github.com/user/nonexistent.git", dest)

        assert result.status == ResultStatus.FAILED
        assert "repository not found" in (result.error or "")

    @patch("subprocess.run")
    def test_clone_timeout(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Test clone timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired("git", 300)

        git = GitOperations()
        dest = tmp_path / "test-repo"
        result = git.clone("https://github.com/user/test-repo.git", dest)

        assert result.status == ResultStatus.FAILED
        assert "timed out" in (result.error or "")


class TestPull:
    """Tests for pull method."""

    @patch("subprocess.run")
    def test_pull_success(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Test successful pull."""
        mock_run.return_value = MagicMock(returncode=0, stdout="")

        git = GitOperations()
        result = git.pull(tmp_path)

        assert result.status == ResultStatus.SUCCESS
        assert "Pulled" in result.message

    @patch("subprocess.run")
    def test_pull_with_auto_prune(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Test pull with auto_prune enabled."""
        mock_run.return_value = MagicMock(returncode=0, stdout="")

        git = GitOperations(auto_prune=True)
        git.pull(tmp_path)

        # Check that fetch --prune was called
        calls = [call[0][0] for call in mock_run.call_args_list]
        fetch_call = [c for c in calls if "fetch" in c and "--prune" in c]
        assert len(fetch_call) == 1

    @patch("subprocess.run")
    def test_pull_failure(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Test pull failure."""
        # First call (fetch) succeeds, second call (pull) fails
        mock_run.side_effect = [
            MagicMock(returncode=0),
            subprocess.CalledProcessError(1, "git", stderr="merge conflict"),
        ]

        git = GitOperations()
        result = git.pull(tmp_path)

        assert result.status == ResultStatus.FAILED
        assert "merge conflict" in (result.error or "")


class TestFetchAndPrune:
    """Tests for fetch_and_prune method."""

    @patch("subprocess.run")
    def test_fetch_and_prune_success(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Test successful fetch and prune."""
        mock_run.return_value = MagicMock(returncode=0)

        git = GitOperations(auto_prune=True)
        result = git.fetch_and_prune(tmp_path)

        assert result is True

    def test_fetch_and_prune_disabled(self, tmp_path: Path) -> None:
        """Test fetch and prune when disabled."""
        git = GitOperations(auto_prune=False)
        result = git.fetch_and_prune(tmp_path)

        assert result is True  # Returns True when disabled


class TestGetMergedBranches:
    """Tests for get_merged_branches method."""

    @patch("subprocess.run")
    def test_get_merged_branches(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Test getting merged branches."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="  feature/done\n* main\n  bugfix/fixed\n",
        )

        git = GitOperations()
        branches = git.get_merged_branches(tmp_path, "main")

        assert "feature/done" in branches
        assert "bugfix/fixed" in branches
        assert "main" not in branches  # Base branch excluded

    @patch("subprocess.run")
    def test_get_merged_branches_empty(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Test when no merged branches."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="* main\n",
        )

        git = GitOperations()
        branches = git.get_merged_branches(tmp_path)

        assert branches == []


class TestDeleteBranch:
    """Tests for delete_branch method."""

    @patch("subprocess.run")
    def test_delete_branch_success(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Test successful branch deletion."""
        mock_run.return_value = MagicMock(returncode=0)

        git = GitOperations()
        result = git.delete_branch(tmp_path, "feature/old")

        assert result is True

    @patch("subprocess.run")
    def test_delete_branch_failure(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Test branch deletion failure."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "git", stderr="branch not found")

        git = GitOperations()
        result = git.delete_branch(tmp_path, "nonexistent")

        assert result is False

    @patch("subprocess.run")
    def test_delete_branch_with_force(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Test force branch deletion."""
        mock_run.return_value = MagicMock(returncode=0)

        git = GitOperations()
        result = git.delete_branch(tmp_path, "feature/old", force=True)

        assert result is True
        # Verify -D flag was used
        call_args = mock_run.call_args[0][0]
        assert "-D" in call_args
        assert "feature/old" in call_args


class TestGetRemoteUrl:
    """Tests for get_remote_url method."""

    @patch("subprocess.run")
    def test_get_remote_url_success(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Test getting remote URL."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="https://github.com/user/repo.git\n",
        )

        git = GitOperations()
        url = git.get_remote_url(tmp_path)

        assert url == "https://github.com/user/repo.git"

    @patch("subprocess.run")
    def test_get_remote_url_not_found(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Test when remote URL is not found."""
        mock_run.return_value = MagicMock(returncode=1, stdout="")

        git = GitOperations()
        url = git.get_remote_url(tmp_path)

        assert url is None


class TestParseGithubRepo:
    """Tests for parse_github_repo method."""

    def test_parse_ssh_url(self) -> None:
        """Test parsing SSH URL."""
        git = GitOperations()
        result = git.parse_github_repo("git@github.com:owner/repo.git")

        assert result == ("owner", "repo")

    def test_parse_ssh_url_without_git_suffix(self) -> None:
        """Test parsing SSH URL without .git suffix."""
        git = GitOperations()
        result = git.parse_github_repo("git@github.com:owner/repo")

        assert result == ("owner", "repo")

    def test_parse_https_url(self) -> None:
        """Test parsing HTTPS URL."""
        git = GitOperations()
        result = git.parse_github_repo("https://github.com/owner/repo.git")

        assert result == ("owner", "repo")

    def test_parse_https_url_without_git_suffix(self) -> None:
        """Test parsing HTTPS URL without .git suffix."""
        git = GitOperations()
        result = git.parse_github_repo("https://github.com/owner/repo")

        assert result == ("owner", "repo")

    def test_parse_non_github_url(self) -> None:
        """Test parsing non-GitHub URL."""
        git = GitOperations()
        result = git.parse_github_repo("https://gitlab.com/owner/repo.git")

        assert result is None


class TestGetLocalBranches:
    """Tests for get_local_branches method."""

    @patch("subprocess.run")
    def test_get_local_branches(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Test getting local branches."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="main\nfeature/test\nbugfix/issue\n",
        )

        git = GitOperations()
        branches = git.get_local_branches(tmp_path)

        assert "main" in branches
        assert "feature/test" in branches
        assert "bugfix/issue" in branches
        assert len(branches) == 3

    @patch("subprocess.run")
    def test_get_local_branches_empty(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Test when no branches found."""
        mock_run.return_value = MagicMock(returncode=0, stdout="")

        git = GitOperations()
        branches = git.get_local_branches(tmp_path)

        assert branches == []


class TestGetCurrentBranch:
    """Tests for get_current_branch method."""

    @patch("subprocess.run")
    def test_get_current_branch(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Test getting current branch."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="feature/test\n",
        )

        git = GitOperations()
        branch = git.get_current_branch(tmp_path)

        assert branch == "feature/test"

    @patch("subprocess.run")
    def test_get_current_branch_not_on_branch(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Test when not on a branch (detached HEAD)."""
        mock_run.return_value = MagicMock(returncode=1, stdout="")

        git = GitOperations()
        branch = git.get_current_branch(tmp_path)

        assert branch is None

    @patch("subprocess.run")
    def test_get_local_branches_empty(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Test when no branches found."""
        mock_run.return_value = MagicMock(returncode=0, stdout="")

        git = GitOperations()
        branches = git.get_local_branches(tmp_path)

        assert branches == []


class TestGetBranchSha:
    """Tests for get_branch_sha method."""

    @patch("subprocess.run")
    def test_get_branch_sha(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Test getting branch SHA."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="abc123def456\n",
        )

        git = GitOperations()
        sha = git.get_branch_sha(tmp_path, "feature/test")

        assert sha == "abc123def456"

    @patch("subprocess.run")
    def test_get_branch_sha_not_found(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Test when branch doesn't exist."""
        mock_run.return_value = MagicMock(returncode=1, stdout="")

        git = GitOperations()
        sha = git.get_branch_sha(tmp_path, "nonexistent")

        assert sha is None


class TestIsAncestor:
    """Tests for is_ancestor method."""

    @patch("subprocess.run")
    def test_is_ancestor_true(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Test when commit is an ancestor."""
        mock_run.return_value = MagicMock(returncode=0)

        git = GitOperations()
        result = git.is_ancestor(tmp_path, "abc123", "def456")

        assert result is True

    @patch("subprocess.run")
    def test_is_ancestor_false(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Test when commit is not an ancestor."""
        mock_run.return_value = MagicMock(returncode=1)

        git = GitOperations()
        result = git.is_ancestor(tmp_path, "abc123", "def456")

        assert result is False
