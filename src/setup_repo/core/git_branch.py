"""Git branch operations."""

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from setup_repo.utils.logging import get_logger

if TYPE_CHECKING:
    from setup_repo.core.git_operations import BasicGitOperations

log = get_logger(__name__)


class GitBranchOperations:
    """Git branch management operations."""

    def __init__(self, runner: "BasicGitOperations") -> None:
        """Initialize branch operations.

        Args:
            runner: Git command runner
        """
        self.runner = runner

    def get_merged_branches(self, repo_path: Path, base_branch: str = "main") -> list[str]:
        """Get merged branches.

        Args:
            repo_path: Repository path
            base_branch: Base branch to compare against

        Returns:
            List of merged branch names
        """
        try:
            result = self.runner.run(
                ["branch", "--merged", base_branch],
                cwd=repo_path,
            )
            branches: list[str] = []
            for line in result.stdout.strip().split("\n"):
                branch = line.strip().lstrip("* ")
                if branch and branch != base_branch:
                    branches.append(branch)
            return branches
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return []

    def delete_branch(self, repo_path: Path, branch: str, force: bool = False) -> bool:
        """Delete a local branch.

        Args:
            repo_path: Repository path
            branch: Branch name to delete
            force: Use -D (force delete) instead of -d

        Returns:
            True if successful
        """
        flag = "-D" if force else "-d"
        try:
            self.runner.run(["branch", flag, branch], cwd=repo_path)
            log.info("branch_deleted", branch=branch, force=force)
            return True
        except subprocess.CalledProcessError as e:
            log.warning("branch_delete_failed", branch=branch, error=e.stderr)
            return False
        except subprocess.TimeoutExpired:
            log.warning("branch_delete_timeout", branch=branch)
            return False

    def get_local_branches(self, repo_path: Path) -> list[str]:
        """Get all local branches.

        Args:
            repo_path: Repository path

        Returns:
            List of branch names
        """
        try:
            result = self.runner.run(["branch", "--format=%(refname:short)"], cwd=repo_path)
            branches: list[str] = []
            for line in result.stdout.strip().split("\n"):
                branch = line.strip()
                if branch:
                    branches.append(branch)
            return branches
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return []

    def get_current_branch(self, repo_path: Path) -> str | None:
        """Get the current branch name.

        Args:
            repo_path: Repository path

        Returns:
            Current branch name or None if not on a branch
        """
        try:
            result = self.runner.run(["branch", "--show-current"], cwd=repo_path, check=False)
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return None

    def get_branch_sha(self, repo_path: Path, branch: str) -> str | None:
        """Get the commit SHA for a branch.

        Args:
            repo_path: Repository path
            branch: Branch name

        Returns:
            Commit SHA or None if branch doesn't exist
        """
        try:
            result = self.runner.run(["rev-parse", branch], cwd=repo_path, check=False)
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return None

    def is_ancestor(self, repo_path: Path, ancestor_sha: str, descendant_ref: str) -> bool:
        """Check if a commit is an ancestor of another ref.

        Args:
            repo_path: Repository path
            ancestor_sha: The potential ancestor commit SHA
            descendant_ref: The descendant ref (branch name or SHA)

        Returns:
            True if ancestor_sha is an ancestor of descendant_ref
        """
        try:
            # git merge-base --is-ancestor returns 0 if true, 1 if false
            result = self.runner.run(
                ["merge-base", "--is-ancestor", ancestor_sha, descendant_ref],
                cwd=repo_path,
                check=False,
            )
            return result.returncode == 0
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return False
