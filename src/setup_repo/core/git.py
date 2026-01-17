"""Git operations wrapper."""

import subprocess
from pathlib import Path

from setup_repo.models.result import ProcessResult, ResultStatus
from setup_repo.utils.logging import get_logger, log_context

log = get_logger(__name__)


class GitOperations:
    """Git command wrapper."""

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
        self.auto_prune = auto_prune
        self.auto_stash = auto_stash
        self.ssl_no_verify = ssl_no_verify

    def _get_env(self) -> dict[str, str] | None:
        """Get environment variables for git commands."""
        if self.ssl_no_verify:
            import os

            env = os.environ.copy()
            env["GIT_SSL_NO_VERIFY"] = "1"
            return env
        return None

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
        cmd = ["git", *args]
        log.debug("git_command", cmd=" ".join(cmd), cwd=str(cwd) if cwd else None)

        return subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=check,
            env=self._get_env(),
            timeout=300,  # 5 minutes timeout
        )

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
        args = ["clone", "--depth", "1"]
        if branch:
            args.extend(["--branch", branch])
        args.extend([url, str(dest)])

        try:
            self._run(args)
            log.info("cloned", url=url, dest=str(dest))
            return ProcessResult(
                repo_name=dest.name,
                status=ResultStatus.SUCCESS,
                message="Cloned successfully",
            )
        except subprocess.CalledProcessError as e:
            log.error("clone_failed", url=url, error=e.stderr)
            return ProcessResult(
                repo_name=dest.name,
                status=ResultStatus.FAILED,
                error=e.stderr,
            )
        except subprocess.TimeoutExpired:
            log.error("clone_timeout", url=url)
            return ProcessResult(
                repo_name=dest.name,
                status=ResultStatus.FAILED,
                error="Clone timed out",
            )

    def fetch_and_prune(self, repo_path: Path) -> bool:
        """Run fetch --prune.

        Args:
            repo_path: Repository path

        Returns:
            True if successful
        """
        if not self.auto_prune:
            return True

        try:
            self._run(["fetch", "--prune"], cwd=repo_path)
            log.debug("fetched_and_pruned", repo=repo_path.name)
            return True
        except subprocess.CalledProcessError as e:
            log.warning("fetch_prune_failed", repo=repo_path.name, error=e.stderr)
            return False
        except subprocess.TimeoutExpired:
            log.warning("fetch_prune_timeout", repo=repo_path.name)
            return False

    def pull(self, repo_path: Path) -> ProcessResult:
        """Pull a repository.

        Args:
            repo_path: Repository path

        Returns:
            ProcessResult
        """
        with log_context(repo=repo_path.name):
            # First fetch --prune
            self.fetch_and_prune(repo_path)

            # Stash if needed
            stashed = False
            if self.auto_stash and self._has_changes(repo_path):
                try:
                    self._run(["stash"], cwd=repo_path)
                    stashed = True
                    log.debug("stashed")
                except subprocess.CalledProcessError as e:
                    log.debug("stash_failed", error=e.stderr)

            try:
                self._run(["pull", "--ff-only"], cwd=repo_path)
                log.info("pulled")

                if stashed:
                    self._run(["stash", "pop"], cwd=repo_path, check=False)
                    log.debug("stash_popped")

                return ProcessResult(
                    repo_name=repo_path.name,
                    status=ResultStatus.SUCCESS,
                    message="Pulled successfully",
                )
            except subprocess.CalledProcessError as e:
                log.error("pull_failed", error=e.stderr)
                return ProcessResult(
                    repo_name=repo_path.name,
                    status=ResultStatus.FAILED,
                    error=e.stderr,
                )
            except subprocess.TimeoutExpired:
                log.error("pull_timeout")
                return ProcessResult(
                    repo_name=repo_path.name,
                    status=ResultStatus.FAILED,
                    error="Pull timed out",
                )

    def _has_changes(self, repo_path: Path) -> bool:
        """Check if repository has uncommitted changes.

        Args:
            repo_path: Repository path

        Returns:
            True if there are changes
        """
        try:
            result = self._run(["status", "--porcelain"], cwd=repo_path, check=False)
            return bool(result.stdout.strip())
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return False

    def get_merged_branches(self, repo_path: Path, base_branch: str = "main") -> list[str]:
        """Get merged branches.

        Args:
            repo_path: Repository path
            base_branch: Base branch to compare against

        Returns:
            List of merged branch names
        """
        try:
            result = self._run(
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

    def delete_branch(self, repo_path: Path, branch: str) -> bool:
        """Delete a local branch.

        Args:
            repo_path: Repository path
            branch: Branch name to delete

        Returns:
            True if successful
        """
        try:
            self._run(["branch", "-d", branch], cwd=repo_path)
            log.info("branch_deleted", branch=branch)
            return True
        except subprocess.CalledProcessError as e:
            log.warning("branch_delete_failed", branch=branch, error=e.stderr)
            return False
        except subprocess.TimeoutExpired:
            log.warning("branch_delete_timeout", branch=branch)
            return False

    def get_remote_url(self, repo_path: Path) -> str | None:
        """Get the remote origin URL.

        Args:
            repo_path: Repository path

        Returns:
            Remote URL or None if not found
        """
        try:
            result = self._run(
                ["remote", "get-url", "origin"],
                cwd=repo_path,
                check=False,
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return None

    def parse_github_repo(self, remote_url: str) -> tuple[str, str] | None:
        """Parse GitHub owner and repo name from remote URL.

        Args:
            remote_url: Git remote URL (HTTPS or SSH)

        Returns:
            Tuple of (owner, repo) or None if not a GitHub URL
        """
        import re

        # Handle SSH URLs: git@github.com:owner/repo.git
        ssh_pattern = r"git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$"
        # Handle HTTPS URLs: https://github.com/owner/repo.git
        https_pattern = r"https://github\.com/([^/]+)/([^/]+?)(?:\.git)?$"

        for pattern in [ssh_pattern, https_pattern]:
            if match := re.match(pattern, remote_url):
                owner, repo = match.groups()
                return (owner, repo)

        return None

    def get_local_branches(self, repo_path: Path) -> list[str]:
        """Get all local branches (excluding current and base branch).

        Args:
            repo_path: Repository path

        Returns:
            List of branch names
        """
        try:
            result = self._run(["branch", "--format=%(refname:short)"], cwd=repo_path)
            branches: list[str] = []
            for line in result.stdout.strip().split("\n"):
                branch = line.strip()
                if branch:
                    branches.append(branch)
            return branches
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return []
