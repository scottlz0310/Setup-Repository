"""Tests for GitHub API client."""

from unittest.mock import MagicMock, patch

import pytest

from setup_repo.core.github import AsyncGitHubClient, GitHubClient


class TestGitHubClient:
    """Tests for GitHubClient class."""

    def test_client_creation(self) -> None:
        """Test client creation with token."""
        client = GitHubClient(token="test_token")
        assert client.token == "test_token"
        assert client.verify_ssl is True

    def test_client_creation_without_token(self) -> None:
        """Test client creation without token."""
        client = GitHubClient()
        assert client.token is None

    def test_client_ssl_verify_disabled(self) -> None:
        """Test client with SSL verification disabled."""
        client = GitHubClient(verify_ssl=False)
        assert client.verify_ssl is False

    def test_get_headers_with_token(self) -> None:
        """Test headers include authorization when token is provided."""
        client = GitHubClient(token="test_token")
        headers = client._get_headers()

        assert headers["Authorization"] == "Bearer test_token"
        assert headers["Accept"] == "application/vnd.github+json"

    def test_get_headers_without_token(self) -> None:
        """Test headers without authorization when no token."""
        client = GitHubClient()
        headers = client._get_headers()

        assert "Authorization" not in headers
        assert headers["Accept"] == "application/vnd.github+json"

    def test_context_manager(self) -> None:
        """Test context manager protocol."""
        with GitHubClient(token="test") as client:
            assert client._client is None  # Not created until first use

        # After exit, client should be closed (None)
        assert client._client is None

    def test_parse_repositories(self) -> None:
        """Test parsing repository data."""
        client = GitHubClient()
        data = [
            {
                "name": "repo1",
                "full_name": "user/repo1",
                "clone_url": "https://github.com/user/repo1.git",
                "ssh_url": "git@github.com:user/repo1.git",
                "default_branch": "main",
                "private": False,
                "archived": False,
                "fork": False,
            },
            {
                "name": "repo2",
                "full_name": "user/repo2",
                "clone_url": "https://github.com/user/repo2.git",
                "ssh_url": "git@github.com:user/repo2.git",
            },
        ]

        repos = client._parse_repositories(data)

        assert len(repos) == 2
        assert repos[0].name == "repo1"
        assert repos[1].name == "repo2"
        assert repos[1].default_branch == "main"  # Default value

    def test_parse_repositories_with_invalid_data(self) -> None:
        """Test parsing handles invalid data gracefully."""
        client = GitHubClient()
        data = [
            {
                "name": "valid-repo",
                "full_name": "user/valid-repo",
                "clone_url": "https://github.com/user/valid-repo.git",
                "ssh_url": "git@github.com:user/valid-repo.git",
            },
            {
                # Missing required fields
                "name": "invalid-repo",
            },
        ]

        repos = client._parse_repositories(data)

        # Should only parse valid repos
        assert len(repos) == 1
        assert repos[0].name == "valid-repo"

    @patch("httpx.Client.get")
    def test_get_repositories(self, mock_get: MagicMock) -> None:
        """Test fetching repositories."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "name": "repo1",
                "full_name": "user/repo1",
                "clone_url": "https://github.com/user/repo1.git",
                "ssh_url": "git@github.com:user/repo1.git",
            }
        ]
        mock_response.raise_for_status = MagicMock()

        # First call returns data, second returns empty (end of pagination)
        mock_get.side_effect = [mock_response, MagicMock(json=lambda: [])]

        with GitHubClient(token="test") as client:
            repos = client.get_repositories("user")

        assert len(repos) == 1
        assert repos[0].name == "repo1"


class TestAsyncGitHubClient:
    """Tests for AsyncGitHubClient class."""

    def test_async_client_creation(self) -> None:
        """Test async client creation."""
        client = AsyncGitHubClient(token="test_token")
        assert client.token == "test_token"
        assert client.verify_ssl is True

    def test_async_get_headers_with_token(self) -> None:
        """Test async client headers with token."""
        client = AsyncGitHubClient(token="test_token")
        headers = client._get_headers()

        assert headers["Authorization"] == "Bearer test_token"

    @pytest.mark.anyio
    async def test_async_context_manager(self) -> None:
        """Test async context manager protocol."""
        async with AsyncGitHubClient(token="test") as client:
            assert client._client is None

        assert client._client is None

    @pytest.mark.anyio
    async def test_async_close(self) -> None:
        """Test async client close."""
        client = AsyncGitHubClient()
        # Force client creation
        _ = client.client
        assert client._client is not None

        await client.close()
        assert client._client is None
