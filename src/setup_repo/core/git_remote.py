"""Git remote operations and URL parsing."""

import re
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from setup_repo.core.git_operations import BasicGitOperations


class GitRemoteOperations:
    """Git remote management operations."""

    def __init__(self, runner: "BasicGitOperations") -> None:
        """Initialize remote operations.

        Args:
            runner: Git command runner
        """
        self.runner = runner

    def get_remote_url(self, repo_path: Path) -> str | None:
        """Get the remote origin URL.

        Args:
            repo_path: Repository path

        Returns:
            Remote URL or None if not found
        """
        try:
            result = self.runner.run(
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
        # Handle SSH URLs: git@github.com:owner/repo.git
        ssh_pattern = r"git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$"
        # Handle HTTPS URLs: https://github.com/owner/repo.git
        https_pattern = r"https://github\.com/([^/]+)/([^/]+?)(?:\.git)?$"

        for pattern in [ssh_pattern, https_pattern]:
            if match := re.match(pattern, remote_url):
                owner, repo = match.groups()
                return (owner, repo)

        return None
