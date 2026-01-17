"""GitHub API client using httpx."""

from typing import Any

import httpx
from pydantic import ValidationError

from setup_repo.models.repository import Repository
from setup_repo.utils.logging import get_logger

log = get_logger(__name__)


class GitHubClient:
    """GitHub API client (synchronous)."""

    BASE_URL = "https://api.github.com"

    def __init__(
        self,
        token: str | None = None,
        verify_ssl: bool = True,
    ) -> None:
        """Initialize the GitHub client.

        Args:
            token: GitHub personal access token
            verify_ssl: Whether to verify SSL certificates
        """
        self.token = token
        self.verify_ssl = verify_ssl
        self._client: httpx.Client | None = None

    def _get_headers(self) -> dict[str, str]:
        """Get common request headers."""
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    @property
    def client(self) -> httpx.Client:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.BASE_URL,
                headers=self._get_headers(),
                timeout=30.0,
                verify=self.verify_ssl,
            )
        return self._client

    def get_repositories(self, owner: str) -> list[Repository]:
        """Get repositories for a user.

        Args:
            owner: GitHub username or organization

        Returns:
            List of Repository objects
        """
        repos: list[Repository] = []
        page = 1

        while True:
            response = self.client.get(
                f"/users/{owner}/repos",
                params={"page": page, "per_page": 100},
            )
            response.raise_for_status()

            data = response.json()
            if not data:
                break

            repos.extend(self._parse_repositories(data))
            page += 1

        log.info("fetched_repositories", owner=owner, count=len(repos))
        return repos

    def _parse_repositories(self, data: list[dict[str, Any]]) -> list[Repository]:
        """Parse API response into Repository objects.

        Args:
            data: List of repository data from API

        Returns:
            List of Repository objects
        """
        repos: list[Repository] = []
        for item in data:
            try:
                repo = Repository(
                    name=item["name"],
                    full_name=item["full_name"],
                    clone_url=item["clone_url"],
                    ssh_url=item["ssh_url"],
                    default_branch=item.get("default_branch", "main"),
                    private=item.get("private", False),
                    archived=item.get("archived", False),
                    fork=item.get("fork", False),
                    pushed_at=item.get("pushed_at"),
                )
                repos.append(repo)
            except (ValidationError, KeyError) as e:
                log.warning("invalid_repo_data", repo=item.get("name"), error=str(e))
        return repos

    def get_merged_pull_requests(self, owner: str, repo: str, base_branch: str = "main") -> dict[str, str]:
        """Get merged pull requests for a repository.

        Args:
            owner: GitHub username or organization
            repo: Repository name
            base_branch: Base branch to check merged PRs against

        Returns:
            Dictionary mapping branch name to merge commit SHA
        """
        merged_prs: dict[str, str] = {}
        page = 1
        # Full repo name to check against PR head.repo
        expected_repo_full_name = f"{owner}/{repo}"

        while True:
            try:
                response = self.client.get(
                    f"/repos/{owner}/{repo}/pulls",
                    params={
                        "state": "closed",
                        "base": base_branch,
                        "page": page,
                        "per_page": 100,
                        "sort": "updated",
                        "direction": "desc",
                    },
                )
                response.raise_for_status()

                data = response.json()
                if not data:
                    break

                for pr in data:
                    # Only include if PR was actually merged (not just closed)
                    if not pr.get("merged_at") or not pr.get("head", {}).get("ref"):
                        continue

                    # Check if PR is from the same repository (not a fork)
                    head_repo = pr.get("head", {}).get("repo")
                    if not head_repo or head_repo.get("full_name") != expected_repo_full_name:
                        continue

                    branch_name = pr["head"]["ref"]
                    merge_commit_sha = pr.get("merge_commit_sha", "")
                    merged_prs[branch_name] = merge_commit_sha

                # Stop if we got less than a full page
                if len(data) < 100:
                    break

                page += 1

            except (httpx.HTTPError, KeyError) as e:
                log.warning("failed_to_fetch_merged_prs", owner=owner, repo=repo, error=str(e))
                break

        log.info("fetched_merged_prs", owner=owner, repo=repo, count=len(merged_prs))
        return merged_prs

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self) -> "GitHubClient":
        """Enter context manager."""
        return self

    def __exit__(self, *args: object) -> None:
        """Exit context manager."""
        self.close()


class AsyncGitHubClient:
    """GitHub API client (asynchronous).

    Use this for large repository fetches or multiple concurrent API calls.
    """

    BASE_URL = "https://api.github.com"

    def __init__(
        self,
        token: str | None = None,
        verify_ssl: bool = True,
    ) -> None:
        """Initialize the async GitHub client.

        Args:
            token: GitHub personal access token
            verify_ssl: Whether to verify SSL certificates
        """
        self.token = token
        self.verify_ssl = verify_ssl
        self._client: httpx.AsyncClient | None = None

    def _get_headers(self) -> dict[str, str]:
        """Get common request headers."""
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create the async HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers=self._get_headers(),
                timeout=30.0,
                verify=self.verify_ssl,
            )
        return self._client

    async def get_repositories(self, owner: str) -> list[Repository]:
        """Get repositories for a user (async).

        Args:
            owner: GitHub username or organization

        Returns:
            List of Repository objects
        """
        repos: list[Repository] = []
        page = 1

        while True:
            response = await self.client.get(
                f"/users/{owner}/repos",
                params={"page": page, "per_page": 100},
            )
            response.raise_for_status()

            data = response.json()
            if not data:
                break

            repos.extend(self._parse_repositories(data))
            page += 1

        log.info("fetched_repositories", owner=owner, count=len(repos))
        return repos

    def _parse_repositories(self, data: list[dict[str, Any]]) -> list[Repository]:
        """Parse API response into Repository objects.

        Args:
            data: List of repository data from API

        Returns:
            List of Repository objects
        """
        repos: list[Repository] = []
        for item in data:
            try:
                repo = Repository(
                    name=item["name"],
                    full_name=item["full_name"],
                    clone_url=item["clone_url"],
                    ssh_url=item["ssh_url"],
                    default_branch=item.get("default_branch", "main"),
                    private=item.get("private", False),
                    archived=item.get("archived", False),
                    fork=item.get("fork", False),
                    pushed_at=item.get("pushed_at"),
                )
                repos.append(repo)
            except (ValidationError, KeyError) as e:
                log.warning("invalid_repo_data", repo=item.get("name"), error=str(e))
        return repos

    async def close(self) -> None:
        """Close the async HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "AsyncGitHubClient":
        """Enter async context manager."""
        return self

    async def __aexit__(self, *args: object) -> None:
        """Exit async context manager."""
        await self.close()
