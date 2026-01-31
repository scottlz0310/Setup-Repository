"""Git operations wrapper - main interface."""

import subprocess
from pathlib import Path

from setup_repo.core.git_branch import GitBranchOperations
from setup_repo.core.git_operations import BasicGitOperations
from setup_repo.core.git_remote import GitRemoteOperations
from setup_repo.models.result import ProcessResult
from setup_repo.utils.logging import get_logger

log = get_logger(__name__)


class GitOperations:
    """Git command wrapper - unified interface.

    This class provides a unified interface to all Git operations
    by delegating to specialized operation classes.
    """

    def __init__(
        self,
        auto_prune: bool = True,
        auto_stash: bool = False,
        ssl_no_verify: bool = False,
    ) -> None:
        """Initialize Git operations.

        Args:
            auto_prune: Run fetch --prune automatically
            auto_stash: Stash changes before pull and pop after
            ssl_no_verify: Skip SSL verification
        """
        # Initialize basic operations
        self._basic_ops = BasicGitOperations(
            auto_prune=auto_prune,
            auto_stash=auto_stash,
            ssl_no_verify=ssl_no_verify,
        )

        # Initialize specialized operations
        self._branch_ops = GitBranchOperations(self._basic_ops)
        self._remote_ops = GitRemoteOperations(self._basic_ops)

        # Keep these for backward compatibility
        self.auto_prune = auto_prune
        self.auto_stash = auto_stash
        self.ssl_no_verify = ssl_no_verify

    def _get_env(self) -> dict[str, str] | None:
        """Get environment variables for git commands."""
        return self._basic_ops.get_env()

    def _run(
        self,
        args: list[str],
        cwd: Path | None = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        """Run a git command.

        Args:
            args: Git command arguments
            cwd: Working directory
            check: Raise on non-zero exit

        Returns:
            CompletedProcess result
        """
        return self._basic_ops.run(args, cwd, check)

    def clone(
        self,
        url: str,
        dest: Path,
        branch: str | None = None,
    ) -> ProcessResult:
        """Clone a repository.

        Args:
            url: Repository URL
            dest: Destination directory
            branch: Branch to clone

        Returns:
            ProcessResult
        """
        return self._basic_ops.clone(url, dest, branch)

    def fetch_and_prune(self, repo_path: Path) -> bool:
        """Run fetch --prune.

        Args:
            repo_path: Repository path

        Returns:
            True if successful
        """
        return self._basic_ops.fetch_and_prune(repo_path)

    def pull(self, repo_path: Path) -> ProcessResult:
        """Pull a repository.

        Args:
            repo_path: Repository path

        Returns:
            ProcessResult
        """
        return self._basic_ops.pull(repo_path)

    def _has_changes(self, repo_path: Path) -> bool:
        """Check if repository has uncommitted changes.

        Args:
            repo_path: Repository path

        Returns:
            True if there are changes
        """
        return self._basic_ops.has_changes(repo_path)

    def get_merged_branches(self, repo_path: Path, base_branch: str = "main") -> list[str]:
        """Get merged branches.

        Args:
            repo_path: Repository path
            base_branch: Base branch to compare against

        Returns:
            List of merged branch names
        """
        return self._branch_ops.get_merged_branches(repo_path, base_branch)

    def delete_branch(self, repo_path: Path, branch: str, force: bool = False) -> bool:
        """Delete a local branch.

        Args:
            repo_path: Repository path
            branch: Branch name to delete
            force: Use -D (force delete) instead of -d

        Returns:
            True if successful
        """
        return self._branch_ops.delete_branch(repo_path, branch, force)

    def get_remote_url(self, repo_path: Path) -> str | None:
        """Get the remote origin URL.

        Args:
            repo_path: Repository path

        Returns:
            Remote URL or None if not found
        """
        return self._remote_ops.get_remote_url(repo_path)

    def parse_github_repo(self, remote_url: str) -> tuple[str, str] | None:
        """Parse GitHub owner and repo name from remote URL.

        Args:
            remote_url: Git remote URL (HTTPS or SSH)

        Returns:
            Tuple of (owner, repo) or None if not a GitHub URL
        """
        return self._remote_ops.parse_github_repo(remote_url)

    def get_local_branches(self, repo_path: Path) -> list[str]:
        """Get all local branches.

        Args:
            repo_path: Repository path

        Returns:
            List of branch names
        """
        return self._branch_ops.get_local_branches(repo_path)

    def get_current_branch(self, repo_path: Path) -> str | None:
        """Get the current branch name.

        Args:
            repo_path: Repository path

        Returns:
            Current branch name or None if not on a branch
        """
        return self._branch_ops.get_current_branch(repo_path)

    def get_branch_sha(self, repo_path: Path, branch: str) -> str | None:
        """Get the commit SHA for a branch.

        Args:
            repo_path: Repository path
            branch: Branch name

        Returns:
            Commit SHA or None if branch doesn't exist
        """
        return self._branch_ops.get_branch_sha(repo_path, branch)

    def is_ancestor(self, repo_path: Path, ancestor_sha: str, descendant_ref: str) -> bool:
        """Check if a commit is an ancestor of another ref.

        Args:
            repo_path: Repository path
            ancestor_sha: The potential ancestor commit SHA
            descendant_ref: The descendant ref (branch name or SHA)

        Returns:
            True if ancestor_sha is an ancestor of descendant_ref
        """
        return self._branch_ops.is_ancestor(repo_path, ancestor_sha, descendant_ref)
