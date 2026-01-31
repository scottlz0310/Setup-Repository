"""Basic Git operations (clone, pull, fetch)."""

import subprocess
from pathlib import Path

from setup_repo.models.result import ProcessResult, ResultStatus
from setup_repo.utils.logging import get_logger, log_context

log = get_logger(__name__)


class BasicGitOperations:
    """Basic Git command operations."""

    def __init__(
        self,
        auto_prune: bool = True,
        auto_stash: bool = False,
        ssl_no_verify: bool = False,
    ) -> None:
        """Initialize basic Git operations.

        Args:
            auto_prune: Run fetch --prune automatically
            auto_stash: Stash changes before pull and pop after
            ssl_no_verify: Skip SSL verification
        """
        self.auto_prune = auto_prune
        self.auto_stash = auto_stash
        self.ssl_no_verify = ssl_no_verify

    def get_env(self) -> dict[str, str] | None:
        """Get environment variables for git commands."""
        if self.ssl_no_verify:
            import os

            env = os.environ.copy()
            env["GIT_SSL_NO_VERIFY"] = "1"
            return env
        return None

    def run(
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
            env=self.get_env(),
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
            self.run(args)
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
            self.run(["fetch", "--prune"], cwd=repo_path)
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
            if self.auto_stash and self.has_changes(repo_path):
                try:
                    self.run(["stash"], cwd=repo_path)
                    stashed = True
                    log.debug("stashed")
                except subprocess.CalledProcessError as e:
                    log.debug("stash_failed", error=e.stderr)

            try:
                self.run(["pull", "--ff-only"], cwd=repo_path)
                log.info("pulled")

                if stashed:
                    self.run(["stash", "pop"], cwd=repo_path, check=False)
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

    def has_changes(self, repo_path: Path) -> bool:
        """Check if repository has uncommitted changes.

        Args:
            repo_path: Repository path

        Returns:
            True if there are changes
        """
        try:
            result = self.run(["status", "--porcelain"], cwd=repo_path, check=False)
            return bool(result.stdout.strip())
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return False
